"""
Задача 6 — Пример кода: бизнес-алгоритм назначения приёма.

Демонстрирует:
  - Pydantic v2: валидаторы, DTO, response-схемы
  - dataclass(frozen=True): иммутабельные доменные объекты
  - StrEnum: типобезопасные строковые константы
  - comprehensions и генераторы везде где уместно
  - type hints: везде, включая return types
  - разбивка на слои: схемы -> доменные объекты -> бизнес-логика -> сервис
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Iterator
from uuid import UUID, uuid4

from pydantic import BaseModel, field_validator, model_validator

# ---------------------------------------------------------------------------
# Константы и перечисления
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(r"^\+7\d{10}$")
MAX_NOTES_LENGTH = 500


class Specialization(StrEnum):
    THERAPIST = "therapist"
    SURGEON = "surgeon"
    NEUROLOGIST = "neurologist"
    CARDIOLOGIST = "cardiologist"


class ReceptionStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# ---------------------------------------------------------------------------
# Входные схемы (Pydantic v2)
# ---------------------------------------------------------------------------

class ReceptionCreateDTO(BaseModel):
    """Данные для записи на приём, поступающие от клиента."""

    patient_phone: str
    doctor_id: int
    specialization: Specialization
    preferred_date: date
    notes: str = ""

    @field_validator("patient_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = v.strip().replace(" ", "").replace("-", "")
        if not PHONE_RE.match(normalized):
            raise ValueError(f"Phone must match +7XXXXXXXXXX, got: {v!r}")
        return normalized

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: str) -> str:
        return v.strip()[:MAX_NOTES_LENGTH]

    @model_validator(mode="after")
    def preferred_date_must_be_future(self) -> ReceptionCreateDTO:
        if self.preferred_date <= date.today():
            raise ValueError("preferred_date must be in the future")
        return self


class ReceptionUpdateDTO(BaseModel):
    """Частичное обновление приёма — все поля опциональны."""

    status: ReceptionStatus | None = None
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        return v.strip()[:MAX_NOTES_LENGTH] if v is not None else None


# ---------------------------------------------------------------------------
# Доменные объекты
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeSlot:
    """Временной слот. Иммутабелен — нельзя изменить после создания."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(f"Slot end {self.end} must be after start {self.start}")

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    def overlaps_with(self, other: TimeSlot) -> bool:
        return self.start < other.end and other.start < self.end

    def __str__(self) -> str:
        return f"{self.start:%H:%M}–{self.end:%H:%M}"


@dataclass
class ScheduleDay:
    """Расписание одного врача на один день."""

    doctor_id: int
    day: date
    booked_slots: list[TimeSlot] = field(default_factory=list)

    WORK_START_HOUR: int = 8
    WORK_END_HOUR: int = 20

    def book(self, slot: TimeSlot) -> None:
        if any(slot.overlaps_with(existing) for existing in self.booked_slots):
            raise ValueError(f"Slot {slot} overlaps with existing bookings")
        self.booked_slots.append(slot)

    def free_slots(self, duration_minutes: int = 30) -> list[TimeSlot]:
        """
        Возвращает все свободные слоты нужной длины.
        Движемся по рабочему времени шагом duration_minutes, пропуская занятые.
        """
        work_start = datetime.combine(self.day, datetime.min.time()).replace(
            hour=self.WORK_START_HOUR
        )
        work_end = work_start.replace(hour=self.WORK_END_HOUR)
        step = timedelta(minutes=duration_minutes)

        return [
            TimeSlot(start=cursor, end=cursor + step)
            for cursor in _datetime_range(work_start, work_end - step, step)
            if not any(
                TimeSlot(cursor, cursor + step).overlaps_with(booked)
                for booked in self.booked_slots
            )
        ]


@dataclass
class Reception:
    """Запись на приём — центральный доменный объект."""

    id: UUID
    patient_phone: str
    doctor_id: int
    specialization: Specialization
    slot: TimeSlot
    status: ReceptionStatus = ReceptionStatus.SCHEDULED
    notes: str = ""

    @classmethod
    def create(cls, dto: ReceptionCreateDTO, slot: TimeSlot) -> Reception:
        return cls(
            id=uuid4(),
            patient_phone=dto.patient_phone,
            doctor_id=dto.doctor_id,
            specialization=dto.specialization,
            slot=slot,
            notes=dto.notes,
        )

    def apply_update(self, update: ReceptionUpdateDTO) -> Reception:
        """Возвращает новый объект с применёнными изменениями (не мутирует self)."""
        return replace(
            self,
            status=update.status if update.status is not None else self.status,
            notes=update.notes if update.notes is not None else self.notes,
        )


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _datetime_range(
    start: datetime,
    stop: datetime,
    step: timedelta,
) -> Iterator[datetime]:
    """Генератор временных меток от start до stop с шагом step."""
    current = start
    while current <= stop:
        yield current
        current += step


# ---------------------------------------------------------------------------
# Бизнес-логика: чистые функции без сайд-эффектов
# ---------------------------------------------------------------------------

def find_nearest_slot(
    schedules: list[ScheduleDay],
    preferred_date: date,
    duration_minutes: int = 30,
) -> tuple[ScheduleDay, TimeSlot] | None:
    """Ищет ближайший свободный слот начиная с preferred_date."""
    for schedule in sorted(schedules, key=lambda s: s.day):
        if schedule.day < preferred_date:
            continue
        if free := schedule.free_slots(duration_minutes):
            return schedule, free[0]
    return None


def group_by_specialization(
    receptions: list[Reception],
) -> dict[Specialization, list[Reception]]:
    """Группирует приёмы по специализации. Пустые группы не включаются."""
    return {
        spec: [r for r in receptions if r.specialization == spec]
        for spec in Specialization
        if any(r.specialization == spec for r in receptions)
    }


def validate_batch(
    raw_items: list[dict],
) -> tuple[list[ReceptionCreateDTO], list[tuple[int, str]]]:
    """
    Валидирует пачку сырых данных (например, из CSV-импорта).
    :returns: (валидные_объекты, [(индекс, сообщение_ошибки)])
    """
    valid: list[ReceptionCreateDTO] = []
    errors: list[tuple[int, str]] = []

    for idx, raw in enumerate(raw_items):
        try:
            valid.append(ReceptionCreateDTO.model_validate(raw))
        except Exception as exc:  # noqa: BLE001
            errors.append((idx, str(exc)))

    return valid, errors


def upcoming_patient_phones(
    receptions: list[Reception],
    from_date: date,
) -> Iterator[str]:
    """
    Генератор: уникальные телефоны пациентов с будущими запланированными приёмами.
    seen-set внутри генератора — дедупликация без промежуточного списка.
    """
    seen: set[str] = set()
    for r in receptions:
        if (
            r.slot.start.date() >= from_date
            and r.status == ReceptionStatus.SCHEDULED
            and r.patient_phone not in seen
        ):
            seen.add(r.patient_phone)
            yield r.patient_phone


def cancellation_rate(receptions: list[Reception]) -> float:
    """Доля отменённых приёмов [0.0, 1.0]. Возвращает 0.0 для пустого списка."""
    if not receptions:
        return 0.0
    return sum(1 for r in receptions if r.status == ReceptionStatus.CANCELLED) / len(receptions)


def receptions_summary(receptions: list[Reception]) -> dict[str, int | float]:
    """Агрегированная статистика по списку приёмов."""
    by_status = {
        status.value: sum(1 for r in receptions if r.status == status)
        for status in ReceptionStatus
    }
    return {
        "total": len(receptions),
        **by_status,
        "cancellation_rate_pct": round(cancellation_rate(receptions) * 100, 1),
    }


# ---------------------------------------------------------------------------
# Сервисный слой
# ---------------------------------------------------------------------------

class ReceptionService:
    """
    Оркестрирует бизнес-логику записи на приём.
    В реальном приложении — инжекция репозитория + транзакции.
    Здесь in-memory хранилище для демонстрации.
    """

    def __init__(self) -> None:
        self._receptions: dict[UUID, Reception] = {}
        self._schedules: dict[int, list[ScheduleDay]] = {}

    def add_schedule(self, schedule: ScheduleDay) -> None:
        self._schedules.setdefault(schedule.doctor_id, []).append(schedule)

    def book(self, dto: ReceptionCreateDTO) -> Reception:
        """Создаёт приём на ближайший свободный слот. Raises ValueError если нет слотов."""
        schedules = self._schedules.get(dto.doctor_id, [])
        result = find_nearest_slot(schedules, dto.preferred_date)
        if result is None:
            raise ValueError(
                f"No available slots for doctor {dto.doctor_id} "
                f"from {dto.preferred_date}"
            )
        schedule_day, slot = result
        schedule_day.book(slot)
        reception = Reception.create(dto, slot)
        self._receptions[reception.id] = reception
        return reception

    def update(self, reception_id: UUID, update: ReceptionUpdateDTO) -> Reception:
        reception = self._receptions[reception_id]
        updated = reception.apply_update(update)
        self._receptions[reception_id] = updated
        return updated

    def get_by_status(self, status: ReceptionStatus) -> list[Reception]:
        return [r for r in self._receptions.values() if r.status == status]

    def summary(self) -> dict[str, int | float]:
        return receptions_summary(list(self._receptions.values()))
