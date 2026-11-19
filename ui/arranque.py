"""Arranque de la API dentro del mismo proceso de Streamlit.

Streamlit Community Cloud corre un solo proceso. Si no hay una API externa configurada (API_URL)
ni una corriendo en el puerto local, esta función levanta FastAPI en un hilo de fondo, una sola vez.
En local con Docker Compose o en OCI, API_URL apunta a la API real y aquí no se hace nada.
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
PUERTO = int(os.getenv("MEDIFLOW_API_PORT", "8000"))
_lock = threading.Lock()
_iniciada = False


def _api_responde(url: str) -> bool:
    try:
        return httpx.get(f"{url}/health", timeout=1).is_success
    except httpx.HTTPError:
        return False


def _secretos_como_entorno() -> None:
    """Las claves guardadas en los secretos de Streamlit pasan al entorno, donde las lee el agente."""
    try:
        import streamlit as st

        for clave, valor in st.secrets.items():
            if isinstance(valor, (str, int, float, bool)):
                os.environ.setdefault(clave, str(valor))
    except Exception:  # sin archivo de secretos
        pass


def asegurar_api() -> None:
    global _iniciada
    if _iniciada or os.getenv("API_URL"):
        return
    with _lock:
        if _iniciada:
            return
        url = f"http://127.0.0.1:{PUERTO}"
        if _api_responde(url):
            _iniciada = True
            return

        _secretos_como_entorno()
        datos = Path(os.getenv("MEDIFLOW_DATA_DIR") or Path(tempfile.gettempdir()) / "mediflow-data")
        datos.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MEDIFLOW_DATA_DIR", str(datos))
        os.environ.setdefault("MEDIFLOW_TRIAGE_DB", str(datos / "triage_results.sqlite3"))
        os.environ.setdefault("RULES_OVERRIDE_PATH", str(datos / "rules.override.yaml"))
        os.environ.setdefault("RULES_AUDIT_PATH", str(datos / "rules.audit.jsonl"))
        os.environ.setdefault("STORAGE_BACKEND", "local")
        os.environ.setdefault("ENV", "dev")
        os.environ.setdefault("MEDIFLOW_DEMO", "true")
        os.environ.setdefault("ALERTA_OCULTAR_PACIENTE", "true")
        os.environ.setdefault("LLM_PRIMARY", "groq/qwen/qwen3.8-27b")
        if "USE_LLM" not in os.environ:
            con_clave = any(os.getenv(k) for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY"))
            os.environ["USE_LLM"] = "true" if con_clave else "false"

        if str(RAIZ) not in sys.path:
            sys.path.insert(0, str(RAIZ))
        import uvicorn

        servidor = uvicorn.Server(uvicorn.Config("api.main:app", host="127.0.0.1", port=PUERTO, log_level="warning"))
        threading.Thread(target=servidor.run, name="mediflow-api", daemon=True).start()
        for _ in range(60):
            if _api_responde(url):
                break
            time.sleep(0.5)
        _iniciada = True
