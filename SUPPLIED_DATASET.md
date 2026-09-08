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
Una edición usa su propia colección `football_supplied_v24_u2`; si cambia el
contenido de la misma colección, reconstruir con `main.py --dataset supplied --rebuild --index-only`.

## Foco en la base vectorial

- Perfil de jugador: posición, puntuaciones técnicas/físicas, pie, filigranas,
  trabajo ataque/defensa y rasgos. Los arqueros tienen métricas de portería.
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
