"""CLI: python main.py --query 'volante mixto' --max-age 27."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from data_loader import BASE_DIR, load_players
from benchmark import SearchBenchmark
from instrumentation import print_search_metrics
from rag_pipeline import LLMConfig, run_scouting
from vector_store import PlayerVectorStore, build_filter


def main() -> int:
    parser = argparse.ArgumentParser(description="Scouting semántico con ChromaDB y RAG")
    parser.add_argument("--query", help="Consulta de scouting en español")
    parser.add_argument("--csv", type=Path, help="CSV propio; por defecto players.csv o mock")
    parser.add_argument("--db", type=Path, default=BASE_DIR / "chroma_db")
    parser.add_argument("--league", help="Liga exacta, por ejemplo 'La Liga'")
    parser.add_argument("--max-age", type=int)
    parser.add_argument("--position", help="supplied: ST, CM, GK, etc. (también secundaria); FIFA: DF/MF/FW/GK; mock: MC/DC")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--provider", choices=["none", "openai", "ollama"], default="none")
    parser.add_argument("--rebuild", action="store_true", help="Reemplazar el índice de jugadores")
    parser.add_argument("--index-only", action="store_true", help="Ingestar y salir")
    parser.add_argument("--benchmark", action="store_true", help="Comparar Chroma ANN vs escaneo léxico LIKE")
    parser.add_argument("--no-rerank", action="store_true",
                        help="supplied: mostrar el orden vectorial puro, sin reordenar por atributos")
    parser.add_argument("--dataset", choices=["supplied", "mock", "fifa"], default="supplied")
    parser.add_argument("--entity-type", choices=["player", "club", "coach"])
    parser.add_argument("--aspect", help="FIFA: technique, defence, physical, tactics, editorial_tactics, economics, roster")
    parser.add_argument("--club", help="Club exacto del corpus FIFA")
    parser.add_argument("--output", type=Path, help="Exportar resultados, contexto y reporte en JSON")
    args = parser.parse_args()
    if args.dataset in ("fifa", "supplied"):
        if args.dataset == "supplied":
            from supplied_data import open_store as open_fifa_store
        else:
            from fifa_corpus import open_fifa_store
        store, _, benchmark = open_fifa_store(rebuild=args.rebuild, db_path=args.db)
        if args.index_only: return 0
        clauses = [{"gender": "male"}]
        if args.dataset == "fifa": clauses.append({"season": 2025})
        elif args.league: clauses.append({"league": args.league})
        for key, value in [("entity_type", args.entity_type), ("aspect", args.aspect),
                           ("club", args.club), ("position", args.position if args.dataset == "fifa" else None)]:
            if value: clauses.append({key: value})
        if args.max_age is not None: clauses.append({"age": {"$lte": args.max_age}})
        if args.position and args.dataset == 'supplied': clauses.append({'plays_'+args.position.upper():True})
        if args.csv or (args.league and args.dataset == 'fifa'): parser.error("Este corpus no acepta --csv; --league sólo aplica a supplied/mock.")
        query = args.query or input("Consulta: ").strip()
        where = {'$and':clauses} if len(clauses)>1 else clauses[0]
        # Sólo supplied guarda percentiles de atributos; el corpus FIFA se deja en
        # orden vectorial puro para no alterar los tiempos que reporta.
        result = run_scouting(query, store, args.k, where, LLMConfig.from_env(args.provider),
                              benchmark if args.benchmark else None,
                              rerank_by_attributes=args.dataset == "supplied" and not args.no_rerank)
        print_search_metrics(result)
        print("\n=== ORDENAMIENTO ===")
        print(result["rerank"]["reason"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.output: args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    try:
        df, source = load_players(args.csv)
        print(f"Dataset: {source.name} | {len(df)} jugadores")
        print("Inicializando Chroma; la primera ejecución descarga el modelo local...")
        store = PlayerVectorStore(args.db)
        indexed = store.initialize(df, rebuild=args.rebuild)
        print(f"{'Indexados' if indexed else 'Índice reutilizado'}: {store.collection.count()} perfiles | coseno")
        if args.index_only:
            return 0
        where = build_filter(args.league, args.max_age, args.position)
        print(f"Filtro Chroma: {json.dumps(where, ensure_ascii=False)}")
        benchmark = SearchBenchmark(store, df) if args.benchmark else None
        while True:
            query = args.query or input("\nConsulta (Enter para salir): ").strip()
            if not query:
                break
            # El mock no expone percentiles: reordenar no aportaría nada.
            result = run_scouting(query, store, args.k, where, LLMConfig.from_env(args.provider),
                                  benchmark, rerank_by_attributes=False)
            print("\nEVIDENCIA RECUPERADA (menor distancia = mayor cercanía)")
            for i, candidate in enumerate(result["candidates"], 1):
                print(f"\n[J{i}] distancia raw={candidate['distance']!r} | "
                      f"score (1 - distancia)={candidate['similarity']!r} | ID={candidate['id']}")
                print(candidate["document"])
                print(json.dumps(candidate["metadata"], ensure_ascii=False))
                print("Metadata del where: " + json.dumps(candidate["filter_metadata"], ensure_ascii=False))
            print_search_metrics(result)
            if result["benchmark"]:
                comparison = result["benchmark"]
                lexical = comparison["lexical"]
                print("\n=== COMPARATIVA ANN / LIKE ===")
                print(f"A · Chroma ANN: {len(result['candidates'])} vecinos | "
                      f"{result['execution_time_ms']:.6f} ms sin embedding")
                print(f"B · pandas LIKE: {lexical['total_matches']} coincidencias totales | "
                      f"{len(lexical['candidates'])} mostradas | {lexical['execution_time_ms']:.6f} ms")
                print(f"Filas elegibles por where: {lexical['eligible_count']}")
                print(f"Términos OR: {lexical['terms']} | Patrones LIKE: {lexical['like_patterns']}")
                for c in lexical["candidates"]:
                    print(f"LIKE · {c['metadata']['name']} | ID={c['id']} | términos={c['matched_terms']}")
                    print(c["document"])
                    print("Metadata del where: " + json.dumps(c["filter_metadata"], ensure_ascii=False))
                print(comparison["interpretation"])
                print(comparison["note"])
            if result["warning"]:
                print(f"\nAviso: {result['warning']}")
            print(f"\n{result['report']}")
            if args.output:
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"\nExportado: {args.output.resolve()}")
            if args.query:
                break
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nHasta luego.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
