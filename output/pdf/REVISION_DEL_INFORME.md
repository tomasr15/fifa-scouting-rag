# Revisión del informe de Bases de Datos Vectoriales

**Dictamen:** el original tiene una base conceptual y una estructura útiles, pero no conviene presentarlo sin corregir. El problema principal es que describe un caso práctico distinto del proyecto disponible. Se preparó una versión revisada de 25 páginas, con cuerpo en Arial 12 y texto justificado. Se sintetizó y reorganizó la teoría para compatibilizar legibilidad y extensión, manteniendo las bases vectoriales como tema central.

## Contraste con la consigna

- La consigna solicita introducción, descripción, características, desarrollo, ambientes y aplicaciones, casos de estudio, caso práctico, conclusión y bibliografía. La versión revisada cubre todos esos apartados.
- Solicita aproximadamente 20 a 25 carillas. El original tiene 27 páginas físicas (24 numeradas de cuerpo); su aceptación dependería de cómo se cuenten portada e índice. La versión nueva tiene 25 páginas físicas.
- Solicita Arial 12 y justificado. El original utiliza mayormente Liberation Sans de 9,2 puntos, con tablas de aproximadamente 6,9 puntos. La versión revisada utiliza Arial 12 en cuerpo y tablas.
- La portada todavía requiere número de grupo, integrantes, correos y fecha real de presentación. Se dejaron espacios en blanco para no inventar datos.
- La consigna también pide una presentación de unas 10 a 15 diapositivas y exposición grupal con el caso funcionando. Estos elementos no se reemplazan con el informe y no fueron creados en esta revisión.
- El documento de consigna indica que el informe debe subirse al CVG antes del 13 de octubre de 2026. No se realizó ninguna entrega ni publicación.

## Problemas detectados y corregidos

1. **Caso práctico ajeno al código:** páginas físicas 20 a 23 del original describen normativa universitaria, Qdrant, BGE-M3, embeddings de 1.024 dimensiones y extracción de PDF. El código implementa scouting con Chroma, MiniLM de 384 dimensiones y CSV. Se reemplazó íntegramente el caso y se alinearon resumen, limitaciones y conclusión.
2. **Resultados que no corresponden al buscador:** se retiraron cifras de fragmentación, umbrales, Precision@K, Recall@K y MRR del prototipo anterior. Su validez para aquel proyecto no se pudo determinar con estos archivos; no son evidencia de este buscador.
3. **Funciones inexistentes:** el buscador no implementa una abstención por umbral semántico, extracción por páginas ni validación automática de todas las citas. Sí implementa reordenamiento por atributos, pese a que el original decía que no había reordenamiento.
4. **Confidencialidad:** embeddings locales no garantizan que los documentos permanezcan en el equipo si se habilita un generador remoto. Se explicó qué se transmite y qué hace el modo sin LLM.
5. **Fecha de DoorDash:** el artículo enlazado es del 17 de septiembre de 2024, no del 15 de abril de 2025. La fuente primaria sí publica cifras de reducción de alucinaciones y problemas de cumplimiento. Se corrigieron fecha, autores y descripción.
6. **Generalizaciones:** se matizaron la supuesta incapacidad de los gestores relacionales para incorporar recuperación vectorial, la equiparación de filtros con fusión léxica/densa, las garantías de escalabilidad y la idea de que RAG resuelve automáticamente privacidad o alucinaciones.
7. **Versiones y límites:** se retiraron versiones presentadas como vigentes sin relación con el proyecto; se incorporaron las fijadas en requirements.txt. El límite de dimensiones de pgvector depende del tipo indexado, no de HNSW en general.
8. **Notas de edición:** se retiraron las indicaciones de ubicación de figuras, la promesa de un Anexo A inexistente, la nota de aplicación de APA y la afirmación de una nueva edición de OWASP del 4 de agosto de 2026, no respaldada en esta revisión. Se referencia explícitamente el catálogo OWASP 2025 consultado.
9. **Procedencia:** el caso principal usa valoraciones FIFA/EA FC edición 24, actualización 2, fechadas el 22/09/2023; no estadísticas del Mundial de Clubes 2025 ni información actual. El origen y la licencia del dataset completo no pudieron establecerse independientemente a partir de los CSV: se explica esta limitación sin atribuirle una autoría inventada.

## Evidencia obtenida

- 35 pruebas de unittest aprobadas en 23,819 s. Cubren distintos modos y algunas muestras; incluyen simulaciones de proveedor generativo. No equivalen a una evaluación de relevancia de 35 consultas sobre el corpus completo.
- Una consulta real con Chroma y MiniLM sobre la colección de 20.421 vectores. Consulta: “Delantero con regate y desborde”; filtros de género, tipo player y posición ST; k=5; proveedor none.
- 3.194 candidatos elegibles y recuperados. Orden final por regate: Mbappé, Griezmann, Gabriel Jesus, Nkunku y Ben Yedder, con las identidades completas en el JSON adjunto.
- Los tiempos corresponden a una única ejecución local, durante la sesión de revisión. No se registró un protocolo de aislamiento de carga ni repeticiones; no se presentan como benchmark de rendimiento general.
- El comparador LIKE encontró 3.194 coincidencias. Es un escaneo pandas con OR de términos, no un motor SQL ni B-Tree. No demuestra inferioridad o superioridad general de una tecnología.
- No se ejecutó generación con una API real ni se incurrió en llamadas generativas para esta comprobación.
- No se modificó el código de la aplicación ni los PDF originales.

## Archivos entregables

- `TPI_Bases_Vectoriales_Futbol_REVISADO.pdf`: informe remaquetado de 25 páginas.
- `TPI_Bases_Vectoriales_Futbol_EDITABLE.html`: fuente textual editable; su impresión desde otro programa puede variar respecto del PDF verificado.
- `evidencia_busqueda.json`: resultado completo de la consulta.
- `evidencia_pruebas.txt`: registro de la ejecución de pruebas.

## Antes de presentar

Completar la portada, leer la versión revisada y ensayar la demo con el mismo snapshot. Si se quiere mostrar RAG completo, comprobar el proveedor y el modelo antes de la exposición: la evidencia adjunta demuestra recuperación y reordenamiento sin generación. No se deben defender las cifras del ejemplo universitario anterior como si fueran mediciones del buscador.

La calificación final depende de la cátedra; técnicamente la versión revisada ofrece una correspondencia verificable entre explicación, código y resultados, con las limitaciones declaradas.

## Fuentes puntuales comprobadas

- [Artículo original de DoorDash](https://careersatdoordash.com/blog/large-language-modules-based-dasher-support-automation/)
- [Ficha de MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Documentación de colecciones de Chroma](https://cookbook.chromadb.dev/core/collections/)
- [Tipos e índices de pgvector](https://github.com/pgvector/pgvector)
- [OWASP: Vector and Embedding Weaknesses 2025](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)
