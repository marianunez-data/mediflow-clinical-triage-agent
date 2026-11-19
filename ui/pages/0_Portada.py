"""Portada: qué es MediFlow, cómo probarlo y qué hay en cada página."""
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import estilo  # noqa: E402

estilo.aplicar()

CON_MODELO = os.getenv("USE_LLM", "false").lower() in ("true", "1", "yes")

estilo.html_(
    '<div class="mf-hero"><div class="mf-eyebrow">MediFlow · Agente de triaje documental clínico</div>'
    "<h1>Cada documento clínico, en la cola correcta y en segundos</h1>"
    "<p>MediFlow lee recetas, informes, órdenes, epicrisis y certificados en PDF, imagen, texto o JSON. "
    "Los clasifica, extrae los datos con su evidencia, detecta urgencias y los envía a la cola que "
    "corresponde. Lo que no puede decidir con seguridad lo pasa a una persona, con el motivo.</p></div>"
)

c1, c2, _ = st.columns([1, 1, 2])
c1.page_link("pages/1_Carga.py", label="Probar con un ejemplo", icon=":material/play_circle:")
c2.page_link("pages/5_Metricas.py", label="Ver métricas", icon=":material/monitoring:")

estilo.html_(
    '<div class="mf-flujo">'
    "<div><b>1 · Lee</b><strong>Cualquier formato</strong>"
    "<span>PDF digital o escaneado, foto, texto o JSON. Las imágenes pasan por OCR y una puerta de "
    "legibilidad.</span></div>"
    "<div><b>2 · Entiende</b><strong>Clasifica y extrae</strong>"
    "<span>Seis tipos de documento. Cada dato extraído cita el fragmento del que sale; lo que no está, "
    "queda vacío.</span></div>"
    "<div><b>3 · Decide</b><strong>Urgencia y destino</strong>"
    "<span>Lo urgente va a Emergencia con aviso a la guardia. El resto, a Farmacia, Autorizaciones o "
    "Historia clínica.</span></div>"
    "<div><b>4 · Pregunta</b><strong>Revisión humana</strong>"
    "<span>Ante una ambigüedad o confianza baja, un auditor aprueba, corrige o rechaza desde "
    "Auditoría.</span></div></div>"
)

izquierda, derecha = st.columns([3, 2], gap="large")
with izquierda:
    estilo.html_('<div class="mf-seccion-titulo">Cómo probarlo en dos minutos</div>')
    st.markdown(
        "1. En **Procesar documento**, elige un escenario de ejemplo y procésalo.\n"
        "2. Mira la decisión: destino, prioridad, confianza y por qué.\n"
        "3. Si fue a revisión, resuélvelo en **Auditoría**.\n"
        "4. Revisa **Documentos**, **Métricas** y la **Traza** paso a paso.\n\n"
        "Prueba el intento de engaño: un laboratorio con una orden escondida para mandarlo a rutina. "
        "El agente la ignora y lo envía a Emergencia."
    )
with derecha:
    estilo.html_('<div class="mf-seccion-titulo">Esta demo</div>')
    modelo = ("Usa un modelo de lenguaje (Groq) para clasificar y extraer." if CON_MODELO else
              "Corre con el motor de reglas, sin modelo de lenguaje: así se comporta MediFlow cuando el "
              "proveedor de IA no responde. La detección de urgencias sigue activa.")
    st.markdown(
        f"- {modelo}\n"
        "- Todos los documentos de ejemplo son sintéticos. No subas datos reales de pacientes.\n"
        "- Lo que proceses se borra cuando el servidor se reinicia.\n"
        "- Hace triaje documental: no interpreta imágenes médicas ni emite diagnósticos."
    )

estilo.html_(
    '<div class="mf-pie" style="margin-top:22px">Proyecto del Equipo 37 en el Hackathon ONE G10 '
    "(Oracle Next Education y Alura), desplegado originalmente en Oracle Cloud. "
    '<a href="https://github.com/marianunez-data/mediflow-clinical-triage-agent" target="_blank">'
    "Código en GitHub</a>.</div>"
)
