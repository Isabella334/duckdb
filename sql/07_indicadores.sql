-- =============================================================================
-- CC3084 - Lab 8 - Ejercicios 7 y 8
-- Indicadores del tablero
--
-- scripts/indicadores.py ejecuta este archivo y guarda cada indicador como una
-- tabla pequenia en data/processed/indicadores.duckdb. Metabase y los notebooks
-- 07 y 08 leen esas tablas, no los Parquet.
--
-- - viajes y viajes_limpios se crean como vistas temporales sobre los Parquet
--   (las mismas del Ejercicio 4, con el anio y el mes del archivo). No se guardan
--   en la base porque sus rutas solo tienen sentido dentro del contenedor `lab`.
-- - zonas y todas las consultas i01..i10 se guardan como tablas.
--
-- Todas las consultas leen data/raw/*/*/*.parquet, asi que un anio nuevo entra
-- solo al volver a ejecutar el script. Todos los indicadores se separan por
-- tipo y anio para no mezclar anios (ver Ejercicio 5.7).
-- =============================================================================


-- name: viajes
-- Vista con nombres de columna comunes para yellow y green. tipo, anio y mes salen de la ruta del archivo.
SELECT
    split_part(filename, '/', 3)                                        AS tipo,
    strptime(regexp_extract(filename, '(\d{4}-\d{2})\.parquet$', 1), '%Y-%m')::DATE AS mes_archivo,
    year(mes_archivo)                                                   AS anio,
    month(mes_archivo)                                                  AS mes,
    VendorID                                                            AS vendor_id,
    coalesce(tpep_pickup_datetime,  lpep_pickup_datetime)               AS pickup,
    coalesce(tpep_dropoff_datetime, lpep_dropoff_datetime)              AS dropoff,
    date_diff('second', coalesce(tpep_pickup_datetime,  lpep_pickup_datetime),
                        coalesce(tpep_dropoff_datetime, lpep_dropoff_datetime)) / 60.0 AS duracion_min,
    passenger_count, trip_distance,
    RatecodeID AS ratecode_id, PULocationID AS pu_zona, DOLocationID AS do_zona,
    payment_type, fare_amount, extra, mta_tax, tip_amount, tolls_amount,
    improvement_surcharge, congestion_surcharge, cbd_congestion_fee,
    Airport_fee AS airport_fee, total_amount, trip_type
FROM read_parquet('data/raw/*/*/*.parquet', filename = true, union_by_name = true);


-- name: viajes_limpios
-- Misma regla de limpieza del Ejercicio 4.
SELECT *
FROM viajes
WHERE date_trunc('month', pickup) = mes_archivo
  AND duracion_min BETWEEN 1 AND 180
  AND trip_distance > 0 AND trip_distance <= 100
  AND fare_amount >= 0 AND total_amount >= 0 AND tip_amount >= 0;


-- name: zonas
-- Tabla de zonas de la TLC (LocationID -> borough y nombre de la zona).
SELECT LocationID AS zona, Borough AS borough, Zone AS nombre_zona
FROM read_csv('https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv');


-- name: i01_demanda_mensual
-- P1. Cuantos viajes hay por dia en cada mes y como cambia entre anios.
-- Se usa el promedio por dia para que los meses de distinta duracion sean comparables.
SELECT tipo, anio, mes,
       make_date(anio, mes, 1)                               AS fecha,
       count(*)                                              AS viajes,
       count(DISTINCT pickup::DATE)                          AS dias,
       round(count(*) / count(DISTINCT pickup::DATE))        AS viajes_por_dia
FROM viajes_limpios
GROUP BY ALL
ORDER BY tipo DESC, anio, mes;


-- name: i02_resumen_anual
-- P2. Cuanto pesa cada tipo de taxi en viajes e ingresos y que parte son viajes de aeropuerto.
-- Los anios no tienen la misma cantidad de meses, por eso se comparan valores por dia.
SELECT tipo, anio,
       count(DISTINCT mes)                                                    AS meses,
       count(*)                                                               AS viajes,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY anio), 2)    AS pct_viajes_del_anio,
       round(count(*) / count(DISTINCT pickup::DATE))                         AS viajes_por_dia,
       round(sum(total_amount) / count(DISTINCT pickup::DATE))                AS ingreso_por_dia_usd,
       round(sum(total_amount) / 1e6, 1)                                      AS ingreso_total_musd,
       round(100.0 * avg((coalesce(ratecode_id, 0) IN (2, 3)
                          OR coalesce(airport_fee, 0) > 0
                          OR pu_zona IN (1, 132, 138) OR do_zona IN (1, 132, 138))::INT), 2) AS pct_aeropuerto
FROM viajes_limpios
GROUP BY tipo, anio
ORDER BY tipo DESC, anio;


-- name: i03_demanda_por_hora
-- P3. A que horas del dia se concentran los viajes.
SELECT tipo, anio, hour(pickup) AS hora,
       count(*)                                                                 AS viajes,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY tipo, anio), 2) AS pct_viajes
FROM viajes_limpios
GROUP BY tipo, anio, hora
ORDER BY tipo DESC, anio, hora;


-- name: i04_velocidad_por_hora
-- P4. A que horas hay mas congestion (velocidad mediana de los viajes).
SELECT tipo, anio, hour(pickup) AS hora,
       round(median(trip_distance / (duracion_min / 60)), 1) AS velocidad_mediana_mph
FROM viajes_limpios
GROUP BY ALL
ORDER BY tipo DESC, anio, hora;


-- name: i05_viaje_tipico
-- P5. Como es el viaje tipico (distancia y duracion medianas) y si cambia con el tiempo.
SELECT tipo, anio, mes,
       make_date(anio, mes, 1)              AS fecha,
       round(median(trip_distance), 2)      AS distancia_mediana_mi,
       round(median(duracion_min), 1)       AS duracion_mediana_min
FROM viajes_limpios
GROUP BY ALL
ORDER BY tipo DESC, anio, mes;


-- name: i06_costo_y_recargos
-- P6. Cuanto cuesta un viaje y que parte del cobro son recargos (incluye el cargo CBD de 2025).
-- Recargos = total - tarifa - propina - peajes.
SELECT tipo, anio, mes,
       make_date(anio, mes, 1)                                                    AS fecha,
       round(median(total_amount), 2)                                             AS total_mediano_usd,
       round(avg(total_amount - fare_amount - tip_amount - tolls_amount), 2)      AS recargos_promedio_usd,
       round(100 * sum(total_amount - fare_amount - tip_amount - tolls_amount)
                 / sum(total_amount), 1)                                          AS pct_del_total_en_recargos,
       round(100.0 * avg((coalesce(cbd_congestion_fee, 0) > 0)::INT), 1)          AS pct_con_cargo_cbd
FROM viajes_limpios
WHERE total_amount > 0
GROUP BY ALL
ORDER BY tipo DESC, anio, mes;


-- name: i07_formas_pago
-- P7. Como pagan los pasajeros y si eso cambia con el tiempo.
-- payment_type 0 o NULL son viajes Flex Fare / sin dato (ver Ejercicio 4).
SELECT tipo, anio, mes,
       make_date(anio, mes, 1)                                          AS fecha,
       round(100.0 * avg((coalesce(payment_type, 0) = 1)::INT), 1)      AS pct_tarjeta,
       round(100.0 * avg((coalesce(payment_type, 0) = 2)::INT), 1)      AS pct_efectivo,
       round(100.0 * avg((coalesce(payment_type, 0) = 0)::INT), 1)      AS pct_flex_fare,
       round(100.0 * avg((coalesce(payment_type, 0) >= 3)::INT), 1)     AS pct_otros
FROM viajes_limpios
GROUP BY ALL
ORDER BY tipo DESC, anio, mes;


-- name: i08_propinas
-- P8. Cuanta propina se deja con tarjeta (las propinas en efectivo no se registran).
SELECT tipo, anio, mes,
       make_date(anio, mes, 1)                                          AS fecha,
       round(100 * median(tip_amount / fare_amount), 1)                 AS propina_mediana_pct,
       round(100.0 * avg((tip_amount = 0)::INT), 1)                     AS pct_sin_propina
FROM viajes_limpios
WHERE payment_type = 1 AND fare_amount > 0
GROUP BY ALL
ORDER BY tipo DESC, anio, mes;


-- name: i09_origen_borough
-- P9. De que borough salen los viajes.
SELECT v.tipo, v.anio, coalesce(z.borough, 'Unknown') AS borough,
       count(*)                                                                     AS viajes,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY v.tipo, v.anio), 2) AS pct_viajes
FROM viajes_limpios v
LEFT JOIN zonas z ON v.pu_zona = z.zona
GROUP BY v.tipo, v.anio, borough
ORDER BY v.tipo DESC, v.anio, viajes DESC;


-- name: i10_calidad_datos
-- P10. Que parte de los registros se descarta por la regla de limpieza en cada mes.
SELECT t.tipo, t.anio, t.mes,
       make_date(t.anio, t.mes, 1)                                  AS fecha,
       t.registros,
       l.registros                                                  AS registros_limpios,
       round(100.0 * (t.registros - l.registros) / t.registros, 2)  AS pct_descartado
FROM (SELECT tipo, anio, mes, count(*) AS registros FROM viajes GROUP BY ALL) t
JOIN (SELECT tipo, anio, mes, count(*) AS registros FROM viajes_limpios GROUP BY ALL) l
  USING (tipo, anio, mes)
ORDER BY t.tipo DESC, t.anio, t.mes;
