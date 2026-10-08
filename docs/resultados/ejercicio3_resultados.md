# Resultados de `sql/03_exploracion_parquet.sql`

Generado con `scripts/run_sql.py` el 2026-10-08 15:02 UTC, DuckDB v1.5.5.

## q01_cantidad_archivos

3.1 Cantidad de archivos Parquet disponibles, por tipo de taxi y anio.

_2 filas, 1.75 s_

| tipo | anio | archivos | primer_mes | ultimo_mes |
|---|---|---|---|---|
| green | 2026 | 8 | 2026-01 | 2026-08 |
| yellow | 2026 | 8 | 2026-01 | 2026-08 |

## q02_registros_por_archivo

3.2 Registros por archivo leyendo solo los metadatos (footer) de cada Parquet.

_16 filas, 0.10 s_

| tipo | mes | registros | row_groups |
|---|---|---|---|
| green | 2026-01 | 40,272 | 1 |
| green | 2026-02 | 37,373 | 1 |
| green | 2026-03 | 44,208 | 1 |
| green | 2026-04 | 44,238 | 1 |
| green | 2026-05 | 44,921 | 1 |
| green | 2026-06 | 44,163 | 1 |
| green | 2026-07 | 41,252 | 1 |
| green | 2026-08 | 40,687 | 1 |
| yellow | 2026-01 | 3,724,889 | 4 |
| yellow | 2026-02 | 3,399,866 | 4 |
| yellow | 2026-03 | 3,952,451 | 4 |
| yellow | 2026-04 | 3,831,240 | 4 |
| yellow | 2026-05 | 4,090,836 | 4 |
| yellow | 2026-06 | 3,837,248 | 4 |
| yellow | 2026-07 | 3,530,109 | 4 |
| yellow | 2026-08 | 3,336,716 | 4 |

## q03_total_registros

3.2 Total de registros por tipo leyendo los datos (valida el resultado de q02).

_3 filas, 2.35 s_

| tipo | registros |
|---|---|
| green | 337,114 |
| yellow | 29,703,355 |
| TOTAL | 30,040,469 |

## q04_consistencia_esquema

3.3 / 3.4 Columnas que no aparecen en todos los archivos de su tipo, o que cambian de tipo entre archivos (deriva de esquema).

_2 filas, 0.27 s_

| tipo | columna | archivos_con_columna | archivos_del_tipo | tipos_vistos | meses |
|---|---|---|---|---|---|
| green | request_source | 3 | 8 | ['BYTE_ARRAY StringType()'] | ['2026-06' '2026-07' '2026-08'] |
| yellow | request_source | 3 | 8 | ['BYTE_ARRAY StringType()'] | ['2026-06' '2026-07' '2026-08'] |

## q05_columnas_yellow

3.3 / 3.4 Columnas y tipos de datos de los taxis amarillos.

_21 filas, 0.08 s_

| column_name | column_type | null | key | default | extra |
|---|---|---|---|---|---|
| VendorID | INTEGER | YES | NULL | NULL | NULL |
| tpep_pickup_datetime | TIMESTAMP | YES | NULL | NULL | NULL |
| tpep_dropoff_datetime | TIMESTAMP | YES | NULL | NULL | NULL |
| passenger_count | BIGINT | YES | NULL | NULL | NULL |
| trip_distance | DOUBLE | YES | NULL | NULL | NULL |
| RatecodeID | BIGINT | YES | NULL | NULL | NULL |
| store_and_fwd_flag | VARCHAR | YES | NULL | NULL | NULL |
| PULocationID | INTEGER | YES | NULL | NULL | NULL |
| DOLocationID | INTEGER | YES | NULL | NULL | NULL |
| payment_type | BIGINT | YES | NULL | NULL | NULL |
| fare_amount | DOUBLE | YES | NULL | NULL | NULL |
| extra | DOUBLE | YES | NULL | NULL | NULL |
| mta_tax | DOUBLE | YES | NULL | NULL | NULL |
| tip_amount | DOUBLE | YES | NULL | NULL | NULL |
| tolls_amount | DOUBLE | YES | NULL | NULL | NULL |
| improvement_surcharge | DOUBLE | YES | NULL | NULL | NULL |
| total_amount | DOUBLE | YES | NULL | NULL | NULL |
| congestion_surcharge | DOUBLE | YES | NULL | NULL | NULL |
| Airport_fee | DOUBLE | YES | NULL | NULL | NULL |
| cbd_congestion_fee | DOUBLE | YES | NULL | NULL | NULL |
| request_source | VARCHAR | YES | NULL | NULL | NULL |

## q06_columnas_green

3.3 / 3.4 Columnas y tipos de datos de los taxis verdes.

_22 filas, 0.08 s_

| column_name | column_type | null | key | default | extra |
|---|---|---|---|---|---|
| VendorID | INTEGER | YES | NULL | NULL | NULL |
| lpep_pickup_datetime | TIMESTAMP | YES | NULL | NULL | NULL |
| lpep_dropoff_datetime | TIMESTAMP | YES | NULL | NULL | NULL |
| store_and_fwd_flag | VARCHAR | YES | NULL | NULL | NULL |
| RatecodeID | BIGINT | YES | NULL | NULL | NULL |
| PULocationID | INTEGER | YES | NULL | NULL | NULL |
| DOLocationID | INTEGER | YES | NULL | NULL | NULL |
| passenger_count | BIGINT | YES | NULL | NULL | NULL |
| trip_distance | DOUBLE | YES | NULL | NULL | NULL |
| fare_amount | DOUBLE | YES | NULL | NULL | NULL |
| extra | DOUBLE | YES | NULL | NULL | NULL |
| mta_tax | DOUBLE | YES | NULL | NULL | NULL |
| tip_amount | DOUBLE | YES | NULL | NULL | NULL |
| tolls_amount | DOUBLE | YES | NULL | NULL | NULL |
| ehail_fee | DOUBLE | YES | NULL | NULL | NULL |
| improvement_surcharge | DOUBLE | YES | NULL | NULL | NULL |
| total_amount | DOUBLE | YES | NULL | NULL | NULL |
| payment_type | BIGINT | YES | NULL | NULL | NULL |
| trip_type | BIGINT | YES | NULL | NULL | NULL |
| congestion_surcharge | DOUBLE | YES | NULL | NULL | NULL |
| cbd_congestion_fee | DOUBLE | YES | NULL | NULL | NULL |
| request_source | VARCHAR | YES | NULL | NULL | NULL |

## q07_comparacion_columnas

3.3 Columnas comunes y exclusivas de cada tipo de taxi.

_25 filas, 0.15 s_

| columna | tipo_yellow | tipo_green | presente_en |
|---|---|---|---|
| DOLocationID | INTEGER | INTEGER | ambos |
| PULocationID | INTEGER | INTEGER | ambos |
| RatecodeID | BIGINT | BIGINT | ambos |
| VendorID | INTEGER | INTEGER | ambos |
| cbd_congestion_fee | DOUBLE | DOUBLE | ambos |
| congestion_surcharge | DOUBLE | DOUBLE | ambos |
| extra | DOUBLE | DOUBLE | ambos |
| fare_amount | DOUBLE | DOUBLE | ambos |
| improvement_surcharge | DOUBLE | DOUBLE | ambos |
| mta_tax | DOUBLE | DOUBLE | ambos |
| passenger_count | BIGINT | BIGINT | ambos |
| payment_type | BIGINT | BIGINT | ambos |
| request_source | VARCHAR | VARCHAR | ambos |
| store_and_fwd_flag | VARCHAR | VARCHAR | ambos |
| tip_amount | DOUBLE | DOUBLE | ambos |
| tolls_amount | DOUBLE | DOUBLE | ambos |
| total_amount | DOUBLE | DOUBLE | ambos |
| trip_distance | DOUBLE | DOUBLE | ambos |
| ehail_fee | NULL | DOUBLE | solo green |
| lpep_dropoff_datetime | NULL | TIMESTAMP | solo green |
| lpep_pickup_datetime | NULL | TIMESTAMP | solo green |
| trip_type | NULL | BIGINT | solo green |
| Airport_fee | DOUBLE | NULL | solo yellow |
| tpep_dropoff_datetime | TIMESTAMP | NULL | solo yellow |
| tpep_pickup_datetime | TIMESTAMP | NULL | solo yellow |

## q08_muestra_yellow

3.5 Muestra aleatoria reproducible de taxis amarillos.

_10 filas, 0.44 s_

| VendorID | tpep_pickup_datetime | tpep_dropoff_datetime | passenger_count | trip_distance | RatecodeID | store_and_fwd_flag | PULocationID | DOLocationID | payment_type | fare_amount | extra | mta_tax | tip_amount | tolls_amount | improvement_surcharge | total_amount | congestion_surcharge | Airport_fee | cbd_congestion_fee | request_source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 2026-01-01 04:31:37 | 2026-01-01 04:36:45 | 3 | 1.01 | 1 | N | 246 | 48 | 1 | 7.2 | 1 | 0.5 | 2.59 | 0 | 1 | 15.54 | 2.5 | 0 | 0.75 | NULL |
| 2 | 2026-01-01 07:47:21 | 2026-01-01 07:49:32 | 1 | 0.39 | 1 | N | 141 | 141 | 1 | 4.4 | 0 | 0.5 | 1 | 0 | 1 | 9.4 | 2.5 | 0 | 0 | NULL |
| 2 | 2026-01-01 10:21:39 | 2026-01-01 10:24:35 | 1 | 0.72 | 1 | N | 50 | 246 | 1 | 5.8 | 0 | 0.5 | 2.64 | 0 | 1 | 13.19 | 2.5 | 0 | 0.75 | NULL |
| 1 | 2026-01-01 11:58:50 | 2026-01-01 12:07:08 | 1 | 1.7 | 1 | N | 239 | 161 | 1 | 10 | 3.25 | 0.5 | 2.95 | 0 | 1 | 17.7 | 2.5 | 0 | 0.75 | NULL |
| 2 | 2026-01-01 12:39:27 | 2026-01-01 12:52:43 | 1 | 4.79 | 1 | N | 140 | 232 | 1 | 21.2 | 0 | 0.5 | 5.19 | 0 | 1 | 31.14 | 2.5 | 0 | 0.75 | NULL |
| 2 | 2026-01-01 13:42:32 | 2026-01-01 13:54:47 | 1 | 1.37 | 1 | N | 162 | 68 | 1 | 12.1 | 0 | 0.5 | 3.37 | 0 | 1 | 20.22 | 2.5 | 0 | 0.75 | NULL |
| 2 | 2026-01-01 13:28:55 | 2026-01-01 13:37:15 | 3 | 1.43 | 1 | N | 100 | 164 | 1 | 9.3 | 0 | 0.5 | 2.81 | 0 | 1 | 16.86 | 2.5 | 0 | 0.75 | NULL |
| 2 | 2026-01-01 14:04:13 | 2026-01-01 14:27:47 | 4 | 10.19 | 1 | N | 100 | 138 | 1 | 42.2 | 5 | 0.5 | 2 | 6.94 | 1 | 60.89 | 2.5 | 0 | 0.75 | NULL |
| 1 | 2026-01-01 15:35:24 | 2026-01-01 16:07:48 | 1 | 22 | 1 | N | 132 | 60 | 1 | 80.7 | 0 | 0.5 | 22.3 | 6.94 | 1 | 111.44 | 0 | 0 | 0 | NULL |
| 2 | 2026-01-01 15:40:44 | 2026-01-01 16:26:18 | 1 | 19.12 | 2 | N | 132 | 79 | 1 | 70 | 0 | 0.5 | 5 | 0 | 1 | 81.5 | 2.5 | 1.75 | 0.75 | NULL |

## q09_muestra_green

3.5 Muestra aleatoria reproducible de taxis verdes.

_10 filas, 0.22 s_

| VendorID | lpep_pickup_datetime | lpep_dropoff_datetime | store_and_fwd_flag | RatecodeID | PULocationID | DOLocationID | passenger_count | trip_distance | fare_amount | extra | mta_tax | tip_amount | tolls_amount | ehail_fee | improvement_surcharge | total_amount | payment_type | trip_type | congestion_surcharge | cbd_congestion_fee | request_source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 2026-01-03 10:31:59 | 2026-01-03 10:35:48 | N | 1 | 75 | 263 | 1 | 0.63 | 5.8 | 0 | 0.5 | 0 | 0 | NULL | 1 | 10.05 | 2 | 1 | 2.75 | 0 | NULL |
| 2 | 2026-01-16 19:55:39 | 2026-01-16 20:12:48 | N | 1 | 97 | 61 | 1 | 3.06 | 18.4 | 1 | 0.5 | 0 | 0 | NULL | 1 | 20.9 | 2 | 1 | 0 | 0 | NULL |
| 2 | 2026-01-19 13:09:08 | 2026-01-19 13:29:44 | N | 1 | 65 | 225 | 1 | 2.98 | 19.8 | 0 | 0.5 | 5 | 0 | NULL | 1 | 26.3 | 1 | 1 | 0 | 0 | NULL |
| 2 | 2026-01-21 17:01:53 | 2026-01-21 17:10:44 | N | 1 | 43 | 263 | 2 | 0.65 | 9.3 | 2.5 | 0.5 | 2.66 | 0 | NULL | 1 | 15.96 | 1 | 1 | 0 | 0 | NULL |
| 2 | 2026-01-23 16:43:58 | 2026-01-23 16:57:21 | N | 1 | 223 | 138 | 1 | 3.53 | 17.7 | 7.5 | 0.5 | 5.34 | 0 | NULL | 1 | 32.04 | 1 | 1 | 0 | 0 | NULL |
| 2 | 2026-01-27 13:42:53 | 2026-01-27 14:03:40 | N | 1 | 74 | 151 | 1 | 2.62 | 19.1 | 0 | 0.5 | 5.15 | 0 | NULL | 1 | 25.75 | 1 | 1 | 0 | 0 | NULL |
| 1 | 2026-01-30 07:39:44 | 2026-01-30 07:45:09 | N | 1 | 74 | 41 | 0 | 0.6 | 6.5 | 0 | 1.5 | 0 | 0 | NULL | 1 | 8 | 2 | 1 | 0 | 0 | NULL |
| 2 | 2026-01-30 23:18:59 | 2026-01-30 23:30:41 | N | 1 | 97 | 66 | 1 | 1.37 | 11.4 | 1 | 0.5 | 2.08 | 0 | NULL | 1 | 15.98 | 1 | 1 | 0 | 0 | NULL |
| 2 | 2026-01-06 16:11:00 | 2026-01-06 16:35:00 | NULL | <NA> | 159 | 151 | <NA> | 3.16 | 28.59 | 0 | 0.5 | 0 | 0 | NULL | 1 | 30.09 | <NA> | <NA> | NULL | 0 | NULL |
| 6 | 2026-01-22 15:42:50 | 2026-01-22 16:03:37 | NULL | <NA> | 130 | 218 | <NA> | 3.23 | 3 | 0 | 0.5 | 0 | 0 | NULL | 0.3 | 17.26 | <NA> | <NA> | NULL | 0 | NULL |

## q10_nulos_por_columna

3.6 Porcentaje de nulos por columna y tipo de taxi.

_14 filas, 53.18 s_

| tipo | columna | pct_nulos |
|---|---|---|
| yellow | request_source | 90.23 |
| yellow | Airport_fee | 25.98 |
| yellow | RatecodeID | 25.98 |
| yellow | congestion_surcharge | 25.98 |
| yellow | passenger_count | 25.98 |
| yellow | store_and_fwd_flag | 25.98 |
| green | ehail_fee | 100 |
| green | request_source | 94.3 |
| green | RatecodeID | 14.47 |
| green | congestion_surcharge | 14.47 |
| green | passenger_count | 14.47 |
| green | payment_type | 14.47 |
| green | store_and_fwd_flag | 14.47 |
| green | trip_type | 14.47 |

## q11_nulos_simultaneos

3.6 Los nulos de passenger_count, RatecodeID, store_and_fwd_flag, congestion_surcharge (y Airport_fee) ocurren en las mismas filas?

_2 filas, 3.48 s_

| tipo | registros | passenger_count_nulo | todos_nulos_juntos | nulos_con_payment_0 | payment_type_0 |
|---|---|---|---|---|---|
| yellow | 29,703,355 | 7,716,688 | 7,716,688 | 7,716,688 | 7,716,688 |
| green | 337,114 | 48,775 | 48,775 | 0 | 0 |

## q12_fechas_fuera_de_periodo

3.6 Viajes cuya fecha de inicio no corresponde al mes del archivo.

_2 filas, 4.30 s_

| tipo | registros | fuera_del_mes | mas_de_un_mes_antes | despues_del_mes | pickup_minimo | pickup_maximo |
|---|---|---|---|---|---|---|
| yellow | 29,703,355 | 146 | 26 | 47 | 2001-01-01 09:23:58 | 2026-08-31 23:59:59 |
| green | 337,114 | 98 | 10 | 29 | 2008-12-31 17:35:31 | 2026-08-31 23:58:28 |

## q13_duracion_viajes

3.6 Duraciones imposibles o sospechosas.

_2 filas, 7.30 s_

| tipo | registros | dropoff_antes_de_pickup | duracion_cero | menos_de_1_min | mas_de_3_horas | mas_de_24_horas | mediana_min | p99_min | max_min |
|---|---|---|---|---|---|---|---|---|---|
| yellow | 29,703,355 | 10 | 371,673 | 309,479 | 10,127 | 263 | 13.93 | 71.17 | 17,165.4 |
| green | 337,114 | 5 | 229 | 11,042 | 1,287 | 4 | 13.07 | 82.23 | 2,456.4 |

## q14_distancias

3.6 Distancias en cero o extremas (trip_distance esta en millas).

_2 filas, 6.34 s_

| tipo | registros | distancia_cero | mas_de_100_millas | mas_de_1000_millas | mediana_millas | p99_millas | max_millas |
|---|---|---|---|---|---|---|---|
| yellow | 29,703,355 | 952,231 | 1,223 | 615 | 1.86 | 19.5 | 328,522.2 |
| green | 337,114 | 12,212 | 72 | 66 | 2.07 | 17.76 | 179,830.92 |

## q15_montos

3.6 Montos negativos, en cero, extremos e inconsistentes con sus componentes.

_2 filas, 6.48 s_

| tipo | registros | tarifa_negativa | total_negativo | total_cero | propina_negativa | total_mayor_500 | total_no_cuadra | pct_no_cuadra |
|---|---|---|---|---|---|---|---|---|
| yellow | 29,703,355 | 157,364 | 161,835 | 5,258 | 883 | 791 | 10,895,756 | 36.68 |
| green | 337,114 | 999 | 1,023 | 543 | 69 | 21 | 66,970 | 19.87 |

## q15b_montos_por_proveedor

3.6 Diferencia entre total_amount y la suma de componentes, por proveedor y forma de pago. Sirve para saber si el total esta mal o si cada proveedor codifica los recargos de forma distinta.

_22 filas, 6.14 s_

| tipo | VendorID | payment_type | registros | no_cuadra | pct_no_cuadra | diferencia_mas_comun |
|---|---|---|---|---|---|---|
| yellow | 1 | 0 | 895,381 | 881,364 | 98.4 | 2.5 |
| yellow | 1 | 1 | 4,028,246 | 3,315,691 | 82.3 | -3.25 |
| yellow | 1 | 2 | 447,521 | 416,904 | 93.2 | -3.25 |
| yellow | 1 | 3 | 59,767 | 50,793 | 85 | -3.25 |
| yellow | 1 | 4 | 36,154 | 28,447 | 78.7 | -3.25 |
| yellow | 2 | 0 | 6,761,917 | 5,963,133 | 88.2 | 2.5 |
| yellow | 2 | 1 | 14,592,874 | 16,620 | 0.1 | 2.5 |
| yellow | 2 | 2 | 2,217,837 | 5,381 | 0.2 | 2.5 |
| yellow | 2 | 3 | 35,455 | 70 | 0.2 | -2.5 |
| yellow | 2 | 4 | 201,691 | 416 | 0.2 | -2.5 |
| yellow | 6 | 0 | 59,390 | 59,389 | 100 | 12.2 |
| yellow | 7 | 1 | 319,888 | 139,226 | 43.5 | 1 |
| yellow | 7 | 2 | 42,673 | 16,170 | 37.9 | 1 |
| yellow | 7 | 3 | 2,916 | 1,126 | 38.6 | 1 |
| yellow | 7 | 4 | 1,643 | 748 | 45.5 | 1 |
| green | 1 | 1 | 21,902 | 21,381 | 97.6 | -1 |
| green | 1 | 2 | 5,514 | 5,391 | 97.8 | -1 |
| green | 2 | 1 | 198,078 | 67 | 0 | 2.5 |
| green | 2 | 2 | 60,407 | 39 | 0.1 | 2.5 |
| green | 2 | 3 | 1,128 | 0 | 0 | NULL |
| green | 2 | NULL | 13,400 | 4,345 | 32.4 | 2.75 |
| green | 6 | NULL | 34,847 | 34,847 | 100 | 12.2 |

## q16_codigos_categoricos

3.6 Distribucion de las columnas codificadas, para detectar codigos fuera del diccionario de datos de la TLC.

_70 filas, 11.45 s_

| tipo | columna | valor | registros |
|---|---|---|---|
| yellow | RatecodeID | 1 | 20,102,072 |
| yellow | RatecodeID | NULL | 7,716,688 |
| yellow | RatecodeID | 99 | 769,693 |
| yellow | RatecodeID | 2 | 694,936 |
| yellow | RatecodeID | 5 | 262,614 |
| yellow | RatecodeID | 3 | 90,052 |
| yellow | RatecodeID | 4 | 67,285 |
| yellow | RatecodeID | 6 | 15 |
| yellow | VendorID | 2 | 23,809,774 |
| yellow | VendorID | 1 | 5,467,071 |
| yellow | VendorID | 7 | 367,120 |
| yellow | VendorID | 6 | 59,390 |
| yellow | passenger_count | 1 | 18,069,219 |
| yellow | passenger_count | NULL | 7,716,688 |
| yellow | passenger_count | 2 | 2,707,073 |
| yellow | passenger_count | 3 | 612,062 |
| yellow | passenger_count | 4 | 417,054 |
| yellow | passenger_count | 0 | 91,359 |
| yellow | passenger_count | 5 | 56,383 |
| yellow | passenger_count | 6 | 33,489 |
| yellow | passenger_count | 8 | 18 |
| yellow | passenger_count | 9 | 6 |
| yellow | passenger_count | 7 | 4 |
| yellow | payment_type | 1 | 18,941,008 |
| yellow | payment_type | 0 | 7,716,688 |
| yellow | payment_type | 2 | 2,708,031 |
| yellow | payment_type | 4 | 239,488 |
| yellow | payment_type | 3 | 98,138 |
| yellow | payment_type | 5 | 2 |
| yellow | request_source | NULL | 7,800,627 |
| yellow | request_source | HV0003 | 2,295,520 |
| yellow | request_source | A | 403,773 |
| yellow | request_source | HV0005 | 181,233 |
| yellow | request_source | EH0004 | 20,769 |
| yellow | request_source | CC | 1,879 |
| yellow | request_source | EH0010 | 272 |
| green | RatecodeID | 1 | 269,152 |
| green | RatecodeID | NULL | 48,775 |
| green | RatecodeID | 5 | 17,739 |
| green | RatecodeID | 2 | 887 |
| green | RatecodeID | 4 | 354 |
| green | RatecodeID | 3 | 203 |
| green | RatecodeID | 99 | 2 |
| green | RatecodeID | 6 | 2 |
| green | VendorID | 2 | 273,571 |
| green | VendorID | 6 | 34,847 |
| green | VendorID | 1 | 28,696 |
| green | passenger_count | 1 | 238,282 |
| green | passenger_count | NULL | 48,775 |
| green | passenger_count | 2 | 28,687 |
| green | passenger_count | 5 | 6,340 |
| green | passenger_count | 0 | 4,527 |
| green | passenger_count | 6 | 4,295 |
| green | passenger_count | 3 | 3,322 |
| green | passenger_count | 4 | 2,787 |
| green | passenger_count | 7 | 36 |
| green | passenger_count | 8 | 32 |
| green | passenger_count | 9 | 31 |
| green | payment_type | 1 | 219,980 |
| green | payment_type | 2 | 65,921 |
| green | payment_type | NULL | 48,775 |
| green | payment_type | 3 | 1,688 |
| green | payment_type | 4 | 750 |
| green | request_source | NULL | 106,891 |
| green | request_source | A | 18,029 |
| green | request_source | HV0005 | 1,179 |
| green | request_source | CC | 3 |
| green | trip_type | 1 | 273,386 |
| green | trip_type | NULL | 48,777 |
| green | trip_type | 2 | 14,951 |

## q17_zonas_desconocidas

3.6 Viajes con zona de origen o destino 264/265 (zonas "Unknown"/"Outside of NYC" en la tabla de zonas de la TLC).

_2 filas, 2.70 s_

| tipo | registros | origen_264_265 | destino_264_265 | pct_afectado |
|---|---|---|---|---|
| yellow | 29,703,355 | 49,676 | 178,136 | 0.68 |
| green | 337,114 | 1,131 | 5,600 | 1.75 |

## q18_duplicados

3.6 Registros exactamente duplicados (todas las columnas iguales). Es la consulta mas costosa del ejercicio (~1 min): DISTINCT sobre ~30 M de filas.

_2 filas, 15.76 s_

| tipo | registros | filas_distintas | duplicados |
|---|---|---|---|
| yellow | 29,703,355 | 29,703,348 | 7 |
| green | 337,114 | 337,114 | 0 |
