"""
Задача 5 — Найти пациентов с приёмами раньше 2017 года.

Два решения с разной временной сложностью.
Запуск: python task_5/main.py
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Генерация исходных данных (не трогаем, задано в условии)
# ---------------------------------------------------------------------------

random.seed(42)

receptions: list[dict] = [
    {
        "patient_id": pid,
        "reception_start": datetime(2017, 6, 30) - timedelta(days=random.randint(1, 500)),
    }
    for pid in range(1, 500_001)
    for _ in range(random.randint(0, 5))
]

patients: list[dict] = [
    {"id": pid, "surname": f"Иванов{pid}"}
    for pid in range(1, 500_001)
]

THRESHOLD = datetime(2017, 1, 1)

# ---------------------------------------------------------------------------
# Решение 1 — «Наивное»: двойной цикл / set comprehension
#
# Алгоритм:
#   1. Проходим по всем приёмам → O(n), где n = len(receptions)
#   2. Для каждого приёма раньше 2017 добавляем patient_id в set
#   3. Проходим по пациентам → O(m), где m = len(patients)
#   4. Проверяем вхождение в set → O(1) амортизированно
#
# Итоговая сложность: O(n + m)
# Память: O(k), где k — количество уникальных patient_id с ранними приёмами
# ---------------------------------------------------------------------------

def solution_1_set_lookup(
    receptions: list[dict],
    patients: list[dict],
    threshold: datetime,
) -> list[dict]:
    """
    Шаг 1: собираем set patient_id с приёмами до порога — O(n).
    Шаг 2: фильтруем пациентов по set — O(m).
    Итого: O(n + m), что оптимально для этой задачи.
    """
    # Set comprehension — один проход по receptions
    early_patient_ids: set[int] = {
        r["patient_id"]
        for r in receptions
        if r["reception_start"] < threshold
    }

    # List comprehension — один проход по patients
    return [p for p in patients if p["id"] in early_patient_ids]


# ---------------------------------------------------------------------------
# Решение 2 — Через словарь-индекс + groupby-подход (демонстрация иного стиля)
#
# Алгоритм:
#   1. Строим индекс patients: {id: patient_dict} → O(m)
#   2. Проходим по receptions, фильтруем и собираем уникальные id → O(n)
#   3. Делаем lookup в индексе → O(k)
#
# Итоговая сложность: O(n + m) — та же, но явно демонстрирует индексирование
# Это полезно, когда нужно не только id, но и дополнительные данные пациента
# ---------------------------------------------------------------------------

def solution_2_dict_index(
    receptions: list[dict],
    patients: list[dict],
    threshold: datetime,
) -> list[dict]:
    """
    Строим словарь-индекс пациентов для O(1)-доступа по id.
    Затем собираем результат через set уникальных id.
    Итого: O(n + m).
    """
    # Индекс: O(m)
    patients_index: dict[int, dict] = {p["id"]: p for p in patients}

    # Уникальные id пациентов с ранними приёмами: O(n)
    early_ids: set[int] = {
        r["patient_id"]
        for r in receptions
        if r["reception_start"] < threshold
    }

    # Сборка результата: O(k), где k = len(early_ids)
    return [patients_index[pid] for pid in early_ids if pid in patients_index]


# ---------------------------------------------------------------------------
# Замер времени
# ---------------------------------------------------------------------------

def benchmark(
    fn,
    label: str,
    *args,
    runs: int = 3,
) -> list[dict]:
    """Запускает функцию `runs` раз, выводит среднее время, возвращает результат."""
    times = []
    result = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = fn(*args)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    avg = sum(times) / len(times)
    print(f"{label}: {avg:.4f}s (avg of {runs} runs), found {len(result)} patients")
    return result


def main() -> None:
    print(f"Данные: {len(receptions):,} приёмов, {len(patients):,} пациентов")
    print(f"Порог: {THRESHOLD.date()}")
    print("-" * 60)

    result1 = benchmark(solution_1_set_lookup, "Решение 1 (set comprehension)", receptions, patients, THRESHOLD)
    result2 = benchmark(solution_2_dict_index, "Решение 2 (dict index)        ", receptions, patients, THRESHOLD)

    # Проверяем, что оба решения дают одинаковый результат
    ids1 = {p["id"] for p in result1}
    ids2 = {p["id"] for p in result2}
    print(f"\nРезультаты совпадают: {ids1 == ids2}")


if __name__ == "__main__":
    main()
