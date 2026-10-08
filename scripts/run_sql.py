#!/usr/bin/env python3
"""Ejecuta las consultas nombradas de un archivo .sql con DuckDB.

Cada consulta del archivo empieza con una linea `-- name: <id>`; las lineas de
comentario que siguen se usan como descripcion. Las consultas se ejecutan en
una conexion en memoria, por lo que no se crea ninguna tabla ni base de datos:
DuckDB lee directamente los archivos Parquet que indique cada consulta.

Uso (desde la raiz del proyecto, dentro del contenedor `lab`):
    python scripts/run_sql.py sql/03_exploracion_parquet.sql
    python scripts/run_sql.py sql/03_exploracion_parquet.sql --solo q01_cantidad_archivos q02_registros_por_archivo
    python scripts/run_sql.py sql/03_exploracion_parquet.sql --salida docs/resultados/ejercicio3.md
"""

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

PATRON_NOMBRE = re.compile(r"^--\s*name:\s*(\S+)\s*$", re.MULTILINE)


def cargar_consultas(ruta: Path) -> dict:
    """Devuelve {nombre: (descripcion, sql)} en el orden del archivo."""
    texto = ruta.read_text(encoding="utf-8")
    marcas = list(PATRON_NOMBRE.finditer(texto))
    consultas = {}
    for i, marca in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        cuerpo = texto[marca.end():fin].strip()
        lineas = cuerpo.splitlines()
        descripcion = []
        while lineas and lineas[0].lstrip().startswith("--"):
            descripcion.append(lineas.pop(0).lstrip()[2:].strip())
        sql = "\n".join(lineas).strip().rstrip(";")
        consultas[marca.group(1)] = (" ".join(descripcion), sql)
    return consultas


def ejecutar(conexion, sql: str):
    """Ejecuta la consulta y devuelve (DataFrame, segundos)."""
    inicio = time.perf_counter()
    df = conexion.sql(sql).df()
    return df, time.perf_counter() - inicio


def formato_valor(valor) -> str:
    if valor is None:
        return "NULL"
    try:
        if valor != valor:  # NaN / NaT
            return "NULL"
    except (TypeError, ValueError):
        pass
    if isinstance(valor, float):
        return f"{valor:,.4f}".rstrip("0").rstrip(".")
    if isinstance(valor, int):
        return f"{valor:,}"
    return str(valor).replace("|", "\\|").replace("\n", " ")


def a_markdown(df, max_filas: int = 100) -> str:
    """Tabla Markdown sin dependencias externas."""
    columnas = [str(c) for c in df.columns]
    lineas = ["| " + " | ".join(columnas) + " |",
              "|" + "|".join("---" for _ in columnas) + "|"]
    for fila in df.head(max_filas).itertuples(index=False):
        lineas.append("| " + " | ".join(formato_valor(v) for v in fila) + " |")
    if len(df) > max_filas:
        lineas.append(f"\n_({len(df) - max_filas} filas mas omitidas)_")
    return "\n".join(lineas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archivo_sql", type=Path)
    parser.add_argument("--solo", nargs="+", help="nombres de las consultas a ejecutar")
    parser.add_argument("--salida", type=Path, help="archivo Markdown donde guardar los resultados")
    argumentos = parser.parse_args()

    consultas = cargar_consultas(argumentos.archivo_sql)
    if argumentos.solo:
        faltantes = set(argumentos.solo) - set(consultas)
        if faltantes:
            print(f"Consultas no encontradas: {', '.join(sorted(faltantes))}", file=sys.stderr)
            return 1
        consultas = {n: consultas[n] for n in argumentos.solo}

    conexion = duckdb.connect()  # en memoria: no se materializa nada
    version = conexion.sql("SELECT version()").fetchone()[0]
    marca = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    secciones = [
        f"# Resultados de `{argumentos.archivo_sql.as_posix()}`\n",
        f"Generado con `scripts/run_sql.py` el {marca}, DuckDB {version}.\n",
    ]
    for nombre, (descripcion, sql) in consultas.items():
        print(f"\n### {nombre}\n{descripcion}")
        df, segundos = ejecutar(conexion, sql)
        with __import__("pandas").option_context("display.width", 250,
                                                 "display.max_columns", 50,
                                                 "display.max_colwidth", 60):
            print(df.to_string(max_rows=100))
        print(f"({len(df)} filas, {segundos:.2f} s)")
        secciones.append(
            f"## {nombre}\n\n{descripcion}\n\n"
            f"_{len(df)} filas, {segundos:.2f} s_\n\n{a_markdown(df)}\n"
        )

    if argumentos.salida:
        argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
        argumentos.salida.write_text("\n".join(secciones), encoding="utf-8")
        print(f"\nResultados guardados en {argumentos.salida.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
