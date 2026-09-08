"""Léxico de atributos y reordenamiento estructurado del pool recuperado.

Un embedding no compara magnitudes. MiniLM ubica «Regate 92/100» y «Regate 41/100»
prácticamente en el mismo punto: el texto sólo se diferencia en un número, que el
modelo tokeniza sin noción de orden. Por eso la recuperación densa sobre fichas
plantilladas devuelve jugadores de la posición pedida en un orden arbitrario y
tiende a repetir los mismos perfiles cortos.

Este módulo cubre las dos mitades del arreglo:

1. ASPECTS describe cada atributo con el vocabulario que lo evoca en una consulta,
   el vocabulario con que se redacta el perfil y la palabra de carencia. El texto
   que se vectoriza se redacta con ese vocabulario en vez de con números, para que
   dos jugadores distintos produzcan vectores distintos.
2. rerank ordena el pool recuperado por los atributos que la consulta menciona,
   usando los percentiles guardados en metadata. No inventa datos: sólo reordena
   candidatos que ya pasaron el filtro exacto y la búsqueda vectorial.
"""
from __future__ import annotations

import re
import unicodedata

# clave -> (disparadores en la consulta, vocabulario del perfil, palabra de carencia)
ASPECTS: dict[str, tuple[str, str, str]] = {
    "pace": (
        "rapido rapida veloz velocidad ritmo rapidez pique pace speed fast",
        "ritmo, velocidad, rapidez, pace, speed", "lento"),
    "movement_sprint_speed": (
        "sprint sprints arrancada punta explosivo explosiva aceleracion acceleration",
        "velocidad punta, sprint, arrancada, sprint speed", "sin arrancada"),
    "dribbling": (
        "regate regateador gambeta gambetear desborde desequilibrio desequilibrante "
        "encarar habilidoso conduccion dribbling dribbler",
        "regate, gambeta, desborde, uno contra uno, conduccion, dribbling", "sin desborde"),
    "shooting": (
        "tiro remate remates disparo pegada zurdazo derechazo distancia shooting",
        "tiro, remate, disparo, pegada, shooting", "sin remate"),
    "attacking_finishing": (
        "definicion definidor gol goles goleador goleadora finalizacion finishing killer",
        "definicion, gol, goleador, finishing", "sin definicion"),
    "passing": (
        "pase pases pasador distribucion circulacion toque passing",
        "pase, distribucion, circulacion, passing", "pase impreciso"),
    "skill_long_passing": (
        "largo largos filtrado filtrados cambio frente lanzamiento diagonal",
        "pase largo, cambio de frente, pase filtrado, long passing", "sin pase largo"),
    "mentality_vision": (
        "vision creativo creativa creatividad enganche playmaker organizador talento "
        "ultimo asistencia asistencias",
        "vision de juego, creatividad, ultimo pase, playmaking", "poca lectura"),
    "defending": (
        "defensa defensivo defensiva marca marcar quite quites corte cortes recuperacion "
        "robar defending tackling solido seguro atras",
        "defensa, marca, quite, corte, defending, tackling", "flojo en defensa"),
    "mentality_interceptions": (
        "anticipo anticipacion anticipar interceptacion intercepta intercepciones interceptions",
        "anticipo, interceptacion, corte, interceptions", "sin anticipo"),
    "power_strength": (
        "fuerza fuerte potente corpulento corpulenta duelo duelos choque aguantar strength",
        "fuerza, potencia, duelo, strength", "debil en el duelo"),
    "attacking_heading_accuracy": (
        "aereo aerea cabeza cabezazo cabeceador cabecear heading",
        "juego aereo, cabeceo, remate de cabeza, heading", "flojo de cabeza"),
    "power_jumping": (
        "salto saltar altura elevacion jumping",
        "salto, elevacion, jumping", "poco salto"),
    "attacking_crossing": (
        "centro centros centrador centrar centrado crossing",
        "centros, envios al area, crossing", "sin centros"),
    "skill_fk_accuracy": (
        "libre libres parada parado tiros especialista",
        "tiro libre, pelota parada, balon parado, free kicks", "sin pelota parada"),
    "physic": (
        "fisico fisica fisicamente aguante intenso intensa porte physicality",
        "fisico, aguante, physicality", "poco fisico"),
    "power_stamina": (
        "resistencia despliegue recorrido pulmon incansable box to box stamina motor",
        "resistencia, despliegue, ida y vuelta, stamina", "poco recorrido"),
}

GK_ASPECTS: dict[str, tuple[str, str, str]] = {
    "goalkeeping_diving": (
        "estirada estiradas vuelo vuelos palo diving", "estiradas, vuelos, diving", "poca estirada"),
    "goalkeeping_handling": (
        "blocaje manos seguro sujetar handling", "blocaje, manos seguras, handling", "manos inseguras"),
    "goalkeeping_reflexes": (
        "reflejos reactivo respuesta atajar atajadas reflexes",
        "reflejos, respuesta, reflexes, shot stopping", "reflejos lentos"),
    "goalkeeping_positioning": (
        "colocacion colocado salida salidas achique achicar positioning",
        "colocacion, salidas, achique, positioning", "mal colocado"),
}

ALL_ASPECTS = ASPECTS | GK_ASPECTS
RANK_PREFIX = "rank_"


def normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFD", str(text).casefold())
    return "".join(c for c in lowered if not unicodedata.combining(c))


def band(percentile: float) -> str | None:
    """Tramo cualitativo. Devuelve None por debajo de la mediana: un atributo del
    montón no es una fortaleza y nombrarlo sólo diluye el vector."""
    if percentile >= 0.95:
        return "de elite, excepcional, world class"
    if percentile >= 0.85:
        return "sobresaliente, muy destacado"
    if percentile >= 0.70:
        return "muy bueno, solido"
    if percentile >= 0.50:
        return "correcto, aceptable"
    return None


def describe(ranked: list[tuple[float, str]], aspects: dict) -> str:
    """Redacta fortalezas y limitaciones a partir de percentiles ya calculados.

    Las carencias usan vocabulario propio («lento») y nunca el término del atributo:
    el modelo no interpreta la negación, así que escribir «poca velocidad» atraería
    justamente las consultas que piden velocidad.
    """
    strong = [(p, key) for p, key in ranked if band(p)][:4]
    weak = [key for p, key in ranked[-3:] if p < 0.35]
    text = ("Fortalezas: " + ". ".join(f"{aspects[k][1]} {band(p)}" for p, k in strong) + ". "
            if strong else "Rendimiento parejo, sin atributos destacados. ")
    if weak:
        text += "Limitaciones: " + ", ".join(aspects[k][2] for k in weak) + ". "
    return text


def aspects_in_query(query: str, keys: dict = ALL_ASPECTS) -> dict[str, list[str]]:
    """Atributos evocados por la consulta y el término que disparó cada uno."""
    words = set(re.findall(r"[a-z]+", normalize(query)))
    hits = {}
    for key, (triggers, _, _) in keys.items():
        matched = sorted(words.intersection(triggers.split()))
        if matched:
            hits[key] = matched
    return hits


def rerank(query: str, candidates: list[dict], k: int) -> tuple[list[dict], dict]:
    """Ordena el pool por los atributos pedidos; deja pasar el orden ANN si no hay.

    La clave primaria es el ajuste de atributos y la similitud coseno sólo desempata.
    No es una decisión estética: medido sobre el índice, MiniLM ubica a Messi en el
    puesto 496 para «regate, visión de juego y último pase», una consulta que lo
    describe con exactitud. Cualquier peso apreciable de esa señal en el orden final
    reinyecta ese ruido y desplaza a los jugadores que la consulta realmente pide.
    La distancia coseno decide *quién es candidato*; los percentiles deciden *el orden*.

    No filtra candidatos ni cambia distancias: sólo reordena y recorta a k. Los
    candidatos sin percentiles en metadata (clubes, técnicos, otros corpus)
    conservan el orden vectorial.
    """
    hits = aspects_in_query(query)
    columns = [key for key in hits if any(RANK_PREFIX + key in c["metadata"] for c in candidates)]
    evidence = {"aspects_detected": hits, "aspects_used": columns, "pool_size": len(candidates),
                "applied": bool(columns)}
    if not columns:
        evidence["reason"] = ("La consulta no menciona atributos medibles del dataset, "
                              "o el corpus no expone percentiles: se conserva el orden vectorial.")
        return candidates[:k], evidence
    for candidate in candidates:
        metadata = candidate["metadata"]
        ranks = [metadata[RANK_PREFIX + col] / 100
                 for col in columns if RANK_PREFIX + col in metadata]
        candidate["attribute_fit"] = round(sum(ranks) / len(ranks), 4) if ranks else 0.0
        # Los percentiles se guardan con un decimal, así que en la cola alta muchos
        # jugadores caen en el mismo casillero. La valoración cruda desempata entre
        # iguales sin sustituir al percentil, que es lo único comparable entre
        # atributos de escalas distintas.
        raw = [metadata[col] for col in columns if isinstance(metadata.get(col), (int, float))]
        candidate["attribute_raw_mean"] = round(sum(raw) / len(raw), 2) if raw else 0.0
    ordered = sorted(candidates, reverse=True, key=lambda c: (
        c["attribute_fit"], c["attribute_raw_mean"], c["similarity"]))[:k]
    evidence["reason"] = ("Orden por el percentil medio de " + ", ".join(columns)
                          + "; la similitud coseno sólo desempata.")
    return ordered, evidence
