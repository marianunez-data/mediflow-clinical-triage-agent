"""Documentos: la cola de revisión humana y todo lo que ya procesó el agente."""
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auditoria as aud  # noqa: E402
import estilo  # noqa: E402
from lib import api_request  # noqa: E402

API_URL = os.getenv("API_URL", "http://localhost:8000")
MAXIMO_PROCESADOS = 50

estilo.aplicar()
estilo.encabezado(
    "Documentos",
    "Lo que espera una decisión humana, con el motivo, y el historial de todo lo que el agente procesó.",
)


def _cola() -> list[dict]:
    try:
        return aud.ordenar_cola(aud.obtener_cola(API_URL))
    except aud.ErrorApi as exc:
        st.error(str(exc))
        return []


def _procesados() -> list[dict]:
    try:
        lista = api_request("GET", "/triage")
    except RuntimeError as exc:
        st.error(str(exc))
        return []
    if not lista.is_success:
        return []
    completos = []
    for fila in (lista.json().get("items") or [])[:MAXIMO_PROCESADOS]:
        respuesta = api_request("GET", f"/triage/{fila['documento_id']}")
        if respuesta.is_success:
            completos.append({**respuesta.json(), "_hora": fila.get("created_at")})
    return completos


cola = _cola()
procesados = _procesados()
urgentes = sum(aud.es_urgente(i["extraccion"]) for i in cola)

c1, c2, c3 = st.columns(3)
with c1:
    estilo.html_(estilo.met.tarjeta_html(
        "Procesados", str(len(procesados)), "documentos en esta sesión del servidor",
        que_es="Documentos que el agente ya leyó y envió a una cola.", fuente="GET /triage"))
with c2:
    estilo.html_(estilo.met.tarjeta_html(
        "Esperan revisión", str(len(cola)), "en la cola del auditor",
        que_es="Documentos que el agente no decidió solo.", fuente="GET /queue/human",
        estado="alerta" if cola else "ok", texto_estado="Pendientes" if cola else "Al día"))
with c3:
    estilo.html_(estilo.met.tarjeta_html(
        "Urgentes en revisión", str(urgentes), "ya están en Emergencia",
        que_es="Urgencias que además tienen un dato dudoso. La revisión no frena el aviso a la guardia.",
        fuente="GET /queue/human", estado="critico" if urgentes else "ok",
        texto_estado="Revisar primero" if urgentes else "Ninguna", derecha=True))

pestana_cola, pestana_todos = st.tabs([f"Esperan revisión ({len(cola)})", f"Procesados ({len(procesados)})"])

with pestana_cola:
    if not cola:
        estilo.html_(estilo.met.vacio_html(
            "No hay documentos esperando revisión",
            "Procesa un ejemplo de ambigüedad o fuera de alcance y aparecerá aquí."))
    else:
        filas = []
        for item in cola:
            ext = item["extraccion"]
            decision = aud.decision_de(ext)
            titulo, _ = aud.motivo_revision(ext)
            filas.append([
                f'<span class="mf-mono">{estilo.e(item["documento_id"])}</span>',
                estilo.e(estilo.nombre_tipo(ext["clasificacion"].get("tipo_documento"))),
                estilo.badge_prioridad(ext["clasificacion"].get("nivel_prioridad")),
                estilo.e(titulo),
                estilo.badge_destino(decision.get("destino_principal")),
                estilo.e(estilo.porcentaje(aud.score_de(ext))),
            ])
        estilo.html_(estilo.tabla(["Documento", "Tipo", "Prioridad", "Motivo", "Destino actual", "Confianza"],
                                  filas))
        st.write("")
        st.page_link("pages/3_Auditoria.py", label="Resolver en Auditoría", icon=":material/fact_check:")

with pestana_todos:
    if not procesados:
        estilo.html_(estilo.met.vacio_html(
            "Todavía no hay documentos procesados", "Ve a Procesar documento y prueba un ejemplo."))
    else:
        filas = []
        for r in procesados:
            decision = r.get("decision_enrutamiento") or {}
            clasificacion = r.get("clasificacion") or {}
            auditoria = estilo.badge("Sí", "#d98a0b") if decision.get("requiere_auditoria_humana") else "No"
            filas.append([
                f'<span class="mf-mono">{estilo.e(r.get("documento_id"))}</span>',
                estilo.e(estilo.nombre_tipo(clasificacion.get("tipo_documento"))),
                estilo.badge_prioridad(clasificacion.get("nivel_prioridad")),
                estilo.badge_destino(decision.get("destino_principal")),
                auditoria,
                estilo.e(estilo.porcentaje(r.get("score_confianza"))),
                estilo.e(estilo.nombre_modelo(r.get("modelo_utilizado"))),
                f'<span class="mf-tenue">{estilo.e(estilo.met.fecha_corta(r.get("_hora")))}</span>',
            ])
        estilo.html_(estilo.tabla(
            ["Documento", "Tipo", "Prioridad", "Destino", "Auditoría", "Confianza", "Leído por", "Hora (UTC)"],
            filas))
