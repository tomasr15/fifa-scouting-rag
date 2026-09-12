"""Laboratorio educativo independiente del corpus, Chroma y los proveedores LLM."""
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "exposition_assets"


def standalone_html():
    """Documento autocontenido: se puede proyectar sin conexión ni dependencias CDN."""
    return (ASSETS / "index.html").read_text(encoding="utf-8").replace(
        "/*__STYLES__*/", (ASSETS / "style.css").read_text(encoding="utf-8")
    ).replace("/*__MODEL__*/", (ASSETS / "model.js").read_text(encoding="utf-8")).replace(
        "/*__UI__*/", (ASSETS / "ui.js").read_text(encoding="utf-8")
    )


def render_exposition():
    import streamlit as st
    import streamlit.components.v1 as components

    def go_to_search():
        st.session_state.app_section = "Buscador"

    st.title("Bases de datos vectoriales")
    st.caption("Laboratorio para la exposición · tres modelos didácticos · sin conexión a servicios externos")
    st.button("Ir al caso práctico: buscador", on_click=go_to_search)
    components.html(standalone_html(), height=1050, scrolling=True)
