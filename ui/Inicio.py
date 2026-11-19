"""MediFlow Streamlit application entry point."""
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arranque import asegurar_api  # noqa: E402

st.set_page_config(page_title="MediFlow", page_icon="🏥", layout="wide")
asegurar_api()

DEMO = os.getenv("MEDIFLOW_DEMO", "").lower() in ("1", "true", "yes")
CON_MODELO = os.getenv("USE_LLM", "false").lower() in ("true", "1", "yes")

st.title("MediFlow")
st.subheader("Triaje documental clínico")
st.markdown(
    "Carga documentos clínicos, consulta su resultado de enrutamiento y revisa manualmente "
    "los casos ambiguos sin perder el archivo original."
)

if DEMO:
    st.info(
        "**Cómo probarlo:** abre **Carga** en el menú lateral, elige un escenario de ejemplo "
        "(rutina, urgencia, ambigüedad, alto riesgo, intento de engaño o fuera de alcance) y procésalo. "
        "Luego revisa la **Cola de triaje**, la **Auditoría**, las **Métricas** y las **Trazas**."
    )
    if not CON_MODELO:
        st.caption(
            "Esta instancia corre con el motor de reglas, sin modelo de lenguaje: así se comporta MediFlow "
            "cuando el proveedor de IA no responde. La detección de urgencias sigue activa."
        )
else:
    st.info("Usa el menú lateral para cargar documentos, consultar la cola de auditoría y revisar métricas.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Formatos soportados", "PDF, imagen, texto, JSON")
with col2:
    st.metric("Revisión humana", "AMB-1 a AMB-6")
with col3:
    st.metric("Procesamiento", "API + grafo LangGraph")

st.caption("MediFlow realiza triaje documental; no interpreta imágenes médicas ni emite diagnósticos.")
if DEMO:
    st.caption(
        "Demo pública con documentos sintéticos. No subas datos reales de pacientes. "
        "Proyecto del Equipo 37, Hackathon ONE G10 (Oracle Next Education y Alura)."
    )
