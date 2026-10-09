# Ejercicio 9 - Discusion


## 9.1 ¿Que caracteristicas de DuckDB resultaron mas utiles?

- **Leer Parquet directamente con comodines.** `read_parquet('data/raw/*/*/*.parquet')` lee todos los archivos como si fueran una sola tabla. Con `filename = true` el tipo de taxi y el anio salen de la ruta del archivo.
- **`union_by_name`.** Permitio juntar anios con columnas distintas. `cbd_congestion_fee` no existe en 2024 y sin esta opcion las consultas fallaban (Ejercicio 5).
- **Funciones de metadatos** (`glob`, `parquet_file_metadata`, `parquet_schema`). Sirven para contar archivos, registros y columnas sin leer los datos (Ejercicio 3).
- **SQL analitico completo.** Se usaron mucho `FILTER`, `QUALIFY`, `GROUP BY ALL`, `median`, `quantile_cont` y las funciones de ventana. Cada pregunta se pudo responder con una sola consulta.
- **Velocidad sin servidor.** Agrupar mas de 100 millones de filas toma entre 2 y 10 segundos dentro de un contenedor, sin instalar ni administrar una base de datos.
- **Integracion con Python y Metabase.** `.df()` entrega el resultado ya agregado a pandas, y Metabase lee el mismo archivo `.duckdb` con su driver.
- **Control de memoria.** Con `memory_limit` y `preserve_insertion_order = false`, DuckDB usa el disco cuando no le alcanza la memoria del contenedor de 8 GB.

## 9.2 ¿Que ventajas y limitaciones tiene consultar directamente archivos Parquet?

**Ventajas**

- No hay que cargar nada antes de consultar. Un archivo nuevo entra en la siguiente consulta sin hacer nada mas (Ejercicios 5 y 8).
- Ocupa la mitad del espacio. Los 40 archivos de 2024 y 2026 pesaban 1.23 GB, contra 2.56 GB como tabla DuckDB (Ejercicio 6).
- Solo se leen las columnas que usa la consulta, y los metadatos permiten contar registros sin leer los datos.
- Los mismos archivos los pueden usar otras herramientas.

**Limitaciones**

- Cada consulta vuelve a abrir y descomprimir los archivos. En el benchmark fue entre 2 y 4 veces mas lento que la tabla en total.
- Si el filtro es sobre una columna calculada, como el `coalesce` de las fechas de yellow y green, DuckDB no puede saltarse partes de los archivos. El filtro de un dia fue hasta 117 veces mas lento que en la tabla.
- El esquema puede cambiar entre archivos (columnas nuevas, tipos distintos), y hay que manejarlo en cada consulta.
- Los datos traen errores que no se corrigen en ningun lado (fechas de 2001, montos negativos), asi que la limpieza se repite en cada consulta.

## 9.3 ¿Que ventajas y limitaciones tienen las tablas materializadas en DuckDB?

**Ventajas**

- Todas las consultas fueron mas rapidas: entre 2 y 4 veces en total, unas 20 veces en el conteo y hasta 117 veces en el filtro por fecha, gracias a que la tabla guarda el minimo y el maximo de cada bloque.
- Las columnas calculadas y la limpieza se hacen una sola vez.
- Para un tablero es lo mejor. Los indicadores del Ejercicio 7 son tablas de pocas filas (3 MB en total) y Metabase responde al instante.

**Limitaciones**

- Ocupan espacio extra: la tabla de 2024 y 2026 pesaba el doble que los Parquet.
- No se actualizan solas. Cuando llegan datos nuevos hay que volver a crearlas (Ejercicio 8).
- Un archivo `.duckdb` admite un solo proceso con permiso de escritura. Para que Metabase pudiera leer la base mientras se reconstruye, se conecto en modo solo lectura y el script escribe primero un archivo temporal que luego reemplaza al anterior.

## 9.4 ¿Que ventajas ofrece este flujo frente a cargar todo con pandas?

Con pandas habria que cargar los datos completos en memoria. Solo 2024, 2025 y 2026 suman 121 millones de registros con unas 20 columnas, que son alrededor de 19 GB en memoria, mas del doble de los 8 GB del contenedor. Con DuckDB los datos se procesan por partes y en paralelo, y a pandas solo llega el resultado ya agregado, que casi nunca pasa de unos cientos de filas. Ademas, las consultas quedan en SQL dentro de archivos `.sql`, se pueden documentar y ejecutar con `scripts/run_sql.py`, y Metabase usa las mismas tablas. Pandas se siguio usando, pero solo para dar forma a los resultados y graficarlos.

## 9.5 ¿Que permite incorporar nuevos datos con cambios minimos?

- La estructura fija `data/raw/<tipo>/<anio>/<archivo>.parquet`: un anio nuevo es solo una carpeta mas.
- Las consultas leen con comodines y sacan el tipo, el anio y el mes de la ruta del archivo.
- `union_by_name` absorbe columnas que aparecen o desaparecen entre anios.
- El script de descarga recibe los anios como parametro, no repite archivos completos y deja un manifiesto. Para agregar 2024 y 2025 solo se cambio una linea.
- Los indicadores siempre separan por anio, asi que un anio nuevo aparece como una serie mas, sin mezclarse con los otros.
- La base de indicadores y el tablero se crean con scripts, por lo que actualizarlos es volver a ejecutarlos.

## 9.6 ¿Que deberia automatizarse en un sistema de produccion?

- **La descarga.** Correr el script cada mes, porque la TLC publica con varias semanas de atraso, y calcular los anios a partir de la fecha actual en lugar de una lista fija.
- **La reconstruccion.** Despues de cada descarga con archivos nuevos, volver a crear la base de indicadores y refrescar el tablero.
- **Los controles de calidad.** Revisar automaticamente el manifiesto y el porcentaje de registros descartados, y avisar si cambian mucho, como los montos negativos de 2025 o columnas nuevas en el esquema.
- **Las pruebas.** Confirmar que las consultas principales siguen funcionando y dando totales razonables antes de publicar el tablero.

## 9.7 ¿Que decisiones de diseno fueron importantes para la reproducibilidad?

- El ambiente es Docker con versiones fijas. DuckDB 1.5.5 es la misma version del driver de Metabase, para que los dos puedan abrir la misma base.
- Los datos no estan en Git. Se descargan siempre desde la fuente oficial con un script que verifica el tamanio y la firma de cada archivo y deja un manifiesto.
- Todas las rutas son relativas a la raiz del proyecto y siguen la estructura del repositorio.
- Las consultas estan en archivos `.sql` con nombre y descripcion, y los notebooks se ejecutan de principio a fin con `nbconvert`.
- Las bases derivadas (`taxis.duckdb` e `indicadores.duckdb`) se recrean desde cero en cada ejecucion, nunca se editan a mano.
- El tablero de Metabase se crea con un script y no a mano, asi que se obtiene el mismo tablero en cualquier computadora.

## 9.8 ¿Que se aprendio que no seria evidente con datos pequenios?

- **Un porcentaje pequenio es mucha informacion.** Problemas que afectan a menos del 2 % de los registros son cientos de miles de viajes, y en 2025 los montos negativos llegaron a casi 3 millones de registros amarillos.
- **La memoria importa.** Algunas operaciones, como las medianas exactas, necesitan tener todos los valores en memoria a la vez, y con 72 millones de filas el contenedor se quedo sin memoria (Ejercicio 6).
- **La forma de guardar los datos importa tanto como la consulta.** La misma consulta tardo 117 veces mas solo por filtrar sobre una columna calculada.
- **Los datos cambian con el tiempo.** Entre anios aparecen columnas nuevas, cambian las reglas (el cargo CBD) y cambia la calidad (2025). Mezclar anios sin separarlos da resultados equivocados sin ningun error visible, como el 72.5 % contra 30.1 % del cargo CBD en el Ejercicio 5.
- **Los valores extremos dominan los promedios.** Con millones de registros siempre hay viajes imposibles, como duraciones negativas o distancias de miles de millas, y por eso se usaron medianas y reglas de limpieza con sentido.
