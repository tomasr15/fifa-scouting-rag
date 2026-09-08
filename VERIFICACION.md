# Verificación de la entrega

Actualización de configuración LLM: **25 pruebas aprobadas**. Se verificó lectura
de `.env`, prioridad del entorno y relectura de cambios sin guardar secretos en el
entorno del proceso. Las 23 pruebas anteriores también siguen aprobadas.

Ejecutada el 8 de septiembre de 2026 en Windows, Python 3.12, con las dependencias
de `requirements-lock-win-py312.txt`.

- `python -m unittest discover -s tests -v`: **23 pruebas aprobadas**, incluidas cobertura FIFA, valores contrastados visualmente con PDF, fuentes, filtros compartidos y búsqueda Streamlit real.
- Corpus FIFA: **1.000 jugadores registrados, 675 con estadísticas, 32 clubes, 32 técnicos, 63 partidos, 1.998 filas jugador-partido y 2.452 vectores**. Sin nulos en las tablas de estadísticas extraídas.
- CLI FIFA reutiliza la colección persistente `football_fifa_2025`: coseno, D=384.
- Consulta FIFA «Lateral que avanza por dentro y genera superioridad en el centro del campo»: Cucurella y Gusto como primeros vecinos. Ejemplo completo en `ejemplo_fifa_resultado.json`; búsqueda Chroma 37,6276 ms en esa ejecución. LIKE encontró 1.354 fragmentos: no se fuerza un resultado vacío ni se presenta como comparación de relevancia etiquetada.
- Datos económicos limitados al rango reglamentario de participación. Fuentes, metodología y reproducción en `FIFA_DATASET.md`.
- Streamlit: búsqueda normal y modo **Comparar ANN vs LIKE**, ambos **aprobados**.
- `python -m pip check`: **No broken requirements found**.
- CLI ejecutada en un proceso nuevo: reutiliza los **30 perfiles** persistidos.
- Servidor Streamlit: endpoint `/_stcore/health` devuelve **ok**.
- Embeddings reales MiniLM/ONNX: **384 dimensiones**; distancia del documento
  consigo mismo aproximadamente 0; configuración persistida **cosine**.

## Consulta reproducida del modo sintético

«Buscame un volante mixto con despliegue físico y buen pase largo para jugar de
titular en Europa». Filtros: La Liga, edad ≤ 27, posición MC; k = 3.

| Candidato del mock | Distancia coseno |
| --- | ---: |
| Federico Valverde | 0,4358 |
| Pedri | 0,4619 |
| Jude Bellingham | 0,5280 |

El contexto completo, filtros, IDs y resumen sin LLM están en `ejemplo_resultado.json`.
Esta es una comprobación de funcionamiento, no un benchmark de calidad: el conjunto
sintético incluye un perfil de Valverde redactado con vocabulario muy próximo a la consulta.

## Comparativa instrumentada

Comando: `python -X utf8 main.py --benchmark --query "pasador" -k 5 --output ejemplo_benchmark.json`.
Índice existente reutilizado; 30 vectores, espacio cosine, D = 384. Sin filtros.

| Medición de esta ejecución | Resultado |
| --- | ---: |
| Chroma `execution_time_ms`, sin embedding | 23,1787 ms |
| Embedding local | 318,4313 ms |
| Recuperación completa sin LLM | 342,4014 ms |
| Escaneo léxico pandas | 0,7381 ms |
| Candidatos vectoriales | 5 |
| Coincidencias léxicas totales | 0 |

Pedri es el primer vecino: distancia raw `0.4340100884437561`, similitud
`0.5659899115562439`. El término «pasador» no aparece literalmente en el corpus,
pero el perfil de Pedri describe pases y asociaciones. La comparación se conserva
completa en `ejemplo_benchmark.json`. Las latencias varían entre ejecuciones, sobre
todo en la primera carga del modelo; no prueban una ventaja de velocidad de ANN.

Se verificaron filtros pandas contra Chroma.get, la distancia contra la fórmula
de coseno, el uso de una única consulta vectorial por RAG/comparativa, colecciones
vacías, filtros sin candidatos, controles léxicos positivos, incompatibilidad de
datasets y presentación de métricas/IDs en Streamlit.

No se midió un B-tree ni un motor SQL real. Chroma puede combinar HNSW y un buffer
de fuerza bruta. «pasador» es un ejemplo ilustrativo seleccionado; otras consultas
con sinónimos en español recuperaron perfiles poco afines con este MiniLM. Por eso
la interfaz no equipara obtener vecinos con demostrar relevancia táctica.

## Alcance de las pruebas del generador

Se probó el SDK OpenAI real con transporte HTTP simulado: endpoint, modelo, contexto
enviado y extracción del reporte. También se verificó que errores del generador
conserven los candidatos y que búsquedas vacías no invoquen el LLM.

**No se realizó una llamada a OpenAI ni una inferencia real con Ollama.** Para eso
se requiere configurar una API key o disponer del servidor y modelo local, como
explica el README. La evidencia exportada está identificada como modo sin LLM.
