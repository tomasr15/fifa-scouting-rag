"""Vista del dataset real, comparte Chroma, instrumentación y pipeline RAG."""
import json
import pandas as pd
import streamlit as st

from fifa_corpus import DATA, open_fifa_store
from rag_pipeline import LLMConfig, run_scouting


@st.cache_resource
def resources():
    return open_fifa_store()


def render():
    st.title("⚽ FIFA real · buscador vectorial de fútbol masculino")
    st.caption("Mundial de Clubes FIFA 2025 · Jugadores / equipos / técnicos · fuentes oficiales, perfiles derivados")
    if not (DATA / "corpus.jsonl").exists():
        st.info("El corpus FIFA se está preparando. Para reconstruir: python fifa_ingest.py --download; python fifa_corpus.py")
        return
    try:
        with st.spinner("Cargando el índice de evidencia FIFA..."):
            store, records, benchmark = resources()
    except Exception as exc:
        st.error(f"No se pudo abrir el corpus: {exc}")
        return
    info = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    count = info["counts"]
    st.success(f"{count['players']} jugadores registrados · {count['clubs']} clubes · {count['coaches']} técnicos · "
               f"{count['matches']} partidos · {len(records)} vectores de evidencia")
    st.caption("Dataset derivado de documentos FIFA oficiales. No es una API ni un CSV publicado por FIFA. "
               "Plantel según lista del 4/7/2025; edades al 14/6/2025. Técnicos de ese snapshot, no actuales.")
    with st.expander("Motor vectorial y diseño de los documentos", expanded=True):
        st.json(store.technical_summary())
        st.write("El embedding contiene **perfil técnico, táctico o físico y estadísticas**. "
                 "Nombres, clubes y enlaces quedan fuera del texto vectorizado, disponibles como metadata y evidencia. "
                 "Un jugador puede tener varios fragmentos; k cuenta vectores, no personas únicas.")
    kinds = {"Jugadores": "player", "Equipos": "club", "Técnicos": "coach", "Todas las entidades": None}
    with st.sidebar:
        st.header("Filtros del corpus FIFA")
        kind_label = st.selectbox("Buscar", list(kinds))
        kind = kinds[kind_label]
        clubs = sorted({r["metadata"]["club"] for r in records})
        club = st.selectbox("Club", ["Todos"] + clubs)
        aspect = st.selectbox("Dimensión del perfil", ["Todas", "technique", "defence", "physical", "tactics", "editorial_tactics", "economics", "roster"])
        with_stats = st.checkbox("Sólo entidades con estadísticas", True)
        clauses = [{"gender": "male"}, {"season": 2025}]
        if kind: clauses.append({"entity_type": kind})
        if club != "Todos": clauses.append({"club": club})
        if aspect != "Todas": clauses.append({"aspect": aspect})
        if with_stats: clauses.append({"has_stats": True})
        if kind == "player":
            position = st.selectbox("Posición FIFA", ["Todas", "GK", "DF", "MF", "FW"])
            if position != "Todas": clauses.append({"position": position})
            use_age = st.checkbox("Limitar edad del jugador")
            max_age = st.slider("Edad máxima al inicio del torneo", 15, 45, 25, disabled=not use_age)
            if use_age: clauses.append({"age": {"$lte": max_age}})
            appearances = st.slider("Mínimo de participaciones observadas", 0, 7, 0)
            if appearances: clauses.append({"appearances": {"$gte": appearances}})
            minimum_passing = st.number_input("Precisión de pase mínima (%)", min_value=0.0, max_value=100.0, value=0.0)
            if minimum_passing: clauses.append({"pass_completion_pct": {"$gte": minimum_passing}})
        k = st.slider("Fragmentos a recuperar", 1, 15, 5)
        compare = st.checkbox("Comparar ANN vs LIKE", True)
        provider = st.selectbox("Generador", ["none", "openai", "ollama"])
        st.caption("Clave: OPENAI_API_KEY en .env, junto a app.py (ver .env.example). "
                   "none = evidencia sin LLM. OpenAI envía consulta y fragmentos al proveedor configurado.")
    with st.form("fifa_query"):
        query = st.text_area("Consulta conceptual", "Lateral que avanza por dentro y genera superioridad en el centro del campo")
        submit = st.form_submit_button("Buscar evidencia FIFA", type="primary")
    st.caption("Ejemplos: presión alta y contrapresión; recuperación e intercepciones; velocidad y sprints; "
               "premio económico por participación. Para economía seleccioná Equipos + economics.")
    if submit:
        st.session_state.pop("fifa_result", None)
        try:
            with st.spinner("Calculando embedding y buscando evidencia..."):
                where = {"$and": clauses}
                st.session_state.fifa_result = run_scouting(query, store, k, where,
                    LLMConfig.from_env(provider), benchmark if compare else None)
        except Exception as exc:
            st.error(str(exc))
    if "fifa_result" not in st.session_state:
        return
    result = st.session_state.fifa_result
    st.subheader("Resultados de la base vectorial")
    st.write(result["query"])
    st.json(result["where_filter"])
    a, b, c = st.columns(3)
    a.metric("Chroma execution_time_ms", f"{result['execution_time_ms']:.6f} ms")
    b.metric("Embedding", f"{result['embedding_time_ms']:.6f} ms")
    c.metric("Recuperación sin LLM", f"{result['retrieval_time_ms']:.6f} ms")
    st.caption("Chroma.query incluye filtros y lectura de evidencia; no es tiempo puro del grafo HNSW. "
               "La similitud = 1 − distancia está en [-1, 1]; no es confianza ni calidad futbolística.")
    candidates = result["candidates"]
    if candidates:
        st.dataframe(pd.DataFrame([{"Entidad": x["metadata"]["name"], "Tipo": x["metadata"]["entity_type"],
             "Club": x["metadata"]["club"], "Aspecto": x["metadata"]["aspect"], "ID vector": x["id"],
             "Distancia raw": x["distance"], "Score 1-d": x["similarity"],
             "Metadata where": json.dumps(x["filter_metadata"], ensure_ascii=False)} for x in candidates]),
             hide_index=True, width="stretch")
    by_id = {r["id"]: r for r in records}
    for i, candidate in enumerate(candidates, 1):
        m = candidate["metadata"]
        with st.expander(f"[J{i}] {m['name']} · {m['aspect']} · evidencia y procedencia"):
            st.write(candidate["document"])
            st.caption("Texto realmente vectorizado (sin identidad):")
            st.text(by_id[candidate["id"]]["embedding_text"])
            st.json({"id": candidate["id"], "distance": candidate["distance"], "similarity": candidate["similarity"], "metadata": m})
            for ref in json.loads(m["source_refs_json"]):
                url = ref["url"] + (f"#page={ref['page']}" if "page" in ref else "")
                st.link_button(f"Fuente FIFA · partido {ref.get('match_id', '—')} · página {ref.get('page', 'web')}", url)
    if result["benchmark"]:
        comp = result["benchmark"]
        lexical = comp["lexical"]
        st.subheader("ANN vs LIKE · el mismo perfil sin nombres")
        st.write(f"ANN: {len(candidates)} fragmentos. LIKE: {lexical['total_matches']} coincidencias totales "
                 f"en {lexical['eligible_count']} documentos elegibles; {lexical['execution_time_ms']:.6f} ms.")
        st.json({"terms": lexical["terms"], "operator": "OR", "patterns": lexical["like_patterns"]})
        for x in lexical["candidates"]:
            st.write(f"LIKE: {x['metadata']['name']} · {x['metadata']['aspect']} · {x['matched_terms']}")
        st.caption(comp["note"])
    if result["warning"]: st.warning(result["warning"])
    st.markdown(result["report"])
    st.download_button("Descargar evidencia con fuentes", json.dumps(result, ensure_ascii=False, indent=2),
                       "fifa_result.json", "application/json")
    st.info("Economía: sólo rango oficial del premio de participación, no ingresos ni presupuesto. "
            "Medias de jugadores por aparición: no ajustadas por minutos. Las métricas del equipo "
            "no son una evaluación causal del técnico. El primer vecino puede no ser relevante.")
