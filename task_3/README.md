# Задача 3 — Обработка ошибок и антипаттерны

---

## Задача 3.1 — Что плохо в `PatientRepository`

### Исходный код

```python
class PatientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[dict]:
        try:
            stmt = select(PatientORM)
            result = await self.session.execute(stmt)
            return [row._asdict() for row in result.all()]
        except Exception as e:
            raise Exception(str(e))
```

### Проблемы

**1. `row._asdict()` — использование приватного API**
`result.all()` возвращает список `Row`-объектов SQLAlchemy. Вызов `._asdict()` работает, но это *приватный* метод (подчёркивание = «не для внешнего использования»). При обновлении SQLAlchemy поведение может измениться.  
→ Правильно: `result.scalars().all()` возвращает сами ORM-объекты, которые затем можно сериализовать.

**2. `except Exception as e: raise Exception(str(e))` — антипаттерн «проглатывание» исключения**
Это теряет:
- тип оригинального исключения (например, `IntegrityError` → `Exception`)
- traceback (стек вызовов обрезается)
- контекст (`__cause__`, `__traceback__`)  
Такой `try/except` хуже, чем его полное отсутствие.

**3. Возвращается `list[dict]`, а не список ORM-моделей или Pydantic-схем**
Репозиторий — слой доступа к данным. Он должен возвращать доменные объекты, а не сырые словари. Преобразование в dict — задача сервисного слоя или схемы ответа.

**4. Нет пагинации / лимита**
`get_all()` без ограничения может вернуть миллионы строк и положить сервер.

**5. Тип возврата `list[dict]` не несёт информации**
`dict` ничего не говорит о структуре. Это нарушает принцип явных интерфейсов.

---

### Исправленная версия

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models import PatientORM
from app.exceptions import RepositoryError


class PatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[PatientORM]:
        """
        Возвращает список пациентов с пагинацией.
        
        :param limit: максимум строк (защита от случайной выгрузки всей БД)
        :param offset: смещение для пагинации
        :raises RepositoryError: при ошибке на уровне БД
        """
        try:
            stmt = select(PatientORM).limit(limit).offset(offset)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            # Перехватываем только ошибки БД, не прячем traceback
            raise RepositoryError("Failed to fetch patients") from exc
```

---

## Задача 3.2 — Что плохо в эндпоинте `/register`

### Исходный код

```python
@router.post("/register")
async def register_patient(phone: str, name: str):
    async with AsyncSession(engine) as session:
        existing = await session.execute(
            select(UserORM).where(UserORM.phone == phone)
        )
        if existing.scalar_one_or_none():
            return {"error": "Пользователь уже существует"}
        user = UserORM(phone=phone, name=name)
        session.add(user)
        await session.commit()
        return {"id": str(user.id), "phone": phone}
```

### 5+ проблем

**1. Нет валидации входных данных (безопасность + корректность)**
`phone: str` принимает любую строку — пустую, с SQL-спецсимволами, 10000 символов. Нужна Pydantic-схема с валидацией формата телефона.

**2. Race condition — нет защиты от параллельных регистраций**
Между `SELECT` (проверка) и `INSERT` (создание) другой запрос может успеть вставить ту же запись. Решение: `UNIQUE` constraint на `phone` + обработка `IntegrityError`.

**3. Ошибка возвращается как `200 OK` с полем `error`**
HTTP-семантика: ошибки → `4xx`. Здесь нужен `409 Conflict` или `400 Bad Request`. FastAPI позволяет `raise HTTPException(status_code=409, detail="...")`.

**4. Сессия создаётся вручную внутри хендлера (архитектура)**
`AsyncSession(engine)` в хендлере — это нарушение Dependency Injection. Сессия должна инжектироваться через `Depends(get_session)`. Это позволяет тестировать хендлер с мок-сессией.

**5. Нет обработки ошибок БД**
Если `session.commit()` упадёт (сеть, constraint), исключение всплывёт как `500 Internal Server Error` с полным трейсбеком в ответе клиенту.

**6. `phone` как параметр пути, а не тело запроса**
`POST /register` с `phone` и `name` в query string (`?phone=...&name=...`) — нарушение REST. Данные для создания ресурса должны идти в теле запроса (JSON).

---

### Исправленная версия

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import UserORM

router = APIRouter()


class RegisterRequest(BaseModel):
    phone: str
    name: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit() or len(cleaned) < 10:
            raise ValueError("Invalid phone number format")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class RegisterResponse(BaseModel):
    id: str
    phone: str


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_patient(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """Регистрирует нового пациента. Возвращает 409 если телефон занят."""
    user = UserORM(phone=body.phone, name=body.name)
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким телефоном уже существует",
        )
    return RegisterResponse(id=str(user.id), phone=user.phone)
```
