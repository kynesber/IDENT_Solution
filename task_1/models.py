"""
Задача 1 — SQLAlchemy ORM-модели для трёх вариантов проектирования БД.
Вариант 3 (Shared Primary Key / Party Model) — рекомендуемый.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Вариант 1 — Две независимые таблицы
# ---------------------------------------------------------------------------

class PatientV1(Base):
    """Пациент — полностью самостоятельная сущность."""

    __tablename__ = "v1_patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))
    card_number = Column(String(50), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<PatientV1 id={self.id} name={self.full_name!r}>"


class EmployeeV1(Base):
    """Сотрудник — полностью самостоятельная сущность."""

    __tablename__ = "v1_employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))
    inn = Column(String(12), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<EmployeeV1 id={self.id} name={self.full_name!r}>"


# ---------------------------------------------------------------------------
# Вариант 2 — Single Table (одна таблица Persons)
# ---------------------------------------------------------------------------

class PersonV2(Base):
    """
    Единая таблица для всех людей.
    NULL-поля означают, что роль не активна для данной записи.
    """

    __tablename__ = "v2_persons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))

    # Поля пациента (NULL если не пациент)
    card_number = Column(String(50), unique=True, nullable=True)
    is_patient = Column(Boolean, default=False, nullable=False)

    # Поля сотрудника (NULL если не сотрудник)
    inn = Column(String(12), unique=True, nullable=True)
    is_employee = Column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        roles = []
        if self.is_patient:
            roles.append("patient")
        if self.is_employee:
            roles.append("employee")
        return f"<PersonV2 id={self.id} roles={roles}>"


# ---------------------------------------------------------------------------
# Вариант 3 — Shared Primary Key (рекомендуемый)
# ---------------------------------------------------------------------------

class Person(Base):
    """
    Общая «корневая» сущность — хранит атрибуты, общие для всех ролей.
    Роли подключаются через отдельные таблицы с FK = PK.
    """

    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20))

    # Связи 1:0..1 — uselist=False означает «не список, а один объект или None»
    patient_info: relationship = relationship(
        "Patient",
        back_populates="person",
        uselist=False,
        cascade="all, delete-orphan",
    )
    employee_info: relationship = relationship(
        "Employee",
        back_populates="person",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def is_patient(self) -> bool:
        return self.patient_info is not None

    @property
    def is_employee(self) -> bool:
        return self.employee_info is not None

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.full_name!r}>"


class Patient(Base):
    """
    Роль «пациент» — дополняет Person специфичными атрибутами.
    person_id одновременно PK и FK → связь 1:1 без лишнего суррогатного ключа.
    """

    __tablename__ = "patients"

    person_id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    card_number = Column(String(50), unique=True, nullable=False)

    person: relationship = relationship("Person", back_populates="patient_info")

    def __repr__(self) -> str:
        return f"<Patient person_id={self.person_id} card={self.card_number!r}>"


class Employee(Base):
    """
    Роль «сотрудник» — дополняет Person специфичными атрибутами.
    """

    __tablename__ = "employees"

    person_id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    inn = Column(String(12), unique=True, nullable=False)

    person: relationship = relationship("Person", back_populates="employee_info")

    def __repr__(self) -> str:
        return f"<Employee person_id={self.person_id} inn={self.inn!r}>"
