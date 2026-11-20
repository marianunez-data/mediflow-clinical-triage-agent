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

import auditoria as aud
import estilo
from lib import api_request, remember_document, show_api_error, show_document_preview

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

estilo.aplicar()
estilo.encabezado(
    "Procesar documento",
    "Elige un escenario de ejemplo o sube tu propio archivo. El agente lo lee, lo clasifica, extrae los datos, "
    "busca urgencias y decide a qué cola va.",
)
if DEMO:
    estilo.html_(
        '<div class="mf-aviso"><b>Demo pública.</b> Usa solo documentos sintéticos: no subas datos reales de '
        "pacientes. Lo que proceses se borra cuando el servidor se reinicia.</div>"
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
        st.caption("Documentos sintéticos del conjunto de prueba del equipo, uno por cada tipo de decisión.")
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
            "Archivo PDF, imagen, texto o JSON (máximo 20 MB)",
            type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "webp", "txt", "json"],
        )
        document_id = st.text_input("ID del documento", key="carga_id")
        channel = st.text_input("Canal de origen", value="streamlit",
                                help="Por dónde llegó el documento: queda registrado con el resultado.")
        submitted = st.form_submit_button("Procesar documento", type="primary")

    if submitted:
        if uploaded is None:
            st.error("Selecciona un archivo antes de procesar.")
        elif not document_id.strip():
            st.error("El ID del documento es obligatorio.")
        else:
            _procesar(uploaded, document_id.strip(), channel.strip())



def _datos_extraidos(result: dict) -> None:
    datos = result.get("datos_extraidos") or {}
    planos = {k: v for k, v in aud.aplanar(datos).items() if k not in aud.LISTAS and v not in (None, "", [])}
    medicamentos = [m for m in datos.get("medicamentos") or [] if isinstance(m, dict)]
    estudios = [str(x) for x in datos.get("estudios_solicitados") or [] if x]
    if not (planos or medicamentos or estudios):
        st.caption("El agente no extrajo datos de este documento.")
        return
    if planos:
        filas = [[estilo.e(aud.etiqueta_campo(k)), estilo.e(v)] for k, v in planos.items()]
        estilo.html_(estilo.tabla(["Dato", "Valor"], filas))
    if medicamentos:
        st.markdown("**Medicamentos**")
        filas = [[estilo.e(m.get(c) or "—") for c in ("nombre", "dosis", "frecuencia", "duracion")]
                 + [estilo.badge("Alto riesgo", "#d98a0b") if m.get("alto_riesgo") else ""] for m in medicamentos]
        estilo.html_(estilo.tabla(["Nombre", "Dosis", "Frecuencia", "Duración", ""], filas))
    if estudios:
        st.markdown("**Estudios solicitados:** " + ", ".join(estudios))


result = st.session_state.get("last_triage_result")
if result:
    st.divider()
    estilo.html_(estilo.tarjeta_resultado(result))
    decision = result.get("decision_enrutamiento", {})
    en_revision = result.get("status") == "revision_humana" or decision.get("requiere_auditoria_humana")
    enlaces = [("pages/6_Trazas.py", "Ver la traza", ":material/timeline:"),
               ("pages/2_Cola_de_triaje.py", "Ver documentos", ":material/inbox:")]
    if en_revision:
        enlaces.insert(0, ("pages/3_Auditoria.py", "Resolver en Auditoría", ":material/fact_check:"))
    for columna, (pagina, texto, icono) in zip(st.columns(4), enlaces, strict=False):
        columna.page_link(pagina, label=texto, icon=icono)

    datos_tab, original_tab, json_tab = st.tabs(["Datos extraídos", "Documento original", "Respuesta JSON"])
    with datos_tab:
        _datos_extraidos(result)
    with original_tab:
        show_document_preview()
    with json_tab:
        st.json(result, expanded=False)
