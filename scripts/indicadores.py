#!/usr/bin/env python3
"""Construye data/processed/indicadores.duckdb a partir de sql/07_indicadores.sql.

Cada consulta i01..i10 del archivo se guarda como una tabla pequenia (ya
agregada). Metabase y los notebooks 07 y 08 leen esas tablas, por lo que el
tablero responde rapido aunque los Parquet tengan mas de 100 millones de filas.

La base se escribe primero en un archivo temporal y al final reemplaza a la
anterior. Asi Metabase, que la abre en modo solo lectura, nunca ve una base a
medio construir y no bloquea la reconstruccion.

Uso (desde la raiz del proyecto, dentro del contenedor `lab`):
    python scripts/indicadores.py
"""

import os
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_sql import cargar_consultas  # noqa: E402

ARCHIVO_SQL = Path("sql/07_indicadores.sql")
BASE = Path("data/processed/indicadores.duckdb")
VISTAS = ("viajes", "viajes_limpios")   # vistas temporales: no se guardan en la base


def construir(archivo_sql: Path = ARCHIVO_SQL, base: Path = BASE) -> list:
    """Crea la base de indicadores y devuelve [(tabla, filas, segundos)]."""
    consultas = cargar_consultas(archivo_sql)
    temporal = base.with_name(base.name + ".tmp")
    base.parent.mkdir(parents=True, exist_ok=True)
    temporal.unlink(missing_ok=True)

    con = duckdb.connect(str(temporal))
    # Mismos ajustes del Ejercicio 6 para no agotar la memoria del contenedor.
    con.sql("SET memory_limit = '4GB'")
    con.sql("SET preserve_insertion_order = false")

    resumen = []
    for nombre, (_, sql) in consultas.items():
        inicio = time.perf_counter()
        if nombre in VISTAS:
            con.sql(f"CREATE TEMP VIEW {nombre} AS {sql}")
            continue
        con.sql(f"CREATE TABLE {nombre} AS {sql}")
        filas = con.sql(f"SELECT count(*) FROM {nombre}").fetchone()[0]
        resumen.append((nombre, filas, time.perf_counter() - inicio))
    con.close()

    os.replace(temporal, base)
    return resumen


def main():
    inicio = time.perf_counter()
    for nombre, filas, segundos in construir():
        print(f"  {nombre:<22} {filas:>6} filas  {segundos:6.1f} s")
    print(f"Base creada: {BASE} ({BASE.stat().st_size / 1e6:.1f} MB) en {time.perf_counter() - inicio:.1f} s")


if __name__ == "__main__":
    main()
