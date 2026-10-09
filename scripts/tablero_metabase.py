#!/usr/bin/env python3
"""Crea en Metabase el tablero de indicadores del Ejercicio 7 usando su API.

Pasos:
1. Si Metabase aun no fue configurado, crea el usuario administrador.
2. Registra data/processed/indicadores.duckdb como base de datos en modo solo
   lectura (dentro del contenedor de Metabase la ruta es /workspace/data/...).
3. Crea una pregunta SQL por indicador y las organiza en un tablero con un
   filtro por tipo de taxi.

Si el tablero ya existe, se borra y se vuelve a crear, por lo que el script se
puede ejecutar las veces que haga falta. Antes hay que construir la base con
scripts/indicadores.py.

Uso (desde la raiz del proyecto, dentro del contenedor `lab`):
    python scripts/tablero_metabase.py
    python scripts/tablero_metabase.py --email yo@correo.com --password ****

Las credenciales tambien se pueden pasar con MB_EMAIL y MB_PASSWORD.
"""

import argparse
import os
import sys

import requests

URL_POR_DEFECTO = "http://metabase:3000"   # nombre del servicio en docker-compose
EMAIL_POR_DEFECTO = "admin@lab8.local"
PASSWORD_POR_DEFECTO = "Lab8-DuckDB-2026"
NOMBRE_BASE = "Taxis NYC - indicadores"
ARCHIVO_BASE = "/workspace/data/processed/indicadores.duckdb"
NOMBRE_COLECCION = "Lab 8 - Indicadores"
NOMBRE_TABLERO = "Taxis de Nueva York 2024-2026"

FILTRO_TIPO = "WHERE tipo = {{tipo}}"

# (nombre, pregunta e interpretacion, sql, tipo de grafico, ajustes de visualizacion)
TARJETAS = [
    ("I1 Viajes por dia en cada mes",
     "P1. Cuantos viajes hay por dia y como cambia entre anios? Los tres anios siguen la misma "
     "temporada: suben hasta mayo, bajan en julio y agosto y se recuperan en otono.",
     f"SELECT mes, anio::VARCHAR AS anio, viajes_por_dia FROM i01_demanda_mensual {FILTRO_TIPO} ORDER BY anio, mes",
     "line", {"graph.dimensions": ["mes", "anio"], "graph.metrics": ["viajes_por_dia"],
              "graph.x_axis.title_text": "mes", "graph.y_axis.title_text": "viajes por dia"}),
    ("I2 Resumen por anio",
     "P2. Cuanto pesa cada tipo de taxi en viajes e ingresos? Los amarillos hacen casi el 99 % de los "
     "viajes. Los anios tienen distinta cantidad de meses, por eso se comparan valores por dia.",
     f"SELECT anio, meses, viajes, pct_viajes_del_anio, viajes_por_dia, ingreso_por_dia_usd, pct_aeropuerto "
     f"FROM i02_resumen_anual {FILTRO_TIPO} ORDER BY anio",
     "table", {}),
    ("I3 Porcentaje de viajes por hora",
     "P3. A que horas se concentran los viajes? Los dos tipos tienen su pico a las 5-6 de la tarde; "
     "los amarillos tambien trabajan mucho de noche y los verdes casi nada.",
     f"SELECT hora, anio::VARCHAR AS anio, pct_viajes FROM i03_demanda_por_hora {FILTRO_TIPO} ORDER BY anio, hora",
     "line", {"graph.dimensions": ["hora", "anio"], "graph.metrics": ["pct_viajes"],
              "graph.y_axis.title_text": "% de viajes"}),
    ("I4 Velocidad mediana por hora",
     "P4. A que horas hay mas congestion? De madrugada los taxis van al doble de velocidad que entre "
     "las 10 y las 18 horas, y el patron es casi identico en los tres anios.",
     f"SELECT hora, anio::VARCHAR AS anio, velocidad_mediana_mph FROM i04_velocidad_por_hora {FILTRO_TIPO} ORDER BY anio, hora",
     "line", {"graph.dimensions": ["hora", "anio"], "graph.metrics": ["velocidad_mediana_mph"],
              "graph.y_axis.title_text": "mph"}),
    ("I5 Viaje tipico (medianas)",
     "P5. Como es el viaje tipico? Menos de 2 millas y unos 13 minutos; la distancia y la duracion "
     "medianas crecen un poco cada anio.",
     f"SELECT fecha, distancia_mediana_mi, duracion_mediana_min FROM i05_viaje_tipico {FILTRO_TIPO} ORDER BY fecha",
     "line", {"graph.dimensions": ["fecha"], "graph.metrics": ["distancia_mediana_mi", "duracion_mediana_min"]}),
    ("I6 Costo del viaje y peso de los recargos",
     "P6. Cuanto cuesta un viaje y que parte son recargos? El total mediano sube cada anio y en enero "
     "de 2025 aparece el cargo por entrar al sur de Manhattan (CBD).",
     f"SELECT fecha, total_mediano_usd, recargos_promedio_usd, pct_con_cargo_cbd FROM i06_costo_y_recargos {FILTRO_TIPO} ORDER BY fecha",
     "line", {"graph.dimensions": ["fecha"],
              "graph.metrics": ["total_mediano_usd", "recargos_promedio_usd", "pct_con_cargo_cbd"]}),
    ("I7 Formas de pago (% de viajes)",
     "P7. Como pagan los pasajeros? La tarjeta domina, pero los viajes Flex Fare (sin forma de pago "
     "registrada) pasan de menos del 10 % en 2024 a cerca de un cuarto en 2026 en los amarillos.",
     f"SELECT fecha, pct_tarjeta, pct_efectivo, pct_flex_fare, pct_otros FROM i07_formas_pago {FILTRO_TIPO} ORDER BY fecha",
     "bar", {"graph.dimensions": ["fecha"],
             "graph.metrics": ["pct_tarjeta", "pct_efectivo", "pct_flex_fare", "pct_otros"],
             "stackable.stack_type": "stacked"}),
    ("I8 Propinas con tarjeta",
     "P8. Cuanta propina se deja? Con tarjeta la propina mediana es cerca del 26 % de la tarifa en los "
     "amarillos y del 24 % en los verdes, y casi no cambia entre anios.",
     f"SELECT fecha, propina_mediana_pct, pct_sin_propina FROM i08_propinas {FILTRO_TIPO} ORDER BY fecha",
     "line", {"graph.dimensions": ["fecha"], "graph.metrics": ["propina_mediana_pct", "pct_sin_propina"]}),
    ("I9 Origen de los viajes por borough",
     "P9. De donde salen los viajes? Casi 9 de cada 10 amarillos salen de Manhattan; los verdes reparten "
     "sus viajes entre el norte de Manhattan, Queens y Brooklyn.",
     f"SELECT borough, anio::VARCHAR AS anio, pct_viajes FROM i09_origen_borough {FILTRO_TIPO} "
     f"AND borough NOT IN ('N/A', 'Unknown', 'EWR') ORDER BY anio, pct_viajes DESC",
     "bar", {"graph.dimensions": ["borough", "anio"], "graph.metrics": ["pct_viajes"],
             "graph.y_axis.title_text": "% de viajes"}),
    ("I10 Registros descartados por la limpieza",
     "P10. Que tan confiables son los datos? Se descarta entre 3 % y 13 % de los registros cada mes; "
     "2025 es el peor anio en los amarillos por la cantidad de montos negativos.",
     f"SELECT fecha, pct_descartado FROM i10_calidad_datos {FILTRO_TIPO} ORDER BY fecha",
     "bar", {"graph.dimensions": ["fecha"], "graph.metrics": ["pct_descartado"],
             "graph.y_axis.title_text": "% descartado"}),
]

TEXTO_ENCABEZADO = (
    "## Viajes de taxi en Nueva York (2024, 2025 y 2026)\n"
    "Indicadores calculados con DuckDB sobre los Parquet de la TLC (`sql/07_indicadores.sql`). "
    "Use el filtro **Tipo de taxi** para cambiar entre `yellow` y `green`. "
    "La descripcion de cada tarjeta (icono de informacion) tiene la pregunta que responde y su interpretacion."
)


class Metabase:
    def __init__(self, url):
        self.url = url.rstrip("/")
        self.sesion = requests.Session()

    def llamar(self, metodo, ruta, **kwargs):
        respuesta = self.sesion.request(metodo, f"{self.url}/api/{ruta}", timeout=120, **kwargs)
        if not respuesta.ok:
            sys.exit(f"Error {respuesta.status_code} en {metodo} /api/{ruta}: {respuesta.text[:500]}")
        return respuesta.json() if respuesta.content else None

    def iniciar_sesion(self, email, password):
        propiedades = self.llamar("GET", "session/properties")
        if not propiedades.get("has-user-setup"):
            print(f"Metabase sin configurar: se crea el usuario {email}")
            datos = self.llamar("POST", "setup", json={
                "token": propiedades["setup-token"],
                "user": {"email": email, "password": password, "first_name": "Lab", "last_name": "8"},
                "prefs": {"site_name": "Lab 8 DuckDB", "site_locale": "es", "allow_tracking": False},
            })
        else:
            datos = self.llamar("POST", "session", json={"username": email, "password": password})
        self.sesion.headers["X-Metabase-Session"] = datos["id"]


def preparar_base(mb):
    detalles = {"database_file": ARCHIVO_BASE, "read_only": True, "old_implicit_casting": True}
    bases = mb.llamar("GET", "database")
    bases = bases["data"] if isinstance(bases, dict) else bases
    existente = next((b for b in bases if b["name"] == NOMBRE_BASE), None)
    if existente:
        mb.llamar("PUT", f"database/{existente['id']}", json={"details": detalles})
        id_base = existente["id"]
    else:
        id_base = mb.llamar("POST", "database", json={"engine": "duckdb", "name": NOMBRE_BASE, "details": detalles})["id"]
    mb.llamar("POST", f"database/{id_base}/sync_schema")
    return id_base


def preparar_coleccion(mb):
    """Devuelve la coleccion del laboratorio, archivando lo que se haya creado antes."""
    colecciones = mb.llamar("GET", "collection")
    coleccion = next((c for c in colecciones if c.get("name") == NOMBRE_COLECCION and not c.get("archived")), None)
    if coleccion is None:
        return mb.llamar("POST", "collection", json={"name": NOMBRE_COLECCION, "parent_id": None})["id"]
    items = mb.llamar("GET", f"collection/{coleccion['id']}/items")["data"]
    for item in items:
        if item["model"] in ("card", "dashboard"):
            mb.llamar("PUT", f"{item['model']}/{item['id']}", json={"archived": True})
    return coleccion["id"]


def crear_tarjeta(mb, id_base, id_coleccion, nombre, descripcion, sql, grafico, ajustes):
    etiqueta = {"id": "tipo", "name": "tipo", "display-name": "Tipo de taxi", "type": "text",
                "required": True, "default": "yellow"}
    tarjeta = mb.llamar("POST", "card", json={
        "name": nombre,
        "description": descripcion,
        "collection_id": id_coleccion,
        "display": grafico,
        "visualization_settings": ajustes,
        "dataset_query": {"type": "native", "database": id_base,
                          "native": {"query": sql, "template-tags": {"tipo": etiqueta}}},
    })
    return tarjeta["id"]


def crear_tablero(mb, id_coleccion, ids_tarjetas):
    parametro = {"id": "tipo", "name": "Tipo de taxi", "slug": "tipo", "type": "string/=",
                 "sectionId": "string", "default": ["yellow"],
                 "values_query_type": "list", "values_source_type": "static-list",
                 "values_source_config": {"values": ["yellow", "green"]}}
    tablero = mb.llamar("POST", "dashboard", json={
        "name": NOMBRE_TABLERO, "collection_id": id_coleccion, "parameters": [parametro],
        "description": "Ejercicios 7 y 8 del Lab 8. Datos: NYC TLC Trip Record Data."})

    dashcards = [{"id": -1, "card_id": None, "row": 0, "col": 0, "size_x": 24, "size_y": 2,
                  "visualization_settings": {"virtual_card": {"name": None, "display": "text",
                                                              "visualization_settings": {}, "archived": False},
                                             "text": TEXTO_ENCABEZADO}}]
    # Dos tarjetas por fila; el resumen anual (tabla) ocupa la fila completa.
    fila, columna = 2, 0
    for i, id_tarjeta in enumerate(ids_tarjetas):
        ancho = 24 if TARJETAS[i][3] == "table" else 12
        if ancho == 24 and columna:
            fila, columna = fila + 6, 0
        dashcards.append({
            "id": -(i + 2), "card_id": id_tarjeta, "row": fila, "col": columna,
            "size_x": ancho, "size_y": 4 if ancho == 24 else 6,
            "parameter_mappings": [{"parameter_id": "tipo", "card_id": id_tarjeta,
                                    "target": ["variable", ["template-tag", "tipo"]]}],
        })
        if ancho == 24:
            fila, columna = fila + 4, 0
        elif columna:
            fila, columna = fila + 6, 0
        else:
            columna = 12
    mb.llamar("PUT", f"dashboard/{tablero['id']}", json={"dashcards": dashcards, "parameters": [parametro]})
    return tablero["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("MB_URL", URL_POR_DEFECTO))
    parser.add_argument("--email", default=os.environ.get("MB_EMAIL", EMAIL_POR_DEFECTO))
    parser.add_argument("--password", default=os.environ.get("MB_PASSWORD", PASSWORD_POR_DEFECTO))
    args = parser.parse_args()

    mb = Metabase(args.url)
    mb.iniciar_sesion(args.email, args.password)
    id_base = preparar_base(mb)
    id_coleccion = preparar_coleccion(mb)
    ids = [crear_tarjeta(mb, id_base, id_coleccion, *tarjeta) for tarjeta in TARJETAS]
    id_tablero = crear_tablero(mb, id_coleccion, ids)

    # Se ejecuta cada tarjeta una vez para confirmar que la consulta funciona en Metabase.
    for (nombre, *_), id_tarjeta in zip(TARJETAS, ids):
        resultado = mb.llamar("POST", f"card/{id_tarjeta}/query")
        if resultado.get("status") != "completed":
            sys.exit(f"La tarjeta '{nombre}' fallo: {resultado.get('error')}")
        print(f"  {nombre:<45} {resultado['row_count']:>4} filas")
    print(f"Tablero listo: http://localhost:3001/dashboard/{id_tablero} (usuario {args.email})")


if __name__ == "__main__":
    main()
