# Dataset principal: los tres CSV aportados

La aplicación usa por defecto `male_players.csv`, `male_teams.csv` y
`male_coaches.csv`. Los archivos contienen FIFA/EA FC con enlaces a SoFIFA:
**son datos del videojuego, no reportes oficiales de la federación FIFA**.

## Selección de temporada

Los originales tienen 180.021 filas de jugadores, 6.947 de equipos y 1.369 técnicos.
Jugadores y equipos abarcan ediciones 15 a 24. Se elige un snapshot común por
`fifa_version`, `fifa_update` y `update_as_of`; no se mezclan distintas temporadas.
La selección predeterminada es edición 24, actualización 2, 22 de septiembre de 2023:

| Entidad | Fichas |
|---|---:|
| Jugadores | 18.350 |
| Equipos | 702 |
| Técnicos | 1.369 |
| Documentos vectorizables | 20.421 |

Se conserva una ficha por entidad en el snapshot. Los técnicos no tienen fecha
en su CSV: se asocian mediante `coach_id` de los equipos seleccionados. Hay 696
técnicos con equipo asociado; el resto conserva identidad sin inventar táctica.
18.263 jugadores tienen correspondencia con un `team_id`; los otros conservan su
ficha de origen y `team_joined=false`. Los técnicos pueden tener varias asociaciones.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Seleccionar **CSV del usuario · FIFA/EA FC**. El buscador empieza inactivo:
marcar **Activar buscador local (Chroma + embeddings MiniLM)** cuando se quiera usar.
La primera activación indexa 20.421 perfiles y puede tardar varios minutos. Las
siguientes reutilizan el índice si el contenido coincide. MiniLM es el modelo local
de embeddings, no un LLM de generación. El servidor no se inicia por instalar o
preparar los datos. Detenerlo con Ctrl+C libera la memoria del proceso.

Para pedir delanteros con regate: tipo `player`, posición `ST`, regate mínimo `80`,
consulta «Delantero con regate y desborde». Se aplican también posiciones secundarias.
Por defecto se excluyen arqueros; seleccionar GK tiene prioridad sobre esa exclusión.
El umbral es una restricción numérica: los embeddings no garantizan orden por regate.

## Por qué la búsqueda densa sola no alcanza

Un embedding no compara magnitudes. Cuando el perfil se redactaba como
`Regate gambeta 41/100. Defensa 73/100. …`, las 18.350 fichas compartían la misma
plantilla y sólo se diferenciaban en números que el modelo tokeniza sin noción de
orden: la similitud coseno media entre dos jugadores al azar era **0,85**. El
resultado era el síntoma esperable de esa colisión — vecinos casi arbitrarios y
siempre los mismos perfiles cortos, porque a menor texto más peso relativo tiene
la palabra de la posición, que es lo único que la consulta reconocía.

El arreglo tiene dos mitades, ambas en [`reranker.py`](reranker.py):

1. **Se vectoriza vocabulario, no cifras.** Cada atributo se convierte a su
   percentil dentro del grupo comparable (campo o arquero) y se redacta con
   términos en español e inglés: «regate, gambeta, desborde, uno contra uno,
   dribbling **sobresaliente**». Sólo se nombran los cuatro atributos por encima de
   la mediana. Las carencias usan vocabulario propio («lento», «sin desborde») y
   nunca el término del atributo, porque el modelo no interpreta la negación y
   «poca velocidad» atraería justamente las consultas que piden velocidad. La
   similitud media entre jugadores baja a **0,75** y los perfiles dejan de ser
   intercambiables. Los valores exactos siguen en el documento que lee el LLM.
2. **La etapa vectorial pasa a ser recall, no precisión.** Se recupera un pool
   amplio (hasta 5.000 vecinos) y se ordena por el percentil de los atributos que
   la consulta menciona. `«Defensor central fuerte en el juego aéreo»` detecta
   `power_strength` y `attacking_heading_accuracy` y ordena por ellos; una consulta
   sin atributos reconocibles conserva intacto el orden por distancia coseno.

**La similitud coseno no pondera el orden final: sólo desempata.** No es una
decisión estética. Medido sobre el índice, MiniLM ubica a Messi en el **puesto 496**
para «regate, visión de juego y último pase», una consulta que lo describe con
exactitud, y deja a Kevin De Bruyne fuera de los primeros 5.000. Cualquier peso
apreciable de esa señal desplaza a los jugadores que la consulta realmente pide: con
peso 0,15 el primer resultado era un mediapunta de valoración 78. La distancia
coseno decide **quién es candidato**; los percentiles deciden **el orden**.

Entre percentiles iguales —se guardan con un decimal, así que en la cola alta hay
empates— desempata el promedio de las valoraciones crudas, y recién después la
similitud. Sin ese desempate, «extremo rápido y desequilibrante» devolvía un
extremo de valoración 64 por delante de Dembélé.

### El filtro de posición no es obligatorio, pero define la cobertura

Sin filtro de posición la búsqueda funciona: `«delantero con definición y remate»`
devuelve a Haaland, Kane, Lewandowski y Benzema aunque nadie haya seleccionado `ST`,
porque los atributos ya son propios de la posición —sólo un delantero tiene
definición de élite—. La diferencia es la **cobertura**:

| Filtro | Elegibles | Pool | Orden |
| --- | --- | --- | --- |
| Ninguno | 16.305 | 5.000 (tope) | Aproximado |
| `ST` | 3.194 | 3.194 | **Exacto** |
| `CB` | 3.976 | 3.976 | **Exacto** |
| `ST` + Premier League | 95 | 95 | **Exacto** |

Cuando el subconjunto elegible entra en el pool, el orden por atributos examina a
**todos** los candidatos y el resultado es exacto. Sin filtro quedan 11.305
jugadores sin examinar, elegidos por una señal —la distancia coseno— que ya vimos
que es poco fiable en este corpus: por eso sin filtro Mbappé se cae del top 5 de
delanteros y Van Dijk del de centrales, aunque con el filtro aparecen. La interfaz
avisa en cada búsqueda si la cobertura fue completa o parcial.

El reordenamiento **no inventa ni filtra** nada: sólo ordena candidatos que ya
pasaron el filtro exacto y la búsqueda vectorial. La casilla **Reordenar por los
atributos de la consulta** lo desactiva para ver el orden vectorial puro, y la
interfaz informa qué atributos detectó y cuántos candidatos no estaban en el top-k
por distancia coseno. `attribute_fit` es un percentil medio entre 0 y 1, no una
probabilidad ni una medida de calidad futbolística.

Generador `openai` usa lo configurado en `.env` (incluido OpenRouter);
`none` no llama a una API. Ver [configuración del LLM](LLM_SETUP.md).

```powershell
.\.venv\Scripts\python.exe main.py --dataset supplied --index-only
.\.venv\Scripts\python.exe main.py --dataset supplied --entity-type player --position ST --query "Delantero con regate" --benchmark
```

## Datos y procedencia

`data/supplied/male_*.csv` incluye la selección lista para usar, conservando todas
las columnas originales; `manifest.json` registra snapshot, cantidades y hashes de
los originales. Las copias históricas completas quedan localmente en
`data/supplied/raw/`, excluidas de Git y del ZIP para evitar duplicación pesada.
Los archivos en Descargas no se modificaron. Para seleccionar otra edición:

```powershell
.\.venv\Scripts\python.exe supplied_data.py --source "C:\Users\Tomas\Downloads" --version 23
```

Este comando sólo prepara CSV y manifiesto; no carga MiniLM. Reiniciar Streamlit
después de cambiar la selección. Para volver al default usar `--version 24`.
Una edición usa su propia colección, con la versión del perfil en el nombre
(`football_supplied_v24_u2_supplied_profile_v3`). Al cambiar la redacción que se
vectoriza se indexa una colección nueva en vez de fallar contra la anterior. Si
cambia el contenido de una misma colección, reconstruir con
`main.py --dataset supplied --rebuild --index-only`.

## Foco en la base vectorial

- Perfil de jugador que se vectoriza: posición y pie en español e inglés, más
  fortalezas y limitaciones redactadas por percentil. Los arqueros se rankean contra
  arqueros, no contra jugadores de campo. Filigranas, trabajo ataque/defensa, rasgos
  y las puntuaciones exactas van al documento, no al embedding.
- Equipo: táctica, ataque/mediocampo/defensa y valores económicos disponibles.
- Técnico: táctica del equipo vinculado, sin atribuirle cualidades personales no documentadas.
- Nombres e identidades quedan en metadata/documento; se vectoriza el perfil.
- Chroma: persistencia, HNSW/coseno, D=384, IDs estables, filtros escalares, tiempos
  separados de embedding y consulta, score 1-distancia y comparativa con LIKE.
- LIKE usa el mismo texto de perfil y los mismos filtros; es un escaneo pandas,
  no un B-Tree real ni una prueba de superioridad de ANN.

`value_eur`, `wage_eur` y `club_worth_eur` son valores del videojuego, no importes
auditados. `transfer_budget_eur` está vacío en la selección 24 y no se sustituye con
presupuestos de versiones anteriores. No se inventa un reporte de partidos a partir
de ratings. El corpus oficial FIFA 2025 y el mock se mantienen como modos separados.

La preparación y las pruebas usan los CSV; la colección completa se construye sólo
al activar el buscador o ejecutar indexación explícita. No se incluyen índices ni
claves en el repositorio.
