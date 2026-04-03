# Задача 1 — Проектирование БД

## Условие

Есть **пациенты** (ФИО, дата рождения, телефон, номер медкарты) и **сотрудники** (ФИО, дата рождения, телефон, ИНН).
Любой пациент может быть сотрудником и наоборот.

---

## Вариант 1 — Две независимые таблицы (наивный подход)

### Схема

```
┌──────────────────────┐     ┌──────────────────────┐
│       Patients       │     │      Employees       │
├──────────────────────┤     ├──────────────────────┤
│ id          INT PK   │     │ id          INT PK   │
│ full_name   VARCHAR  │     │ full_name   VARCHAR  │
│ birth_date  DATE     │     │ birth_date  DATE     │
│ phone       VARCHAR  │     │ phone       VARCHAR  │
│ card_number VARCHAR  │     │ inn         VARCHAR  │
└──────────────────────┘     └──────────────────────┘
```

### SQLAlchemy ORM

```python
class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))
    card_number = Column(String(50), unique=True)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))
    inn = Column(String(12), unique=True)
```

---

## Вариант 2 — Single Table (одна общая таблица Persons)

### Схема

```
┌─────────────────────────────┐
│           Persons           │
├─────────────────────────────┤
│ id          INT PK          │
│ full_name   VARCHAR         │
│ birth_date  DATE            │
│ phone       VARCHAR         │
│ card_number VARCHAR NULL    │  ← только для пациентов
│ inn         VARCHAR NULL    │  ← только для сотрудников
│ is_patient  BOOLEAN         │
│ is_employee BOOLEAN         │
└─────────────────────────────┘
```

### SQLAlchemy ORM

```python
class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))
    card_number = Column(String(50), nullable=True, unique=True)
    inn = Column(String(12), nullable=True, unique=True)
    is_patient = Column(Boolean, default=False)
    is_employee = Column(Boolean, default=False)
```

---

## Вариант 3 — Паттерн «Shared Primary Key» / Party Model (рекомендуемый)

Общая таблица `persons` хранит общие атрибуты. Специфичные данные — в отдельных таблицах, связанных FK 1:1.

### Схема

```
┌──────────────────────┐
│        Persons       │
├──────────────────────┤
│ id         INT PK    │
│ full_name  VARCHAR   │
│ birth_date DATE      │
│ phone      VARCHAR   │
└──────┬───────────────┘
       │ 1:0..1              1:0..1
       ├──────────────────────────────────────────┐
       ▼                                          ▼
┌─────────────────────┐              ┌──────────────────────┐
│      Patients       │              │      Employees       │
├─────────────────────┤              ├──────────────────────┤
│ person_id  INT PK FK│              │ person_id  INT PK FK │
│ card_number VARCHAR │              │ inn        VARCHAR   │
└─────────────────────┘              └──────────────────────┘
```

### SQLAlchemy ORM

```python
class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))

    patient_info = relationship("Patient", back_populates="person", uselist=False)
    employee_info = relationship("Employee", back_populates="person", uselist=False)

    @property
    def is_patient(self) -> bool:
        return self.patient_info is not None

    @property
    def is_employee(self) -> bool:
        return self.employee_info is not None


class Patient(Base):
    __tablename__ = "patients"
    person_id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    card_number = Column(String(50), unique=True, nullable=False)

    person = relationship("Person", back_populates="patient_info")


class Employee(Base):
    __tablename__ = "employees"
    person_id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    inn = Column(String(12), unique=True, nullable=False)

    person = relationship("Person", back_populates="employee_info")
```

---

## Сравнительная таблица

| Критерий | Вариант 1 (две таблицы) | Вариант 2 (одна таблица) | Вариант 3 (shared PK) |
|---|---|---|---|
| **Удобство использования** | Сложно: два разных объекта для одного человека, дублирование | Просто: один объект, один запрос | Умеренно: JOIN нужен, но структура понятна |
| **Расширяемость** | Плохо: добавление роли «поставщик» = новая таблица без связи с существующими | Плохо: каждая новая роль добавляет NULL-колонки | Отлично: новая таблица `Suppliers(person_id FK)` — всё чисто |
| **Целостность (FK на приёмы)** | Проблема: FK в `Receptions` на `patients.id` и на `employees.id` — разные сущности | Нормально: один FK на `persons.id` | Отлично: FK на `persons.id`, роль проверяется через JOIN |
| **Производительность** | Плохо: поиск «человека» требует UNION двух таблиц | Отлично: нет JOIN, один индекс на `id` | Хорошо: один JOIN, индексы на PK/FK эффективны |
| **Нормализация / дублирование** | Плохо: ФИО, телефон, дата рождения дублируются | Плохо: NULL в каждой строке для «чужих» атрибутов | Отлично: данные хранятся ровно один раз |

### Вывод

**Вариант 3** — оптимальный выбор для продакшена. Он соответствует принципу DRY, обеспечивает ссылочную целостность, легко расширяется новыми ролями и эффективен при запросах благодаря индексам на PK.
