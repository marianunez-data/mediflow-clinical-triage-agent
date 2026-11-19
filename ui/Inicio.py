"""Punto de entrada de la app: arranca la API si hace falta y arma el menú con todas las páginas."""
import sys
from pathlib import Path

import streamlit as st

UI = Path(__file__).resolve().parent
sys.path.insert(0, str(UI))
from arranque import asegurar_api  # noqa: E402

st.set_page_config(page_title="MediFlow · Triaje documental clínico", page_icon="🏥", layout="wide")
asegurar_api()

navegacion = st.navigation({
    "": [
        st.Page("pages/0_Portada.py", title="Inicio", icon=":material/home:", url_path="portada", default=True),
    ],
    "Operación": [
        st.Page("pages/1_Carga.py", title="Procesar documento", icon=":material/upload_file:", url_path="carga"),
        st.Page("pages/2_Cola_de_triaje.py", title="Documentos", icon=":material/inbox:", url_path="documentos"),
        st.Page("pages/3_Auditoria.py", title="Auditoría", icon=":material/fact_check:", url_path="auditoria"),
    ],
    "Análisis": [
        st.Page("pages/5_Metricas.py", title="Métricas", icon=":material/monitoring:", url_path="metricas"),
        st.Page("pages/6_Trazas.py", title="Trazas", icon=":material/timeline:", url_path="trazas"),
        st.Page("pages/4_Reglas.py", title="Reglas", icon=":material/tune:", url_path="reglas"),
    ],
})
navegacion.run()
