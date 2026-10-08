-- =============================================================================
-- CC3084 - Lab 8 - Ejercicio 3
-- Consultas directas sobre archivos Parquet (sin importar a una tabla)
--
-- Todas las rutas son relativas a la raiz del proyecto (/workspace dentro del
-- contenedor `lab`). Ninguna consulta crea tablas: DuckDB lee los .parquet
-- directamente con read_parquet() / glob() / parquet_metadata().
--
-- Cada consulta empieza con una linea `-- name: <id>` para que el notebook
-- notebooks/03_exploracion_parquet.ipynb y scripts/run_sql.py puedan
-- ejecutarlas por nombre. La documentacion de cada una (objetivo, fuente,
-- resultado y decision) esta en docs/ejercicio3_exploracion.md.
--
-- Nota: se usa siempre union_by_name=true porque el esquema NO es igual en
-- todos los archivos (ver q04). Sin esa opcion DuckDB toma el esquema del
-- primer archivo y descarta en silencio las columnas que solo existen en otros.
-- =============================================================================


-- name: q01_cantidad_archivos
-- 3.1 Cantidad de archivos Parquet disponibles, por tipo de taxi y anio.
SELECT
    split_part(file, '/', 3)            AS tipo,
    split_part(file, '/', 4)            AS anio,
    count(*)                            AS archivos,
    min(regexp_extract(file, '(\d{4}-\d{2})\.parquet$', 1)) AS primer_mes,
    max(regexp_extract(file, '(\d{4}-\d{2})\.parquet$', 1)) AS ultimo_mes
FROM glob('data/raw/*/*/*.parquet')
GROUP BY ALL
ORDER BY tipo, anio;


-- name: q02_registros_por_archivo
-- 3.2 Registros por archivo leyendo solo los metadatos (footer) de cada Parquet.
SELECT
    split_part(file_name, '/', 3)       AS tipo,
    regexp_extract(file_name, '(\d{4}-\d{2})\.parquet$', 1) AS mes,
    num_rows                            AS registros,
    num_row_groups                      AS row_groups
FROM parquet_file_metadata('data/raw/*/*/*.parquet')
ORDER BY tipo, mes;


-- name: q03_total_registros
-- 3.2 Total de registros por tipo leyendo los datos (valida el resultado de q02).
SELECT
    split_part(filename, '/', 3)        AS tipo,
    count(*)                            AS registros
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL
UNION ALL
SELECT 'TOTAL', count(*)
FROM read_parquet('data/raw/*/*/*.parquet', union_by_name = true)
ORDER BY registros;


-- name: q04_consistencia_esquema
-- 3.3 / 3.4 Columnas que no aparecen en todos los archivos de su tipo, o que
-- cambian de tipo entre archivos (deriva de esquema).
WITH esquema AS (
    SELECT
        split_part(file_name, '/', 3)   AS tipo,
        file_name,
        name                            AS columna,
        type                            AS tipo_fisico,
        coalesce(logical_type::VARCHAR, converted_type::VARCHAR, '') AS tipo_logico
    FROM parquet_schema('data/raw/*/*/*.parquet')
    WHERE name <> 'schema'
),
archivos_por_tipo AS (
    SELECT tipo, count(DISTINCT file_name) AS total FROM esquema GROUP BY tipo
)
SELECT
    e.tipo,
    e.columna,
    count(DISTINCT e.file_name)         AS archivos_con_columna,
    a.total                             AS archivos_del_tipo,
    list(DISTINCT e.tipo_fisico || ' ' || e.tipo_logico) AS tipos_vistos,
    list(DISTINCT regexp_extract(e.file_name, '(\d{4}-\d{2})\.parquet$', 1)
         ORDER BY regexp_extract(e.file_name, '(\d{4}-\d{2})\.parquet$', 1)) AS meses
FROM esquema e
JOIN archivos_por_tipo a USING (tipo)
GROUP BY e.tipo, e.columna, a.total
HAVING count(DISTINCT e.file_name) <> a.total
    OR count(DISTINCT e.tipo_fisico || ' ' || e.tipo_logico) > 1
ORDER BY e.tipo, e.columna;


-- name: q05_columnas_yellow
-- 3.3 / 3.4 Columnas y tipos de datos de los taxis amarillos.
DESCRIBE SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true);


-- name: q06_columnas_green
-- 3.3 / 3.4 Columnas y tipos de datos de los taxis verdes.
DESCRIBE SELECT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true);


-- name: q07_comparacion_columnas
-- 3.3 Columnas comunes y exclusivas de cada tipo de taxi.
WITH y AS (
    SELECT column_name, column_type
    FROM (DESCRIBE SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true))
),
g AS (
    SELECT column_name, column_type
    FROM (DESCRIBE SELECT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true))
)
SELECT
    coalesce(y.column_name, g.column_name) AS columna,
    y.column_type                          AS tipo_yellow,
    g.column_type                          AS tipo_green,
    CASE WHEN y.column_name IS NULL THEN 'solo green'
         WHEN g.column_name IS NULL THEN 'solo yellow'
         WHEN y.column_type <> g.column_type THEN 'ambos (tipo distinto)'
         ELSE 'ambos' END                  AS presente_en
FROM y FULL OUTER JOIN g ON y.column_name = g.column_name
ORDER BY presente_en, columna;


-- name: q08_muestra_yellow
-- 3.5 Muestra aleatoria reproducible de taxis amarillos.
SELECT *
FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true)
USING SAMPLE reservoir(10 ROWS) REPEATABLE (42);


-- name: q09_muestra_green
-- 3.5 Muestra aleatoria reproducible de taxis verdes.
SELECT *
FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true)
USING SAMPLE reservoir(10 ROWS) REPEATABLE (42);


-- name: q10_nulos_por_columna
-- 3.6 Porcentaje de nulos por columna y tipo de taxi.
SELECT 'yellow' AS tipo, column_name AS columna, null_percentage AS pct_nulos
FROM (SUMMARIZE SELECT * FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true))
WHERE null_percentage > 0
UNION ALL
SELECT 'green', column_name, null_percentage
FROM (SUMMARIZE SELECT * FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true))
WHERE null_percentage > 0
ORDER BY tipo DESC, pct_nulos DESC, columna;


-- name: q11_nulos_simultaneos
-- 3.6 Los nulos de passenger_count, RatecodeID, store_and_fwd_flag,
-- congestion_surcharge (y Airport_fee) ocurren en las mismas filas?
SELECT
    split_part(filename, '/', 3)                             AS tipo,
    count(*)                                                 AS registros,
    count(*) FILTER (passenger_count IS NULL)                AS passenger_count_nulo,
    count(*) FILTER (passenger_count IS NULL AND RatecodeID IS NULL
                     AND store_and_fwd_flag IS NULL
                     AND congestion_surcharge IS NULL)       AS todos_nulos_juntos,
    count(*) FILTER (passenger_count IS NULL AND payment_type = 0) AS nulos_con_payment_0,
    count(*) FILTER (payment_type = 0)                       AS payment_type_0
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL
ORDER BY tipo DESC;


-- name: q12_fechas_fuera_de_periodo
-- 3.6 Viajes cuya fecha de inicio no corresponde al mes del archivo.
WITH viajes AS (
    SELECT
        split_part(filename, '/', 3)                                  AS tipo,
        strptime(regexp_extract(filename, '(\d{4}-\d{2})\.parquet$', 1), '%Y-%m')::DATE AS mes_archivo,
        coalesce(tpep_pickup_datetime, lpep_pickup_datetime)          AS pickup
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT
    tipo,
    count(*)                                                       AS registros,
    count(*) FILTER (date_trunc('month', pickup) <> mes_archivo)   AS fuera_del_mes,
    count(*) FILTER (pickup < mes_archivo - INTERVAL 1 MONTH)      AS mas_de_un_mes_antes,
    count(*) FILTER (pickup >= mes_archivo + INTERVAL 1 MONTH)     AS despues_del_mes,
    min(pickup)                                                    AS pickup_minimo,
    max(pickup)                                                    AS pickup_maximo
FROM viajes
GROUP BY tipo
ORDER BY tipo DESC;


-- name: q13_duracion_viajes
-- 3.6 Duraciones imposibles o sospechosas.
WITH viajes AS (
    SELECT
        split_part(filename, '/', 3) AS tipo,
        date_diff('second',
                  coalesce(tpep_pickup_datetime, lpep_pickup_datetime),
                  coalesce(tpep_dropoff_datetime, lpep_dropoff_datetime)) / 60.0 AS minutos
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT
    tipo,
    count(*)                                        AS registros,
    count(*) FILTER (minutos < 0)                   AS dropoff_antes_de_pickup,
    count(*) FILTER (minutos = 0)                   AS duracion_cero,
    count(*) FILTER (minutos > 0 AND minutos < 1)   AS menos_de_1_min,
    count(*) FILTER (minutos > 180)                 AS mas_de_3_horas,
    count(*) FILTER (minutos > 1440)                AS mas_de_24_horas,
    round(quantile_cont(minutos, 0.5), 2)           AS mediana_min,
    round(quantile_cont(minutos, 0.99), 2)          AS p99_min,
    round(max(minutos), 1)                          AS max_min
FROM viajes
GROUP BY tipo
ORDER BY tipo DESC;


-- name: q14_distancias
-- 3.6 Distancias en cero o extremas (trip_distance esta en millas).
SELECT
    split_part(filename, '/', 3)                           AS tipo,
    count(*)                                               AS registros,
    count(*) FILTER (trip_distance = 0)                    AS distancia_cero,
    count(*) FILTER (trip_distance > 100)                  AS mas_de_100_millas,
    count(*) FILTER (trip_distance > 1000)                 AS mas_de_1000_millas,
    round(quantile_cont(trip_distance, 0.5), 2)            AS mediana_millas,
    round(quantile_cont(trip_distance, 0.99), 2)           AS p99_millas,
    max(trip_distance)                                     AS max_millas
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL
ORDER BY tipo DESC;


-- name: q15_montos
-- 3.6 Montos negativos, en cero, extremos e inconsistentes con sus componentes.
WITH viajes AS (
    SELECT
        split_part(filename, '/', 3) AS tipo,
        *,
        fare_amount + extra + mta_tax + tip_amount + tolls_amount
          + improvement_surcharge
          + coalesce(congestion_surcharge, 0) + coalesce(Airport_fee, 0)
          + coalesce(cbd_congestion_fee, 0) + coalesce(ehail_fee, 0) AS suma_componentes
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT
    tipo,
    count(*)                                                   AS registros,
    count(*) FILTER (fare_amount < 0)                          AS tarifa_negativa,
    count(*) FILTER (total_amount < 0)                         AS total_negativo,
    count(*) FILTER (total_amount = 0)                         AS total_cero,
    count(*) FILTER (tip_amount < 0)                           AS propina_negativa,
    count(*) FILTER (total_amount > 500)                       AS total_mayor_500,
    count(*) FILTER (abs(total_amount - suma_componentes) > 0.01) AS total_no_cuadra,
    round(100.0 * count(*) FILTER (abs(total_amount - suma_componentes) > 0.01) / count(*), 2)
                                                               AS pct_no_cuadra
FROM viajes
GROUP BY tipo
ORDER BY tipo DESC;


-- name: q15b_montos_por_proveedor
-- 3.6 Diferencia entre total_amount y la suma de componentes, por proveedor y
-- forma de pago. Sirve para saber si el total esta mal o si cada proveedor
-- codifica los recargos de forma distinta.
WITH viajes AS (
    SELECT
        split_part(filename, '/', 3) AS tipo,
        VendorID,
        coalesce(payment_type::VARCHAR, 'NULL') AS payment_type,
        round(total_amount - (
            fare_amount + extra + mta_tax + tip_amount + tolls_amount
            + improvement_surcharge
            + coalesce(congestion_surcharge, 0) + coalesce(Airport_fee, 0)
            + coalesce(cbd_congestion_fee, 0) + coalesce(ehail_fee, 0)), 2) AS diferencia
    FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
)
SELECT
    tipo,
    VendorID,
    payment_type,
    count(*)                                         AS registros,
    count(*) FILTER (abs(diferencia) > 0.01)         AS no_cuadra,
    round(100.0 * count(*) FILTER (abs(diferencia) > 0.01) / count(*), 1) AS pct_no_cuadra,
    mode(diferencia) FILTER (abs(diferencia) > 0.01) AS diferencia_mas_comun
FROM viajes
GROUP BY ALL
HAVING count(*) > 1000
ORDER BY tipo DESC, VendorID, payment_type;


-- name: q16_codigos_categoricos
-- 3.6 Distribucion de las columnas codificadas, para detectar codigos fuera del
-- diccionario de datos de la TLC.
SELECT split_part(filename, '/', 3) AS tipo, 'VendorID' AS columna,
       VendorID::VARCHAR AS valor, count(*) AS registros
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL
SELECT split_part(filename, '/', 3), 'RatecodeID', RatecodeID::VARCHAR, count(*)
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL
SELECT split_part(filename, '/', 3), 'payment_type', payment_type::VARCHAR, count(*)
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL
SELECT split_part(filename, '/', 3), 'passenger_count', passenger_count::VARCHAR, count(*)
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL
SELECT split_part(filename, '/', 3), 'trip_type', trip_type::VARCHAR, count(*)
FROM read_parquet('data/raw/green/*/*.parquet', filename = true, union_by_name = true) GROUP BY ALL
UNION ALL
SELECT split_part(filename, '/', 3), 'request_source', request_source, count(*)
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
WHERE regexp_extract(filename, '\d{4}-(\d{2})\.parquet$', 1) >= '06'
GROUP BY ALL
ORDER BY tipo DESC, columna, registros DESC;


-- name: q17_zonas_desconocidas
-- 3.6 Viajes con zona de origen o destino 264/265 (zonas "Unknown"/"Outside of NYC"
-- en la tabla de zonas de la TLC).
SELECT
    split_part(filename, '/', 3)                                   AS tipo,
    count(*)                                                       AS registros,
    count(*) FILTER (PULocationID IN (264, 265))                   AS origen_264_265,
    count(*) FILTER (DOLocationID IN (264, 265))                   AS destino_264_265,
    round(100.0 * count(*) FILTER (PULocationID IN (264, 265)
                                   OR DOLocationID IN (264, 265)) / count(*), 2) AS pct_afectado
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true)
GROUP BY ALL
ORDER BY tipo DESC;


-- name: q18_duplicados
-- 3.6 Registros exactamente duplicados (todas las columnas iguales).
-- Es la consulta mas costosa del ejercicio (~1 min): DISTINCT sobre ~30 M de filas.
WITH conteos AS (
    SELECT 'yellow' AS tipo,
           (SELECT count(*) FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true)) AS registros,
           (SELECT count(*) FROM (SELECT DISTINCT *
               FROM read_parquet('data/raw/yellow/*/*.parquet', union_by_name = true))) AS filas_distintas
    UNION ALL
    SELECT 'green',
           (SELECT count(*) FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true)),
           (SELECT count(*) FROM (SELECT DISTINCT *
               FROM read_parquet('data/raw/green/*/*.parquet', union_by_name = true)))
)
SELECT tipo, registros, filas_distintas, registros - filas_distintas AS duplicados
FROM conteos
ORDER BY tipo DESC;
