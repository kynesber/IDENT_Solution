"""
Задача 4 — Слой отображения (форматированный вывод в консоль).

Этот модуль отвечает ТОЛЬКО за форматирование и вывод.
Никакой работы с Pydantic здесь нет — только ModelMeta/FieldMeta.
"""

from __future__ import annotations

from introspection import FieldMeta, ModelMeta

# Минимальная ширина каждой колонки (для красивого вывода)
_COL_FIELD = 17
_COL_TYPE = 19
_COL_DEFAULT = 9


def _col_widths(fields: list[FieldMeta]) -> tuple[int, int, int]:
    """Вычисляет ширину колонок по содержимому."""
    w_field = max((len(f.name) for f in fields), default=5)
    w_type = max((len(f.type_repr) for f in fields), default=4)
    w_default = max((len(f.default_display) for f in fields), default=7)
    return (
        max(w_field, _COL_FIELD),
        max(w_type, _COL_TYPE),
        max(w_default, _COL_DEFAULT),
    )


def _separator(w1: int, w2: int, w3: int) -> str:
    return f"+-{'-' * w1}-+-{'-' * w2}-+-{'-' * w3}-+"


def _header_row(w1: int, w2: int, w3: int) -> str:
    return f"| {'Field':<{w1}} | {'Type':<{w2}} | {'Default':<{w3}} |"


def _data_row(field: FieldMeta, w1: int, w2: int, w3: int) -> str:
    return (
        f"| {field.name:<{w1}} "
        f"| {field.type_repr:<{w2}} "
        f"| {field.default_display:<{w3}} |"
    )


def format_model(meta: ModelMeta) -> str:
    """
    Форматирует одну ModelMeta в строку с таблицей.

    Пример вывода:
        Model: UserSchema
        +-----------------+-------------------+---------+
        | Field           | Type              | Default |
        +-----------------+-------------------+---------+
        | id              | UUID              | —       |
        | phone           | int               | —       |
        | birthday        | Optional[str]     | None    |
        +-----------------+-------------------+---------+
    """
    w1, w2, w3 = _col_widths(meta.fields)
    sep = _separator(w1, w2, w3)

    lines = [
        f"Model: {meta.model_name}",
        sep,
        _header_row(w1, w2, w3),
        sep,
        *(_data_row(f, w1, w2, w3) for f in meta.fields),
        sep,
    ]
    return "\n".join(lines)


def format_models(metas: list[ModelMeta]) -> str:
    """Форматирует список ModelMeta, разделяя пустой строкой."""
    return "\n\n".join(format_model(m) for m in metas)


def print_models(metas: list[ModelMeta]) -> None:
    """Выводит таблицы для всех моделей в stdout."""
    print(format_models(metas))
