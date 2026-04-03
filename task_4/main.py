"""
Задача 4 — точка запуска.

Запуск:
    python -m task_4.main
    # или из корня проекта:
    python task_4/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

# Добавляем корень проекта в path, чтобы работал импорт task_4.xxx
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel, Field

from display import print_models
from introspection import introspect_models


# ---------------------------------------------------------------------------
# Демонстрационные модели (имитируют реальные схемы медсистемы)
# ---------------------------------------------------------------------------

class UserSchema(BaseModel):
    id: UUID
    phone: int
    birthday: Optional[str] = None
    profile_data: Optional[dict] = None


class ReceptionSchema(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    start_datetime: str
    notes: Optional[str] = None
    duration_minutes: int = Field(default=30)


class DoctorSchema(BaseModel):
    id: int
    full_name: str
    specialization: str
    is_active: bool = True
    rating: Optional[float] = None


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def main() -> None:
    models = [UserSchema, ReceptionSchema, DoctorSchema]
    metas = introspect_models(models)
    print_models(metas)


if __name__ == "__main__":
    main()
