"""ETL reproducible de fuentes FIFA oficiales, Mundial de Clubes masculino 2025.

Ejecutar: python fifa_ingest.py [--download]. No genera valoraciones de videojuego.
Extrae celdas por coordenadas para conservar los ceros grises de las tablas FIFA.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import logging
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote, urljoin
from urllib.request import urlopen

import pandas as pd
import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent / "data" / "fifa"
RAW = ROOT / "raw"
HUB = "https://www.fifatrainingcentre.com/en/game/tournaments/fcwc/2025/post-match-summary-reports.php"
SQUADS = "https://fdp.fifa.org/assetspublic/ce233/pdf/SquadLists-English.pdf"
ECONOMY = "https://inside.fifa.com/organisation/news/club-world-cup-2025-record-prize-money-unprecedented-solidarity-benefit-club-football?entryId=Qqle9UafPSuWrUUj9isYF&requester=MediaHub"
logging.getLogger("pdfminer").setLevel(logging.ERROR)
DISTRIBUTION = ["passes_attempted", "passes_completed", "pass_completion_pct", "switches",
                "crosses_attempted", "crosses_completed", "line_breaks_attempted", "line_breaks_completed",
                "line_break_completion_pct", "ball_progressions", "take_ons", "step_ins", "shots", "goals"]
DEFENCE = ["tackles_attempted", "tackles_won", "blocks", "interceptions", "direct_pressures",
           "indirect_pressures", "aerial_duels_won", "physical_duels_won", "possession_contests_won",
           "clearances", "loose_ball_receptions", "pushing_on", "pushing_on_pressing", "regains", "interruptions"]
PHYSICAL = ["distance_m", "zone1_m", "zone2_m", "zone3_m", "zone4_m", "zone5_m",
            "high_speed_runs", "sprints", "top_speed_kmh"]
PHASES = {"Build Up Unopposed": "build_up_unopposed_pct", "Build Up Opposed": "build_up_opposed_pct",
          "Progression": "progression_pct", "Final Third": "final_third_pct", "Long Ball": "long_ball_pct",
          "Attacking Transition": "attacking_transition_pct", "Counter Attack": "counter_attack_pct",
          "High Press": "high_press_pct", "Mid Press": "mid_press_pct", "Low Press": "low_press_pct",
          "High Block": "high_block_pct", "Mid Block": "mid_block_pct", "Low Block": "low_block_pct",
          "Counter-press": "counter_press_pct"}


def key(text: str) -> str:
    text = text.replace("\x00", "fi")
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower())


def fetch(url: str, path: Path) -> bytes:
    if path.exists():
        return path.read_bytes()
    url = quote(url, safe=":/?=&%")
    for attempt in range(3):
        try:
            data = urlopen(url, timeout=90).read()
            if path.suffix == ".pdf" and not data.startswith(b"%PDF"):
                raise ValueError(f"No es PDF: {url}")
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".part")
            tmp.write_bytes(data)
            tmp.replace(path)
            return data
        except Exception:
            if attempt == 2:
                raise


def download_sources() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    snapshot_path = ROOT / "sources.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else {}
    squad_bytes = fetch(SQUADS, RAW / "squads.pdf")
    if snapshot.get("squad_sha256") and hashlib.sha256(squad_bytes).hexdigest() != snapshot["squad_sha256"]:
        raise ValueError("FIFA cambió el PDF de planteles: no coincide con el snapshot incluido.")
    links = []
    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "a":
                for attr, value in attrs:
                    if attr == "href" and re.search(r"/M\d{2}\s", value):
                        links.append(urljoin(HUB, value))
    Links().feed(fetch(HUB, RAW / "match_hub.html").decode())
    links = list(dict.fromkeys(links))
    if len(links) != 63:
        raise ValueError(f"Se esperaban 63 reportes FIFA, se encontraron {len(links)}.")
    def download(url):
        match_id = int(re.search(r"/M(\d+)", url)[1])
        path = RAW / f"match_{match_id:02}.pdf"
        data = fetch(url, path)
        expected = next((r["sha256"] for r in snapshot.get("matches", []) if r["match_id"] == match_id), None)
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"El reporte M{match_id:02} no coincide con el snapshot incluido.")
        print(f"Fuente M{match_id:02}: {len(data)} bytes", flush=True)
        return {"match_id": match_id, "url": quote(url, safe=":/%"), "file": path.name,
                "sha256": hashlib.sha256(data).hexdigest()}
    with ThreadPoolExecutor(max_workers=3) as pool:
        manifest = sorted(pool.map(download, links), key=lambda r: r["match_id"])
    (RAW / "match_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def rows(page, tolerance=1.3):
    grouped = []
    for word in sorted(page.extract_words(x_tolerance=1, y_tolerance=1), key=lambda w: (w["top"], w["x0"])):
        if not grouped or abs(word["top"] - grouped[-1][0]) > tolerance:
            grouped.append((word["top"], [word]))
        else:
            grouped[-1][1].append(word)
    return [(y, sorted(words, key=lambda w: w["x0"])) for y, words in grouped]


def text_between(words, left, right):
    return " ".join(w["text"] for w in words if left <= w["x0"] < right).replace("\x00", "fi")


def parse_squads():
    players, clubs, coaches = [], [], []
    with pdfplumber.open(RAW / "squads.pdf") as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            words = page.extract_words(x_tolerance=1, y_tolerance=1)
            title = text_between([w for w in words if 34 < w["top"] < 40], 0, 500)
            match = re.fullmatch(r"(.+?)\s+\(([A-Z]{3})\)", title)
            if not match:
                raise ValueError(f"Encabezado de plantel no reconocido: {title}")
            club, country = match.groups()
            club_id = key(club)
            base = {"club_id": club_id, "club": club, "country_code": country,
                    "source_url": SQUADS, "source_page": page_number,
                    "snapshot_date": "2025-07-04", "competition": "FIFA Club World Cup 2025", "gender": "male"}
            clubs.append(base)
            for y, line in rows(page, tolerance=0.8):
                borders = sorted({r["x0"] for r in page.rects
                                  if r["top"] <= y <= r["bottom"] and r["x1"]-r["x0"] < 1})
                bounds = [0] + borders + [page.width]
                cells = [text_between(line, a, b) for a, b in zip(bounds, bounds[1:])]
                number = cells[0]
                if number.isdigit() and 48 < y < 240:
                    if len(cells) != 9:
                        raise ValueError(f"Colonnes plantilla {page_number}: {cells}")
                    pos = cells[1]
                    if pos not in {"GK", "DF", "MF", "FW"}:
                        continue
                    dob = cells[6]
                    birth = datetime.strptime(dob, "%d/%m/%Y").date()
                    age = 2025 - birth.year - ((6, 14) < (birth.month, birth.day))
                    height = cells[8]
                    players.append({**base, "entity_id": f"{club_id}:{number}", "shirt_number": int(number),
                                    "position": pos, "name": cells[2], "dob": birth.isoformat(),
                                    "age": age, "age_reference_date": "2025-06-14",
                                    "nationality": cells[7],
                                    "height_cm": int(height) if height.isdigit() else None})
                if cells[0] == "Head coach":
                    if len(cells) != 5: raise ValueError(f"Columnas técnico: {cells}")
                    coaches.append({**base, "entity_id": f"coach:{club_id}",
                                    "name": cells[1],
                                    "nationality": cells[4],
                                    "attribution": "Head coach en lista FIFA del 4 de julio; no verificación partido a partido"})
    if len(clubs) != 32 or len(coaches) != 32:
        raise ValueError(f"Planteles incompletos: {len(clubs)} clubes, {len(coaches)} técnicos.")
    return players, clubs, coaches


def resolve_club(name, clubs):
    lookup = {key(c["club"]): c for c in clubs}
    aliases = {"sep almeiras": "Palmeiras", "sepalmeiras": "Palmeiras", "slbenfica": "SL Benfica",
               "esperancedetunis": "Espérance De Tunisie", "esperance": "Espérance De Tunisie",
               "alhilal": "Al Hilal", "realmadridcf": "Real Madrid C. F."}
    normalized = key(name)
    normalized = key(aliases.get(normalized, name))
    if normalized not in lookup:
        raise ValueError(f"Club no reconocido: {name!r}")
    return lookup[normalized]


def numeric(text):
    # Fuente PDF usa glifos privados en las tablas físicas; comprobado visualmente.
    text = text.translate({**{0xE071+i: str(i) for i in range(10)}, 0xE094: "."})
    return float(text.rstrip("%"))


def parse_individual(page, fields, physical=False, defensive=False):
    result = []
    for y, words in rows(page):
        if y < (108 if physical else 115):
            continue
        number = text_between(words, 0, 40)
        if not number.isdigit():
            continue
        name_limit = 250 if physical else 190
        name = text_between(words, 40, name_limit)
        values = [w["text"] for w in words if w["x0"] >= name_limit]
        if defensive:
            values = [v for v in values if v != "/"]
        if len(values) != len(fields):
            raise ValueError(f"Fila incompleta página {page.page_number}, dorsal {number}: {values}")
        result.append({"shirt_number": int(number), "match_name": name,
                       **dict(zip(fields, map(numeric, values)))})
    if not 11 <= len(result) <= 18:
        raise ValueError(f"Cantidad de jugadores inesperada en página {page.page_number}: {len(result)}")
    return result


def parse_match(entry, clubs):
    path = RAW / entry["file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError(f"Checksum incorrecto: {path}")
    reader = PdfReader(path)
    cover = reader.pages[0].extract_text()
    match = re.search(r"REPORT\s*\n(.+?)(\d+)\s*-\s*(\d+)\s*\n(.+?)\n", cover)
    if not match:
        raise ValueError(f"Portada no reconocida: {path}")
    home, hg, ag, away = match.groups()
    home, away = resolve_club(home.strip(), clubs), resolve_club(away.strip(), clubs)
    match_date = re.search(r"\d{1,2} (?:June|July) 2025", cover)[0]
    match_date = datetime.strptime(match_date, "%d %B %Y").date().isoformat()
    match_id = entry["match_id"]
    teams = [{"match_id": match_id, "date": match_date, "club_id": c["club_id"], "club": c["club"],
              "opponent": other["club"], "goals": int(g), "goals_against": int(ga),
              "source_url": entry["url"], "source_page": 3, "phases_page": 4}
             for c, other, g, ga in [(home, away, hg, ag), (away, home, ag, hg)]]
    key_stats = reader.pages[2].extract_text()
    possession = re.search(r"Total\s+([\d.]+)%\s+[\d.]+%\s+([\d.]+)%\s+Total", key_stats)
    if possession:
        for team, value in zip(teams, possession.groups()): team["possession_pct"] = float(value)
    formation = re.findall(r"FORMATION\s+([\d-]+)", reader.pages[1].extract_text())
    if len(formation) == 2:
        for team, value in zip(teams, formation): team["formation"] = value
    phase_text = reader.pages[3].extract_text()
    for label, field in PHASES.items():
        found = re.search(r"(\d+)%\s+" + re.escape(label) + r"\s+(\d+)%", phase_text)
        if found:
            for team, value in zip(teams, found.groups()): team[field] = float(value)
    if any("high_press_pct" not in t for t in teams):
        raise ValueError(f"Fases tácticas faltantes: partido {match_id}")
    individual = {}
    with pdfplumber.open(path) as pdf:
        for index, raw_page in enumerate(reader.pages):
            text = raw_page.extract_text()
            mode = next((p for p in ["In Possession - Distributions", "Out of Possession", "Physical Data"]
                         if text.startswith(p + " ")), None)
            if not mode:
                continue
            team_name = text.splitlines()[0][len(mode):].strip()
            club = resolve_club(team_name, clubs)
            fields = DISTRIBUTION if mode.startswith("In Possession") else DEFENCE if mode == "Out of Possession" else PHYSICAL
            page = pdf.pages[index]
            for row in parse_individual(page, fields, fields == PHYSICAL, fields == DEFENCE):
                entity_id = f"{club['club_id']}:{row['shirt_number']}"
                combined = individual.setdefault(entity_id, {"entity_id": entity_id, "club_id": club["club_id"],
                    "club": club["club"], "match_id": match_id, "date": match_date, "source_url": entry["url"]})
                combined.update(row)
                combined[{"In Possession - Distributions": "distribution_page", "Out of Possession": "defence_page",
                          "Physical Data": "physical_page"}[mode]] = index + 1
            page.close()
    for row in individual.values():
        if not all(k in row for k in ("passes_attempted", "regains", "distance_m")):
            raise ValueError(f"Tablas no conciliadas: {match_id}, {row['entity_id']}")
        if row["passes_completed"] > row["passes_attempted"] or not 0 <= row["top_speed_kmh"] < 45:
            raise ValueError(f"Valores inválidos: {match_id}, {row['entity_id']}")
    for team in teams:
        club_rows = [r for r in individual.values() if r["club_id"] == team["club_id"]]
        for field in ["passes_attempted", "passes_completed", "line_breaks_completed", "direct_pressures", "shots", "distance_m"]:
            team[field] = sum(r[field] for r in club_rows)
        team["pass_completion_pct"] = 100 * team["passes_completed"] / max(team["passes_attempted"], 1)
    return list(individual.values()), teams


def build_dataset():
    roster, clubs, coaches = parse_squads()
    manifest = json.loads((RAW / "match_manifest.json").read_text())
    if sorted(m["match_id"] for m in manifest) != list(range(1, 64)):
        raise ValueError("Se requiere cobertura de los 63 partidos.")
    player_matches, team_matches = [], []
    for entry in manifest:
        cache = ROOT / "parsed" / f"match_{entry['match_id']:02}.json"
        if cache.exists():
            payload = json.loads(cache.read_text(encoding="utf-8"))
            if payload["sha256"] != entry["sha256"]:
                raise ValueError("Cache desactualizada; retirar parsed/ y reprocesar.")
            pm, tm = payload["players"], payload["teams"]
        else:
            pm, tm = parse_match(entry, clubs)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"sha256": entry["sha256"], "players": pm, "teams": tm}, ensure_ascii=False), encoding="utf-8")
        player_matches.extend(pm); team_matches.extend(tm)
        print(f"Extraído M{entry['match_id']:02}: {len(pm)} jugadores", flush=True)
    known = {r["entity_id"] for r in roster}
    for row in player_matches:
        if row["entity_id"] not in known:
            # No inventar edad/nacionalidad/posición de participantes fuera del snapshot.
            roster.append({k: row[k] for k in ("entity_id", "club_id", "club", "shirt_number", "source_url")}
                          | {"name": row["match_name"], "position": "unknown", "gender": "male",
                             "source_page": row["distribution_page"], "snapshot_date": row["date"]})
            known.add(row["entity_id"])
    for filename, records in [("players.csv", roster), ("clubs.csv", clubs), ("coaches.csv", coaches),
                               ("player_matches.csv", player_matches), ("team_matches.csv", team_matches)]:
        pd.DataFrame(records).to_csv(ROOT / filename, index=False, encoding="utf-8")
    sources = {"publisher": "FIFA", "competition": "FIFA Club World Cup 2025", "gender": "male",
               "retrieved_at": datetime.now(timezone.utc).isoformat(), "match_hub": HUB,
               "squad_source": SQUADS, "squad_sha256": hashlib.sha256((RAW / "squads.pdf").read_bytes()).hexdigest(),
               "squad_snapshot": "2025-07-04", "matches": manifest, "economic_source": ECONOMY,
               "counts": {"players": len(roster), "clubs": len(clubs), "coaches": len(coaches),
                          "matches": 63, "player_match_rows": len(player_matches)}}
    (ROOT / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(sources["counts"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download: download_sources()
    build_dataset()
