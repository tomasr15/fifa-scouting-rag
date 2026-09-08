# Dataset real FIFA para la defensa

La aplicación abre por defecto el Mundial de Clubes FIFA masculino 2025. Incluye
1.000 jugadores registrados, 32 clubes y 32 técnicos del listado oficial del
4 de julio de 2025. Los 63 reportes de partido aportan 1.998 filas jugador-partido,
con estadísticas de 675 jugadores. Los otros 325 conservan sólo su ficha de plantel:
no se inventan estadísticas ni valoraciones. Las edades corresponden al 14/6/2025.

El CSV y los perfiles fueron extraídos y construidos para este proyecto: **las
fuentes son oficiales; FIFA no publicó este CSV ni estos embeddings**.

## Ejecutar con los datos incluidos

Desde la carpeta del proyecto, PowerShell, Python 3.12 recomendado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --dataset fifa --index-only
.\.venv\Scripts\python.exe -m streamlit run app.py
```

La primera indexación descarga el modelo MiniLM. Después funciona localmente.
Los CSV y `data/fifa/corpus.jsonl` están incluidos; no hace falta descargar PDFs.
En Linux/macOS reemplazar el ejecutable por `.venv/bin/python`.
El generador `none` muestra evidencia sin un LLM. OpenAI/Ollama se configuran con
las variables del README y se seleccionan en la barra lateral.

```powershell
.\.venv\Scripts\python.exe main.py --dataset fifa --entity-type player --query "Lateral que avanza por dentro y genera superioridad central" --benchmark --output resultado_fifa.json
.\.venv\Scripts\python.exe main.py --dataset fifa --entity-type coach --query "presión alta y contrapresión"
.\.venv\Scripts\python.exe main.py --dataset fifa --entity-type club --aspect economics --query "premio de participación en el torneo"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Qué se vectoriza y qué se filtra

Hay **2.452 fragmentos**, con vectores de 384 dimensiones: técnica, defensa y físico
por jugador observado; plantel sin estadísticas; táctica por club y técnico;
economía por club; seis síntesis editoriales de análisis tácticos FIFA.
Los nombres, clubes y URLs quedan fuera del embedding. Se conservan en metadata
y en el documento entregado al RAG. El buscador compara perfiles y estadísticas;
para buscar una identidad o exigir un umbral se usan filtros escalares.

Chroma persiste la colección `football_fifa_2025` con `hnsw:space=cosine`, separada
del ejemplo sintético. Reutiliza el índice si coincide la huella del corpus.
Cada resultado expone ID, distancia raw, score `1-distancia`, metadata del `where`,
texto realmente vectorizado y fuentes con página. El score puede ser negativo;
no es una probabilidad ni una nota de calidad del futbolista. `k` cuenta fragmentos:
varios pueden pertenecer a una misma persona.

La latencia `execution_time_ms` mide la llamada Chroma.query completa, incluidos
filtros y recuperación del documento. El embedding se mide aparte. La comparación
LIKE busca substrings OR sobre el mismo texto sin nombres y aplica el mismo filtro.
Es un escaneo pandas, no un B-Tree real; un LIKE con comodín inicial tampoco prueba
el rendimiento de un B-Tree. No se fuerza que LIKE devuelva cero. ANN puede devolver
vecinos irrelevantes y en colecciones pequeñas Chroma también utiliza un buffer
de búsqueda exhaustiva. Una sola latencia no demuestra superioridad ni recall.

## Estadísticas y límites

- Técnica: pases, precisión, cambios de orientación, centros, rupturas de líneas,
  progresiones, acciones individuales, remates y goles de los reportes.
- Defensa: presiones, recuperaciones, intercepciones, entradas, duelos y despejes.
- Físico: metros recorridos, carreras a alta velocidad, sprints y velocidad máxima.
- Club: formaciones iniciales, posesión y porcentajes de fases de juego publicados.
- Técnicos: identidad oficial y perfil del equipo asociado al snapshot. Las cifras
  no permiten atribuir causalmente el rendimiento al entrenador ni describen su carrera.
- Economía: rango oficial del pilar de participación según confederación. No son
  presupuestos de fichajes, ingresos anuales, salarios, deuda ni cobros auditados.
  No se calculó el premio adicional por resultados deportivos.

Los totales se suman por torneo; las medias individuales son **por aparición, no
por 90 minutos**. La precisión agregada divide pases completos entre intentos.
La velocidad es el máximo observado. Porcentajes colectivos: medias simples por
partido, conservando la definición FIFA; posesión incluye tiempo en disputa.
No hay ajuste por rival, minutos ni posición específica: FIFA agrupa GK/DF/MF/FW.
MiniLM no garantiza razonamiento numérico ni alta calidad en español: los umbrales
numéricos deben expresarse como filtros. Los seis textos editoriales son paráfrasis
curadas separadas de los perfiles estadísticos, no etiquetas para todo el plantel.

## Fuentes y reconstrucción

- [FIFA: 63 reportes oficiales](https://www.fifatrainingcentre.com/en/game/tournaments/fcwc/2025/post-match-summary-reports.php).
- [FIFA: lista de planteles y técnicos](https://fdp.fifa.org/assetspublic/ce233/pdf/SquadLists-English.pdf).
- [FIFA: distribución económica oficial](https://inside.fifa.com/organisation/news/club-world-cup-2025-record-prize-money-unprecedented-solidarity-benefit-club-football?entryId=Qqle9UafPSuWrUUj9isYF&requester=MediaHub).

`data/fifa/sources.json` registra URLs, fecha de extracción y SHA-256 de cada PDF.
Cada fragmento añade fuentes concretas a `source_refs_json`. Se preservan las tablas
de partido y los agregados para auditar la transformación sin depender del LLM.

Para reconstruir desde los PDFs (aproximadamente 320 MB; requiere Internet):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ingest.txt
.\.venv\Scripts\python.exe fifa_ingest.py --download
.\.venv\Scripts\python.exe fifa_corpus.py
```

Los archivos descargados quedan en caché local. Los PDFs originales y la caché del
índice no están en el ZIP; se incluyen las tablas derivadas y el corpus. Si cambian
los perfiles, reconstruir explícitamente con `main.py --dataset fifa --rebuild --index-only`.
Los datos corresponden a ese torneo y snapshot, no a planteles ni finanzas actuales.
