"""Interfaz para los tres CSV del usuario, con filtros escalares visibles."""
import json
import pandas as pd
import streamlit as st
from supplied_data import DATA, POSITION, open_store
from rag_pipeline import LLMConfig, run_scouting


@st.cache_resource
def resources():
    return open_store()


def render():
    st.title('⚽ Scouting · CSV de jugadores, equipos y técnicos')
    info=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    st.caption(f"FIFA/EA FC {info['snapshot']['fifa_version']} · {info['snapshot']['update_as_of']} · CSV aportados por el usuario, enlaces SoFIFA")
    st.info('Datos del videojuego: valoraciones técnicas, tácticas y valores económicos; no son estadísticas oficiales de partidos ni finanzas auditadas.')
    st.write(info['counts'])
    # No indexar ni cargar MiniLM por el mero hecho de abrir la página.
    if not st.checkbox('Activar buscador local (Chroma + embeddings MiniLM)',key='supplied_enabled'):
        st.caption('Buscador inactivo. Al activarlo se carga el modelo pequeño de embeddings; el reporte LLM se genera por API. La primera indexación puede demorar varios minutos.')
        return
    with st.spinner('Preparando la colección vectorial del nuevo dataset…'):
        store,records,benchmark=resources()
    with st.expander('Colección e instrumentación',expanded=True): st.json(store.technical_summary())
    with st.sidebar:
        kind=st.selectbox('Tipo de entidad',['player','club','coach'])
        clauses=[{'entity_type':kind},{'gender':'male'}]
        eligible=[r for r in records if r['metadata']['entity_type']==kind]
        league=st.selectbox('Liga',['Todas']+sorted({r['metadata']['league'] for r in eligible}))
        if league!='Todas': clauses.append({'league':league})
        if kind=='player':
            pos=st.selectbox('Posición',['Todas']+list(POSITION),format_func=lambda x: f'{x} · {POSITION[x]}' if x in POSITION else x)
            if pos!='Todas': clauses.append({'plays_'+pos:True})
            if st.checkbox('Excluir arqueros',True): clauses.append({'is_goalkeeper':False})
            if pos=='GK':
                clauses=[c for c in clauses if 'is_goalkeeper' not in c]
            if st.checkbox('Limitar edad'):
                clauses.append({'age':{'$lte':st.slider('Edad máxima',15,50,25)}})
            minimum=st.slider('Regate mínimo (valoración del juego)',0,100,0)
            if minimum: clauses.append({'dribbling':{'$gte':minimum}})
        elif kind=='coach' and st.checkbox('Sólo técnicos con equipo asociado',True):
            clauses.append({'has_team':True})
        k=st.slider('Resultados',1,15,5)
        rerank=st.checkbox('Reordenar por los atributos de la consulta',True)
        st.caption('El embedding no compara magnitudes. Con esta opción se recupera un pool amplio por '
                   'cercanía semántica y se ordena por el percentil de los atributos nombrados en el texto. '
                   'Desactivala para ver el orden vectorial puro.')
        provider=st.selectbox('Generador',['none','openai','ollama'])
        st.caption('openai usa el proveedor configurado en .env, incluido OpenRouter. none no llama al LLM.')
        compare=st.checkbox('Comparar ANN vs LIKE',True)
    with st.form('supplied_search'):
        query=st.text_area('Consulta','Delantero con regate y desborde')
        submit=st.form_submit_button('Buscar en los CSV')
    st.caption('La consulta no crea filtros automáticamente. Usá posición y umbrales para requisitos exactos. Los nombres quedan fuera de los embeddings.')
    if submit:
        st.session_state.pop('supplied_result',None)
        try:
            with st.spinner('Buscando y preparando el reporte…'):
                st.session_state.supplied_result=run_scouting(query,store,k,{'$and':clauses},LLMConfig.from_env(provider),benchmark if compare else None,rerank_by_attributes=rerank)
        except Exception as exc: st.error(f'No se completó la búsqueda: {type(exc).__name__}')
    if 'rerank' not in st.session_state.get('supplied_result',{'rerank':None}):
        # Descarta salidas de una versión anterior al recargar una sesión ya abierta.
        st.session_state.pop('supplied_result')
    if 'supplied_result' not in st.session_state: return
    r=st.session_state.supplied_result
    st.write('Consulta ejecutada:',r['query']); st.json(r['where_filter'])
    a,b,c=st.columns(3)
    a.metric('Chroma execution_time_ms',f"{r['execution_time_ms']:.6f} ms")
    b.metric('Embedding',f"{r['embedding_time_ms']:.6f} ms")
    c.metric('Recuperación',f"{r['retrieval_time_ms']:.6f} ms")
    st.caption('Chroma.query incluye filtros y lectura de documentos. Score = 1 − distancia coseno, no confianza ni calidad futbolística.')
    rr=r['rerank']
    with st.expander('Ordenamiento aplicado',expanded=True):
        st.write(rr['reason'])
        if rr['applied']:
            st.write(f"Pool recuperado por ANN: **{rr['pool_size']}** vectores. "
                     "La distancia coseno decide quién es candidato; el percentil de los "
                     "atributos decide el orden, y la similitud sólo desempata.")
            st.json({'atributos_detectados':rr['aspects_detected'],'usados':rr['aspects_used']})
            moved=[i for i,x in enumerate(r['candidates']) if x['id'] not in r['ann_top_ids']]
            st.caption(f"{len(moved)} de {len(r['candidates'])} candidatos no estaban en el top {len(r['ann_top_ids'])} "
                       "por distancia coseno: el orden vectorial puro los ubicaba más abajo del pool.")
            if rr.get('pool_exhaustive'):
                st.success('Cobertura completa: el pool agotó el subconjunto que pasa los filtros, '
                           'así que el orden por atributos examinó a todos los candidatos elegibles.')
            else:
                st.warning('Cobertura parcial: hay más candidatos elegibles que el tope del pool, así que '
                           'se ordenaron los más cercanos semánticamente y el resto quedó sin examinar. '
                           'Acotá con posición o liga para obtener un orden exacto.')
        elif rr.get('aspects_detected'):
            st.caption('Se detectaron atributos pero el corpus no guarda percentiles para ellos.')
    if r['candidates']:
        st.dataframe(pd.DataFrame([{'Nombre':x['metadata']['name'],'Equipo':x['metadata']['club'],
           'ID vector':x['id'],'Distancia raw':x['distance'],'Score 1-d':x['similarity'],
           'Ajuste atributos':x.get('attribute_fit'),'Valoración media':x.get('attribute_raw_mean'),
           'Metadata where':json.dumps(x['filter_metadata'],ensure_ascii=False)} for x in r['candidates']]),hide_index=True)
        st.caption('«Ajuste atributos» es el percentil medio de los atributos que nombra la consulta, entre 0 y 1, '
                   'y es la clave de orden. «Valoración media» es el promedio crudo de esos mismos atributos y '
                   'desempata entre percentiles iguales. Ninguno es una probabilidad ni una medida de calidad futbolística.')
    for i,x in enumerate(r['candidates'],1):
        with st.expander(f"[J{i}] {x['metadata']['name']}"):
            st.write(x['document']); st.json(x['metadata'])
    if r['benchmark']:
        lex=r['benchmark']['lexical']
        st.subheader('ANN vs LIKE')
        st.write(f"ANN: {len(r['candidates'])} vecinos; LIKE: {lex['total_matches']} coincidencias, {lex['execution_time_ms']:.6f} ms")
        st.json({'terms':lex['terms'],'eligible_count':lex['eligible_count']})
        st.caption(r['benchmark']['note'])
    if r['warning']: st.warning(r['warning'])
    st.success('Reporte generado por el LLM') if r['generated'] else st.info('Evidencia local sin reporte LLM')
    st.markdown(r['report'])
    st.download_button('Descargar evidencia con fuentes',json.dumps(r,ensure_ascii=False,indent=2),'csv_result.json','application/json')
