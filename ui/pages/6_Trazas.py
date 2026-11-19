"""Traza: los pasos que siguió el agente con un documento, en orden y con su tiempo."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import estilo  # noqa: E402
from lib import api_request  # noqa: E402

estilo.aplicar()
estilo.encabezado(
    "Traza del agente",
    "Cada paso del grafo de decisión para un documento: qué hizo, qué encontró y cuánto tardó. Sirve para "
    "auditar por qué el agente decidió lo que decidió.",
)

OMITIR = {"confianza_ocr", "palabras_ocr", "ocr_disponible", "imagenes_no_decodificables", "multiples_documentos",
          "legibilidad_provisional", "motivo_fuera_de_alcance"}


def _valor(valor) -> str:
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, float):
        return f"{valor:.2f}".replace(".", ",")
    return str(valor).replace("_", " ")


def _pares(detalle: dict) -> str:
    pares = []
    for clave, valor in (detalle or {}).items():
        if clave in OMITIR or valor in (None, "", [], {}):
            continue
        nombre = estilo.NOMBRES_CLAVE.get(clave, clave.replace("_", " "))
        if clave == "destino_principal":
            valor = estilo.nombre_destino(valor)
        elif clave == "tipo_documento":
            valor = estilo.nombre_tipo(valor)
        pares.append(f'<span class="mf-kv"><b>{estilo.e(nombre)}</b>{estilo.e(_valor(valor))}</span>')
    return "".join(pares)


def _color(paso: dict) -> str:
    detalle = paso.get("detalle") or {}
    if paso.get("nodo") == "detectar_urgencia" and detalle.get("detectada"):
        return "#d43c3c"
    if paso.get("nodo") == "validar" and detalle.get("categoria_amb"):
        return "#d98a0b"
    if paso.get("nodo") == "enrutar":
        return estilo.COLOR_DESTINO.get(str(detalle.get("destino_principal")), "#2a78d6")
    return "#2a78d6"


def _documentos() -> list[str]:
    try:
        respuesta = api_request("GET", "/triage")
    except RuntimeError as exc:
        st.error(str(exc))
        return []
    return [f["documento_id"] for f in respuesta.json().get("items", [])] if respuesta.is_success else []


ultimo = st.session_state.get("last_triage_result")
ids = _documentos()
if ultimo and ultimo.get("documento_id") not in ids:
    ids.insert(0, ultimo["documento_id"])

if not ids:
    estilo.html_(estilo.met.vacio_html(
        "Todavía no hay trazas", "Procesa un documento en Procesar documento y vuelve a esta página."))
    st.stop()

inicial = ids.index(ultimo["documento_id"]) if ultimo and ultimo.get("documento_id") in ids else 0
elegido = st.selectbox("Documento", ids, index=inicial)
if ultimo and ultimo.get("documento_id") == elegido:
    resultado = ultimo
else:
    respuesta = api_request("GET", f"/triage/{elegido}")
    resultado = respuesta.json() if respuesta.is_success else {}

pasos = [p for p in resultado.get("trace") or [] if isinstance(p, dict)]
if not pasos:
    st.info("La API no devolvió pasos de traza para este documento.")
    st.stop()

decision = resultado.get("decision_enrutamiento") or {}
tiempos = [p.get("ts") for p in pasos if isinstance(p.get("ts"), (int, float))]
total = (max(tiempos) - min(tiempos)) if len(tiempos) > 1 else None
estilo.html_(
    f'<div class="mf-resumen"><span class="mf-resumen-marca"></span><div>'
    f'<div class="mf-resumen-etiqueta">Resumen</div>'
    f'{len(pasos)} pasos{f" en <b>{total:.1f} s</b>".replace(".", ",") if total is not None else ""}. '
    f'Terminó en {estilo.badge_destino(decision.get("destino_principal"))} con confianza '
    f'<b>{estilo.e(estilo.porcentaje(resultado.get("score_confianza")))}</b>, leído por '
    f'<b>{estilo.e(estilo.nombre_modelo(resultado.get("modelo_utilizado")))}</b>.</div></div>'
)

items = []
anterior = None
for numero, paso in enumerate(pasos, start=1):
    nombre, que_hace = estilo.PASOS.get(paso.get("nodo"), (str(paso.get("nodo")).replace("_", " ").title(), ""))
    ts = paso.get("ts")
    duracion = ""
    if isinstance(ts, (int, float)) and isinstance(anterior, (int, float)):
        ms = max(0.0, (ts - anterior) * 1000)
        duracion = f"{ms / 1000:.1f} s".replace(".", ",") if ms >= 1000 else f"{ms:.0f} ms"
    anterior = ts if isinstance(ts, (int, float)) else anterior
    modelo = paso.get("modelo")
    con_modelo = (f'<span class="mf-kv"><b>modelo</b>{estilo.e(estilo.nombre_modelo(modelo))}</span>'
                  if modelo else "")
    items.append(
        f'<li class="mf-paso" style="--mf-c:{_color(paso)}"><div class="mf-paso-n">{numero}</div>'
        f'<div><div class="mf-paso-t">{estilo.e(nombre)}</div><div class="mf-paso-d">{estilo.e(que_hace)}</div>'
        f'{_pares(paso.get("detalle") or {})}{con_modelo}</div><div class="mf-paso-ms">{duracion}</div></li>'
    )

with st.container(border=True, key="mf_panel_traza"):
    estilo.html_(f'<ol class="mf-pasos">{"".join(items)}</ol>')

with st.expander("Traza en JSON"):
    st.json(pasos, expanded=False)
