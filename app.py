"""Interfaz de demostración: python -m streamlit run app.py."""
import json

import streamlit as st

st.set_page_config(page_title="Bases vectoriales · Scouting", page_icon="⚽", layout="wide")
section = st.sidebar.radio("Sección", ["Buscador", "Exposición interactiva"], key="app_section")
if section == "Exposición interactiva":
    from exposition import render_exposition
    render_exposition()
    st.stop()

import pandas as pd
from data_loader import load_players
from benchmark import BENCHMARK_NOTE, DEMO_QUERY, SearchBenchmark
from rag_pipeline import LLMConfig, run_scouting
from vector_store import PlayerVectorStore, build_filter

dataset_mode = st.sidebar.selectbox("Dataset", ["CSV del usuario · FIFA/EA FC", "FIFA real · Mundial de Clubes 2025", "Demo sintética · 30 jugadores"])
if dataset_mode.startswith("CSV del usuario"):
    from supplied_app import render
    render()
    st.stop()
if dataset_mode.startswith("FIFA real"):
    from fifa_app import render
    render()
    st.stop()
st.title("⚽ Scouting semántico")
st.caption("CSV → MiniLM local · 384 dimensiones → ChromaDB / coseno → contexto → LLM")


@st.cache_resource
def load_store():
    df, source = load_players()
    store = PlayerVectorStore()
    store.initialize(df)
    return store, df, source, SearchBenchmark(store, df), store.technical_summary()


try:
    with st.spinner("Preparando el índice local. La primera ejecución descarga MiniLM..."):
        store, players, source, benchmark, technical = load_store()
except Exception as exc:
    st.error(f"No se pudo cargar el índice: {exc}")
    st.info("Revisá el CSV y la conexión para la primera descarga. Si cambió el dataset, "
            "cerrá Streamlit y ejecutá: python main.py --rebuild --index-only")
    st.stop()

with st.expander("Ficha técnica de la colección vectorial", expanded=True):
    st.write(f"**{technical['collection_name']}** · espacio **{technical['space']}** · "
             f"**{technical['vector_count']} vectores** · **D = {technical['dimensions']}**")
    st.code('metadata={"hnsw:space": "cosine"}', language="python")
    st.caption("La métrica se verifica en configuration de la colección; D se lee de un vector almacenado. "
               "Chroma usa HNSW y puede incluir un buffer de fuerza bruta; estos tiempos no aíslan el grafo.")

with st.sidebar:
    st.header("Criterios de scouting")
    st.caption(f"{source.name} · {store.collection.count()} jugadores indexados")
    st.caption("El mock contiene datos sintéticos ilustrativos; no son fichas actuales.")
    league = st.selectbox("Liga", ["Todas"] + sorted(players["league"].unique().tolist()))
    limit_age = st.checkbox("Filtrar por edad máxima")
    max_age = st.slider("Edad máxima", 15, 60, 27, disabled=not limit_age)
    position = st.selectbox("Posición", ["Todas"] + sorted(players["position"].unique().tolist()))
    k = st.slider("Cantidad de candidatos", 1, 15, 5)
    compare = st.checkbox("Comparar ANN vs LIKE", value=False)
    st.caption(f"Ejemplo conceptual para el mock: «{DEMO_QUERY}». "
               "Compará también con «pase largo» para ver coincidencias literales.")
    provider_label = st.selectbox("Generador", ["Sin LLM (demostración)", "OpenAI / compatible", "Ollama local"])
    provider = {"Sin LLM (demostración)": "none", "OpenAI / compatible": "openai",
                "Ollama local": "ollama"}[provider_label]
    st.caption("Credenciales, URL y modelo se leen de variables de entorno. Ver README.")
    if provider == "openai":
        st.caption("Al buscar se envían la consulta y los perfiles recuperados al proveedor configurado.")

with st.form("scouting_query"):
    query = st.text_area("¿Qué perfil buscás?", value="Buscame un volante mixto con despliegue físico y buen pase largo para jugar de titular en Europa.")
    submitted = st.form_submit_button("Buscar candidatos", type="primary")

st.caption("Las restricciones exactas se aplican con los controles. Mencionarlas en el texto "
           "orienta la búsqueda semántica, pero no crea filtros automáticamente.")

if submitted:
    # Quitar resultados previos evita mostrarlos como si fueran de una consulta fallida.
    st.session_state.pop("result", None)
    try:
        where = build_filter(None if league == "Todas" else league,
                             max_age if limit_age else None,
                             None if position == "Todas" else position)
        with st.spinner("Buscando perfiles y preparando el reporte..."):
            # El mock no expone percentiles de atributos: reordenar no aportaría nada
            # y ampliar el pool distorsionaría los tiempos que muestra esta pantalla.
            st.session_state.result = run_scouting(query, store, k, where, LLMConfig.from_env(provider),
                                                  benchmark if compare else None,
                                                  rerank_by_attributes=False)
    except Exception as exc:
        st.error(f"No se pudo completar la búsqueda: {exc}")

if "result" in st.session_state and "execution_time_ms" not in st.session_state.result:
    # Descarta salidas de la versión anterior al recargar una sesión ya abierta.
    st.session_state.pop("result")

if "result" in st.session_state:
    result = st.session_state.result
    st.subheader("Evidencia de la última búsqueda")
    st.write(result["query"])
    with st.expander("Filtro enviado a ChromaDB"):
        st.json(result["where_filter"] or {})
    candidates = result["candidates"]
    if candidates:
        table = [{"Referencia": f"J{i}", "Jugador": c["metadata"]["name"],
                  "Posición": c["metadata"]["position"], "Edad": c["metadata"]["age"],
                  "Liga": c["metadata"]["league"], "Overall": c["metadata"]["overall_rating"],
                  "ID vector": c["id"], "Distancia coseno raw ↓": c["distance"],
                  "Score 1 − distancia ↑": c["similarity"],
                  "Metadata where": json.dumps(c["filter_metadata"], ensure_ascii=False)}
                 for i, c in enumerate(candidates, 1)]
        st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
        st.caption("distancia = 1 − similitud coseno. No es un porcentaje de confianza "
                   "ni una medida de calidad del jugador. Chroma devuelve los vecinos incluso si el encaje es pobre.")
        for i, c in enumerate(candidates, 1):
            with st.expander(f"[J{i}] {c['metadata']['name']} · distancia {c['distance']:.4f}"):
                st.text(c["document"])
                st.json({"id": c["id"], **c["metadata"]})
                st.json({"distance_raw": c["distance"], "similarity": c["similarity"],
                         "where": result["where_filter"], "filter_metadata": c["filter_metadata"]})
    st.subheader("Instrumentación de la búsqueda vectorial")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Chroma · execution_time_ms", f"{result['execution_time_ms']:.6f} ms")
    col_b.metric("Embedding local", f"{result['embedding_time_ms']:.6f} ms")
    col_c.metric("Recuperación total sin LLM", f"{result['retrieval_time_ms']:.6f} ms")
    st.caption("Cronómetro perf_counter_ns: execution_time_ms mide collection.query con el vector ya "
               "calculado, incluyendo filtros y lectura de resultados. Son mediciones locales variables, "
               "no tiempos exactos del grafo HNSW. La primera consulta puede cargar el modelo. "
               "1 − distancia es similitud coseno en [-1, 1], no un score restringido a [0, 1].")
    if result.get("benchmark"):
        comparison = result["benchmark"]
        lexical = comparison["lexical"]
        st.subheader("Comparativa técnica: ANN vs coincidencia léxica")
        st.dataframe(pd.DataFrame([
            {"Motor": "Chroma / ANN", "Tiempo sin embedding (ms)": result["execution_time_ms"],
             "Resultados mostrados": len(candidates)},
            {"Motor": "pandas / LIKE (escaneo)", "Tiempo sin embedding (ms)": lexical["execution_time_ms"],
             "Resultados mostrados": len(lexical["candidates"])}
        ]), hide_index=True, width="stretch")
        st.write(f"**LIKE: {lexical['total_matches']} coincidencias totales** entre "
                 f"{lexical['eligible_count']} filas elegibles por el mismo where.")
        st.json({"terms": lexical["terms"], "operator": "OR", "LIKE": lexical["like_patterns"],
                 "order_by": lexical["order_by"], "limit": lexical["limit"]})
        for c in lexical["candidates"]:
            with st.expander(f"LIKE · {c['metadata']['name']} · términos: {', '.join(c['matched_terms'])}"):
                st.text(c["document"])
                st.json(c)
        st.write(comparison["interpretation"])
        st.caption(f"Vecinos sin coincidencia literal: {len(comparison['vector_only_ids'])}.")
        st.caption(BENCHMARK_NOTE)
    if result["warning"]:
        st.warning(result["warning"])
    st.subheader("Reporte del asistente" if result["generated"] else "Resumen de recuperación")
    if result["model"]:
        st.caption(f"Modelo: {result['model']}")
    st.markdown(result["report"])
    with st.expander("Prompt y contexto RAG completos"):
        st.json(result["messages"])
    st.download_button("Descargar evidencia y reporte (JSON)",
                       json.dumps(result, ensure_ascii=False, indent=2),
                       file_name="scouting_result.json", mime="application/json")
