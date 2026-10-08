# Ejercicio 2 - Sistema de descarga

Script: [`scripts/download_data.py`](../scripts/download_data.py)

## 2.1 Analisis del script proporcionado

El script base ya sabia construir las URLs de la TLC
(`https://d37ci6vzurychx.cloudfront.net/trip-data/<tipo>_tripdata_<anio>-<mes>.parquet`),
consultar con `HEAD` que meses existen, guardar en `data/raw/<tipo>/<anio>/` y descargar
sobre un archivo temporal `.part`. Al analizarlo se identificaron estas limitaciones:

| # | Problema en el script original | Consecuencia |
|---|---|---|
| 1 | El anio estaba fijo en una constante (`ANIO = 2026`) usada por todas las funciones. | No se puede descargar otro anio sin editar el codigo. |
| 2 | Un archivo se consideraba "ya descargado" si existia con tamanio > 0. | Un archivo truncado o corrupto (p. ej. copiado a medias o danado en disco) se omitia para siempre y rompia las consultas despues. |
| 3 | `esta_publicado()` devolvia `False` ante **cualquier** error, incluido un fallo de red. | Un corte de internet se reportaba como "aun no publicado por la TLC" y el resumen decia que todo estaba bien. |
| 4 | No se comparaba el tamanio descargado con el `Content-Length` del servidor. | Una conexion cortada que el servidor cerrara "limpiamente" podia dejar un archivo incompleto marcado como listo. |
| 5 | No se verificaba que el archivo fuera un Parquet. | Una pagina de error HTML guardada como `.parquet` pasaria como valida. |
| 6 | No quedaba registro de que se descargo ni cuando. | No habia forma de demostrar que el conjunto de datos estaba completo. |

## 2.2 - 2.4 y 2.6 Cambios realizados

| Cambio | Detalle |
|---|---|
| Anios como parametro | Nuevo argumento `--anios` (por defecto `2026`). `construir_nombre`, `construir_url` y `ruta_destino` reciben el anio. Esto deja listo el script para los Ejercicios 5 y 8 sin cambiar la logica. |
| Deteccion de archivos existentes mas estricta (2.4) | `archivo_completo()` considera que un archivo local esta completo solo si **(a)** tiene la firma `PAR1` al inicio y al final y **(b)** su tamanio es igual al `Content-Length` del servidor. Si cumple, no se vuelve a descargar; si no, se reemplaza. |
| Verificacion de cada descarga | `descargar_archivo()` rechaza la descarga si los bytes recibidos no coinciden con el `Content-Length` o si no es un Parquet valido, y reintenta (3 intentos). El `.parquet` final solo aparece si la descarga es correcta. |
| Distincion "no publicado" vs. "error" | `consultar_servidor()` devuelve `publicado`, `no_publicado` (HTTP 403/404, que es como responde CloudFront a un mes inexistente) o `error` (red u otro codigo HTTP, con reintentos). Los errores cuentan como fallidos y el script termina con codigo 1. |
| Modo `--verificar` | Revisa los archivos locales contra el servidor sin descargar nada. Sirve para comprobar que el conjunto esta completo. |
| Manifiesto | Al final se escribe `data/raw/manifest.csv` con tipo, anio, mes, ruta, estado en el servidor, bytes en el servidor, bytes locales y estado final de cada archivo. Esta en `data/raw/`, por lo que no se versiona. |
| Almacenamiento (2.3) | Se mantiene la estructura del proyecto: `data/raw/<tipo>/<anio>/<nombre-original>.parquet`, p. ej. `data/raw/yellow/2026/yellow_tripdata_2026-01.parquet`. |

Uso:

```bash
docker compose exec lab python scripts/download_data.py              # yellow + green 2026
docker compose exec lab python scripts/download_data.py --taxi green
docker compose exec lab python scripts/download_data.py --anios 2026
docker compose exec lab python scripts/download_data.py --verificar  # no descarga
```

## 2.5 Ejecucion y verificacion

Ejecucion inicial (08/10/2026), resumen:

```text
=== YELLOW 2026 ===
  2026-01  listo (61.2 MiB) -> data/raw/yellow/2026/yellow_tripdata_2026-01.parquet
  ...
  2026-08  listo (56.3 MiB) -> data/raw/yellow/2026/yellow_tripdata_2026-08.parquet
  2026-09  aun no publicado por la TLC
  ...
============================================================
RESUMEN
============================================================
  anios         : 2026
  descargados   : 16
  ya existian   : 0
  no publicados : 8
      yellow 2026-09, yellow 2026-10, yellow 2026-11, yellow 2026-12,
      green 2026-09, green 2026-10, green 2026-11, green 2026-12
  fallidos      : 0
```

Archivos obtenidos (enero a agosto de 2026, ~496 MB en total):

| Tipo | Archivos | Meses | Tamanio |
|---|---|---|---|
| yellow | 8 | 2026-01 a 2026-08 | ~488 MB (56-67 MB por mes) |
| green | 8 | 2026-01 a 2026-08 | ~8 MB (~1 MB por mes) |

Pruebas del comportamiento:

| Prueba | Resultado |
|---|---|
| Segunda ejecucion sin cambios | `descargados: 0`, `ya existian: 16`: no descarga nada de nuevo. |
| Se trunco `green_tripdata_2026-02.parquet` a 400 KB y se ejecuto `--verificar` | Lo reporta como `incompleto o corrupto` (1 faltante). |
| Ejecucion normal despues del truncado | Detecta el archivo danado, lo vuelve a descargar (`descargados: 1`) y el resultado es identico byte a byte al original (`cmp`). |
| `--verificar` final | 16 archivos `completo`, 0 faltantes, codigo de salida 0. |

## 2.7 Como se determino que el conjunto de datos esta completo

La completitud se verifico en tres niveles:

1. **Contra la fuente.** Para cada uno de los 24 meses posibles (2 tipos x 12 meses) se
   consulto el servidor de la TLC. Enero a agosto respondieron HTTP 200 y septiembre a
   diciembre respondieron 403 (no publicados). Esto es consistente con el atraso de
   publicacion de la TLC, de unas 6-8 semanas: al 8 de octubre de 2026 el ultimo mes
   disponible es agosto. Esperados: 16 archivos; descargados: 16.
2. **Integridad de cada archivo.** El tamanio local de cada archivo es exactamente igual
   al `Content-Length` del servidor y todos tienen la firma `PAR1` al inicio y al final.
   El resultado queda en `data/raw/manifest.csv` (columna `estado = completo`) y se
   puede volver a comprobar en cualquier momento con `--verificar`.
3. **Legibilidad con DuckDB.** Los 16 archivos se leen sin errores con DuckDB. Sus
   metadatos reportan 29,703,355 viajes amarillos y 337,114 verdes, y un `count(*)`
   sobre los datos da los mismos totales. Cada mes tiene un volumen similar (3.3-4.1 M de
   viajes amarillos y 37-45 mil verdes), sin meses vacios ni anormalmente pequenos que
   indiquen un archivo parcial. Ver consultas `q01`-`q03` del
   [Ejercicio 3](ejercicio3_exploracion.md).

Cuando la TLC publique septiembre, basta con volver a ejecutar el script: solo descargara
los meses nuevos.
