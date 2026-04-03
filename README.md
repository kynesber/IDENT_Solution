# IDENT_Solution

## Структура проекта

```
ident_solution/
├── task_1/          # Проектирование БД — три варианта ORM-моделей
│   ├── README.md    # Схемы, сравнение, объяснения
│   └── models.py    # SQLAlchemy ORM (все три варианта)
│
├── task_2/          # SQL-запросы
│   └── README.md    # Запросы с объяснением, сравнение вариантов
│
├── task_3/          # Code review — антипаттерны и исправления
│   └── README.md    # Разбор проблем + исправленный код
│
├── task_4/          # Pydantic v2 introspection utility
│   ├── introspection.py   # Слой данных: извлечение метаданных
│   ├── display.py         # Слой отображения: форматирование таблиц
│   ├── main.py            # Точка входа
│   └── tests.py           # 18 юнит-тестов (pytest)
│
├── task_5/          # Производительность Python
│   ├── main.py      # Два решения + замер времени
│   └── README.md    # Big-O анализ, результаты
│
├── task_6/          # Пример codestyle
│   └── domain.py    # Валидация, трансформация, type hints
│
└── requirements.txt
```

## Зависимости

```bash
pip install -r requirements.txt
```

## Запуск

```bash
# Задача 4 — introspection utility
python task_4/main.py

# Задача 4 — тесты
pytest task_4/tests.py -v

# Задача 5 — benchmark
python task_5/main.py
```

## Стек

| Технология | Версия | Применение |
|---|---|---|
| Python | 3.11+ | Основной язык |
| Pydantic v2 | ≥ 2.0 | Валидация, интроспекция (задача 4, 6) |
| SQLAlchemy | ≥ 2.0 | ORM-модели (задача 1) |
| FastAPI | ≥ 0.100 | Пример эндпоинта (задача 3) |
| pytest | ≥ 7.0 | Юнит-тесты (задача 4) |