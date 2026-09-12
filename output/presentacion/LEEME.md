# Exposición de bases de datos vectoriales

Material preparado el 12/09/2026 para cinco integrantes. El guion asigna 26 minutos y deja hasta cuatro minutos para transiciones e imprevistos. La duración oral debe confirmarse con un ensayo grupal.

- `Bases_Vectoriales_Exposicion_Final.pptx`: 15 diapositivas editables con notas para cada expositor y fuentes.
- `Bases_Vectoriales_Exposicion_Final.pdf`: exportación de las mismas 15 diapositivas.
- `Guion_5_Integrantes.pdf` y `.md`: guion ampliado con bases teóricas por diapositiva, fórmulas explicadas, ejemplos resueltos, tiempos, transiciones, preguntas habituales y alternativas ante fallos. El PDF incluye marcadores de navegación. El texto de estudio amplía el guion oral; leerlo completo excede los 26 minutos previstos.
- `Laboratorio_Vectorial_OFFLINE.html`: abrir directamente en un navegador; los tres módulos funcionan sin conexión ni instalación.
- `respaldo/`: capturas de los modelos didácticos y evidencia de una consulta registrada el 12/09/2026. Identificar estos archivos como respaldo, no como ejecución en vivo.

## Aplicación integrada

Desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

El menú lateral permite elegir **Buscador** o **Exposición interactiva**. El buscador sigue siendo la entrada predeterminada. La sección educativa no importa el motor de búsqueda ni carga embeddings, índices o proveedores LLM. El botón **Ir al caso práctico: buscador** vuelve al buscador.

Para la demostración: CSV FIFA/EA FC, entidad `player`, posición `ST`, cinco resultados, consulta **Delantero con regate y desborde**, generador `none`. Ejecutar con reordenamiento y después desactivarlo para explicar la diferencia de criterio. No se necesitan llamadas al LLM. El corpus tiene 20.421 vectores de 384 dimensiones y métrica coseno; el snapshot corresponde al 22/09/2023.

## Verificación realizada

Pasaron 38 pruebas Python (incluidas navegación y aislamiento) y cinco pruebas JavaScript del modelo didáctico. Se verificaron en navegador los ángulos de referencia, filtros, resultados vacíos y controles del recorrido HNSW, con vistas de 1366 y 1024 píxeles de ancho. El HTML incluye todos sus recursos; no necesita servicios externos.

La consulta real en Streamlit devolvió cinco jugadores con el generador desactivado, y se comprobó la navegación entre ambas secciones. Se inspeccionaron las 15 diapositivas renderizadas desde el PowerPoint mediante LibreOffice y su PDF. El guion incluye un ensayo sugerido: no se realizó un ensayo oral de cinco personas.

El grafo HNSW y las coordenadas 2D son ejemplos didácticos, no una visualización del índice interno ni embeddings reales de jugadores. Las valoraciones del juego y el orden por atributos no constituyen una evaluación deportiva actual.
