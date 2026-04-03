# Задача 6 — Пример кода (codestyle)

## Что реализовано

Небольшой модуль `domain.py` — бизнес-логика записи пациента на приём к врачу.

Файл намеренно **не зависит** от FastAPI, SQLAlchemy или БД — только Python + Pydantic.
Это демонстрирует принцип разделения: бизнес-логика не должна знать о транспорте и хранилище.

---

## Архитектурные слои в одном файле

```
ReceptionCreateDTO      ← Pydantic v2: валидация входных данных
ReceptionUpdateDTO      ← Pydantic v2: частичное обновление

TimeSlot                ← dataclass(frozen=True): иммутабельный слот
ScheduleDay             ← dataclass: расписание дня, метод free_slots()
Reception               ← dataclass: приём, фабричный метод create()

find_nearest_slot()     ← чистая функция: поиск слота
group_by_specialization() ← чистая функция: агрегация
validate_batch()        ← чистая функция: массовая валидация
upcoming_patient_phones() ← генератор с дедупликацией

ReceptionService        ← сервисный слой: оркестрация
```

---

## Ключевые приёмы

### `dataclass(frozen=True)` — иммутабельность
```python
@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime
    # После создания поля нельзя изменить — как tuple, но с атрибутами
```

### `dataclasses.replace()` — функциональное обновление
```python
def apply_update(self, update: ReceptionUpdateDTO) -> Reception:
    return replace(self, status=update.status or self.status)
    # Создаёт новый объект, не мутирует старый
```

### Walrus operator `:=` в условии
```python
if free := schedule.free_slots(duration_minutes):
    return schedule, free[0]
# Присваивает И проверяет на истинность за один шаг
```

### Генератор с `seen`-set — дедупликация без промежуточного списка
```python
def upcoming_patient_phones(...) -> Iterator[str]:
    seen: set[str] = set()
    for r in receptions:
        if r.patient_phone not in seen:
            seen.add(r.patient_phone)
            yield r.patient_phone
```

### Dict comprehension + `**` распаковка
```python
by_status = {status.value: count for status in ReceptionStatus}
return {"total": len(receptions), **by_status, "rate": ...}
```

### `StrEnum` — строковые константы с типизацией
```python
class Specialization(StrEnum):
    THERAPIST = "therapist"
# Работает как str: Specialization.THERAPIST == "therapist" → True
# Но проверяется type checker'ом
```
