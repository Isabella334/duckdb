#!/usr/bin/env python3
"""Descarga los archivos Parquet del NYC TLC Trip Record Data.

Descarga los registros de viajes de taxis amarillos (yellow) y verdes (green)
para los anios indicados. Por defecto descarga 2026, que es el conjunto de
datos inicial del laboratorio.

Fuente oficial de los datos:
    https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Uso:
    python scripts/download_data.py                     # amarillos y verdes de 2026
    python scripts/download_data.py --taxi yellow
    python scripts/download_data.py --taxi green
    python scripts/download_data.py --anios 2026        # uno o varios anios
    python scripts/download_data.py --verificar         # solo verifica, no descarga

Los archivos se guardan en:
    data/raw/<tipo>/<anio>/<nombre-original>.parquet

Comportamiento:
  - La TLC publica cada mes con varias semanas de atraso, por lo que no todos
    los meses de 2026 existen todavia. El script consulta al servidor que
    meses estan publicados en lugar de suponerlos.
  - Un archivo que ya existe localmente y esta completo no se vuelve a
    descargar. Se considera completo si su tamanio coincide con el
    Content-Length que reporta el servidor y tiene la firma Parquet (PAR1) al
    inicio y al final. Un archivo local truncado o corrupto se descarga de nuevo.
  - La descarga se hace sobre un nombre temporal y solo se renombra al
    terminar, de modo que una interrupcion no deja archivos .parquet a medias.
  - Se distingue entre un mes que la TLC aun no publica (403/404) y un error
    de red, para no confundir un fallo de conexion con "no publicado".
  - Al terminar se escribe data/raw/manifest.csv con el estado de cada archivo
    (tamanio local, tamanio en el servidor y resultado de la verificacion).
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ANIOS_POR_DEFECTO = (2026,)
TIPOS_TAXI = ("yellow", "green")
URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
DIR_DESTINO = Path("data/raw")
MANIFIESTO = DIR_DESTINO / "manifest.csv"

TIEMPO_ESPERA = 60          # segundos por peticion
INTENTOS = 3                # intentos por archivo antes de darse por vencido
BLOQUE = 1024 * 1024        # 1 MiB por bloque de descarga
SUFIJO_TEMPORAL = ".part"
FIRMA_PARQUET = b"PAR1"     # los Parquet empiezan y terminan con estos 4 bytes

# Codigos con los que el servidor (CloudFront/S3) responde a un mes no publicado.
CODIGOS_NO_PUBLICADO = (403, 404)


def construir_nombre(tipo: str, anio: int, mes: int) -> str:
    """Nombre del archivo publicado por la TLC, p. ej. yellow_tripdata_2026-01.parquet."""
    return f"{tipo}_tripdata_{anio}-{mes:02d}.parquet"


def construir_url(tipo: str, anio: int, mes: int) -> str:
    """URL completa del archivo Parquet mensual."""
    return f"{URL_BASE}/{construir_nombre(tipo, anio, mes)}"


def ruta_destino(tipo: str, anio: int, mes: int) -> Path:
    """Ruta local donde se guarda el archivo."""
    return DIR_DESTINO / tipo / str(anio) / construir_nombre(tipo, anio, mes)


def consultar_servidor(url: str) -> tuple:
    """Consulta el archivo en el servidor sin descargarlo.

    Devuelve (estado, tamanio):
      - ("publicado", bytes)  si existe; bytes puede ser None si no se informa
      - ("no_publicado", None) si el servidor responde 403/404
      - ("error", None)        si hubo un problema de red u otro codigo HTTP
    """
    ultimo_error = None
    for _ in range(INTENTOS):
        try:
            respuesta = requests.head(url, timeout=TIEMPO_ESPERA, allow_redirects=True)
        except requests.RequestException as error:
            ultimo_error = error
            continue
        if respuesta.ok:
            longitud = respuesta.headers.get("Content-Length")
            return "publicado", int(longitud) if longitud else None
        if respuesta.status_code in CODIGOS_NO_PUBLICADO:
            return "no_publicado", None
        ultimo_error = f"HTTP {respuesta.status_code}"
    print(f"      no se pudo consultar el servidor ({ultimo_error})")
    return "error", None


def es_parquet_valido(ruta: Path) -> bool:
    """Revisa la firma PAR1 al inicio y al final del archivo."""
    try:
        if ruta.stat().st_size < 2 * len(FIRMA_PARQUET):
            return False
        with ruta.open("rb") as archivo:
            inicio = archivo.read(len(FIRMA_PARQUET))
            archivo.seek(-len(FIRMA_PARQUET), 2)
            fin = archivo.read(len(FIRMA_PARQUET))
    except OSError:
        return False
    return inicio == FIRMA_PARQUET and fin == FIRMA_PARQUET


def archivo_completo(ruta: Path, tamanio_servidor) -> bool:
    """Un archivo local esta completo si es un Parquet valido y su tamanio
    coincide con el del servidor (cuando el servidor lo informa)."""
    if not ruta.exists() or not es_parquet_valido(ruta):
        return False
    if tamanio_servidor is None:
        return True
    return ruta.stat().st_size == tamanio_servidor


def formato_tamanio(n: float) -> str:
    for unidad in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unidad == "GiB":
            return f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GiB"


def descargar_archivo(url: str, destino: Path, tamanio_esperado=None) -> int:
    """Descarga `url` en `destino`. Devuelve la cantidad de bytes escritos."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + SUFIJO_TEMPORAL)

    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        try:
            with requests.get(url, stream=True, timeout=TIEMPO_ESPERA) as respuesta:
                respuesta.raise_for_status()
                escritos = 0
                with temporal.open("wb") as archivo:
                    for bloque in respuesta.iter_content(chunk_size=BLOQUE):
                        if bloque:
                            archivo.write(bloque)
                            escritos += len(bloque)
            if escritos == 0:
                raise requests.RequestException("el servidor devolvio un archivo vacio")
            if tamanio_esperado is not None and escritos != tamanio_esperado:
                raise requests.RequestException(
                    f"descarga incompleta ({escritos} de {tamanio_esperado} bytes)"
                )
            if not es_parquet_valido(temporal):
                raise requests.RequestException("el archivo descargado no es un Parquet valido")
            temporal.replace(destino)
            return escritos
        except requests.RequestException as error:
            ultimo_error = error
            temporal.unlink(missing_ok=True)
            if intento < INTENTOS:
                print(f"      intento {intento}/{INTENTOS} fallido ({error}); reintentando")

    raise requests.RequestException(f"no se pudo descargar {url}: {ultimo_error}")


def procesar(tipo: str, anio: int, solo_verificar: bool, filas_manifiesto: list) -> dict:
    """Descarga (o verifica) todos los meses publicados de un tipo de taxi y anio."""
    print(f"\n=== {tipo.upper()} {anio} ===")
    resumen = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}

    for mes in range(1, 13):
        etiqueta = f"{anio}-{mes:02d}"
        destino = ruta_destino(tipo, anio, mes)
        url = construir_url(tipo, anio, mes)

        estado_servidor, tamanio_servidor = consultar_servidor(url)
        fila = {
            "tipo": tipo, "anio": anio, "mes": mes,
            "archivo": destino.as_posix(),
            "estado_servidor": estado_servidor,
            "bytes_servidor": tamanio_servidor if tamanio_servidor is not None else "",
            "bytes_local": destino.stat().st_size if destino.exists() else "",
            "estado": "",
        }

        if estado_servidor == "no_publicado":
            if destino.exists():
                # Raro, pero posible si la TLC retira un archivo: se conserva el local.
                print(f"  {etiqueta}  ya no aparece en el servidor; se conserva el archivo local")
                fila["estado"] = "local_sin_servidor"
                resumen["omitidos"] += 1
            else:
                print(f"  {etiqueta}  aun no publicado por la TLC")
                fila["estado"] = "no_publicado"
                resumen["no_publicados"].append(etiqueta)
            filas_manifiesto.append(fila)
            continue

        if estado_servidor == "error":
            # Sin respuesta del servidor no se puede comparar el tamanio; si el
            # archivo local es un Parquet valido se conserva, si no, es un fallo.
            if es_parquet_valido(destino):
                print(f"  {etiqueta}  ya existe (no se pudo comparar con el servidor), se omite")
                fila["estado"] = "existente_sin_verificar"
                resumen["omitidos"] += 1
            else:
                print(f"  {etiqueta}  ERROR: no se pudo consultar el servidor")
                fila["estado"] = "fallido"
                resumen["fallidos"].append(etiqueta)
            filas_manifiesto.append(fila)
            continue

        if archivo_completo(destino, tamanio_servidor):
            print(f"  {etiqueta}  ya existe y esta completo, se omite")
            fila["estado"] = "completo"
            resumen["omitidos"] += 1
            filas_manifiesto.append(fila)
            continue

        if solo_verificar:
            motivo = "falta" if not destino.exists() else "incompleto o corrupto"
            print(f"  {etiqueta}  {motivo}")
            fila["estado"] = "falta" if not destino.exists() else "incompleto"
            resumen["fallidos"].append(etiqueta)
            filas_manifiesto.append(fila)
            continue

        if destino.exists():
            print(f"  {etiqueta}  archivo local incompleto o corrupto, se descarga de nuevo...")
        else:
            print(f"  {etiqueta}  descargando...")
        try:
            escritos = descargar_archivo(url, destino, tamanio_servidor)
        except requests.RequestException as error:
            print(f"  {etiqueta}  ERROR: {error}")
            fila["estado"] = "fallido"
            resumen["fallidos"].append(etiqueta)
        else:
            print(f"  {etiqueta}  listo ({formato_tamanio(escritos)}) -> {destino}")
            fila["estado"] = "descargado"
            fila["bytes_local"] = escritos
            resumen["descargados"] += 1
        filas_manifiesto.append(fila)

    return resumen


def escribir_manifiesto(filas: list) -> None:
    """Guarda el estado de cada archivo esperado en data/raw/manifest.csv."""
    MANIFIESTO.parent.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).isoformat(timespec="seconds")
    campos = ["tipo", "anio", "mes", "archivo", "estado_servidor",
              "bytes_servidor", "bytes_local", "estado", "verificado_utc"]
    with MANIFIESTO.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({**fila, "verificado_utc": marca})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga los datos de taxis amarillos y verdes del NYC TLC."
    )
    parser.add_argument(
        "--taxi", choices=(*TIPOS_TAXI, "all"), default="all",
        help="tipo de taxi a descargar (por defecto: all)",
    )
    parser.add_argument(
        "--anios", type=int, nargs="+", default=list(ANIOS_POR_DEFECTO),
        help="anio o anios a descargar (por defecto: %(default)s)",
    )
    parser.add_argument(
        "--verificar", action="store_true",
        help="solo verifica los archivos locales contra el servidor, sin descargar",
    )
    argumentos = parser.parse_args()

    tipos = TIPOS_TAXI if argumentos.taxi == "all" else (argumentos.taxi,)
    anios = sorted(set(argumentos.anios))

    total = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": []}
    filas_manifiesto = []
    for anio in anios:
        for tipo in tipos:
            resumen = procesar(tipo, anio, argumentos.verificar, filas_manifiesto)
            total["descargados"] += resumen["descargados"]
            total["omitidos"] += resumen["omitidos"]
            total["no_publicados"] += [f"{tipo} {m}" for m in resumen["no_publicados"]]
            total["fallidos"] += [f"{tipo} {m}" for m in resumen["fallidos"]]

    escribir_manifiesto(filas_manifiesto)

    print("\n" + "=" * 60)
    print("RESUMEN" + (" (solo verificacion)" if argumentos.verificar else ""))
    print("=" * 60)
    print(f"  anios         : {', '.join(map(str, anios))}")
    print(f"  descargados   : {total['descargados']}")
    print(f"  ya existian   : {total['omitidos']}")
    print(f"  no publicados : {len(total['no_publicados'])}")
    if total["no_publicados"]:
        print(f"      {', '.join(total['no_publicados'])}")
    etiqueta_fallidos = "faltantes" if argumentos.verificar else "fallidos"
    print(f"  {etiqueta_fallidos:<14}: {len(total['fallidos'])}")
    if total["fallidos"]:
        print(f"      {', '.join(total['fallidos'])}")
    print(f"  manifiesto    : {MANIFIESTO.as_posix()}")
    print("=" * 60)

    return 1 if total["fallidos"] else 0


if __name__ == "__main__":
    sys.exit(main())
