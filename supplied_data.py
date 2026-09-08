"""CSV del usuario: snapshots FIFA/EA FC de SoFIFA, separados de datos FIFA reales.

Preparar tablas no carga el modelo ni inicia el servidor. Indexar es explícito.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from data_loader import BASE_DIR
from reranker import ALL_ASPECTS, ASPECTS, GK_ASPECTS, RANK_PREFIX, describe

DATA = BASE_DIR / 'data' / 'supplied'
PROFILE_VERSION = 'supplied-profile-v3'
# Nombre en español y término inglés: el modelo de embeddings es all-MiniLM-L6-v2,
# entrenado en inglés, y ancla mucho mejor el rol con ambas formas presentes.
POSITION = {'GK': 'Arquero portero goalkeeper', 'ST': 'Delantero centro nueve striker',
            'CF': 'Segundo delantero forward', 'LW': 'Extremo izquierdo winger',
            'RW': 'Extremo derecho winger', 'LM': 'Volante izquierdo left midfielder',
            'RM': 'Volante derecho right midfielder', 'CM': 'Mediocampista central midfielder',
            'CAM': 'Mediapunta creativo attacking midfielder',
            'CDM': 'Mediocentro defensivo pivote holding midfielder',
            'CB': 'Defensor central zaguero centre back', 'LB': 'Lateral izquierdo left back',
            'RB': 'Lateral derecho right back', 'LWB': 'Carrilero izquierdo left wing back',
            'RWB': 'Carrilero derecho right wing back'}
ATTRIBUTES = {'pace': 'Ritmo', 'shooting': 'Tiro', 'passing': 'Pase', 'dribbling': 'Regate gambeta',
 'defending': 'Defensa', 'physic': 'Físico', 'skill_long_passing': 'Pase largo',
 'mentality_vision': 'Visión', 'power_stamina': 'Resistencia', 'power_strength': 'Fuerza',
 'movement_sprint_speed': 'Velocidad', 'attacking_finishing': 'Definición',
 'mentality_interceptions': 'Intercepciones', 'attacking_heading_accuracy': 'Juego aéreo',
 'power_jumping': 'Salto', 'attacking_crossing': 'Centros', 'skill_fk_accuracy': 'Tiros libres',
 'goalkeeping_diving': 'Estiradas', 'goalkeeping_handling': 'Blocaje',
 'goalkeeping_reflexes': 'Reflejos', 'goalkeeping_positioning': 'Colocación de portero'}
TACTICS = {'def_style':'Estilo defensivo', 'off_style':'Estilo ofensivo',
 'off_build_up_play':'Construcción de juego', 'off_chance_creation':'Creación de ocasiones',
 'def_team_depth':'Profundidad defensiva', 'def_team_width':'Anchura defensiva',
 'off_team_width':'Anchura ofensiva', 'off_players_in_box':'Jugadores en el área',
 'build_up_play_speed':'Velocidad de construcción', 'def_defence_pressure':'Presión defensiva'}
TRANSLATE = {'Press after possession loss':'Presión tras pérdida', 'Constant pressure':'Presión constante',
 'Pressure on heavy touch':'Presión ante mal control', 'Drop back':'Repliegue', 'Balanced':'Equilibrado',
 'Slow build up':'Construcción lenta', 'Fast build up':'Construcción rápida', 'Long ball':'Balón largo',
 'Possession':'Posesión', 'Forward runs':'Desmarques hacia adelante', 'Direct passing':'Pase directo'}


FOOT = {'Left': 'zurdo, pie izquierdo, left footed', 'Right': 'diestro, pie derecho, right footed'}


def clean(row):
    return {k: v for k, v in row.items() if pd.notna(v) and isinstance(v, (str, int, float, bool))}


def rank_table(frame):
    """Percentil de cada atributo dentro del grupo comparable: campo o arquero.

    Se usa el percentil y no el valor bruto porque las escalas no son homogéneas:
    la resistencia se concentra entre 60 y 85 mientras la definición se dispersa
    de 20 a 95. Promediar valores brutos de atributos distintos dejaría que el eje
    de mayor escala domine siempre el orden.
    """
    keeper = frame['player_positions'].fillna('').str.contains('GK')
    parts = [frame.loc[mask, [c for c in aspects if c in frame]].rank(pct=True)
             for aspects, mask in ((ASPECTS, ~keeper), (GK_ASPECTS, keeper))]
    return pd.concat(parts).reindex(frame.index)


def prepare(source: Path = DATA / 'raw', destination: Path = DATA, version: int | None = None):
    frames = {kind: pd.read_csv(source / f'male_{kind}.csv', low_memory=False)
              for kind in ('players', 'teams', 'coaches')}
    p, t, c = frames.values()
    for frame, id_col in [(p,'player_id'),(t,'team_id'),(c,'coach_id')]:
        if id_col not in frame or frame[id_col].isna().any():
            raise ValueError(f'ID obligatorio ausente: {id_col}')
    # Un snapshot común evita mezclar edades, clubes o versiones en los joins.
    keys = ['fifa_version', 'fifa_update', 'update_as_of']
    common = p[keys].drop_duplicates().merge(t[keys].drop_duplicates(), on=keys)
    if version is not None: common = common[common.fifa_version == version]
    if common.empty: raise ValueError('No hay snapshot común para jugadores y equipos.')
    snap = common.sort_values(keys).iloc[-1]
    selected = {}
    for kind, frame in [('players',p),('teams',t)]:
        mask = pd.Series(True, index=frame.index)
        for k in keys: mask &= frame[k] == snap[k]
        selected[kind] = frame[mask].copy()
    selected['coaches'] = c.copy()
    for kind, frame in selected.items():
        id_col = {'players':'player_id','teams':'team_id','coaches':'coach_id'}[kind]
        if frame[id_col].duplicated().any(): raise ValueError(f'IDs duplicados en {kind}')
    destination.mkdir(parents=True, exist_ok=True)
    for kind, frame in selected.items(): frame.to_csv(destination / f'male_{kind}.csv', index=False)
    info = {'source_kind':'user CSV / FIFA-EA FC videogame / SoFIFA links',
      'snapshot': {'fifa_version':int(snap.fifa_version),'fifa_update':int(snap.fifa_update),
                   'update_as_of':str(snap.update_as_of)},
      'counts':{k:len(v) for k,v in selected.items()}, 'original_counts':{k:len(v) for k,v in frames.items()},
      'files':{f'male_{k}.csv': hashlib.sha256((source/f'male_{k}.csv').read_bytes()).hexdigest() for k in frames},
      'note':'Coaches CSV sin fecha de actualización. Asociación según coach_id del snapshot de equipos; no prueba situación actual.'}
    (destination/'manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    return info


def build_records(data_dir: Path = DATA):
    info = json.loads((data_dir/'manifest.json').read_text(encoding='utf-8'))
    snapshot = info['snapshot']
    frames = {kind:pd.read_csv(data_dir/f'male_{kind}.csv',low_memory=False) for kind in ('players','teams','coaches')}
    teams = {int(r['team_id']):clean(r) for r in frames['teams'].to_dict('records')}
    records = []
    def add(kind, entity_id, name, club, profile, metadata, source, detail=''):
        # profile se vectoriza; detail sólo se agrega al documento que lee el LLM.
        # Así los valores numéricos exactos quedan disponibles para el reporte sin
        # contaminar el embedding, que no sabe comparar magnitudes.
        m = clean(metadata) | snapshot | {'entity_type':kind,'entity_id':str(entity_id),'name':name,
             'club':club,'gender':'male','source_kind':info['source_kind'],'aspect':'profile',
             'source_refs_json':json.dumps([{'url':source}],ensure_ascii=False) if source else '[]'}
        identity = f"{kind}:{entity_id}:{snapshot['fifa_version']}:{snapshot['fifa_update']}:{snapshot['update_as_of']}"
        records.append({'id':hashlib.sha256(identity.encode()).hexdigest(), 'embedding_text':profile,
          'document':f"{kind}: {name} | Equipo: {club} | FIFA/EA FC {snapshot['fifa_version']}, {snapshot['update_as_of']}. "
            + profile + detail + ' Valoraciones y economía del videojuego, no estadísticas reales de partidos ni finanzas auditadas.', 'metadata':m})
    def source_url(value):
        if not isinstance(value,str): return ''
        return 'https://sofifa.com'+value if value.startswith('/') else value
    def tactics(row):
        return '. '.join(f'{label}: {TRANSLATE.get(str(row[k]),str(row[k]))}' for k,label in TACTICS.items() if k in row)
    ranks = rank_table(frames['players'])
    for index, raw in zip(frames['players'].index, frames['players'].to_dict('records')):
        r=clean(raw); positions=[x.strip() for x in r['player_positions'].split(',')]
        keeper = 'GK' in positions
        aspects = GK_ASPECTS if keeper else ASPECTS
        percentiles = {k: float(ranks.at[index, k]) for k in aspects
                       if k in ranks and pd.notna(ranks.at[index, k])}
        # El perfil se redacta con vocabulario, no con cifras: «Regate 41/100» y
        # «Regate 92/100» son casi el mismo vector para MiniLM, y esa plantilla
        # idéntica para 18.000 jugadores era la causa de que la búsqueda devolviera
        # siempre los mismos perfiles cortos.
        profile=', '.join(POSITION.get(x,x) for x in positions)+'. '
        profile+=describe(sorted(((p,k) for k,p in percentiles.items()), reverse=True), aspects)
        if r.get('preferred_foot') in FOOT: profile+=f"Perfil: {FOOT[r['preferred_foot']]}. "
        fields = [k for k in ATTRIBUTES if k.startswith('goalkeeping_') == keeper]
        detail=' Valoraciones del juego: '+', '.join(f'{ATTRIBUTES[k]} {r[k]:g}/100' for k in fields if k in r)+'.'
        for k,label in [('skill_moves','Filigranas (1 a 5)'),('work_rate','Trabajo ataque/defensa'),('player_traits','Rasgos')]:
            if k in r: detail+=f' {label}: {r[k]}.'
        team=teams.get(int(r.get('club_team_id',-1)),{})
        m={k:v for k,v in r.items() if k in set(ATTRIBUTES)|{'age','overall','potential','value_eur','wage_eur','skill_moves','weak_foot','nationality_name','player_positions','club_team_id','preferred_foot'}}
        m.update(position=positions[0],is_goalkeeper=keeper,league=r.get('league_name','Sin liga'),
                 team_joined=bool(team))
        # Los percentiles viajan en metadata para que el reordenamiento compare
        # atributos de escalas distintas sin recalcular nada en cada consulta.
        m.update({RANK_PREFIX+k: round(p*100, 1) for k, p in percentiles.items()})
        for pos in POSITION: m['plays_'+pos] = pos in positions
        add('player',int(r['player_id']),r.get('long_name',r['short_name']),r.get('club_name','Sin club'),profile,m,source_url(r.get('player_url')),detail)
    for r in teams.values():
        m={k:v for k,v in r.items() if k in set(TACTICS)|{'overall','attack','midfield','defence','transfer_budget_eur','club_worth_eur','coach_id','nationality_name'}}
        m['league']=r.get('league_name','Sin liga')
        profile='Equipo. '+tactics(r)
        for k,label in [('attack','Ataque'),('midfield','Mediocampo'),('defence','Defensa')]:
            if k in r: profile+=f'. {label} {r[k]}/100'
        for k,label in [('transfer_budget_eur','Presupuesto de transferencias'),('club_worth_eur','Valor del club')]:
            if k in r: profile+=f'. {label} en el videojuego: EUR {r[k]:g}'
        add('club',int(r['team_id']),r['team_name'],r['team_name'],profile,m,source_url(r.get('team_url')))
    for raw in frames['coaches'].to_dict('records'):
        r=clean(raw); linked=[t for t in teams.values() if t.get('coach_id')==r['coach_id']]
        # Una ficha por técnico, preservando todas sus asociaciones en metadata.
        profile='Técnico entrenador. '
        profile += ' | '.join(tactics(t) for t in linked) if linked else 'Sin equipo asociado en el snapshot seleccionado; no hay perfil táctico documentado.'
        profile += ' Táctica del equipo en el videojuego; no evaluación causal ni estilo personal verificado del técnico.'
        clubs=', '.join(t['team_name'] for t in linked) or 'Sin equipo asociado'
        add('coach',int(r['coach_id']),r.get('long_name',r['short_name']),clubs,profile,
            {'nationality_name':r.get('nationality_name','Sin dato'),'league':' / '.join(sorted({t.get('league_name','Sin liga') for t in linked})) or 'Sin liga',
             'has_team':bool(linked),'team_ids_json':json.dumps([int(t['team_id']) for t in linked]),
             'coach_snapshot_known':False},source_url(r.get('coach_url')))
        refs=json.loads(records[-1]['metadata']['source_refs_json'])
        refs.extend({'url':source_url(t.get('team_url')),'date':snapshot['update_as_of']} for t in linked if t.get('team_url'))
        records[-1]['metadata']['source_refs_json']=json.dumps(refs,ensure_ascii=False)
    return records


def open_store(rebuild=False, db_path=None):
    # Importación diferida: preparar CSV no carga el modelo de embeddings.
    from fifa_corpus import CorpusBenchmark, fingerprint
    from vector_store import PlayerVectorStore
    records=build_records()
    info=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    s=info['snapshot']
    # La versión del perfil forma parte del nombre: al cambiar la redacción que se
    # vectoriza se indexa una colección nueva en vez de fallar contra la anterior.
    collection=f"football_supplied_v{s['fifa_version']}_u{s['fifa_update']}_{PROFILE_VERSION.replace('-','_')}"
    store=PlayerVectorStore(collection_name=collection,**({'persist_path':db_path} if db_path else {}))
    store.initialize_records([r['id'] for r in records],[r['document'] for r in records],
        [r['metadata'] for r in records],fingerprint(records),PROFILE_VERSION,rebuild=rebuild,
        embedding_texts=[r['embedding_text'] for r in records])
    return store,records,CorpusBenchmark(store,records)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=DATA/'raw')
    parser.add_argument('--version',type=int)
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,version=args.version),ensure_ascii=False,indent=2))
