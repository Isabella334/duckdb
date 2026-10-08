# Lab 8 - DuckDB

Repositorio base del laboratorio 8 del curso **CC3084 - Data Science**
(Universidad del Valle de Guatemala, Ciclo 2, 2026).

Este es el repositorio **proporcionado por el docente**. Contiene la estructura
del proyecto, el ambiente de ejecucion basado en Docker y un script que descarga
los datos de **2026**. Todo lo demas debe ser construido por cada equipo.

## Trabajo con fork

El laboratorio se desarrolla y se entrega sobre un **fork** de este repositorio.
No se trabaja directamente sobre el repositorio del docente.

1. Realice un fork de este repositorio:
   <https://github.com/menene/duckdb>

2. Clone **su propio fork** (no el del docente):

   ```bash
   git clone https://github.com/<su-usuario>/duckdb.git
   cd duckdb
   ```

3. Opcional, para recibir correcciones publicadas por el docente:

   ```bash
   git remote add upstream https://github.com/menene/duckdb.git
   git fetch upstream
   ```

Realice commits frecuentes y descriptivos: el historial del repositorio es parte
de la evaluacion. **La entrega del laboratorio es la URL de su fork.**

## Estructura

```text
duckdb/
|
+-- data/
|   +-- raw/
|   +-- processed/
|
+-- notebooks/
|
+-- scripts/
|
+-- sql/
|
+-- docs/
|
+-- Dockerfile
+-- metabase.Dockerfile
+-- docker-compose.yml
+-- README.md
```

## Requisitos

- Docker, con Docker Compose
- Git

La primera construccion del ambiente descarga varios cientos de MB y puede
tardar algunos minutos.

Considere el espacio en disco: las imagenes de Docker ocupan unos 3 GB y los
datos de los tres anios del laboratorio superan 1.5 GB, a los que se suma la
base materializada del Ejercicio 6. Se recomienda tener al menos 10 GB libres.

## Datos

El repositorio incluye `scripts/download_data.py`, que descarga los archivos de
2026 publicados por la TLC (`--help` muestra las opciones disponibles). Los
archivos se guardan en `data/raw/<tipo>/<anio>/`.

La TLC publica cada mes con varias semanas de atraso, por lo que los ultimos
meses de 2026 todavia no existen. El script consulta al servidor que meses estan
publicados, de modo que vuelve a ejecutarse sin problema conforme aparezcan
nuevos archivos.

Los datos descargados **no deben incluirse en el repositorio Git**. El archivo
`.gitignore` ya esta configurado para evitarlo.

Fuente de datos: NYC TLC Trip Record Data
<https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>

Dentro de los contenedores, la carpeta `data/` del proyecto esta montada en
`/workspace/data`. Esa es la ruta que deben usar las herramientas que corren
dentro del ambiente, no la ruta de su computadora.

> **Nota sobre DuckDB:** un archivo `.duckdb` admite un solo proceso con permiso
> de escritura a la vez. Si conecta una herramienta externa a su base de datos,
> use el modo de solo lectura (`read_only`) en esa conexion; de lo contrario los
> demas procesos no podran abrir el archivo.

## Material a entregar

Al finalizar, su fork debe contener:

- el codigo fuente modificado y los scripts de descarga;
- las consultas SQL desarrolladas;
- el notebook o notebooks utilizados;
- la documentacion de las consultas;
- los scripts utilizados para los benchmarks;
- el codigo de los indicadores y visualizaciones;
- el tablero o la evidencia del tablero desarrollado;
- este `README.md`, completado segun la siguiente seccion.

Los archivos de datos descargados **no** deben incluirse.

---

# Documentacion del equipo

Las siguientes secciones deben ser completadas por cada equipo. El README final
debe permitir que una persona que no participo en el desarrollo pueda levantar el
ambiente, descargar los datos, ejecutar el analisis, reproducir los benchmarks y
generar los resultados principales.

## Como levantar el ambiente

Detalle, verificacion y herramientas disponibles: [`docs/ejercicio1_ambiente.md`](docs/ejercicio1_ambiente.md).

1. Instale Docker Desktop (o Docker Engine con el plugin Compose) y asegurese de que
   este **en ejecucion**. En Windows, si `docker info` falla con
   `dockerDesktopLinuxEngine ... cannot find the file`, Docker Desktop no esta abierto.
2. Clone su fork y entre a la carpeta:

   ```bash
   git clone https://github.com/<su-usuario>/<su-fork>.git
   cd <su-fork>
   ```

3. Construya y levante los servicios en segundo plano (la primera vez tarda mas de
   10 minutos):

   ```bash
   docker compose up --build -d
   ```

4. Verifique que ambos servicios esten `Up`:

   ```bash
   docker compose ps
   ```

| Servicio | URL | Contenido |
|---|---|---|
| `lab` | <http://localhost:8888> | JupyterLab con Python 3.11, DuckDB 1.5.5, pandas, pyarrow y matplotlib (sin token) |
| `metabase` | <http://localhost:3000> | Metabase v0.63.19 con el driver de DuckDB. Tarda 1-2 minutos en arrancar; `http://localhost:3000/api/health` debe responder `{"status":"ok"}` |

Los comandos de Python se ejecutan **dentro** del contenedor `lab`, desde `/workspace`
(la raiz del proyecto):

```bash
docker compose exec lab python -c "import duckdb; print(duckdb.__version__)"
```

Para detener el ambiente: `docker compose down` (los datos de `data/` y la configuracion
de Metabase se conservan).

## Como descargar los datos

Detalle de los cambios al script y de la verificacion: [`docs/ejercicio2_descarga.md`](docs/ejercicio2_descarga.md).

```bash
# Taxis amarillos y verdes de 2026 (todos los meses publicados)
docker compose exec lab python scripts/download_data.py

# Opciones
docker compose exec lab python scripts/download_data.py --taxi yellow   # o green
docker compose exec lab python scripts/download_data.py --anios 2026    # uno o varios anios
docker compose exec lab python scripts/download_data.py --verificar     # revisar sin descargar
```

- Los archivos quedan en `data/raw/<tipo>/<anio>/<tipo>_tripdata_<anio>-<mes>.parquet`.
- El script consulta al servidor de la TLC que meses estan publicados; los que aun no
  existen se reportan como "no publicados" y no se cuentan como error.
- Un archivo que ya existe **y esta completo** (mismo tamanio que en el servidor y firma
  Parquet valida) no se vuelve a descargar. Un archivo truncado o corrupto se reemplaza.
- Al terminar se escribe `data/raw/manifest.csv` con el estado de cada archivo. El script
  devuelve codigo 1 si alguna descarga fallo.

## Como ejecutar el analisis

### Ejercicio 3 - Exploracion directa sobre Parquet

Documentacion: [`docs/ejercicio3_exploracion.md`](docs/ejercicio3_exploracion.md).
Consultas: [`sql/03_exploracion_parquet.sql`](sql/03_exploracion_parquet.sql).

```bash
# Ejecuta todas las consultas y guarda los resultados en Markdown
docker compose exec lab python scripts/run_sql.py sql/03_exploracion_parquet.sql --salida docs/resultados/ejercicio3_resultados.md

# Solo algunas consultas
docker compose exec lab python scripts/run_sql.py sql/03_exploracion_parquet.sql --solo q01_cantidad_archivos q03_total_registros
```

Tambien se puede abrir `notebooks/03_exploracion_parquet.ipynb` en JupyterLab y ejecutar
todas las celdas (tarda ~2.5 minutos), o ejecutarlo desde la terminal:

```bash
docker compose exec lab jupyter nbconvert --to notebook --execute --inplace notebooks/03_exploracion_parquet.ipynb
```

<!-- TODO: Ejercicios 4 en adelante -->

## Como reproducir los benchmarks

<!-- TODO (Ejercicio 6) -->

## Como generar los resultados principales

<!-- TODO -->
