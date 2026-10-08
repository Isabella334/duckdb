# Ejercicio 1 - Preparacion del ambiente

## Estructura del proyecto y proposito de cada directorio

| Ruta | Proposito |
|---|---|
| `data/raw/` | Datos **tal como los publica la fuente** (Parquet mensuales de la TLC), organizados en `data/raw/<tipo>/<anio>/`. Nunca se modifican a mano: si hay que corregir algo se hace en una transformacion documentada. Esta excluido de Git (`.gitignore`) y montado en los contenedores como `/workspace/data`. |
| `data/processed/` | Resultados derivados de `raw/`: datos limpios, agregados, y la base `.duckdb` materializada del Ejercicio 6. Tambien excluido de Git porque se puede regenerar a partir de `raw/` y de los scripts. |
| `notebooks/` | Notebooks de Jupyter con el analisis exploratorio y las visualizaciones (p. ej. `03_exploracion_parquet.ipynb`). |
| `scripts/` | Codigo ejecutable y reproducible desde la linea de comandos: descarga de datos (`download_data.py`), ejecucion de consultas (`run_sql.py`) y, mas adelante, benchmarks. |
| `sql/` | Consultas SQL versionadas, separadas del codigo Python para poder revisarlas, reutilizarlas desde el notebook, los scripts y Metabase, y documentarlas. |
| `docs/` | Documentacion del laboratorio: explicacion de cada ejercicio, documentacion de consultas y resultados generados (`docs/resultados/`). |
| `Dockerfile` | Imagen del servicio `lab`: Python 3.11 + JupyterLab + DuckDB y librerias de analisis con versiones fijas. |
| `metabase.Dockerfile` | Imagen del servicio `metabase` con el driver de DuckDB ya instalado (sobre Debian porque el driver requiere glibc). |
| `docker-compose.yml` | Orquesta ambos servicios, sus puertos y los volumenes que montan las carpetas del proyecto dentro de los contenedores. |
| `requirements.txt` | Versiones exactas de las librerias de Python. `duckdb` debe coincidir con la version del driver de Metabase. |
| `.gitignore` | Evita versionar los datos (`data/raw/**`, `data/processed/**`) y archivos temporales. |

## 1.1 - 1.2 Fork, clonado y levantamiento del ambiente

1. Fork de <https://github.com/menene/duckdb> desde GitHub (boton **Fork**).
2. Clonar el fork propio (`git clone https://github.com/<usuario>/<fork>.git`).
3. Con Docker Desktop iniciado, desde la raiz del repositorio:

   ```bash
   docker compose up --build -d
   ```

   La primera construccion tardo un poco mas de 10 minutos (descarga de imagenes base,
   de Metabase y del driver de DuckDB, e instalacion de las librerias de Python).
   Las siguientes veces basta con `docker compose up -d`.

## 1.3 Verificacion de los servicios

| Verificacion | Comando / URL | Resultado obtenido |
|---|---|---|
| Contenedores en ejecucion | `docker compose ps` | `lab` y `metabase` en estado `Up` |
| JupyterLab responde | <http://localhost:8888/api> | `{"version": "2.21.1"}` |
| DuckDB funciona dentro de `lab` | `docker compose exec lab python -c "import duckdb; print(duckdb.sql('select version()').fetchone())"` | `('v1.5.5',)` |
| Metabase responde | <http://localhost:3000/api/health> | `{"status":"ok"}` (tarda 1-2 minutos en pasar de `initializing` a `ok`) |
| Driver DuckDB en Metabase | `http://localhost:3000/api/session/properties` | Metabase `v0.63.19` con el motor `duckdb` disponible |
| Carpetas montadas | `docker compose exec lab ls /workspace` | `data docs notebooks requirements.txt scripts sql` |
| Descarga y consulta de datos | `docker compose exec lab python scripts/download_data.py` | 16 archivos descargados y legibles desde DuckDB (ver Ejercicios 2 y 3) |

Los puertos estan publicados solo en `127.0.0.1`, por lo que los servicios no quedan
expuestos a la red local. JupyterLab corre sin token, lo cual es aceptable unicamente por
esa razon.

## 1.4 Herramientas disponibles en el ambiente

**Servicio `lab`** (imagen `python:3.11.14-slim`, Debian 13):

| Herramienta | Version | Uso en el laboratorio |
|---|---|---|
| Python | 3.11.14 | Lenguaje de los scripts y notebooks |
| DuckDB (modulo de Python) | 1.5.5 | Motor analitico SQL; consulta los Parquet directamente |
| JupyterLab | 4.6.4 | Notebooks interactivos en <http://localhost:8888> |
| pandas | 3.0.6 | Recibir resultados de DuckDB como DataFrame (`.df()`) |
| pyarrow | 25.0.1 | Lectura/escritura de Parquet y Arrow |
| matplotlib | 3.11.2 | Graficas en los notebooks |
| requests | 2.34.2 | Descarga de los archivos de la TLC |
| nbconvert / ipykernel | 7.17.1 / 7.4.0 | Ejecutar notebooks desde la terminal |
| curl | sistema | Pruebas HTTP |

No se incluye el CLI `duckdb`; DuckDB se usa desde Python (`import duckdb`).

**Servicio `metabase`** (imagen `eclipse-temurin:21-jre-jammy`):

| Herramienta | Version | Uso |
|---|---|---|
| Metabase | v0.63.19 | Tableros e indicadores (Ejercicio 7) en <http://localhost:3000> |
| Driver DuckDB para Metabase | 1.5.5.0 | Permite a Metabase leer archivos `.duckdb` / Parquet |
| Java (OpenJDK) | 21 | Ejecuta Metabase |

Dentro de Metabase la carpeta de datos se ve como `/workspace/data`, no con la ruta de
la computadora anfitriona.

## 1.5 Procedimiento para levantar el ambiente

Documentado en la seccion **"Como levantar el ambiente"** del [`README.md`](../README.md).

## 1.6 Por que es importante un ambiente reproducible

- **Mismos resultados para todos.** Las versiones de Python, DuckDB, pandas, Metabase y el
  driver estan fijas. Un cambio de version puede cambiar resultados, funciones disponibles
  o incluso el formato de un archivo `.duckdb`, que no siempre se puede abrir con otra version.
  En este proyecto, por ejemplo, `duckdb` en Python y el driver de Metabase deben coincidir;
  sin el ambiente fijado, la combinacion fallaria de forma dificil de diagnosticar.
- **Elimina el "en mi maquina si funciona".** Cada integrante del equipo (y el catedratico)
  levanta exactamente el mismo sistema con un solo comando, sin importar su sistema
  operativo ni lo que tenga instalado. Esto fue evidente en este equipo: en Windows el
  driver de DuckDB para Metabase necesitaria glibc, y Docker lo resuelve sin configuracion
  manual.
- **Separa codigo, datos y ambiente.** El repositorio guarda el codigo y la receta del
  ambiente; los datos se regeneran con los scripts. Asi el analisis completo se puede
  reconstruir desde cero, y cualquiera puede verificar las conclusiones.
- **Facilita el trabajo incremental.** Cuando lleguen nuevos datos (2024, 2025) o nuevos
  integrantes, se vuelve a ejecutar el mismo flujo en vez de reconfigurar herramientas.
- **Aislamiento.** Las dependencias del laboratorio no interfieren con otros proyectos de la
  computadora, y el ambiente se puede eliminar sin dejar residuos (`docker compose down`).
