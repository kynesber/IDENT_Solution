# Задача 2 — SQL-запросы

```sql
CREATE TABLE Receptions (
    ID           INT      NOT NULL PRIMARY KEY,
    ID_Patients  INT      NOT NULL,
    ID_Doctors   INT      NOT NULL,
    StartDateTime DATETIME NOT NULL
);
```

---

## Задача 2.1 — Приёмы по каждой дате 2015 года (включая нули)

Ключевая сложность: нужно вернуть **все 365 дат** года, даже если приёмов не было.
Для этого нужен источник «всех дат» — календарная таблица или её аналог.

---

### Вариант 1 — Рекурсивный CTE (работает в PostgreSQL, MySQL 8+, SQLite 3.35+)

```sql
WITH RECURSIVE calendar AS (
    -- Начальная точка: 1 января 2015
    SELECT DATE('2015-01-01') AS day
    UNION ALL
    -- Добавляем по одному дню, пока не выйдем за год
    SELECT DATE(day, '+1 day')
    FROM   calendar
    WHERE  day < DATE('2015-12-31')
),
daily_counts AS (
    SELECT
        CAST(StartDateTime AS DATE) AS reception_date,
        COUNT(*)                    AS cnt
    FROM   Receptions
    WHERE  StartDateTime >= '2015-01-01'
      AND  StartDateTime <  '2016-01-01'
    GROUP BY CAST(StartDateTime AS DATE)
)
SELECT
    c.day                        AS reception_date,
    COALESCE(d.cnt, 0)           AS reception_count
FROM       calendar       c
LEFT JOIN  daily_counts   d  ON d.reception_date = c.day
ORDER BY   c.day;
```

**Как работает:**
1. `RECURSIVE CTE calendar` генерирует строку для каждого дня с 01.01.2015 по 31.12.2015.
2. `daily_counts` считает реальные приёмы, сгруппированные по дате.
3. `LEFT JOIN` — ключевой момент: для дней без приёмов строки из `daily_counts` будут NULL, которые `COALESCE` заменяет на `0`.

---

### Вариант 2 — Готовая таблица-календарь (production-подход)

В реальных системах принято иметь специальную таблицу дат:

```sql
-- Предполагаем, что такая таблица уже существует
-- CREATE TABLE dim_date (day DATE PRIMARY KEY);

WITH daily_counts AS (
    SELECT
        CAST(StartDateTime AS DATE) AS reception_date,
        COUNT(*)                    AS cnt
    FROM   Receptions
    WHERE  StartDateTime >= '2015-01-01'
      AND  StartDateTime <  '2016-01-01'
    GROUP BY CAST(StartDateTime AS DATE)
)
SELECT
    d.day                        AS reception_date,
    COALESCE(dc.cnt, 0)          AS reception_count
FROM       dim_date      d
LEFT JOIN  daily_counts  dc  ON dc.reception_date = d.day
WHERE      d.day BETWEEN '2015-01-01' AND '2015-12-31'
ORDER BY   d.day;
```

**Разница между вариантами:**

| | Вариант 1 (Recursive CTE) | Вариант 2 (dim_date) |
|---|---|---|
| Зависимости | Только стандартный SQL | Требует заранее созданную таблицу |
| Скорость | Генерация 365 строк — мгновенно | Чуть быстрее: таблица уже индексирована |
| Поддержка СУБД | PostgreSQL, MySQL 8+, SQLite 3.35+ | Любая СУБД |
| Удобство | Самодостаточный запрос | Чище, если `dim_date` уже есть в схеме |

---

## Задача 2.2 — Для каждого пациента — врач из последнего приёма

---

### Вариант 1 — Коррелированный подзапрос

```sql
SELECT
    r.ID_Patients,
    r.ID_Doctors
FROM Receptions r
WHERE r.StartDateTime = (
    -- Для каждой строки находим максимальную дату ЭТОГО пациента
    SELECT MAX(r2.StartDateTime)
    FROM   Receptions r2
    WHERE  r2.ID_Patients = r.ID_Patients
);
```

**Плюсы:** простота, понятность.  
**Минусы:** коррелированный подзапрос выполняется для **каждой строки** внешнего запроса → O(n²) при отсутствии хорошего индекса.

---

### Вариант 2 — JOIN с агрегирующим подзапросом

```sql
SELECT
    r.ID_Patients,
    r.ID_Doctors
FROM Receptions r
INNER JOIN (
    SELECT ID_Patients, MAX(StartDateTime) AS last_dt
    FROM   Receptions
    GROUP BY ID_Patients
) last_visit
    ON  last_visit.ID_Patients = r.ID_Patients
    AND last_visit.last_dt     = r.StartDateTime;
```

**Плюсы:** подзапрос выполняется **один раз**, результат кешируется; эффективнее варианта 1.  
**Минусы:** если у пациента два приёма с одинаковым `StartDateTime` (тай), вернётся **несколько строк** (оба врача).

---

### Вариант 3 — Window function ROW_NUMBER()

```sql
WITH ranked AS (
    SELECT
        ID_Patients,
        ID_Doctors,
        StartDateTime,
        ROW_NUMBER() OVER (
            PARTITION BY ID_Patients          -- для каждого пациента
            ORDER BY StartDateTime DESC       -- сначала самый поздний
        ) AS rn
    FROM Receptions
)
SELECT
    ID_Patients,
    ID_Doctors,
    StartDateTime
FROM ranked
WHERE rn = 1;
```

**Плюсы:**
- Гарантированно **одна строка** на пациента (тай разрешается детерминированно).
- Оконные функции обрабатываются одним проходом по данным — O(n log n).
- Легко добавить `StartDateTime` в SELECT для отладки.

**Минусы:** требует PostgreSQL / MySQL 8+ / SQL Server / SQLite 3.25+.

---

### Сравнение вариантов

| | Вариант 1 (коррелированный) | Вариант 2 (JOIN + GROUP BY) | Вариант 3 (ROW_NUMBER) |
|---|---|---|---|
| **Тай (два приёма в одно время)** | Вернёт **оба** врача | Вернёт **оба** врача | Вернёт **одного** (детерминированно) |
| **Эффективность** | Плохо: O(n²) | Хорошо: O(n) | Отлично: O(n log n), один проход |
| **Читаемость** | Просто | Умеренно | Чисто и явно |
| **Поддержка СУБД** | Любая | Любая | PostgreSQL, MySQL 8+, SQLite 3.25+ |

**Рекомендация:** для больших объёмов — **Вариант 3**. Индекс `(ID_Patients, StartDateTime DESC)` сделает его работу почти мгновенной.
