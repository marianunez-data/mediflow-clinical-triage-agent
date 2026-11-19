"""Reglas: cómo decide el agente, en lenguaje claro. La edición queda para un administrador con token."""
import json
import sys
import unicodedata
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auditoria as aud  # noqa: E402
import estilo  # noqa: E402
from lib import admin_headers, api_request, show_api_error  # noqa: E402

estilo.aplicar()
estilo.encabezado(
    "Reglas de decisión",
    "Los umbrales, las señales de urgencia y los destinos que usa el agente. Viven en agent/rules/rules.yaml y "
    "se cambian sin tocar el código.",
)

try:
    response = api_request("GET", "/rules")
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()
if not response.is_success:
    show_api_error(response)
    st.stop()
reglas = response.json() or {}


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _unicos(lista) -> list[str]:
    """La lista trae cada término con y sin tilde para que el texto coincida igual; se muestra una vez."""
    vistos, salida = set(), []
    for termino in lista or []:
        clave = _sin_tildes(str(termino))
        if clave not in vistos:
            vistos.add(clave)
            salida.append(str(termino))
    return salida


def _fichas(lista) -> str:
    return '<div class="mf-fichas">' + "".join(f'<span class="mf-ficha">{estilo.e(t)}</span>' for t in lista) + "</div>"


def _panel(nombre: str, titulo: str, subtitulo: str):
    contenedor = st.container(border=True, key=f"mf_panel_{nombre}")
    with contenedor:
        estilo.html_(f'<div class="mf-seccion"><div><div class="mf-seccion-titulo">{estilo.e(titulo)}</div>'
                     f'<div class="mf-seccion-sub">{estilo.e(subtitulo)}</div></div></div>')
    return contenedor


umbrales = reglas.get("umbrales") or {}
destinos = reglas.get("destinos") or {}
izquierda, derecha = st.columns(2, gap="medium")

with izquierda:
    with _panel("umbrales", "Umbrales de confianza", "Cuándo el agente decide solo y cuándo pregunta"):
        filas = [
            (umbrales.get("automatico"), "o más: se enruta solo",
             "El documento va directo a su cola, sin intervención humana."),
            (umbrales.get("segunda_opinion"), "o más: zona media",
             "Se enruta, pero con marca de auditoría o segunda opinión."),
            (umbrales.get("legibilidad_minima"), "de legibilidad mínima",
             "Por debajo, la imagen es ilegible: se pide una nueva captura."),
        ]
        estilo.html_("".join(
            f'<div class="mf-umbral"><div class="mf-umbral-v">{estilo.e(estilo.met.decimal(v))}</div>'
            f'<div class="mf-umbral-t">{estilo.e(t)}<span>{estilo.e(d)}</span></div></div>' for v, t, d in filas))
        st.caption("El score combina legibilidad (25 %), validación de datos (30 %), el modelo (25 %) y el acuerdo "
                   "entre pasos (20 %).")

with derecha:
    with _panel("destinos", "Adónde va cada documento", "Si no es urgente ni ambiguo"):
        filas = [[estilo.e(estilo.nombre_tipo(t)), estilo.badge_destino(d)]
                 for t, d in (destinos.get("por_tipo") or {}).items()]
        filas.insert(0, ["<b>Cualquier urgencia</b>", estilo.badge_destino(destinos.get("urgencia"))])
        estilo.html_(estilo.tabla(["Tipo de documento", "Destino"], filas))

with _panel("urgencia", "Señales de urgencia",
            "Basta con una para enviar el documento a Emergencia y avisar a la guardia"):
    aplica = [estilo.nombre_tipo(t) for t in (reglas.get("deteccion_automatica_urgencia") or {}).get("aplica_a", [])]
    st.caption("Las listas automáticas se aplican a: " + ", ".join(aplica) + ". En recetas, epicrisis y "
               "certificados decide el modelo, porque ahí las frases de alarma suelen ser instrucciones de alta.")
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("**Hallazgos críticos**")
        estilo.html_(_fichas(_unicos(reglas.get("hallazgos_criticos"))))
        st.markdown("**Palabras de urgencia**")
        estilo.html_(_fichas(_unicos(reglas.get("palabras_urgencia"))))
    with b:
        st.markdown("**Valores críticos de laboratorio**")
        filas = []
        for v in reglas.get("valores_criticos_laboratorio") or []:
            signo = {">=": "≥", "<=": "≤", ">": ">", "<": "<"}.get(str(v.get("operador")), v.get("operador"))
            numero = v.get("valor")
            if isinstance(numero, int):
                valor = f"{numero:,}".replace(",", ".")
            else:
                valor = str(numero).replace(".", ",")
            filas.append([estilo.e(str(v.get("analito", "")).capitalize()),
                          estilo.e(f"{signo} {valor} {v.get('unidad', '')}")])
        estilo.html_(estilo.tabla(["Analito", "Valor crítico"], filas))

izquierda, derecha = st.columns(2, gap="medium")
with izquierda:
    with _panel("riesgo", "Medicamentos de alto riesgo",
                "No disparan Emergencia: la receta va a Farmacia con auditoría obligatoria"):
        estilo.html_(_fichas(_unicos(reglas.get("medicamentos_alto_riesgo"))))
    with _panel("alcance", "Fuera de alcance (AMB-6)", "El agente reconoce lo que no le corresponde decidir"):
        motivos = (reglas.get("fuera_de_alcance") or {}).get("motivos") or {}
        st.markdown("\n".join(f"- {m}" for m in motivos.values()))
        st.caption("El texto del documento es dato, nunca instrucción: una orden escondida en el documento se ignora.")
with derecha:
    with _panel("obligatorios", "Campos obligatorios", "Si falta alguno, el documento va a revisión (AMB-1)"):
        filas = [[estilo.e(estilo.nombre_tipo(t)), estilo.e(", ".join(aud.etiqueta_campo(c) for c in campos))]
                 for t, campos in (reglas.get("campos_obligatorios") or {}).items() if campos]
        estilo.html_(estilo.tabla(["Tipo", "Campos"], filas))

with st.expander("Editar reglas (administrador)"):
    st.caption("Requiere RULES_ADMIN_TOKEN en el servidor. En la demo pública la edición está desactivada.")
    editor = st.text_input("Quién edita", help="Queda registrado en la auditoría de cambios.")
    raw = st.text_area("Reglas (JSON)", value=json.dumps(reglas, indent=2, ensure_ascii=False), height=300)
    if st.button("Guardar reglas", type="primary"):
        if not editor.strip():
            st.error("Indica quién edita.")
            st.stop()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            st.error(f"JSON inválido: {exc}")
            st.stop()
        try:
            put_response = api_request("PUT", "/rules", json=payload, headers=admin_headers(editor.strip()))
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()
        if put_response.is_success:
            st.success("Reglas guardadas.")
            body = put_response.json()
            if isinstance(body, dict) and body.get("aviso"):
                st.warning(body["aviso"])
        else:
            show_api_error(put_response)
