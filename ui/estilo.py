"""Estilo común de todas las páginas: la misma hoja de estilos del panel de Métricas más los componentes
de las demás páginas (tarjeta de resultado, etiquetas de destino, pasos de la traza y fichas de reglas).

Todo el HTML que se arma aquí escapa los textos que vienen del documento o de la API.
"""
from __future__ import annotations

import html
from typing import Any

import metricas as met
import streamlit as st

# Color de cada destino: lo urgente en rojo, lo que espera a una persona en ámbar, lo que sigue solo en verde.
COLOR_DESTINO = {
    "Cola_Emergencia_Medica": "#d43c3c",
    "Cola_Revision_Humana": "#d98a0b",
    "Farmacia_Hospitalaria": "#23945a",
    "Auditoria_Autorizaciones": "#23945a",
    "Historia_Clinica_Electronica": "#23945a",
    "Rechazado": "#7a7974",
}
COLOR_PRIORIDAD = {"Urgente": "#d43c3c", "Prioritario": "#d98a0b", "Rutina": "#2a78d6"}

# Pasos del grafo, en el orden en que corren, con un nombre que entiende cualquiera.
PASOS = {
    "normalizar": ("Lectura", "Detecta el formato, extrae el texto (OCR en imágenes) y mide la legibilidad."),
    "clasificar": ("Clasificación", "El modelo decide qué tipo de documento es y su prioridad."),
    "extraer": ("Extracción", "El modelo saca los datos clínicos y cita el fragmento de donde sale cada uno."),
    "validar": ("Validación", "Revisa campos obligatorios, CIE-10, dosis y contradicciones."),
    "puntuar": ("Confianza", "Combina legibilidad, validación, modelo y acuerdo en un score de 0 a 1."),
    "segunda_opinion": ("Segunda opinión", "Consulta a otro modelo cuando la confianza es media."),
    "detectar_urgencia": ("Urgencia", "Busca hallazgos críticos, palabras de alarma y valores críticos."),
    "enrutar": ("Enrutamiento", "Elige la cola de destino y si hace falta auditoría."),
    "revision_humana": ("Revisión humana", "Pausa el documento hasta que un auditor decida."),
    "persistir": ("Guardado", "Guarda el original y el resultado en el almacenamiento."),
    "notificar": ("Aviso", "Si es urgente, avisa a la guardia sin el nombre del paciente."),
}
NOMBRES_CLAVE = {
    "tipo_archivo": "formato", "legibilidad": "legibilidad", "caracteres": "caracteres leídos",
    "fuente": "origen del texto", "tipo_documento": "tipo", "nivel_prioridad": "prioridad",
    "score_confianza_clasificacion": "confianza", "idioma": "idioma", "legible": "legible",
    "campos_cantidad": "campos extraídos", "campos_faltantes_cantidad": "campos faltantes",
    "conflictos_cantidad": "contradicciones", "categoria_amb": "categoría", "validacion": "validación",
    "modelo": "modelo", "acuerdo": "acuerdo", "score": "score", "detectada": "urgencia detectada",
    "destino_principal": "destino", "requiere_auditoria_humana": "requiere auditoría",
    "status_backup": "guardado", "enviada": "aviso enviado", "imagenes": "imágenes",
    "legibilidad_provisional": "legibilidad provisional",
}


def tema_actual() -> str | None:
    try:
        return st.context.theme.type
    except Exception:  # noqa: BLE001 - versiones de Streamlit que no lo exponen
        return None


EXTRA = """<style>
[data-testid="stSidebarNav"] a span{font-size:.92rem}
.mf-marca{font-weight:700;font-size:1.15rem;letter-spacing:-.01em;color:var(--mf-texto);margin:0 0 2px}
.mf-marca small{display:block;font-weight:500;font-size:.75rem;color:var(--mf-suave);letter-spacing:0}
.mf-badge{display:inline-flex;align-items:center;gap:6px;font-size:.8rem;font-weight:600;padding:4px 10px;
  border-radius:999px;color:var(--mf-c);background:color-mix(in srgb,var(--mf-c) 13%,transparent);
  white-space:nowrap}
.mf-badge::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--mf-c)}
.mf-resultado{background:var(--mf-panel);border:1px solid var(--mf-borde);border-left:5px solid var(--mf-c);
  border-radius:14px;padding:20px 24px;box-shadow:0 1px 2px var(--mf-sombra);margin:6px 0 14px}
.mf-resultado-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.mf-resultado-destino{font-size:1.45rem;font-weight:700;color:var(--mf-texto);letter-spacing:-.01em;margin:4px 0 2px}
.mf-resultado-que{color:var(--mf-suave);font-size:.92rem;max-width:640px;line-height:1.5}
.mf-datos{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-top:18px;
  padding-top:16px;border-top:1px solid var(--mf-borde)}
.mf-dato-et{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--mf-tenue)}
.mf-dato-v{font-size:1rem;font-weight:600;color:var(--mf-texto);margin-top:3px;overflow-wrap:anywhere}
.mf-razones{margin:14px 0 0;padding:0;list-style:none}
.mf-razones li{position:relative;padding:6px 0 6px 22px;color:var(--mf-texto);font-size:.93rem;line-height:1.5}
.mf-razones li::before{content:"";position:absolute;left:4px;top:14px;width:7px;height:7px;border-radius:50%;
  background:var(--mf-c)}
.mf-tabla{width:100%;border-collapse:separate;border-spacing:0;font-size:.9rem;background:var(--mf-panel);
  border:1px solid var(--mf-borde);border-radius:14px;overflow:hidden;box-shadow:0 1px 2px var(--mf-sombra)}
.mf-tabla th{text-align:left;font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--mf-tenue);padding:12px 14px;border-bottom:1px solid var(--mf-borde);background:var(--mf-panel)}
.mf-tabla td{padding:12px 14px;border-bottom:1px solid var(--mf-borde);color:var(--mf-texto);vertical-align:top}
.mf-tabla tr:last-child td{border-bottom:none}
.mf-tabla .mf-mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.84rem}
.mf-tabla .mf-tenue{color:var(--mf-suave);font-size:.85rem}
.mf-pasos{position:relative;margin:8px 0 0;padding:0;list-style:none}
.mf-paso{position:relative;display:grid;grid-template-columns:34px 1fr auto;gap:14px;padding:0 0 18px}
.mf-paso::before{content:"";position:absolute;left:16px;top:30px;bottom:0;width:2px;background:var(--mf-borde)}
.mf-paso:last-child::before{display:none}
.mf-paso-n{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:.85rem;color:#fff;background:var(--mf-c);z-index:1}
.mf-paso-t{font-weight:650;color:var(--mf-texto);font-size:.98rem}
.mf-paso-d{color:var(--mf-suave);font-size:.84rem;margin:2px 0 6px}
.mf-paso-ms{color:var(--mf-tenue);font-size:.8rem;font-variant-numeric:tabular-nums;white-space:nowrap;padding-top:4px}
.mf-kv{display:inline-flex;gap:4px;font-size:.78rem;background:var(--mf-pista);color:var(--mf-texto);
  border-radius:8px;padding:3px 8px;margin:3px 6px 0 0}
.mf-kv b{font-weight:600;color:var(--mf-suave)}
.mf-fichas{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.mf-ficha{font-size:.82rem;background:var(--mf-pista);color:var(--mf-texto);border-radius:8px;padding:4px 10px}
.mf-umbral{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--mf-borde)}
.mf-umbral:last-child{border-bottom:none}
.mf-umbral-v{font-size:1.4rem;font-weight:700;color:var(--mf-texto);min-width:70px;font-variant-numeric:tabular-nums}
.mf-umbral-t{color:var(--mf-texto);font-size:.92rem;line-height:1.45}
.mf-umbral-t span{display:block;color:var(--mf-suave);font-size:.82rem}
.mf-hero{background:linear-gradient(135deg,#123a6b 0%,#2a78d6 100%);color:#fff;border-radius:18px;
  padding:34px 36px;margin:4px 0 22px;box-shadow:0 8px 24px rgba(16,24,40,.12)}
.mf-hero h1{color:#fff!important;font-size:2.3rem;font-weight:750;letter-spacing:-.02em;margin:6px 0 8px;padding:0}
.mf-hero p{color:rgba(255,255,255,.88);font-size:1.05rem;line-height:1.6;max-width:760px;margin:0}
.mf-hero .mf-eyebrow{color:#9cc7f5}
.mf-flujo{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:6px 0 20px}
.mf-flujo div{background:var(--mf-panel);border:1px solid var(--mf-borde);border-radius:14px;padding:16px 18px;
  box-shadow:0 1px 2px var(--mf-sombra)}
.mf-flujo b{display:block;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;color:var(--mf-acento);
  margin-bottom:6px}
.mf-flujo strong{display:block;color:var(--mf-texto);font-size:1rem;margin-bottom:4px}
.mf-flujo span{color:var(--mf-suave);font-size:.86rem;line-height:1.45}
.mf-aviso{background:var(--mf-panel);border:1px solid var(--mf-borde);border-radius:12px;padding:12px 16px;
  color:var(--mf-suave);font-size:.86rem;line-height:1.5;margin:4px 0 16px}
.mf-aviso b{color:var(--mf-texto)}
</style>"""


def aplicar() -> None:
    """Hoja de estilos de MediFlow y marca en la barra lateral. Se llama al inicio de cada página."""
    st.markdown(met.estilos(tema_actual()), unsafe_allow_html=True)
    st.markdown(EXTRA, unsafe_allow_html=True)


def html_(texto: str) -> None:
    st.markdown(texto, unsafe_allow_html=True)


def e(valor: Any) -> str:
    return html.escape(str(valor if valor is not None else "—"))


def encabezado(titulo: str, subtitulo: str, estado: str | None = None, ok: bool = True) -> None:
    if estado:
        html_(met.encabezado_html(titulo, subtitulo, api_ok=ok, detalle_api=estado))
    else:
        html_(f'<div class="mf-top"><div><div class="mf-eyebrow">MediFlow · Triaje documental clínico</div>'
              f'<div class="mf-h1">{e(titulo)}</div><div class="mf-sub">{e(subtitulo)}</div></div></div>')


def nombre_destino(destino: str | None) -> str:
    if destino == "Rechazado":
        return "Rechazado"
    return met.DESTINOS.get(str(destino), str(destino or "—").replace("_", " "))


def nombre_tipo(tipo: str | None) -> str:
    return met.TIPOS.get(str(tipo), str(tipo or "Sin clasificar"))


def badge(texto: str, color: str) -> str:
    return f'<span class="mf-badge" style="--mf-c:{color}">{e(texto)}</span>'


def badge_destino(destino: str | None) -> str:
    return badge(nombre_destino(destino), COLOR_DESTINO.get(str(destino), "#2a78d6"))


def badge_prioridad(prioridad: str | None) -> str:
    return badge(prioridad or "Sin prioridad", COLOR_PRIORIDAD.get(str(prioridad), "#7a7974"))


def porcentaje(valor: Any) -> str:
    return met.porcentaje(valor)


def tabla(columnas: list[str], filas: list[list[str]]) -> str:
    """Tabla HTML. Las celdas ya vienen escapadas o armadas con badge()."""
    cabeza = "".join(f"<th>{e(c)}</th>" for c in columnas)
    cuerpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in fila) + "</tr>" for fila in filas)
    return f'<table class="mf-tabla"><thead><tr>{cabeza}</tr></thead><tbody>{cuerpo}</tbody></table>'


def marca_lateral() -> None:
    with st.sidebar:
        html_('<div class="mf-marca">MediFlow<small>Triaje documental clínico</small></div>')


def nombre_modelo(modelo: str | None) -> str:
    if not modelo or modelo in ("stub", "sin modelo", "reglas"):
        return "Motor de reglas"
    return str(modelo).split("/")[-1]


def categoria_amb(resultado: dict) -> str | None:
    """La categoría de ambigüedad que anotó el paso de validación, si hubo una."""
    for paso in resultado.get("trace") or []:
        if isinstance(paso, dict) and paso.get("nodo") == "validar":
            categoria = (paso.get("detalle") or {}).get("categoria_amb")
            if categoria:
                return str(categoria)
    return None


def razones(justificacion: str | None) -> list[str]:
    """Parte la justificación del enrutamiento en frases cortas, una por razón."""
    texto = str(justificacion or "").strip()
    if not texto:
        return []
    partes: list[str] = []
    for frase in texto.replace("; ", ". ").split(". "):
        frase = frase.strip().rstrip(".")
        if frase:
            partes.append(frase[0].upper() + frase[1:] + ".")
    return partes


def tarjeta_resultado(resultado: dict) -> str:
    decision = resultado.get("decision_enrutamiento") or {}
    clasificacion = resultado.get("clasificacion") or {}
    destino = decision.get("destino_principal")
    color = COLOR_DESTINO.get(str(destino), "#2a78d6")
    insignias = [badge_prioridad(clasificacion.get("nivel_prioridad"))]
    if decision.get("requiere_auditoria_humana") and destino != "Cola_Revision_Humana":
        insignias.append(badge("Marcado para auditoría", "#d98a0b"))
    if decision.get("notificacion_generada"):
        insignias.append(badge("Guardia avisada", "#d43c3c"))
    amb = categoria_amb(resultado)
    if amb:
        insignias.append(badge(amb, "#7a7974"))
    lista = "".join(f"<li>{e(r)}</li>" for r in razones(decision.get("justificacion_enrutamiento")))
    almacenamiento = resultado.get("almacenamiento_oci") or {}
    datos = [
        ("Documento", resultado.get("documento_id")),
        ("Tipo", nombre_tipo(clasificacion.get("tipo_documento"))),
        ("Confianza", porcentaje(resultado.get("score_confianza"))),
        ("Leído por", nombre_modelo(resultado.get("modelo_utilizado"))),
        ("Guardado", "Sí" if almacenamiento.get("status_backup") == "exito" else "No"),
    ]
    grilla = "".join(f'<div><div class="mf-dato-et">{e(k)}</div><div class="mf-dato-v">{e(v)}</div></div>'
                     for k, v in datos)
    return (
        f'<div class="mf-resultado" style="--mf-c:{color}"><div class="mf-resultado-top"><div>'
        f'<div class="mf-eyebrow">Decisión del agente</div>'
        f'<div class="mf-resultado-destino">{e(nombre_destino(destino))}</div>'
        f'<div class="mf-resultado-que">{e(met.SIGNIFICADO_DESTINOS.get(str(destino), ""))}</div></div>'
        f'<div class="mf-fichas">{"".join(insignias)}</div></div>'
        f'<ul class="mf-razones">{lista}</ul><div class="mf-datos">{grilla}</div></div>'
    )
