"""
Задача 4 — Слой получения данных (интроспекция Pydantic v2 моделей).

Этот модуль отвечает ТОЛЬКО за извлечение метаданных полей.
Никакого форматирования здесь нет — только чистые данные.
"""

from __future__ import annotations

import inspect
import types
import typing
from dataclasses import dataclass, field
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

_MISSING = object()  # sentinel для «нет дефолта»


@dataclass(frozen=True)
class FieldMeta:
    """Структурированные метаданные одного поля модели."""

    name: str
    type_repr: str          # человекочитаемое представление типа
    has_default: bool
    default: Any = field(default=_MISSING, compare=False)

    @property
    def default_display(self) -> str:
        """Строка для отображения в таблице."""
        if not self.has_default:
            return "—"
        if self.default is None:
            return "None"
        return repr(self.default)


@dataclass(frozen=True)
class ModelMeta:
    """Метаданные одной Pydantic-модели."""

    model_name: str
    fields: list[FieldMeta]


def _type_to_str(annotation: Any) -> str:
    """
    Рекурсивно превращает тип Python в читаемую строку.

    Примеры:
        str                 → "str"
        Optional[str]       → "Optional[str]"
        list[int]           → "list[int]"
        dict[str, Any]      → "dict[str, Any]"
        UUID                → "UUID"
    """
    if annotation is type(None):
        return "None"

    # Для типов вида Optional[X] (= Union[X, None]) и других Union
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is typing.Union or (
        # Python 3.10+ позволяет X | Y, что тоже является Union
        isinstance(origin, types.UnionType) if hasattr(types, "UnionType") else False
    ):
        # Если Union[X, None] → Optional[X]
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return f"Optional[{_type_to_str(non_none[0])}]"
        return f"Union[{', '.join(_type_to_str(a) for a in args)}]"

    if origin is not None:
        # Generic types: list[int], dict[str, Any], etc.
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            args_str = ", ".join(_type_to_str(a) for a in args)
            return f"{origin_name}[{args_str}]"
        return origin_name

    # Простые типы
    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation)


def _extract_field_meta(name: str, field_info: FieldInfo, annotation: Any) -> FieldMeta:
    """Извлекает FieldMeta из одного поля Pydantic v2."""
    type_repr = _type_to_str(annotation)

    # Pydantic v2: default хранится в field_info.default
    # PydanticUndefined означает «нет дефолта» (аналог нашего _MISSING)
    from pydantic_core import PydanticUndefinedType

    if isinstance(field_info.default, PydanticUndefinedType):
        # Проверяем default_factory
        if field_info.default_factory is not None:  # type: ignore[misc]
            return FieldMeta(
                name=name,
                type_repr=type_repr,
                has_default=True,
                default=f"<factory: {field_info.default_factory.__name__}>",
            )
        return FieldMeta(name=name, type_repr=type_repr, has_default=False)

    return FieldMeta(
        name=name,
        type_repr=type_repr,
        has_default=True,
        default=field_info.default,
    )


def introspect_model(model_cls: type[BaseModel]) -> ModelMeta:
    """
    Интроспектирует одну Pydantic v2 модель.

    :param model_cls: класс, наследующий BaseModel
    :returns: ModelMeta с именем модели и списком FieldMeta
    :raises TypeError: если передан не BaseModel
    """
    if not (inspect.isclass(model_cls) and issubclass(model_cls, BaseModel)):
        raise TypeError(f"{model_cls!r} is not a Pydantic BaseModel subclass")

    fields: list[FieldMeta] = []
    # model_fields — публичный API Pydantic v2 (dict[str, FieldInfo])
    for field_name, field_info in model_cls.model_fields.items():
        # Аннотации берём из __annotations__ через model_fields напрямую
        annotation = model_cls.__annotations__.get(field_name, Any)
        fields.append(_extract_field_meta(field_name, field_info, annotation))

    return ModelMeta(model_name=model_cls.__name__, fields=fields)


def introspect_models(model_classes: list[type[BaseModel]]) -> list[ModelMeta]:
    """
    Интроспектирует список Pydantic-моделей.

    :param model_classes: список классов BaseModel
    :returns: список ModelMeta
    """
    return [introspect_model(cls) for cls in model_classes]
