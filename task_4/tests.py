"""
Задача 4 — юнит-тесты для слоёв интроспекции и отображения.

Запуск:
    pytest task_4/tests.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel, Field

from display import format_model, format_models
from introspection import FieldMeta, ModelMeta, introspect_model, introspect_models


# ---------------------------------------------------------------------------
# Фикстуры — тестовые модели
# ---------------------------------------------------------------------------

class SimpleModel(BaseModel):
    id: int
    name: str


class ModelWithDefaults(BaseModel):
    id: int
    active: bool = True
    tag: Optional[str] = None
    score: float = Field(default=0.0)


class EmptyModel(BaseModel):
    pass


# ---------------------------------------------------------------------------
# Тесты интроспекции
# ---------------------------------------------------------------------------

class TestIntrospectModel:
    def test_simple_model_field_count(self) -> None:
        meta = introspect_model(SimpleModel)
        assert len(meta.fields) == 2

    def test_simple_model_field_names(self) -> None:
        meta = introspect_model(SimpleModel)
        names = [f.name for f in meta.fields]
        assert names == ["id", "name"]

    def test_model_name(self) -> None:
        meta = introspect_model(SimpleModel)
        assert meta.model_name == "SimpleModel"

    def test_fields_without_default(self) -> None:
        meta = introspect_model(SimpleModel)
        for f in meta.fields:
            assert f.has_default is False
            assert f.default_display == "—"

    def test_field_with_default_bool(self) -> None:
        meta = introspect_model(ModelWithDefaults)
        active_field = next(f for f in meta.fields if f.name == "active")
        assert active_field.has_default is True
        assert active_field.default is True

    def test_field_with_default_none(self) -> None:
        meta = introspect_model(ModelWithDefaults)
        tag_field = next(f for f in meta.fields if f.name == "tag")
        assert tag_field.has_default is True
        assert tag_field.default is None
        assert tag_field.default_display == "None"

    def test_field_with_pydantic_field_default(self) -> None:
        meta = introspect_model(ModelWithDefaults)
        score_field = next(f for f in meta.fields if f.name == "score")
        assert score_field.has_default is True
        assert score_field.default == 0.0

    def test_optional_type_repr(self) -> None:
        meta = introspect_model(ModelWithDefaults)
        tag_field = next(f for f in meta.fields if f.name == "tag")
        assert tag_field.type_repr == "Optional[str]"

    def test_empty_model(self) -> None:
        meta = introspect_model(EmptyModel)
        assert meta.fields == []

    def test_raises_for_non_basemodel(self) -> None:
        class NotAModel:
            pass

        with pytest.raises(TypeError):
            introspect_model(NotAModel)  # type: ignore

    def test_introspect_multiple_models(self) -> None:
        metas = introspect_models([SimpleModel, ModelWithDefaults])
        assert len(metas) == 2
        assert metas[0].model_name == "SimpleModel"
        assert metas[1].model_name == "ModelWithDefaults"


# ---------------------------------------------------------------------------
# Тесты отображения
# ---------------------------------------------------------------------------

class TestFormatModel:
    def test_output_contains_model_name(self) -> None:
        meta = introspect_model(SimpleModel)
        output = format_model(meta)
        assert "Model: SimpleModel" in output

    def test_output_contains_field_names(self) -> None:
        meta = introspect_model(SimpleModel)
        output = format_model(meta)
        assert "id" in output
        assert "name" in output

    def test_output_contains_separator(self) -> None:
        meta = introspect_model(SimpleModel)
        output = format_model(meta)
        assert "+-" in output

    def test_output_contains_header(self) -> None:
        meta = introspect_model(SimpleModel)
        output = format_model(meta)
        assert "Field" in output
        assert "Type" in output
        assert "Default" in output

    def test_missing_default_shows_dash(self) -> None:
        meta = introspect_model(SimpleModel)
        output = format_model(meta)
        assert "—" in output

    def test_none_default_shows_none(self) -> None:
        meta = introspect_model(ModelWithDefaults)
        output = format_model(meta)
        assert "None" in output

    def test_format_multiple_models_separated(self) -> None:
        metas = introspect_models([SimpleModel, ModelWithDefaults])
        output = format_models(metas)
        assert "Model: SimpleModel" in output
        assert "Model: ModelWithDefaults" in output
        # Между моделями должна быть пустая строка
        assert "\n\n" in output
