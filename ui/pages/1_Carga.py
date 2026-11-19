"""Document upload and triage page."""
from __future__ import annotations

import mimetypes
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import api_request, remember_document, render_result, show_api_error

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_EJEMPLOS = RAIZ / "evals" / "golden" / "files"
DEMO = os.getenv("MEDIFLOW_DEMO", "").lower() in ("1", "true", "yes")

# Documentos sintéticos del conjunto de prueba, uno por escenario de la demo.
EJEMPLOS = {
    "Rutina · certificado médico (GS-28, texto)": "GS-28.txt",
    "Urgencia · tomografía con tromboembolismo pulmonar (GS-07, texto)": "GS-07.txt",
    "Urgencia · el mismo informe escaneado (GS-07, imagen)": "GS-07_escaneado.png",
    "Ambigüedad · receta con dosis dudosa (GS-06, texto)": "GS-06.txt",
    "Alto riesgo · receta con anticoagulante (GS-04, texto)": "GS-04.txt",
    "Urgencia con ambigüedad · laboratorio de sepsis (GS-14, JSON)": "GS-14.json",
    "Intento de engaño · orden escondida en el texto (FA-05, texto)": "FA-05.txt",
    "Fuera de alcance · receta veterinaria (FA-07, PDF)": "FA-07.pdf",
}

st.title("📄 Carga de documento")
st.caption("El original se conserva en la sesión para que pueda ser revisado si el grafo solicita auditoría humana.")

if DEMO:
    st.warning(
        "Demo pública: usa solo documentos sintéticos. No subas datos reales de pacientes. "
        "Los documentos se borran cuando el servidor se reinicia."
    )


@dataclass
class _Archivo:
    """Misma interfaz que el archivo de st.file_uploader, para los ejemplos del repositorio."""

    name: str
    type: str
    datos: bytes

    def getvalue(self) -> bytes:
        return self.datos


def _id_nuevo() -> str:
    return f"DOC-UI-{uuid.uuid4().hex[:8].upper()}"


def _procesar(archivo, document_id: str, channel: str) -> None:
    remember_document(archivo)
    with st.spinner("Ejecutando ingesta y grafo de triaje..."):
        try:
            response = api_request(
                "POST",
                "/triage/upload",
                data={"documento_id": document_id, "canal_origen": channel or "streamlit"},
                files={"archivo": (archivo.name, archivo.getvalue(), archivo.type or "application/octet-stream")},
            )
        except RuntimeError as exc:
            st.error(str(exc))
            return
    if response.is_success:
        st.session_state["last_triage_result"] = response.json()
        st.session_state["carga_id_rotar"] = True  # el siguiente documento lleva un ID nuevo
        st.rerun()  # el resultado se pinta desde la sesión; el formulario vuelve con el ID nuevo
    else:
        show_api_error(response)


# El ID por defecto se genera una vez por sesión. Si cambiara en cada ejecución, Streamlit trataría el campo
# como uno nuevo al enviar el formulario y descartaría el ID que la persona escribió.
if st.session_state.pop("carga_id_rotar", False) or "carga_id" not in st.session_state:
    st.session_state["carga_id"] = _id_nuevo()

ejemplos_disponibles = {k: v for k, v in EJEMPLOS.items() if (CARPETA_EJEMPLOS / v).exists()}
tab_ejemplo, tab_subir = st.tabs(["Probar con un ejemplo", "Subir mi documento"])

with tab_ejemplo:
    if ejemplos_disponibles:
        st.write("Elige un escenario y procésalo en un clic. Todos los documentos son sintéticos.")
        elegido = st.selectbox("Escenario", list(ejemplos_disponibles))
        nombre = ejemplos_disponibles[elegido]
        ruta = CARPETA_EJEMPLOS / nombre
        if ruta.suffix in (".txt", ".json"):
            with st.expander("Ver el documento"):
                st.code(ruta.read_text(encoding="utf-8"), language="json" if ruta.suffix == ".json" else "text")
        elif ruta.suffix == ".png":
            with st.expander("Ver el documento"):
                st.image(str(ruta), use_container_width=True)
        if st.button("Procesar ejemplo", type="primary"):
            mime = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
            _procesar(
                _Archivo(nombre, mime, ruta.read_bytes()),
                f"DEMO-{ruta.stem}-{uuid.uuid4().hex[:4].upper()}",
                "demo",
            )
    else:
        st.info("No hay documentos de ejemplo en esta instalación.")

with tab_subir:
    with st.form("triage_upload"):
        uploaded = st.file_uploader(
            "Selecciona un PDF, imagen, texto o JSON",
            type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "webp", "txt", "json"],
        )
        document_id = st.text_input("ID del documento", key="carga_id")
        channel = st.text_input("Canal de origen", value="streamlit")
        submitted = st.form_submit_button("Procesar documento", type="primary")

    if submitted:
        if uploaded is None:
            st.error("Selecciona un archivo antes de procesar.")
        elif not document_id.strip():
            st.error("El ID del documento es obligatorio.")
        else:
            _procesar(uploaded, document_id.strip(), channel.strip())

result = st.session_state.get("last_triage_result")
if result:
    st.divider()
    render_result(result)
    decision = result.get("decision_enrutamiento", {})
    if result.get("status") == "revision_humana" or decision.get("requiere_auditoria_humana"):
        with st.expander("Abrir documento para auditoría", expanded=True):
            from lib import show_document_preview

            show_document_preview()
