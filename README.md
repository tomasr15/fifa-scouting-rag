# Buscador semántico y asistente de scouting

Repositorio: [tomasr15/fifa-scouting-rag](https://github.com/tomasr15/fifa-scouting-rag).
Para configurar la API: [LLM_SETUP.md](LLM_SETUP.md). La clave se guarda en `.env` local.

Prototipo universitario de RAG en Python. Abre por defecto el **Mundial de Clubes
FIFA masculino 2025**: 1.000 jugadores, 32 clubes, 32 técnicos y 63 partidos de fuentes
oficiales, transformados en 2.452 fragmentos vectoriales. Incluye estadísticas,
táctica y contexto económico del premio de participación. [Guía del dataset real,
fuentes, reconstrucción y límites](FIFA_DATASET.md).

Usa MiniLM local de 384 dimensiones, Chroma persistente con coseno, filtros escalares,
Streamlit, CLI, comparativa ANN/LIKE y generación OpenAI/Ollama. Se mantiene un modo
separado de 30 jugadores sintéticos para ejemplos básicos; no son datos actuales.

## Ejecución rápida

Requiere Python **3.10–3.12 de 64 bits**; se recomienda 3.12 para reproducir el entorno
de prueba. No necesita Docker ni servidores para la búsqueda. La instalación y la
primera descarga de MiniLM requieren Internet; las búsquedas posteriores son locales.

Desde esta carpeta, en Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --dataset fifa --index-only
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abrir [la aplicación local](http://localhost:8501). No hace falta activar el entorno.
Si `python` abre Microsoft Store, instalar Python 3.12 de 64 bits y habilitarlo en PATH
(o usar `py -3.12` en el primer comando si ya está instalado el lanzador).

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py --dataset fifa --index-only
.venv/bin/python -m streamlit run app.py
```

El modo predeterminado **Sin LLM** permite demostrar toda la recuperación sin claves.
Su resumen es determinista y está etiquetado; para el RAG completo configurar uno de
los siguientes generadores y seleccionarlo en la barra lateral.

## Generación con OpenAI

**Pegar la API key en `.env`, junto a `app.py`, en la línea `OPENAI_API_KEY=`.**
El archivo `.env` se excluye de Git y del ZIP. La plantilla `.env.example` sí se publica.
Ver [configuración del LLM](LLM_SETUP.md) para los pasos completos y problemas comunes.

```powershell
Copy-Item .env.example .env
notepad .env
```

Guardar el archivo y seleccionar **openai** en **Generador** (modo FIFA), o
**OpenAI / compatible** en el modo sintético. Alternativamente, en la misma terminal
donde se inicia Streamlit:

```powershell
$env:OPENAI_API_KEY="tu-clave"
$env:OPENAI_MODEL="gpt-4o-mini"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Elegir **OpenAI / compatible** y buscar. La generación utiliza la API y puede tener
costo; la vectorización sigue siendo local. Para otro servidor compatible configurar
también `OPENAI_BASE_URL` (incluyendo `/v1`) y su modelo en `OPENAI_MODEL`.
El programa lee `.env` en cada consulta; las variables de entorno tienen prioridad.
En bash usar `export OPENAI_API_KEY="tu-clave"`.

## Generación local con Ollama

Instalar e iniciar Ollama y descargar un modelo una sola vez:

```powershell
ollama pull llama3.2:3b
```

Con el servidor Ollama corriendo, elegir **Ollama local** en Streamlit. Si no está
iniciado por la aplicación de escritorio, ejecutar `ollama serve` en otra terminal.
Valores predeterminados: `http://localhost:11434/v1`, modelo `llama3.2:3b` y clave
ficticia `ollama` requerida por el SDK. Se pueden cambiar con `OLLAMA_BASE_URL` y
`OLLAMA_MODEL`. La velocidad depende del hardware. Un error de generación conserva
los candidatos y muestra un aviso; no se presenta el resumen como salida de un LLM.

## CLI y ejemplos para la exposición

```powershell
.\.venv\Scripts\python.exe main.py --query "Volante mixto con despliegue físico y buen pase largo" --league "La Liga" --max-age 27 --position MC -k 3 --output resultado.json
.\.venv\Scripts\python.exe main.py --query "Central rápido para defender con línea alta" --max-age 25 --provider ollama
.\.venv\Scripts\python.exe main.py --query "Delantero de área potente y goleador" --provider openai
.\.venv\Scripts\python.exe main.py
```

El último comando abre un bucle interactivo; Enter vacío o Ctrl+C termina.
`--output` exporta la consulta, filtros, documentos, IDs, metadata, métricas, prompt y
reporte, sin credenciales. La app también permite descargar este JSON.

## CSV propio e indexación

Colocar `players.csv` junto a `app.py`. Si no existe, se crea `players_mock.csv` de
forma determinista. Un CSV propio inválido produce un error y no se sustituye en silencio.
Codificación UTF-8, separador coma y estas columnas obligatorias:

```text
name,age,club,league,nationality,position,overall_rating,pace,shooting,passing,dribbling,defending,physical,scouting_report
```

Edad entera entre 15 y 60; valoraciones enteras entre 0 y 99; textos no vacíos.
No se admiten duplicados de nombre y club. Las posiciones se normalizan a mayúsculas;
las ligas se comparan exactamente. Reportes breves y ricos en español son preferibles
a textos extensos: MiniLM tiene un límite de entrada y puede truncarlos.

La CLI acepta `--csv ruta/al/archivo.csv` y `--db ruta/al/indice`. Streamlit utiliza
las rutas predeterminadas junto al código, independientemente del directorio actual.

La colección `players_scouting` se carga sólo si está vacía; conserva los embeddings
entre ejecuciones. Un hash detecta cambios del CSV o ingestas incompletas. Para
actualizarlo, cerrar las interfaces y ejecutar:

```powershell
.\.venv\Scripts\python.exe main.py --rebuild --index-only
```

Esto reemplaza únicamente la colección de jugadores. Volver a iniciar Streamlit
para renovar su caché. No ejecutar reconstrucciones concurrentes desde otros procesos.

## Arquitectura y fundamentos del TP

| Archivo | Responsabilidad |
| --- | --- |
| `data_loader.py` | Mock reproducible, validación, texto unificado, metadata e IDs SHA-256 |
| `vector_store.py` | PersistentClient, índice HNSW coseno, ingesta por lotes y búsqueda |
| `rag_pipeline.py` | Contexto con referencias J1…Jk, prompt y SDK OpenAI compatible |
| `app.py` | Interfaz Streamlit con filtros, evidencia y descarga |
| `main.py` | CLI interactiva o consulta única |
| `instrumentation.py` | Latencias, campos del where y resumen técnico real de la colección |
| `benchmark.py` | Comparativa Chroma ANN vs escaneo de substrings LIKE en pandas |
| `tests/test_pipeline.py` | Pruebas con Chroma y embeddings reales; transporte LLM simulado |
| `tests/test_benchmark.py` | Distancia matemática, latencias, filtros equivalentes y UI comparativa |

Cada jugador es un documento que combina identidad, atributos numéricos y descripción
táctica. El embedding por defecto de Chroma ejecuta `all-MiniLM-L6-v2` con ONNX Runtime;
no requiere `sentence-transformers`, PyTorch ni API para vectorizar. Consulta y
documentos se procesan con el mismo modelo. La metadata conserva atributos tipados,
incluidos `age`, `overall_rating`, `position` y `league`.

Ejemplo de filtro enviado directamente a Chroma antes de obtener los vecinos:

```python
{"$and": [{"league": {"$eq": "La Liga"}}, {"age": {"$lte": 27}}]}
```

API pública (primero inicializar con el dataset):

```python
from data_loader import load_players
from vector_store import get_default_store, query_players

df, _ = load_players()
get_default_store().initialize(df)
hits = query_players("volante mixto", n_results=5, where_filter={"age": {"$lte": 27}})
```

`distancia_coseno = 1 - similitud_coseno`: menor distancia implica mayor cercanía.
La similitud tiene rango teórico [-1, 1], la distancia [0, 2], con posibles pequeños
errores de redondeo. **No son porcentajes de confianza**. La búsqueda devuelve hasta
k vecinos aunque tengan poco encaje; no hay un umbral de relevancia calibrado.

El generador recibe sólo los perfiles recuperados, los filtros y la consulta, y debe
justificar candidatos, comparar y recomendar con citas `[J1]`. Si no hay resultados,
no se llama al LLM. Se puede inspeccionar el prompt completo desde la interfaz.

### Límites y reproducibilidad

- MiniLM es principalmente un modelo de inglés; este baseline admite texto español
  pero no garantiza una buena recuperación multilingüe. Un modelo multilingüe sería
  una extensión futura que requiere reconstruir el índice y evaluar calidad.
- Los números embebidos aportan contexto, pero no sustituyen comparaciones exactas.
  Una edad o liga mencionada en lenguaje natural no se transforma automáticamente
  en filtro: usar los controles o los argumentos de CLI.
- No hay inferencia fiable de potencial, precio, lesiones o titularidad a partir de
  estos datos. Para porteros se necesitan atributos específicos adicionales.
- El mock y los IDs son deterministas. El LLM usa temperatura 0, pero sus respuestas
  no son necesariamente idénticas entre ejecuciones/proveedores. HNSW y distintas
  plataformas también pueden introducir pequeñas diferencias de ranking.
- Las versiones directas están fijadas en `requirements.txt`. Para reproducir todas
  las dependencias del entorno de prueba Windows/Python 3.12 se incluye
  `requirements-lock-win-py312.txt`; en otros sistemas usar `requirements.txt`.
- Internet sólo es necesario al instalar/descargar modelos y al usar un LLM remoto.
  Se deshabilita la telemetría de producto de Chroma; almacenamiento y embeddings son locales.

## Verificación

### Instrumentación y comparativa para la defensa

En Streamlit activar **Comparar ANN vs LIKE** en la barra lateral y ejecutar una
consulta. Debajo de los candidatos aparecen las latencias y la tabla comparativa;
la ficha de la colección muestra nombre, espacio real, cantidad de vectores y D.
No es necesario reconstruir el índice ni instalar dependencias adicionales.

En PowerShell:

```powershell
.\.venv\Scripts\python.exe -X utf8 main.py --benchmark --query "pasador" -k 5 --output ejemplo_benchmark.json
.\.venv\Scripts\python.exe -X utf8 main.py --benchmark --query "Haaland" -k 5
.\.venv\Scripts\python.exe -X utf8 main.py --benchmark --query "pase largo" --league "La Liga" --max-age 27 --position MC -k 3
```

Usar `-X utf8` conserva los acentos también cuando se redirige la salida de consola.
El primer ejemplo permite demostrar una recuperación sin coincidencia literal:
**«pasador» no aparece en el mock**, pero el primer vecino observado es Pedri, cuyo
perfil describe pases y asociaciones. LIKE devuelve cero. El ejemplo «Haaland»
funciona como control positivo léxico. «Pase largo» muestra que ambos métodos pueden
recuperar candidatos; además, la etiqueta «Pase» se repite en todos los documentos,
por lo que ese término genérico tiene poca capacidad para discriminar perfiles.
Estos ejemplos fueron seleccionados para explicar comportamientos; no constituyen
una evaluación independiente ni garantizan aciertos en consultas nuevas.

#### Qué mide cada campo

| Campo JSON | Alcance |
| --- | --- |
| `execution_time_ms` | Tiempo de `collection.query(query_embeddings=...)`: SDK, filtros, búsqueda y lectura de documentos/metadata; excluye embedding y LLM |
| `embedding_time_ms` | Cálculo local del embedding de consulta; puede incluir carga/descarga inicial del modelo |
| `retrieval_time_ms` | Recuperación completa: validación, count, embedding, query y preparación de candidatos; excluye LLM |
| `query_executed` | Indica si se llamó a Chroma.query; una colección vacía devuelve false y tiempo de query 0 |
| `candidates[].id` | ID persistido del vector |
| `candidates[].distance` | Distancia coseno raw devuelta por Chroma, sin redondear ni transformar |
| `candidates[].similarity` | Exactamente `1 - distance`, sin clipping; rango teórico [-1, 1], no probabilidad ni normalización a [0, 1] |
| `candidates[].filter_metadata` | Valores escalares de los campos referenciados por el where; `{}` si no hubo filtro |
| `where_filter` | Expresión completa enviada a Chroma, también visible en consola/UI |

Se usa `time.perf_counter_ns()` y se convierten nanosegundos a milisegundos. Se
conservan los floats completos en JSON y se muestran seis decimales para tiempos
en consola/UI. Es una medición de reloj de alta resolución, no un tiempo exacto del
grafo ni una garantía de precisión de nanosegundos. Caché, carga del sistema y primera
carga del modelo afectan las latencias. El LLM y la búsqueda léxica no se incluyen
en la medición vectorial. La medición pertenece a cada respuesta; no hay un atributo
global mutable de «última latencia» que mezcle consultas concurrentes.

#### Cómo se calcula la búsqueda B

Se preparan una vez en memoria **los mismos textos e IDs que se enviaron a Chroma**.
Se normalizan mayúsculas y tildes en corpus y consulta; se extraen palabras y se
descartan palabras funcionales de una lista explícita en `benchmark.py`. No hay
sinónimos, stemming ni embeddings en B. La condición de texto es inclusiva:

```sql
WHERE <mismo filtro de metadata>
  AND (normalized_description LIKE '%termino1%'
       OR normalized_description LIKE '%termino2%')
ORDER BY vector_id ASC
LIMIT k
```

La sintaxis SQL es ilustrativa: se ejecuta con `Series.str.contains(regex=False)`
en pandas. Las cadenas se tratan como substrings literales. Se muestran los términos,
patrones, operador OR, cantidad total de coincidencias y filas elegibles. El límite k
es el mismo que en A; el orden léxico por ID es determinista y no representa relevancia.
`vector_only_ids` compara contra **todas** las coincidencias léxicas, no sólo su top-k.
Una consulta compuesta sólo por palabras vacías produce cero matches, con explicación.

Los filtros escalares `$eq`, `$ne`, `$lt`, `$lte`, `$gt`, `$gte`, `$in`, `$nin`, `$and`
y `$or` se reproducen en pandas. Se validan antes de comparar; campos desconocidos
se rechazan. Un hash impide comparar contra un DataFrame distinto del índice.
La latencia B incluye el procesamiento de la consulta, filtro de metadata, escaneo,
ordenamiento y preparación de resultados; excluye preparación inicial del corpus.
Cada comparación hace **una sola consulta vectorial**, reutilizada para el RAG.

#### API Python

```python
from benchmark import benchmark_search

comparison = benchmark_search("pasador", {"age": {"$lte": 27}})
print(comparison["vector"]["execution_time_ms"])
print(comparison["lexical"]["execution_time_ms"])
print(comparison["lexical"]["total_matches"])
```

La función pública inicializa el dataset/índice predeterminado una sola vez. Para
otro CSV, DB o k, usar `SearchBenchmark(store, players).benchmark_search(query, where, k)`.
`store.query_players_measured(...)` devuelve candidatos y métricas; `query_players(...)`
conserva su API anterior de lista. Al cambiar un CSV, reiniciar la app/CLI como se indicó.

#### Límites de la comparación de motores

Este experimento **no implementa ni mide un B-tree**. Un patrón con comodín inicial
como `LIKE '%palabra%'` no equivale a la búsqueda de prefijo que puede aprovechar
un B-tree; así se explica en la [documentación de PostgreSQL](https://www.postgresql.org/docs/current/indexes-types.html).
Tampoco se mide un servidor SQL real: pandas escanea datos en memoria.

Chroma configura HNSW, pero también puede consultar un buffer de fuerza bruta antes
de actualizar el grafo, según su [documentación](https://cookbook.chromadb.dev/faq/#what-does-chroma-use-to-index-embedding-vectors).
Por eso el rótulo ANN identifica la vía vectorial y su índice configurado: no afirma
que cada vecino provino exclusivamente del grafo, especialmente con sólo 30 filas.
No se modificó el índice persistente existente. `metadata={"hnsw:space": "cosine"}`
se usa al crear; al iniciar se lee la métrica efectiva de `collection.configuration`
y la dimensión de un embedding almacenado (sin volver a generarlo).

La búsqueda vectorial devuelve vecinos incluso para conceptos que MiniLM no
interpreta bien. Que LIKE devuelva cero y Chroma devuelva k **no prueba calidad**:
hay que revisar el perfil. La aplicación muestra esta advertencia y también casos
con coincidencias en ambos métodos. Un benchmark de rendimiento serio requeriría
más datos, consultas etiquetadas, repeticiones, calentamiento, percentiles y recall
contra vecinos exactos. Este módulo sirve para observar y explicar el pipeline.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Las pruebas verifican persistencia, dimensión 384, distancia del mismo documento,
filtros combinados, orden, resultados vacíos, validación, CSV cambiado, recuperación
ante fallos del LLM, contrato HTTP del SDK y búsqueda en Streamlit. La primera corrida
puede descargar MiniLM. Los índices de prueba quedan en el directorio temporal del
sistema por los handles abiertos de Chroma en Windows. La calidad táctica de un
modelo remoto/local requiere validación manual con ese proveedor.

## Documentación oficial consultada

- [Chroma: embeddings locales](https://docs.trychroma.com/docs/embeddings/embedding-functions)
- [Chroma: cliente persistente](https://docs.trychroma.com/reference/python/client)
- [OpenAI: GPT-4o mini y Chat Completions](https://developers.openai.com/api/docs/models/gpt-4o-mini)
- [Ollama: compatibilidad con OpenAI](https://docs.ollama.com/api/openai-compatibility)
- [MiniLM: ficha del modelo](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
