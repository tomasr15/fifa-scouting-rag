"""Carga y validación del CSV. El conjunto de demostración es sintético."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
COLUMNS = ["name", "age", "club", "league", "nationality", "position",
           "overall_rating", "pace", "shooting", "passing", "dribbling",
           "defending", "physical", "scouting_report"]
NUMERIC = ["age", "overall_rating", "pace", "shooting", "passing", "dribbling",
           "defending", "physical"]

# Valores ilustrativos y clubes de referencia; no representan datos actuales de EA.
MOCK_ROWS = [
    ("Lionel Messi", 37, "Inter Miami", "MLS", "Argentina", "ED", 90, 78, 89, 91, 94, 33, 64, "Extremo creativo zurdo que se mueve como enganche entre líneas. Pase filtrado, regate corto y definición; necesita libertad y cobertura defensiva."),
    ("Rodrigo De Paul", 30, "Atlético de Madrid", "La Liga", "Argentina", "MC", 84, 75, 77, 85, 82, 77, 82, "Volante mixto con despliegue físico, presión y buen pase largo. Une recuperación y ataque por el sector derecho, sostiene intensidad y ayuda al lateral."),
    ("Erling Haaland", 24, "Manchester City", "Premier League", "Noruega", "DC", 91, 89, 93, 66, 80, 45, 88, "Delantero centro potente y goleador de área. Ataca espacios con velocidad, domina duelos físicos y finaliza centros; participa menos en la creación."),
    ("Federico Valverde", 26, "Real Madrid", "La Liga", "Uruguay", "MC", 88, 88, 82, 86, 83, 80, 87, "Volante mixto de enorme despliegue físico y buen pase largo para competir como titular en Europa. Recorre ambas áreas, presiona, cubre bandas y remata desde lejos."),
    ("Jude Bellingham", 21, "Real Madrid", "La Liga", "Inglaterra", "MC", 90, 80, 87, 83, 88, 78, 83, "Interior con llegada al área y conducción vertical. Combina potencia, presión y regate entre líneas; aporta goles desde segunda línea y liderazgo ofensivo."),
    ("Enzo Fernández", 23, "Chelsea", "Premier League", "Argentina", "MC", 83, 69, 73, 87, 81, 76, 78, "Mediocampista organizador con buen pase largo y cambios de orientación. Da salida bajo presión y regula el ritmo; requiere apoyo para cubrir grandes espacios."),
    ("Rodri", 28, "Manchester City", "Premier League", "España", "MCD", 91, 66, 80, 86, 84, 87, 85, "Pivote posicional que equilibra al equipo. Anticipa, recupera y ofrece pase seguro y largo; excelente lectura táctica, menor velocidad en carreras extensas."),
    ("Kevin De Bruyne", 33, "Manchester City", "Premier League", "Bélgica", "MCO", 90, 67, 87, 94, 87, 65, 78, "Mediapunta especialista en pase largo, centros tensos y asistencias. Crea ocasiones desde el carril interior y remata de media distancia; demanda cobertura."),
    ("Nicolò Barella", 27, "Inter", "Serie A", "Italia", "MC", 87, 81, 80, 83, 86, 78, 80, "Volante mixto intenso con presión sostenida, despliegue físico y pase vertical. Se asocia en corto, rompe líneas sin pelota y colabora en recuperación."),
    ("Declan Rice", 25, "Arsenal", "Premier League", "Inglaterra", "MCD", 87, 73, 65, 80, 77, 85, 85, "Mediocentro defensivo fuerte que recupera y protege transiciones. Puede avanzar como interior y distribuir en largo; sobresale en duelos y coberturas."),
    ("Alexis Mac Allister", 25, "Liverpool", "Premier League", "Argentina", "MC", 86, 70, 79, 86, 84, 78, 76, "Interior asociativo con visión, pase largo y lectura de espacios. Ordena la circulación, presiona con criterio y llega al área sin depender de la velocidad."),
    ("Pedri", 22, "Barcelona", "La Liga", "España", "MC", 86, 77, 68, 88, 89, 66, 61, "Interior técnico que recibe entre líneas, gira bajo presión y filtra pases. Ideal para posesión y asociaciones cortas; menor capacidad de choque físico."),
    ("Florian Wirtz", 21, "Bayer Leverkusen", "Bundesliga", "Alemania", "MCO", 88, 81, 78, 87, 89, 50, 67, "Enganche joven creativo con último pase y regate en espacios reducidos. Conduce transiciones y conecta con el delantero; no es un recuperador posicional."),
    ("Jamal Musiala", 21, "Bayern Múnich", "Bundesliga", "Alemania", "MCO", 87, 84, 81, 78, 92, 63, 64, "Mediapunta joven de regate desequilibrante que rompe líneas conduciendo. Ataca el área desde el centro y combina paredes; su fuerte no es el duelo aéreo."),
    ("Kylian Mbappé", 26, "Real Madrid", "La Liga", "Francia", "DC", 91, 97, 90, 80, 92, 36, 78, "Atacante veloz de desmarques profundos y definición. Parte desde la izquierda o como punta, desequilibra al espacio y castiga defensas adelantadas."),
    ("Vinícius Júnior", 24, "Real Madrid", "La Liga", "Brasil", "EI", 90, 95, 84, 81, 91, 29, 69, "Extremo izquierdo explosivo para el uno contra uno. Desborda, acelera transiciones y asiste desde línea de fondo; necesita espacios para correr."),
    ("Lamine Yamal", 17, "Barcelona", "La Liga", "España", "ED", 81, 82, 73, 78, 86, 23, 48, "Extremo derecho joven y zurdo con creatividad, regate y pase interior. Abre defensas cerradas, aunque debe desarrollar fuerza para duelos físicos."),
    ("Mohamed Salah", 32, "Liverpool", "Premier League", "Egipto", "ED", 89, 89, 88, 82, 88, 45, 75, "Extremo derecho goleador que ataca diagonales y define con zurda. Amenaza a la espalda, combina velocidad y desmarque y aporta gol desde banda."),
    ("Lautaro Martínez", 27, "Inter", "Serie A", "Argentina", "DC", 89, 82, 88, 75, 87, 54, 85, "Delantero de presión intensa, movilidad y definición. Se asocia con otro punta, protege la pelota y ocupa el área; aporta trabajo defensivo adelantado."),
    ("Julián Álvarez", 24, "Atlético de Madrid", "La Liga", "Argentina", "DC", 84, 85, 85, 78, 83, 57, 75, "Delantero versátil con presión alta, movilidad y asociación. Puede ser segundo punta, atacar espacios y asistir; combina sacrificio y definición."),
    ("Virgil van Dijk", 33, "Liverpool", "Premier League", "Países Bajos", "DFC", 89, 78, 60, 71, 71, 89, 86, "Defensor central dominante por arriba, fuerte y sereno. Ordena la línea, anticipa y lanza pases largos; ideal para controlar duelos de área."),
    ("Cristian Romero", 26, "Tottenham", "Premier League", "Argentina", "DFC", 84, 73, 46, 59, 65, 85, 83, "Central agresivo de anticipación, marca y duelos físicos. Salta a presionar y defiende hacia adelante; necesita coordinación para cubrir su espalda."),
    ("William Saliba", 23, "Arsenal", "Premier League", "Francia", "DFC", 87, 82, 39, 67, 70, 87, 83, "Central joven rápido para sostener una línea alta. Corrige al espacio, gana duelos y sale con calma; aporta seguridad defensiva y cobertura."),
    ("Alessandro Bastoni", 25, "Inter", "Serie A", "Italia", "DFC", 87, 74, 44, 74, 73, 87, 83, "Central zurdo con salida limpia y pase progresivo. Conduce para superar la primera presión y centra desde atrás; cómodo en defensa de tres."),
    ("Achraf Hakimi", 26, "Paris Saint-Germain", "Ligue 1", "Marruecos", "LD", 84, 91, 76, 80, 80, 75, 76, "Lateral derecho ofensivo con velocidad y recorrido. Ofrece profundidad, centros y llegada al área; requiere cobertura cuando se incorpora al ataque."),
    ("Alphonso Davies", 24, "Bayern Múnich", "Bundesliga", "Canadá", "LI", 82, 95, 66, 77, 84, 72, 76, "Lateral izquierdo muy rápido de conducción y desborde. Recupera terreno en transición y da amplitud; debe mejorar posicionamiento en defensa cerrada."),
    ("Emiliano Martínez", 32, "Aston Villa", "Premier League", "Argentina", "POR", 87, 45, 20, 55, 40, 30, 80, "Arquero de reflejos, dominio del área y gran respuesta en mano a mano. Ordena la defensa y destaca en penales; estadísticas de campo poco representativas."),
    ("Thibaut Courtois", 32, "Real Madrid", "La Liga", "Bélgica", "POR", 89, 40, 18, 52, 38, 28, 79, "Arquero alto de gran alcance y seguridad aérea. Especialista en atajadas dentro del área y mano a mano; se necesitan métricas específicas de portería."),
    ("Alan Varela", 23, "Porto", "Primeira Liga", "Argentina", "MCD", 78, 65, 50, 75, 72, 77, 76, "Pivote joven ordenado con recuperación y primer pase simple. Protege a los centrales y ofrece apoyo en salida; prospecto para desarrollar distribución larga."),
    ("Franco Mastantuono", 17, "River Plate", "Liga Argentina", "Argentina", "MCO", 73, 76, 70, 74, 78, 40, 57, "Mediapunta zurdo joven de creatividad, pelota parada y conducción. Busca pases filtrados y remate desde fuera; necesita desarrollo físico y experiencia."),
]


def generate_mock_csv(path: str | Path = BASE_DIR / "players_mock.csv") -> Path:
    """Genera siempre las mismas 30 filas, sin aleatoriedad ni llamadas externas."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(MOCK_ROWS, columns=COLUMNS).to_csv(path, index=False, encoding="utf-8")
    return path


def load_players(csv_path: str | Path | None = None) -> tuple[pd.DataFrame, Path]:
    """Un archivo explícito inválido falla; el fallback sólo aplica al modo automático."""
    path = Path(csv_path) if csv_path is not None else BASE_DIR / "players.csv"
    if csv_path is None and not path.exists():
        path = BASE_DIR / "players_mock.csv"
        if not path.exists():
            generate_mock_csv(path)
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas: {', '.join(sorted(missing))}")
    df = df[COLUMNS].copy()
    if df.empty or df.isna().any().any():
        raise ValueError("El CSV está vacío o contiene valores faltantes.")
    for col in NUMERIC:
        values = pd.to_numeric(df[col], errors="raise")
        low, high = (15, 60) if col == "age" else (0, 99)
        if not (values.between(low, high) & values.mod(1).eq(0)).all():
            raise ValueError(f"{col} debe contener enteros entre {low} y {high}.")
        df[col] = values.astype(int)
    for col in set(COLUMNS) - set(NUMERIC):
        df[col] = df[col].astype(str).str.strip()
        if df[col].eq("").any():
            raise ValueError(f"Texto vacío en {col}.")
    df["position"] = df["position"].str.upper()
    if df.duplicated(subset=["name", "club"]).any():
        raise ValueError("Hay jugadores duplicados (mismo nombre y club).")
    return df, path.resolve()


def build_document(row: dict) -> str:
    return (
        f"Jugador: {row['name']} | Posición: {row['position']} | Edad: {row['age']} | "
        f"Club: {row['club']} ({row['league']}) | Nacionalidad: {row['nationality']} | "
        f"Valoración general: {row['overall_rating']}. Estadísticas: Ritmo {row['pace']}, "
        f"Tiro {row['shooting']}, Pase {row['passing']}, Regate {row['dribbling']}, "
        f"Defensa {row['defending']}, Físico {row['physical']}. "
        f"Perfil táctico: {row['scouting_report']}"
    )


def prepare_records(df: pd.DataFrame) -> tuple[list, list, list]:
    ids, documents, metadatas = [], [], []
    for row in df.to_dict(orient="records"):
        identity = json.dumps([row['name'], row['club']], ensure_ascii=False)
        ids.append(hashlib.sha256(identity.encode("utf-8")).hexdigest())
        documents.append(build_document(row))
        metadatas.append({k: v for k, v in row.items() if k != "scouting_report"})
    return ids, documents, metadatas


def dataset_fingerprint(df: pd.DataFrame) -> str:
    # Ordenar hace que reordenar el CSV no requiera reconstruir el índice.
    canonical = df.sort_values(["name", "club"]).to_json(orient="records", force_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
