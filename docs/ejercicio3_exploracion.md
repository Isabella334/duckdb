# Ejercicio 3 - Consultas directas sobre archivos Parquet

| Recurso | Ruta |
|---|---|
| Consultas SQL | [`sql/03_exploracion_parquet.sql`](../sql/03_exploracion_parquet.sql) |
| Notebook (ejecutado, con resultados) | [`notebooks/03_exploracion_parquet.ipynb`](../notebooks/03_exploracion_parquet.ipynb) |
| Resultados completos de cada consulta | [`docs/resultados/ejercicio3_resultados.md`](resultados/ejercicio3_resultados.md) |

**Reproducir:**

```bash
docker compose exec lab python scripts/run_sql.py sql/03_exploracion_parquet.sql --salida docs/resultados/ejercicio3_resultados.md
```

o abrir el notebook en <http://localhost:8888> y ejecutar todas las celdas.

**Datos usados:** 16 archivos de 2026 (enero-agosto) descargados en el Ejercicio 2.
Ninguna consulta crea tablas: se usa una conexion de DuckDB en memoria y todas leen los
Parquet con `read_parquet()`, `glob()`, `parquet_file_metadata()` o `parquet_schema()`.
Los tiempos son los medidos dentro del contenedor `lab`.

**Abreviaturas de fuentes:**

- `Y` = `data/raw/yellow/2026/yellow_tripdata_2026-{01..08}.parquet` (8 archivos)
- `G` = `data/raw/green/2026/green_tripdata_2026-{01..08}.parquet` (8 archivos)
- `Y+G` = `data/raw/*/*/*.parquet` (16 archivos)

---

## Resumen de la exploracion

| Pregunta | Respuesta |
|---|---|
| 3.1 Archivos | **16**: 8 yellow + 8 green, enero a agosto de 2026 |
| 3.2 Registros | **30,040,469**: 29,703,355 yellow + 337,114 green |
| 3.3 Columnas | yellow: 21, green: 22; 18 comunes. Las fechas se llaman distinto (`tpep_*` en yellow, `lpep_*` en green) |
| 3.4 Tipos | `TIMESTAMP` (fechas), `INTEGER`/`BIGINT` (codigos, zonas, pasajeros), `DOUBLE` (distancia y montos), `VARCHAR` (`store_and_fwd_flag`, `request_source`) |
| 3.6 Calidad | Deriva de esquema, bloques de nulos ligados a un tipo de pago, fechas de 2001/2008, duraciones y distancias imposibles, montos negativos, codificacion de recargos distinta segun el proveedor, 7 duplicados |

---

## 3.1 Cantidad de archivos - `q01_cantidad_archivos`

```sql
SELECT
    split_part(file, '/', 3)            AS tipo,
    split_part(file, '/', 4)            AS anio,
    count(*)                            AS archivos,
    min(regexp_extract(file, '(\d{4}-\d{2})\.parquet$', 1)) AS primer_mes,
    max(regexp_extract(file, '(\d{4}-\d{2})\.parquet$', 1)) AS ultimo_mes
FROM glob('data/raw/*/*/*.parquet')
GROUP BY ALL
ORDER BY tipo, anio;
```

- **Objetivo:** contar los archivos disponibles y ver que meses cubren, usando solo el sistema de archivos.
- **Fuente:** `Y+G` (via `glob`; no abre los archivos).
- **Resultado:**

  | tipo | anio | archivos | primer_mes | ultimo_mes |
  |---|---|---|---|---|
  | green | 2026 | 8 | 2026-01 | 2026-08 |
  | yellow | 2026 | 8 | 2026-01 | 2026-08 |

- **Decision:** coincide con los 16 archivos que la TLC tiene publicados (Ejercicio 2.7). La
  ruta `data/raw/<tipo>/<anio>/` permite sacar el tipo y el anio del path, asi que no hace
  falta agregar esas columnas a los datos.

## 3.2 Cantidad de registros

### `q02_registros_por_archivo`

```sql
SELECT
    split_part(file_name, '/', 3)       AS tipo,
    regexp_extract(file_name, '(\d{4}-\d{2})\.parquet$', 1) AS mes,
    num_rows                            AS registros,
    num_row_groups                      AS row_groups
FROM parquet_file_metadata('data/raw/*/*/*.parquet')
ORDER BY tipo, mes;
```

- **Objetivo:** contar los registros de cada archivo leyendo solo el *footer* (metadatos) del Parquet.
- **Fuente:** `Y+G` (solo metadatos).
- **Resultado (0.17 s):**

  | mes | yellow | green |
  |---|---|---|
  | 2026-01 | 3,724,889 | 40,272 |
  | 2026-02 | 3,399,866 | 37,373 |
  | 2026-03 | 3,952,451 | 44,208 |
  | 2026-04 | 3,831,240 | 44,238 |
  | 2026-05 | 4,090,836 | 44,921 |
  | 2026-06 | 3,837,248 | 44,163 |
  | 2026-07 | 3,530,109 | 41,252 |
  | 2026-08 | 3,336,716 | 40,687 |

  Cada archivo yellow tiene 4 *row groups* y cada green tiene 1.

- **Decision:** ningun mes esta vacio ni es anormalmente pequeno, lo que confirma que la
  descarga esta completa. Mayo es el mes con mas viajes en ambos tipos; el mas bajo es
  agosto en yellow y febrero (que tiene menos dias) en green.
  Los taxis verdes son ~1.1 % del volumen de los amarillos, asi que en las comparaciones
  entre tipos (Ejercicio 4) hay que usar proporciones o promedios, no totales.

### `q03_total_registros`

```sql
SELECT split_part(filename, '/', 3) AS tipo, count(*) AS registros
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL
UNION ALL
SELECT 'TOTAL', count(*)
FROM read_parquet('data/raw/*/*/*.parquet', union_by_name = true)
ORDER BY registros;
```

- **Objetivo:** confirmar el total contando los datos, no solo los metadatos.
- **Fuente:** `Y+G`.
- **Resultado (1.8 s):** green 337,114 · yellow 29,703,355 · **TOTAL 30,040,469**.
- **Decision:** coincide exactamente con la suma de `q02`, asi que los metadatos son
  confiables. En adelante, para conteos simples basta con `parquet_file_metadata`, que es
  ~10 veces mas rapido.

## 3.3 / 3.4 Columnas y tipos de datos

### `q04_consistencia_esquema`

```sql
WITH esquema AS (
    SELECT split_part(file_name, '/', 3) AS tipo, file_name, name AS columna,
           type AS tipo_fisico,
           coalesce(logical_type::VARCHAR, converted_type::VARCHAR, '') AS tipo_logico
    FROM parquet_schema('data/raw/*/*/*.parquet')
    WHERE name <> 'schema'
),
archivos_por_tipo AS (
    SELECT tipo, count(DISTINCT file_name) AS total FROM esquema GROUP BY tipo
)
SELECT e.tipo, e.columna,
       count(DISTINCT e.file_name) AS archivos_con_columna,
       a.total AS archivos_del_tipo,
       list(DISTINCT e.tipo_fisico || ' ' || e.tipo_logico) AS tipos_vistos,
       list(DISTINCT regexp_extract(e.file_name, '(\d{4}-\d{2})\.parquet$', 1) ORDER BY ...) AS meses
FROM esquema e JOIN archivos_por_tipo a USING (tipo)
GROUP BY e.tipo, e.columna, a.total
HAVING count(DISTINCT e.file_name) <> a.total
    OR count(DISTINCT e.tipo_fisico || ' ' || e.tipo_logico) > 1
ORDER BY e.tipo, e.columna;
```

(Version completa en el archivo `.sql`.)

- **Objetivo:** antes de describir columnas, verificar que el esquema sea igual en todos
  los archivos de un mismo tipo (que no aparezcan o desaparezcan columnas ni cambien tipos).
- **Fuente:** `Y+G` (solo el esquema de cada archivo).
- **Resultado:**

  | tipo | columna | archivos_con_columna | archivos_del_tipo | meses |
  |---|---|---|---|---|
  | green | request_source | 3 | 8 | 2026-06, 2026-07, 2026-08 |
  | yellow | request_source | 3 | 8 | 2026-06, 2026-07, 2026-08 |

  Ninguna columna cambia de tipo entre archivos.

- **Decision:** **hay deriva de esquema**: la TLC agrego `request_source` a partir de junio
  de 2026. Se comprobo que leer el glob **sin** `union_by_name` devuelve 20 columnas en
  lugar de 21: DuckDB toma el esquema del primer archivo (enero) y descarta
  `request_source` sin ningun aviso. **Todas las consultas del proyecto usan
  `read_parquet(..., union_by_name = true)`**, que une las columnas por nombre y llena con
  `NULL` las que faltan. Esto sera todavia mas importante al agregar 2024 y 2025.

### `q05_columnas_yellow` y `q06_columnas_green`

```sql
DESCRIBE SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true);
DESCRIBE SELECT * FROM read_parquet('data/raw/green/*/*.parquet',  union_by_name = true);
```

- **Objetivo:** listar las columnas y sus tipos de datos para cada tipo de taxi.
- **Fuente:** `Y` y `G` respectivamente (solo esquema).
- **Resultado:** ver `q07`.

### `q07_comparacion_columnas`

```sql
WITH y AS (SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true))),
     g AS (SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_parquet('data/raw/green/*/*.parquet',  union_by_name = true)))
SELECT coalesce(y.column_name, g.column_name) AS columna,
       y.column_type AS tipo_yellow, g.column_type AS tipo_green,
       CASE WHEN y.column_name IS NULL THEN 'solo green'
            WHEN g.column_name IS NULL THEN 'solo yellow'
            WHEN y.column_type <> g.column_type THEN 'ambos (tipo distinto)'
            ELSE 'ambos' END AS presente_en
FROM y FULL OUTER JOIN g ON y.column_name = g.column_name
ORDER BY presente_en, columna;
```

- **Objetivo:** identificar que columnas comparten ambos tipos de taxi y cuales son exclusivas.
- **Fuente:** `Y` y `G` (solo esquema).
- **Resultado:** columnas y tipos de datos (significado segun el diccionario de datos de la TLC):

  | Columna | Tipo | Presente en | Significado |
  |---|---|---|---|
  | `VendorID` | INTEGER | ambos | Proveedor del sistema del taximetro (1 Creative Mobile Technologies, 2 Curb Mobility, 6 Myle Technologies, 7 Helix) |
  | `tpep_pickup_datetime` / `lpep_pickup_datetime` | TIMESTAMP | yellow / green | Inicio del viaje |
  | `tpep_dropoff_datetime` / `lpep_dropoff_datetime` | TIMESTAMP | yellow / green | Fin del viaje |
  | `passenger_count` | BIGINT | ambos | Pasajeros (lo ingresa el conductor) |
  | `trip_distance` | DOUBLE | ambos | Distancia en millas segun el taximetro |
  | `RatecodeID` | BIGINT | ambos | Tarifa: 1 estandar, 2 JFK, 3 Newark, 4 Nassau/Westchester, 5 negociada, 6 grupo, 99 desconocida |
  | `store_and_fwd_flag` | VARCHAR | ambos | `Y` si el viaje se guardo en el vehiculo y se envio despues |
  | `PULocationID` / `DOLocationID` | INTEGER | ambos | Zona TLC de origen / destino (1-265) |
  | `payment_type` | BIGINT | ambos | 0 Flex Fare, 1 tarjeta, 2 efectivo, 3 sin cargo, 4 disputa, 5 desconocido, 6 anulado |
  | `fare_amount` | DOUBLE | ambos | Tarifa por tiempo y distancia |
  | `extra`, `mta_tax`, `improvement_surcharge`, `congestion_surcharge`, `cbd_congestion_fee` | DOUBLE | ambos | Recargos e impuestos |
  | `tip_amount` | DOUBLE | ambos | Propina (solo se registra la pagada con tarjeta) |
  | `tolls_amount` | DOUBLE | ambos | Peajes |
  | `total_amount` | DOUBLE | ambos | Total cobrado (sin propina en efectivo) |
  | `request_source` | VARCHAR | ambos | Nueva desde 2026-06; **no aparece en el diccionario de datos publicado** (ver q16) |
  | `Airport_fee` | DOUBLE | solo yellow | Recargo por recoger en LaGuardia / JFK |
  | `ehail_fee` | DOUBLE | solo green | Tarifa de e-hail |
  | `trip_type` | BIGINT | solo green | 1 parada en la calle, 2 despacho |

- **Decision:** ningun par de columnas comunes tiene tipos distintos, asi que yellow y green
  se pueden unir. Para analizarlos juntos se usa
  `coalesce(tpep_pickup_datetime, lpep_pickup_datetime)` (y lo mismo con dropoff). Las
  columnas exclusivas se tratan como `NULL` en el otro tipo. `payment_type` y `RatecodeID`
  son codigos y no cantidades: no tiene sentido promediarlos.

## 3.5 Muestra de registros - `q08_muestra_yellow`, `q09_muestra_green`

```sql
SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true)
USING SAMPLE reservoir(10 ROWS) REPEATABLE (42);

SELECT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true)
USING SAMPLE reservoir(10 ROWS) REPEATABLE (42);
```

- **Objetivo:** ver registros reales para entender el formato de cada campo. Se usa
  muestreo aleatorio con semilla fija (`REPEATABLE (42)`) en lugar de `LIMIT`, porque
  `LIMIT` siempre devuelve las primeras filas de enero y no son representativas.
- **Fuente:** `Y` y `G`.
- **Resultado:** las 10 filas de cada muestra estan en
  [`ejercicio3_resultados.md`](resultados/ejercicio3_resultados.md#q08_muestra_yellow). Ejemplo (yellow):

  | VendorID | pickup | dropoff | pasajeros | millas | PU | DO | pago | tarifa | propina | total |
  |---|---|---|---|---|---|---|---|---|---|---|
  | 2 | 2026-01-01 12:39:27 | 2026-01-01 12:52:43 | 1 | 4.79 | 140 | 232 | 1 | 21.20 | 5.19 | 31.14 |
  | 1 | 2026-01-01 15:35:24 | 2026-01-01 16:07:48 | 1 | 22.00 | 132 | 60 | 1 | 80.70 | 22.30 | 111.44 |

- **Decision:** en la muestra de green ya aparecen filas con `passenger_count`, `RatecodeID`,
  `payment_type` y `trip_type` en `NULL` al mismo tiempo, y una fila con `fare_amount` 3.00
  pero total 17.26. Esto motivo las consultas de nulos (`q10`/`q11`) y de montos (`q15`/`q15b`).

## 3.6 Problemas de calidad de datos

### `q10_nulos_por_columna`

```sql
SELECT 'yellow' AS tipo, column_name AS columna, null_percentage AS pct_nulos
FROM (SUMMARIZE SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true))
WHERE null_percentage > 0
UNION ALL
SELECT 'green', column_name, null_percentage
FROM (SUMMARIZE SELECT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true))
WHERE null_percentage > 0
ORDER BY tipo DESC, pct_nulos DESC, columna;
```

- **Objetivo:** medir el porcentaje de nulos de cada columna.
- **Fuente:** `Y`, `G`.
- **Resultado (~40-55 s; `SUMMARIZE` calcula estadisticas de todas las columnas):**

  | yellow | % nulos | green | % nulos |
  |---|---|---|---|
  | request_source | 90.23 | ehail_fee | **100.00** |
  | passenger_count, RatecodeID, store_and_fwd_flag, congestion_surcharge, Airport_fee | **25.98** | request_source | 94.30 |
  | | | passenger_count, RatecodeID, store_and_fwd_flag, payment_type, trip_type, congestion_surcharge | **14.47** |

  Las fechas, zonas, distancias y montos no tienen nulos.

- **Decision:** el mismo porcentaje en varias columnas sugiere que los nulos estan en las
  mismas filas; se verifica en `q11`. `ehail_fee` esta vacia en 100 % de los registros,
  asi que se descarta del analisis. `request_source` solo existe desde junio (ver `q04`).

### `q11_nulos_simultaneos`

```sql
SELECT split_part(filename, '/', 3) AS tipo,
       count(*) AS registros,
       count(*) FILTER (passenger_count IS NULL) AS passenger_count_nulo,
       count(*) FILTER (passenger_count IS NULL AND RatecodeID IS NULL
                        AND store_and_fwd_flag IS NULL
                        AND congestion_surcharge IS NULL) AS todos_nulos_juntos,
       count(*) FILTER (passenger_count IS NULL AND payment_type = 0) AS nulos_con_payment_0,
       count(*) FILTER (payment_type = 0) AS payment_type_0
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL ORDER BY tipo DESC;
```

- **Objetivo:** confirmar si los nulos ocurren en las mismas filas y si se relacionan con algun tipo de pago.
- **Fuente:** `Y+G`.
- **Resultado (2.7 s):**

  | tipo | registros | passenger_count nulo | todos nulos juntos | nulos con payment_type = 0 | payment_type = 0 |
  |---|---|---|---|---|---|
  | yellow | 29,703,355 | 7,716,688 | 7,716,688 | 7,716,688 | 7,716,688 |
  | green | 337,114 | 48,775 | 48,775 | 0 | 0 |

- **Decision:** en yellow, **los nulos son exactamente los viajes con `payment_type = 0`**
  ("Flex Fare", el 26 % de los viajes). No son errores aleatorios: es un tipo de viaje
  que no reporta esos campos. En green ocurre lo mismo, pero ahi `payment_type` tambien es
  nulo. Por tanto:
  - no se eliminan esas filas (seria perder una cuarta parte de los viajes);
  - los analisis de pasajeros, tarifa (`RatecodeID`) o recargo de congestion se calculan
    sobre las filas no nulas y se indica el filtro;
  - en el analisis de pagos, `payment_type = 0` / `NULL` se trata como una categoria propia.

### `q12_fechas_fuera_de_periodo`

```sql
WITH viajes AS (
    SELECT split_part(filename, '/', 3) AS tipo,
           strptime(regexp_extract(filename, '(\d{4}-\d{2})\.parquet$', 1), '%Y-%m')::DATE AS mes_archivo,
           coalesce(tpep_pickup_datetime, lpep_pickup_datetime) AS pickup
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT tipo, count(*) AS registros,
       count(*) FILTER (date_trunc('month', pickup) <> mes_archivo) AS fuera_del_mes,
       count(*) FILTER (pickup < mes_archivo - INTERVAL 1 MONTH)    AS mas_de_un_mes_antes,
       count(*) FILTER (pickup >= mes_archivo + INTERVAL 1 MONTH)   AS despues_del_mes,
       min(pickup) AS pickup_minimo, max(pickup) AS pickup_maximo
FROM viajes GROUP BY tipo ORDER BY tipo DESC;
```

- **Objetivo:** comprobar que cada archivo solo contiene viajes de su mes.
- **Fuente:** `Y+G` (el mes esperado se toma del nombre del archivo).
- **Resultado (2.9 s):**

  | tipo | fuera del mes | > 1 mes antes | despues del mes | pickup minimo | pickup maximo |
  |---|---|---|---|---|---|
  | yellow | 146 | 26 | 47 | **2001-01-01 09:23:58** | 2026-08-31 23:59:59 |
  | green | 98 | 10 | 29 | **2008-12-31 17:35:31** | 2026-08-31 23:58:28 |

- **Decision:** son pocos registros (< 0.03 % en green, < 0.001 % en yellow). Los que caen
  justo antes o despues del mes son viajes que cruzan la medianoche del cambio de mes; los
  de 2001 y 2008 son errores de reloj del taximetro. **Para analisis temporales se filtrara
  por la fecha de pickup dentro del periodo del archivo** (o, de forma equivalente,
  `pickup` entre `2026-01-01` y la fecha del ultimo mes publicado). Agrupar por el mes del
  pickup sin filtrar generaria "meses" falsos como 2001-01.

### `q13_duracion_viajes`

```sql
WITH viajes AS (
    SELECT split_part(filename, '/', 3) AS tipo,
           date_diff('second',
                     coalesce(tpep_pickup_datetime, lpep_pickup_datetime),
                     coalesce(tpep_dropoff_datetime, lpep_dropoff_datetime)) / 60.0 AS minutos
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT tipo, count(*) AS registros,
       count(*) FILTER (minutos < 0)                 AS dropoff_antes_de_pickup,
       count(*) FILTER (minutos = 0)                 AS duracion_cero,
       count(*) FILTER (minutos > 0 AND minutos < 1) AS menos_de_1_min,
       count(*) FILTER (minutos > 180)               AS mas_de_3_horas,
       count(*) FILTER (minutos > 1440)              AS mas_de_24_horas,
       round(quantile_cont(minutos, 0.5), 2)         AS mediana_min,
       round(quantile_cont(minutos, 0.99), 2)        AS p99_min,
       round(max(minutos), 1)                        AS max_min
FROM viajes GROUP BY tipo ORDER BY tipo DESC;
```

- **Objetivo:** detectar duraciones imposibles (negativas o nulas) o sospechosamente largas.
- **Fuente:** `Y+G`.
- **Resultado (7-15 s):**

  | tipo | dropoff < pickup | duracion 0 | < 1 min | > 3 h | > 24 h | mediana | p99 | maximo |
  |---|---|---|---|---|---|---|---|---|
  | yellow | 10 | 371,673 | 309,479 | 10,127 | 263 | 13.9 min | 71.2 min | 17,165 min (~12 dias) |
  | green | 5 | 229 | 11,042 | 1,287 | 4 | 13.1 min | 82.2 min | 2,456 min |

- **Decision:** la mediana (~14 min) y el p99 (~1-1.5 h) son razonables, pero hay ~1.25 %
  de viajes yellow con duracion 0 y algunos con duracion negativa o de dias. Para
  analizar duraciones o velocidades se usara un filtro de validez (p. ej. duracion
  entre 1 minuto y 3 horas) y se reportara cuantos registros se excluyen. Para conteos
  de viajes o ingresos no se filtran, porque son viajes cobrados.

### `q14_distancias`

```sql
SELECT split_part(filename, '/', 3) AS tipo, count(*) AS registros,
       count(*) FILTER (trip_distance = 0)    AS distancia_cero,
       count(*) FILTER (trip_distance > 100)  AS mas_de_100_millas,
       count(*) FILTER (trip_distance > 1000) AS mas_de_1000_millas,
       round(quantile_cont(trip_distance, 0.5), 2)  AS mediana_millas,
       round(quantile_cont(trip_distance, 0.99), 2) AS p99_millas,
       max(trip_distance) AS max_millas
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL ORDER BY tipo DESC;
```

- **Objetivo:** detectar distancias en cero y valores extremos.
- **Fuente:** `Y+G`.
- **Resultado (7.5 s):**

  | tipo | distancia 0 | > 100 mi | > 1000 mi | mediana | p99 | maximo |
  |---|---|---|---|---|---|---|
  | yellow | 952,231 (3.2 %) | 1,223 | 615 | 1.86 mi | 19.50 mi | **328,522 mi** |
  | green | 12,212 (3.6 %) | 72 | 66 | 2.07 mi | 17.76 mi | **179,831 mi** |

- **Decision:** 328,522 millas es mas que la distancia de la Tierra a la Luna: es un error
  del taximetro. Por eso el **promedio de `trip_distance` (5.55 mi en yellow) esta inflado**
  y no representa el viaje tipico; en el analisis se usaran la mediana y percentiles, o
  promedios con un tope razonable (p. ej. `trip_distance` entre 0 y 100 millas). Las
  distancias en cero pueden ser viajes cancelados o con GPS desactivado; se cuantifican
  aparte en lugar de borrarse.

### `q15_montos`

```sql
WITH viajes AS (
    SELECT split_part(filename, '/', 3) AS tipo, *,
           fare_amount + extra + mta_tax + tip_amount + tolls_amount + improvement_surcharge
           + coalesce(congestion_surcharge, 0) + coalesce(Airport_fee, 0)
           + coalesce(cbd_congestion_fee, 0) + coalesce(ehail_fee, 0) AS suma_componentes
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT tipo, count(*) AS registros,
       count(*) FILTER (fare_amount < 0)  AS tarifa_negativa,
       count(*) FILTER (total_amount < 0) AS total_negativo,
       count(*) FILTER (total_amount = 0) AS total_cero,
       count(*) FILTER (tip_amount < 0)   AS propina_negativa,
       count(*) FILTER (total_amount > 500) AS total_mayor_500,
       count(*) FILTER (abs(total_amount - suma_componentes) > 0.01) AS total_no_cuadra,
       round(100.0 * count(*) FILTER (abs(total_amount - suma_componentes) > 0.01) / count(*), 2) AS pct_no_cuadra
FROM viajes GROUP BY tipo ORDER BY tipo DESC;
```

- **Objetivo:** detectar montos negativos, en cero o extremos, y verificar si `total_amount`
  es la suma de sus componentes.
- **Fuente:** `Y+G`.
- **Resultado (5.9 s):**

  | tipo | tarifa < 0 | total < 0 | total = 0 | propina < 0 | total > $500 | total no cuadra |
  |---|---|---|---|---|---|---|
  | yellow | 157,364 | 161,835 (0.54 %) | 5,258 | 883 | 791 | 10,895,756 (**36.7 %**) |
  | green | 999 | 1,023 (0.30 %) | 543 | 69 | 21 | 66,970 (19.9 %) |

- **Decision:** los montos negativos parecen reversiones o reembolsos: en una consulta
  adicional, el 73 % de los totales negativos de yellow (y el 82 % de green) tienen
  `payment_type` 3 "sin cargo" o 4 "disputa", y la mayoria del resto son en efectivo. Se excluiran de los
  promedios de tarifa y propina, pero se pueden analizar por separado. Que el 37 % de
  los totales "no cuadre" era sospechoso, asi que se investigo en `q15b`.

### `q15b_montos_por_proveedor`

```sql
WITH viajes AS (
    SELECT split_part(filename, '/', 3) AS tipo, VendorID,
           coalesce(payment_type::VARCHAR, 'NULL') AS payment_type,
           round(total_amount - (fare_amount + extra + mta_tax + tip_amount + tolls_amount
                 + improvement_surcharge + coalesce(congestion_surcharge, 0)
                 + coalesce(Airport_fee, 0) + coalesce(cbd_congestion_fee, 0)
                 + coalesce(ehail_fee, 0)), 2) AS diferencia
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT tipo, VendorID, payment_type, count(*) AS registros,
       count(*) FILTER (abs(diferencia) > 0.01) AS no_cuadra,
       round(100.0 * count(*) FILTER (abs(diferencia) > 0.01) / count(*), 1) AS pct_no_cuadra,
       mode(diferencia) FILTER (abs(diferencia) > 0.01) AS diferencia_mas_comun
FROM viajes GROUP BY ALL HAVING count(*) > 1000
ORDER BY tipo DESC, VendorID, payment_type;
```

- **Objetivo:** saber si los totales estan mal o si la diferencia depende de como cada
  proveedor registra los recargos.
- **Fuente:** `Y+G`.
- **Resultado (7 s), extracto de yellow:**

  | VendorID | payment_type | registros | % no cuadra | diferencia mas comun |
  |---|---|---|---|---|
  | 1 (CMT) | 1 tarjeta | 4,028,246 | 82.3 % | **-3.25** |
  | 1 (CMT) | 0 Flex Fare | 895,381 | 98.4 % | +2.50 |
  | 2 (Curb) | 1 tarjeta | 14,592,874 | **0.1 %** | +2.50 |
  | 2 (Curb) | 2 efectivo | 2,217,837 | **0.2 %** | +2.50 |
  | 2 (Curb) | 0 Flex Fare | 6,761,917 | 88.2 % | **+2.50** |
  | 6 (Myle) | 0 Flex Fare | 59,390 | 100 % | +12.20 |
  | 7 (Helix) | 1 tarjeta | 319,888 | 43.5 % | +1.00 |

- **Decision:** el problema **no son los totales, sino que la codificacion de los
  componentes cambia segun el proveedor y el tipo de pago**:
  - Curb (VendorID 2, 80 % de los viajes yellow) cuadra en el 99.9 % de los viajes con
    tarjeta o efectivo.
  - CMT (VendorID 1) da -3.25 = 2.50 (congestion) + 0.75 (CBD): incluye esos recargos dentro
    de `extra` **y** en sus propias columnas, asi que la suma los cuenta dos veces.
  - En Flex Fare (`payment_type = 0`) la diferencia es +2.50: el recargo de congestion si se
    cobra en el total, pero la columna `congestion_surcharge` viene en `NULL` (`q11`).

  Conclusiones para el analisis: (1) usar `total_amount` y `fare_amount` tal como vienen y
  **no recalcular el total sumando componentes**; (2) no comparar recargos individuales
  (`extra`, `congestion_surcharge`) entre proveedores sin tomar en cuenta esta diferencia;
  (3) controlar por `VendorID` cuando un resultado dependa de esas columnas.

### `q16_codigos_categoricos`

```sql
SELECT split_part(filename, '/', 3) AS tipo, 'VendorID' AS columna, VendorID::VARCHAR AS valor, count(*) AS registros
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL
SELECT split_part(filename, '/', 3), 'RatecodeID', RatecodeID::VARCHAR, count(*)
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL ...   -- payment_type, passenger_count, trip_type y request_source (desde junio)
ORDER BY tipo DESC, columna, registros DESC;
```

(Version completa en el archivo `.sql`.)

- **Objetivo:** comparar los valores de cada columna codificada con el diccionario de datos
  de la TLC y encontrar codigos invalidos o "comodin".
- **Fuente:** `Y+G` (para `request_source`, solo junio-agosto).
- **Resultado (12 s), valores relevantes:**

  | Columna | Hallazgo |
  |---|---|
  | `VendorID` | yellow: 2 (80.2 %), 1 (18.4 %), 7, 6. green: 2, 6, 1. Todos estan en el diccionario. |
  | `RatecodeID` | **99 = desconocido** en 769,693 viajes yellow (2.6 %) y 2 green; 7,716,688 nulos (Flex Fare). La tarifa negociada (5) es mucho mas comun en green (5.3 %) que en yellow (0.9 %). |
  | `passenger_count` | **0 pasajeros** en 91,359 viajes yellow y 4,527 green; valores de 7 a 9 en muy pocos viajes. |
  | `payment_type` | yellow: 1 tarjeta 63.8 %, **0 Flex Fare 26.0 %**, 2 efectivo 9.1 %, 4 disputa, 3 sin cargo, 5 desconocido (2 viajes). |
  | `trip_type` (green) | 1 parada en la calle 273,386; 2 despacho 14,951; 48,777 nulos. |
  | `request_source` (jun-ago) | yellow: `HV0003` 2,295,520, `A` 403,773, `HV0005` 181,233, `EH0004` 20,769, `CC` 1,879, `EH0010` 272; nulo en el 73 % de los viajes de esos meses. green: `A` 18,029, `HV0005` 1,179, `CC` 3. |

- **Decision:**
  - `RatecodeID = 99` y `passenger_count = 0` se trataran como **valores faltantes**, no
    como categorias reales (por ejemplo, no se promedian los pasajeros incluyendo ceros).
  - `request_source` **no aparece en el diccionario de datos publicado** (version de marzo
    de 2025). Los valores `HV0003` y `HV0005` coinciden con las licencias de bases de alto
    volumen de la TLC (Uber y Lyft en los datos FHVHV), lo que sugiere que indica por
    que plataforma se pidio el taxi. Como no esta documentado y solo existe en 3 meses,
    **no se usara para conclusiones** hasta confirmar su significado.

### `q17_zonas_desconocidas`

```sql
SELECT split_part(filename, '/', 3) AS tipo, count(*) AS registros,
       count(*) FILTER (PULocationID IN (264, 265)) AS origen_264_265,
       count(*) FILTER (DOLocationID IN (264, 265)) AS destino_264_265,
       round(100.0 * count(*) FILTER (PULocationID IN (264, 265) OR DOLocationID IN (264, 265)) / count(*), 2) AS pct_afectado
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL ORDER BY tipo DESC;
```

- **Objetivo:** contar viajes con zona desconocida (264) o fuera de NYC (265).
- **Fuente:** `Y+G`.
- **Resultado (3 s):** yellow 0.68 % (49,676 origenes y 178,136 destinos); green 1.75 %
  (1,131 origenes y 5,600 destinos).
- **Decision:** afecta a pocos viajes. Se mantienen en los totales, pero se excluyen de
  los analisis geograficos por zona/borough. Que haya mas destinos que origenes en
  264/265 es esperable: los taxis recogen dentro de NYC y a veces dejan fuera de la ciudad.

### `q18_duplicados`

```sql
WITH conteos AS (
    SELECT 'yellow' AS tipo,
           (SELECT count(*) FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true)) AS registros,
           (SELECT count(*) FROM (SELECT DISTINCT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true))) AS filas_distintas
    UNION ALL
    SELECT 'green',
           (SELECT count(*) FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true)),
           (SELECT count(*) FROM (SELECT DISTINCT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true)))
)
SELECT tipo, registros, filas_distintas, registros - filas_distintas AS duplicados
FROM conteos ORDER BY tipo DESC;
```

- **Objetivo:** detectar registros exactamente duplicados (todas las columnas iguales).
- **Fuente:** `Y`, `G`.
- **Resultado (29-36 s, la consulta mas costosa del ejercicio):** yellow **7** duplicados
  (29,703,348 filas distintas); green 0.
- **Decision:** el impacto es despreciable (7 de 29.7 millones), pero si se materializa una
  tabla limpia (Ejercicio 6) se puede usar `SELECT DISTINCT`. Una primera version de la
  consulta usaba `hash(COLUMNS(*))`, pero eso calcula un hash **por columna** y no uno por
  fila, y daba un resultado falso (4 filas "distintas"). Se corrigio usando `DISTINCT *`.

---

## Resumen de decisiones para los siguientes ejercicios

1. Leer siempre con `read_parquet('data/raw/<tipo>/*/*.parquet', union_by_name = true)`.
2. Unificar las fechas con `coalesce(tpep_*, lpep_*)` cuando se combinen yellow y green.
3. Filtrar el periodo valido por fecha de pickup en analisis temporales (excluye 2001/2008).
4. Duraciones y velocidades: solo viajes entre 1 minuto y 3 horas. Distancias: usar la mediana o un tope de 100 millas.
5. Promedios de tarifa y propina: excluir montos negativos.
6. Tratar `payment_type = 0` / `NULL` como categoria propia (Flex Fare), y `RatecodeID = 99` y `passenger_count = 0` como faltantes.
7. No recalcular `total_amount` a partir de sus componentes; controlar por `VendorID` al analizar recargos.
8. No usar `request_source` (no documentada) ni `ehail_fee` (100 % nula).

---

## 3.9 Que significa consultar directamente un archivo Parquet

Consultar directamente un Parquet significa que el motor SQL usa el archivo **como si fuera
una tabla**, sin cargarlo antes en una base de datos. En DuckDB basta con
`SELECT ... FROM read_parquet('data/raw/yellow/*/*.parquet')`: el archivo se lee en el
momento de la consulta y no se crea ninguna copia de los datos. Todo este ejercicio se hizo
asi, con una base en memoria vacia.

Es util con volumenes grandes porque Parquet es un formato **columnar, comprimido y con
metadatos**, y DuckDB aprovecha las tres cosas:

- **Solo lee las columnas necesarias (*projection pushdown*).** El plan de ejecucion
  (`EXPLAIN ANALYZE`, ultima celda del notebook) de
  `SELECT payment_type, avg(tip_amount) ... WHERE tpep_pickup_datetime >= '2026-08-01'`
  muestra un `READ_PARQUET` que proyecta solo `payment_type` y `tip_amount` (y la fecha para
  el filtro) de las 21 columnas.
- **Filtra durante la lectura (*filter pushdown*).** En el mismo plan, el filtro de fecha
  aparece dentro del `READ_PARQUET` y no como un paso posterior: de las 29.7 M filas solo
  3.3 M (agosto) salen del escaneo, y la consulta completa tardo 0.3 s. Ademas, cada
  *row group* guarda el minimo y el maximo de cada columna, y DuckDB usa esas estadisticas
  para saltarse bloques que no pueden cumplir el filtro.
- **Algunas respuestas salen solo de los metadatos.** El conteo de registros por archivo
  (`q02`) tardo 0.17 s frente a 1.8 s del `count(*)` (`q03`), porque `num_rows` esta en el
  *footer* del archivo.
- **No hay paso de carga ni datos duplicados.** No hay que esperar un `INSERT` ni guardar
  una segunda copia de ~500 MB (con tres anios seran mas de 1.5 GB). Cuando llega un mes
  nuevo basta con dejar el archivo en `data/raw/<tipo>/<anio>/`: el patron `*/*.parquet`
  lo incluye automaticamente en la siguiente consulta.
- **Memoria acotada.** DuckDB procesa los datos por bloques (streaming) en lugar de cargar
  todo en RAM. Con pandas, cargar los 30 M de filas y 21 columnas ocuparia varios GB de
  memoria antes de poder hacer cualquier consulta.
- **Formato abierto.** Los mismos archivos se pueden leer desde Python, Metabase, Spark u
  otras herramientas sin conversiones.

Limitaciones observadas: cada consulta vuelve a leer y descomprimir los archivos (las que
recorren todas las columnas, como `SUMMARIZE` o `DISTINCT *`, tardaron 30-55 s), y si los
archivos no tienen el mismo esquema hay que usar `union_by_name`. La comparacion con una
tabla materializada se hace en el Ejercicio 6.
