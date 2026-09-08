"""Corpus heterogéneo de evidencia FIFA; identidades fuera del embedding."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pandas as pd

from benchmark import SearchBenchmark, normalize_text
from data_loader import BASE_DIR
from vector_store import PlayerVectorStore

DATA = BASE_DIR / "data" / "fifa"
COLLECTION = "football_fifa_2025"
VERSION = "fifa-profile-noidentity-v1"
PRIZE_SOURCE = "https://inside.fifa.com/organisation/news/club-world-cup-2025-record-prize-money-unprecedented-solidarity-benefit-club-football?entryId=Qqle9UafPSuWrUUj9isYF&requester=MediaHub"
CHELSEA_TACTICS = "https://www.fifatrainingcentre.com/en/game/tournaments/fcwc/2025/team-analyses/chelsea-fc-the-inverted-full-back-and-central-overloads.php"
FINAL_TACTICS = "https://www.fifatrainingcentre.com/en/game/tournaments/fcwc/2025/team-analyses/formed-by-fluidity-understanding-psg-and-chelseas-tactical-approaches-with-roberto-martinez.php"
VITINHA_TACTICS = "https://www.fifatrainingcentre.com/en/game/tournaments/fcwc/2025/team-analyses/vitinha-paris-saint-germains-versatile-playmaker.php"
POSITION = {"GK": "Arquero portero; goalkeeper", "DF": "Defensor; defender", "MF": "Mediocampista volante; midfielder",
            "FW": "Delantero atacante; forward", "unknown": "Posición no disponible"}
CONFED = {"ENG": "UEFA", "ESP": "UEFA", "GER": "UEFA", "ITA": "UEFA", "POR": "UEFA", "AUT": "UEFA", "FRA": "UEFA",
          "ARG": "CONMEBOL", "BRA": "CONMEBOL", "MEX": "Concacaf", "USA": "Concacaf", "EGY": "CAF",
          "MAR": "CAF", "TUN": "CAF", "RSA": "CAF", "UAE": "AFC", "KSA": "AFC", "KOR": "AFC", "JPN": "AFC", "NZL": "OFC"}


def scalar_dict(row):
    return {k: v for k, v in row.items() if pd.notna(v) and isinstance(v, (str, int, float, bool))}


def fingerprint(records):
    return hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build_corpus(data_dir: Path = DATA):
    roster = pd.read_csv(data_dir / "players.csv").to_dict("records")
    clubs = pd.read_csv(data_dir / "clubs.csv").to_dict("records")
    coaches = pd.read_csv(data_dir / "coaches.csv").to_dict("records")
    pm = pd.read_csv(data_dir / "player_matches.csv")
    tm = pd.read_csv(data_dir / "team_matches.csv")
    records, aggregates, club_aggregates = [], [], []

    def add(meta, aspect, profile, refs, metrics=None):
        metadata = scalar_dict(meta) | {"aspect": aspect, "gender": "male", "season": 2025,
                    "competition": "FIFA Club World Cup 2025", "source_kind": "FIFA official / derived",
                    "source_refs_json": json.dumps(refs, ensure_ascii=False)} | (metrics or {})
        document = (f"{metadata['entity_type']}: {metadata['name']} | Club: {metadata['club']} | "
                    f"Mundial de Clubes masculino 2025. {profile}\n"
                    "Alcance: este torneo, no habilidad permanente ni información actual de contratos.")
        vector_id = hashlib.sha256(f"{metadata['entity_type']}:{metadata['entity_id']}:{aspect}".encode()).hexdigest()
        records.append({"id": vector_id, "document": document, "embedding_text": profile,
                        "metadata": metadata})

    for player in roster:
        m = scalar_dict(player) | {"entity_type": "player"}
        group = pm[pm.entity_id == player["entity_id"]]
        n = len(group)
        m["appearances"] = n
        m["has_stats"] = bool(n)
        refs = [{"url": player["source_url"], "page": int(player["source_page"])}]
        prefix = POSITION.get(player.get("position"), POSITION["unknown"]) + ". "
        if not n:
            add(m, "roster", prefix + "Registrado en plantel. Sin estadísticas de participación en los reportes procesados; no se evalúa desempeño.", refs)
            continue
        totals = group.select_dtypes("number").sum()
        def avg(field): return float(totals[field] / n)
        completion = 100 * totals.passes_completed / max(totals.passes_attempted, 1)
        stats = {"appearances": n, "passes_completed": int(totals.passes_completed),
                 "pass_completion_pct": round(completion, 3), "line_breaks_completed": int(totals.line_breaks_completed),
                 "goals": int(totals.goals), "shots": int(totals.shots), "direct_pressures": int(totals.direct_pressures),
                 "regains": int(totals.regains), "distance_m": round(float(totals.distance_m), 1),
                 "top_speed_kmh": float(group.top_speed_kmh.max()), "sprints": int(totals.sprints)}
        aggregates.append({**scalar_dict(player), **stats})
        m.update(stats)
        def evidence(page_key):
            return refs + [{"url": r.source_url, "page": int(getattr(r, page_key)), "match_id": int(r.match_id)}
                           for r in group.itertuples()]
        technique = (prefix + f"Técnica de pase y progresión; passing, ball progression. {n} participaciones. "
                     f"Por aparición: {avg('passes_completed'):.1f} pases completos, precisión global {completion:.1f}%, "
                     f"{avg('line_breaks_completed'):.1f} rupturas de líneas completas, {avg('switches'):.1f} cambios de orientación, "
                     f"{avg('take_ons'):.1f} regates y {avg('crosses_completed'):.1f} centros completos. "
                     f"Finalización: {int(totals.goals)} goles y {int(totals.shots)} tiros acumulados. "
                     "Medias por aparición, no por 90 minutos; no predicen potencial.")
        defensive = (prefix + f"Recuperación, marca y presión; defending, pressing. {n} participaciones. "
                     f"Por aparición: {avg('direct_pressures'):.1f} presiones directas, {avg('interceptions'):.1f} intercepciones, "
                     f"{avg('tackles_won'):.1f} entradas ganadas, {avg('regains'):.1f} recuperaciones, "
                     f"{avg('aerial_duels_won'):.1f} duelos aéreos ganados y {avg('clearances'):.1f} despejes. "
                     "Acciones observadas, no valoración general; exposición desigual por minutos.")
        physical = (prefix + f"Despliegue físico, velocidad y sprints; physical running speed. {n} participaciones. "
                    f"Media por aparición: {avg('distance_m')/1000:.2f} km recorridos, {avg('zone4_m'):.1f} m a 20-25 km/h, "
                    f"{avg('zone5_m'):.1f} m por encima de 25 km/h y {avg('sprints'):.1f} sprints. "
                    f"Velocidad máxima observada {stats['top_speed_kmh']:.1f} km/h. "
                    "No ajustado por minutos ni por tiempo efectivo de juego.")
        add(m, "technique", technique, evidence("distribution_page"))
        add(m, "defence", defensive, evidence("defence_page"))
        add(m, "physical", physical, evidence("physical_page"))

    coach_by_club = {c["club_id"]: c for c in coaches}
    for club in clubs:
        group = tm[tm.club_id == club["club_id"]]
        n = len(group)
        if n < 3: raise ValueError(f"Cobertura insuficiente para {club['club']}")
        region = CONFED[club["country_code"]]
        low, high = (12.81, 38.19) if region == "UEFA" else (15.21, 15.21) if region == "CONMEBOL" else (3.58, 3.58) if region == "OFC" else (9.55, 9.55)
        means = group.select_dtypes("number").mean()
        stats = {"matches": n, "goals": int(group.goals.sum()), "goals_against": int(group.goals_against.sum()),
                 "possession_pct": round(float(means.possession_pct), 3),
                 "high_press_pct": round(float(means.high_press_pct), 3),
                 "counter_press_pct": round(float(means.counter_press_pct), 3),
                 "pass_completion_pct": round(100 * group.passes_completed.sum() / group.passes_attempted.sum(), 3),
                 "participation_min_usd": int(low * 1e6), "participation_max_usd": int(high * 1e6)}
        m = scalar_dict(club) | {"entity_id": club["club_id"], "entity_type": "club", "name": club["club"],
                              "confederation": region, "has_stats": True} | stats
        club_aggregates.append(m)
        formation = ", ".join(sorted(set(group.formation.dropna())))
        profile = (f"Equipo: modelo de juego y organización táctica; team tactics. {n} partidos. "
                   f"Formaciones iniciales observadas {formation}. Posesión media {stats['possession_pct']:.1f}%; "
                   f"precisión de pase {stats['pass_completion_pct']:.1f}%. "
                   f"Fases sin balón: presión alta {means.high_press_pct:.1f}%, contrapresión {means.counter_press_pct:.1f}%, "
                   f"bloque bajo {means.low_block_pct:.1f}%. "
                   f"Ataque: transiciones {means.attacking_transition_pct:.1f}%, balón largo {means.long_ball_pct:.1f}%. "
                   f"{stats['goals']} goles a favor, {stats['goals_against']} en contra. "
                   "Promedios simples de porcentajes FIFA por partido; incluyen sus denominadores originales.")
        refs = [{"url": r.source_url, "page": 4, "match_id": int(r.match_id)} for r in group.itertuples()]
        refs += [{"url": r.source_url, "page": 3, "match_id": int(r.match_id)} for r in group.itertuples()]
        add(m, "tactics", profile, refs)
        economics = (f"Contexto económico de participación FIFA 2025, confederación {region}. "
                     f"Pilar de participación oficial: entre USD {low:.2f} y {high:.2f} millones. "
                     "Rango reglamentario, no cobro auditado. No equivale a ingresos anuales, presupuesto de fichajes, "
                     "salarios, deuda ni valor de plantilla. Esas variables no están disponibles en este corpus.")
        add(m, "economics", economics, [{"url": PRIZE_SOURCE, "date": "2025-03-26"}])
        coach = scalar_dict(coach_by_club[club["club_id"]]) | {"entity_type": "coach", "has_stats": True} | stats
        add(coach, "tactics", "Técnico; coach. Perfil del equipo asociado, sin atribución causal al entrenador. " + profile,
            [{"url": coach["source_url"], "page": int(coach["source_page"]), "date": "2025-07-04"}] + refs)

    # Breves paráfrasis editoriales verificadas, separadas de los atributos derivados.
    curated = [
        ("chelseafc:3", "Lateral invertido que avanza por dentro para generar superioridad central; al cambiar el mediocampo pasa a integrar el doble pivote.", CHELSEA_TACTICS, "2025-06-18"),
        ("chelseafc:8", "Interior que llega desde segunda línea al área, ocupando espacios centrales de ataque y aportando amenaza de gol.", CHELSEA_TACTICS, "2025-06-18"),
        ("chelseafc:25", "Mediocentro que cubre el espacio abandonado por el lateral adelantado y sostiene la contrapresión en transiciones defensivas.", CHELSEA_TACTICS, "2025-06-18"),
        ("parissaintgermain:2", "Lateral con desmarques profundos que puede convertirse en el atacante más avanzado gracias a rotaciones coordinadas.", FINAL_TACTICS, "2025-07-12"),
        ("chelseafc:27", "Lateral que se desplaza al centro para actuar como organizador durante la salida y la progresión del balón.", FINAL_TACTICS, "2025-07-12"),
        ("parissaintgermain:17", "Mediocampista organizador versátil que se ofrece para recibir, conecta pases y contribuye a la progresión del juego.", VITINHA_TACTICS, "2025-06-27"),
    ]
    indexed_players = {r["metadata"]["entity_id"]: r["metadata"] for r in records if r["metadata"]["entity_type"] == "player"}
    for entity_id, profile, source, published in curated:
        if entity_id not in indexed_players: raise ValueError(f"Análisis sin jugador: {entity_id}")
        add(indexed_players[entity_id], "editorial_tactics", "Síntesis del análisis técnico FIFA: " + profile,
            [{"url": source, "date": published}])
    pd.DataFrame(aggregates).to_csv(data_dir / "player_aggregates.csv", index=False)
    pd.DataFrame(club_aggregates).to_csv(data_dir / "club_aggregates.csv", index=False)
    (data_dir / "corpus.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    return records


def load_corpus():
    return [json.loads(line) for line in (DATA / "corpus.jsonl").read_text(encoding="utf-8").splitlines() if line]


class CorpusBenchmark(SearchBenchmark):
    def __init__(self, store, records):
        self.store = store
        self.fingerprint = fingerprint(records)
        self.ids = [r["id"] for r in records]
        self.documents = [r["document"] for r in records]
        self.metadatas = [r["metadata"] for r in records]
        self.frame = pd.DataFrame(self.metadatas)
        self.normalized_documents = pd.Series([normalize_text(r["embedding_text"]) for r in records])


def open_fifa_store(rebuild=False, db_path=None):
    records = load_corpus()
    store = PlayerVectorStore(collection_name=COLLECTION, **({"persist_path": db_path} if db_path else {}))
    store.initialize_records([r["id"] for r in records], [r["document"] for r in records],
                             [r["metadata"] for r in records], fingerprint(records), VERSION,
                             rebuild=rebuild, embedding_texts=[r["embedding_text"] for r in records])
    return store, records, CorpusBenchmark(store, records)


if __name__ == "__main__":
    records = build_corpus()
    print(f"Corpus: {len(records)} fragmentos verificables.")
    open_fifa_store()
