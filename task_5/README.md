# Задача 5 — Производительность (Python)

## Задание

Найти всех пациентов, у которых есть приёмы раньше 2017 года.

Исходные данные: ~1 250 000 приёмов, 500 000 пациентов.

---

## Решение 1 — Set comprehension (рекомендуемое)

```python
def solution_1_set_lookup(receptions, patients, threshold):
    early_patient_ids: set[int] = {
        r["patient_id"]
        for r in receptions
        if r["reception_start"] < threshold
    }
    return [p for p in patients if p["id"] in early_patient_ids]
```

**Временная сложность:** O(n + m)
- O(n) — один проход по `receptions` для построения `set`
- O(m) — один проход по `patients` для фильтрации
- O(1) — проверка `in set` амортизированно

**Пространственная сложность:** O(k), где k — уникальных patient_id с ранними приёмами

---

## Решение 2 — Dict-индекс пациентов

```python
def solution_2_dict_index(receptions, patients, threshold):
    patients_index: dict[int, dict] = {p["id"]: p for p in patients}
    early_ids: set[int] = {
        r["patient_id"]
        for r in receptions
        if r["reception_start"] < threshold
    }
    return [patients_index[pid] for pid in early_ids if pid in patients_index]
```

**Временная сложность:** O(n + m)
- O(m) — построение индекса
- O(n) — проход по приёмам
- O(k) — сборка результата

**Отличие от решения 1:** явно строит словарь `{id → patient}`. Это полезно, когда:
- Нужно делать несколько подобных фильтраций по одному набору пациентов
- Нужен O(1) доступ к данным пациента по id без повторного перебора

---

## Результаты замера (3 прогона, среднее)

| Решение | Время | Найдено пациентов |
|---|---|---|
| Решение 1 (set comprehension) | ~0.156s | 369 937 |
| Решение 2 (dict index) | ~0.174s | 369 937 |

Решение 1 немного быстрее — не строит промежуточный словарь пациентов.
Оба решения одинаково корректны и масштабируемы.

---

## Почему НЕ используем вложенный цикл?

```python
# ПЛОХО — O(n × m) ≈ O(625 млрд операций)
result = [
    p for p in patients
    if any(r["patient_id"] == p["id"] and r["reception_start"] < threshold
           for r in receptions)
]
```

На 500k пациентов × 1.25M приёмов это заняло бы **минуты**, а не доли секунды.
