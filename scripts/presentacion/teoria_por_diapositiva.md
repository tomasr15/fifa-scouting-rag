## 1
### Base teórica para preparar esta diapositiva

Una base de datos vectorial es un sistema que almacena representaciones numéricas y permite recuperar registros por cercanía entre esas representaciones. Su propósito es administrar información y ofrecer consultas de similitud. El vector aporta una forma de comparar; el gestor organiza los registros, conserva sus datos y permite recuperarlos. [L1]

Conviene separar cuatro conceptos desde el comienzo. El modelo de embeddings transforma contenido en números. El índice vectorial organiza esos números para buscar vecinos. La base de datos administra el índice junto con identificadores, metadatos y contenido. La aplicación combina todo eso con una interfaz y reglas de negocio. Un LLM generativo es un componente adicional que puede redactar una respuesta. [L1, L2]

### Ejemplo para explicarlo con palabras propias

“Tenemos muchas fichas de jugadores y una persona describe qué perfil necesita. Primero representamos las fichas numéricamente. Después usamos la base para recuperar perfiles cercanos a su pedido. Finalmente mostramos los datos que justifican el resultado.”

### Idea que debe quedar clara

El tema central es cómo almacenar, organizar y recuperar vectores. El fútbol permite observar ese mecanismo y RAG muestra una posible aplicación. No hace falta generar texto para que exista una búsqueda vectorial.

## 2
### Base teórica para preparar esta diapositiva

Recuperar información consiste en seleccionar, entre muchos registros, los que pueden servir para una necesidad. Hay consultas exactas, como buscar un identificador o exigir edad menor o igual a 25; consultas léxicas, que utilizan términos del texto; y consultas por similitud, que comparan representaciones. Son operaciones distintas y pueden coexistir. [L1]

Una búsqueda literal por “automóvil” puede omitir un documento que sólo contenga “coche”. Es un desajuste de vocabulario. Los sistemas léxicos pueden incorporar sinónimos, normalización e índices invertidos. Por eso no debe afirmarse que toda búsqueda tradicional se limita a comparar cadenas idénticas. La búsqueda semántica intenta relacionar formulaciones por medio de una representación aprendida, con posibles errores. [L1]

En nuestro caso, “delantero con regate y desborde” mezcla una intención descriptiva con requisitos que podrían expresarse en columnas. “Parecido a mi pedido” admite un grado; “tiene posición ST” es una condición que se cumple o no. El texto de la consulta no crea por sí solo todas las restricciones del usuario. [L2]

### Ejemplo para explicarlo con palabras propias

“Dos jugadores pueden tener perfiles parecidos, pero uno juega en una posición que no quiero. La similitud ayuda a encontrar candidatos; el filtro hace cumplir esa condición.”

### Error que conviene evitar

Que una búsqueda devuelva resultados cuando otra devuelve cero no demuestra que los resultados sean relevantes. Hay que examinar qué se recuperó y con qué criterio.

## 3
### Base teórica para preparar esta diapositiva

Un registro vectorial puede entenderse como una unidad con cuatro partes. El identificador distingue el registro y permite asociarlo con su origen. El vector interviene en el cálculo de semejanza. Los metadatos contienen campos útiles para condiciones exactas, como edad y posición. El documento o referencia conserva la información que una persona puede interpretar y verificar. La disposición física concreta depende del gestor. [L1]

Una colección agrupa registros que se consultan juntos con una configuración compatible. Para comparar sus vectores deben coincidir el espacio de representación y la dimensión esperada. Tener 384 números no basta si fueron producidos por modelos incompatibles. [L1, L2]

Una base relacional organiza datos mediante tablas y relaciones; permite consultas, restricciones de integridad y transacciones según el gestor. Incorporar búsqueda vectorial no elimina esas necesidades. PostgreSQL puede almacenar y consultar vectores mediante pgvector: “relacional” y “vectorial” no son categorías necesariamente excluyentes. [T5]

Un índice es una estructura de acceso; no equivale al sistema gestor completo. La persistencia, las copias de seguridad, los permisos y la concurrencia son responsabilidades adicionales cuya implementación debe verificarse. [L1]

### Ejemplo para explicarlo con palabras propias

“El ID nos dice qué ficha es; el vector ayuda a encontrarla; la edad permite filtrarla; el documento permite leer por qué apareció. Guardar sólo el vector nos dejaría sin evidencia comprensible para el usuario.”

## 4
### Base teórica para preparar esta diapositiva

Un vector es una lista ordenada de componentes: x = (x₁, x₂, …, xD). D es la dimensión. Un punto 2D tiene dos coordenadas; un vector de 384 dimensiones tiene 384 componentes, aunque no podamos dibujar ese espacio completo. La posición de cada componente importa para las operaciones. [L1]

Un embedding es una representación del contenido producida por un modelo. En este proyecto, la función de embeddings utiliza all-MiniLM-L6-v2 y entrega vectores densos de 384 dimensiones. “Denso” indica que las componentes se almacenan como una representación compacta con muchos valores potencialmente distintos de cero. Un vector disperso, en cambio, puede tener muchísimas posiciones y pocas activas. [T1, L1]

Las dimensiones de un embedding aprendido no suelen tener nombres individuales como “regate” o “velocidad”. La información se distribuye entre componentes. No podemos leer un número aislado y atribuirle una habilidad futbolística. Tampoco se garantiza que el modelo interprete correctamente toda frase, negación o magnitud numérica. [L1, L2]

Un texto se procesa mediante el modelo y se resume en una representación de longitud fija. La ficha completa puede conservarse por separado. Embedding y documento cumplen funciones diferentes; el vector no es una compresión reversible que permita reconstruir exactamente el texto. [L1]

### Ejemplo y precaución

El vector inventado (velocidad, regate) sería interpretable porque nosotros definimos sus ejes. Las dos coordenadas del laboratorio son igualmente didácticas: no son las dos primeras dimensiones de MiniLM ni una proyección validada de los jugadores.

Mantener compatible el procesamiento de fichas y consultas es indispensable. Cambiar de modelo exige preparar una colección compatible y volver a generar representaciones cuando corresponda.

## 5
### Base teórica para preparar esta diapositiva

La similitud coseno mide orientación entre dos vectores no nulos. Se calcula dividiendo el producto interno por el producto de sus longitudes. En la notación siguiente, Σ significa sumar sobre todas las componentes y √ significa raíz cuadrada. [T2]

FÓRMULA: cos(x, y) = Σ(xᵢ · yᵢ) / (√Σxᵢ² · √Σyᵢ²)

La norma ||x|| es la longitud √Σxᵢ². Normalizar consiste en dividir cada componente por esa longitud; así se obtiene un vector unitario. Para vectores unitarios, el coseno coincide con el producto interno. Multiplicar un vector por un número positivo cambia su longitud, pero no su orientación. [T2]

### Cálculo resuelto para practicar

Tomemos x = (1, 0) e y = (3, 4). El producto interno es 1 × 3 + 0 × 4 = 3. Las normas son 1 y 5. Entonces cos(x, y) = 3 / 5 = 0,6. Con la convención del proyecto, distancia coseno = 1 - 0,6 = 0,4. El ejemplo es geométrico: esos números no son valoraciones de jugadores.

Con vectores unitarios, 0° produce similitud 1 y distancia 0; 90° produce 0 y 1; 180° produce -1 y 2. Un vector nulo impide calcular coseno porque su norma es cero. Por eso el laboratorio rechaza la consulta (0, 0).

### Comparación con otras medidas

La distancia euclídea es √Σ(xᵢ - yᵢ)²: mide separación geométrica y depende de las longitudes. El producto interno sin normalizar también depende de magnitudes. Para vectores unitarios, la distancia euclídea al cuadrado es 2 × (1 - coseno), por lo que produce el mismo orden que coseno. Elegir una medida debe ser coherente con la representación. [L1]

### Precisión para responder preguntas

El intervalo general del coseno es [-1, 1]. Un valor negativo indica orientación opuesta, no necesariamente significado lingüístico contrario. Un valor 0,9 no significa 90 % de acierto. Aunque se la llama “distancia coseno”, 1 - coseno no cumple en general todas las propiedades de una métrica matemática, como la desigualdad triangular. [L1]

## 6
### Base teórica para preparar esta diapositiva

La búsqueda de vecinos próximos ordena vectores por cercanía a una consulta. En una búsqueda exacta, el resultado corresponde a los k mejores según la medida y el conjunto elegible. “Exacta” se refiere a ese problema geométrico; no certifica relevancia humana. ANN significa Approximate Nearest Neighbors, o vecinos próximos aproximados. Puede omitir alguno de los vecinos que encontraría la búsqueda exacta. [L1, T3]

Para un escaneo exhaustivo con N vectores de D componentes, calcular todas las distancias requiere trabajo proporcional a N × D. Seleccionar los mejores agrega un costo que depende del algoritmo usado. Un índice aproximado busca evitar muchas comparaciones, pero consume memoria y tiene un costo de construcción. No se puede prometer que siempre sea más rápido: influyen N, D, filtros, hardware y configuración. [L1]

### Ejemplo resuelto

Si las distancias de cuatro candidatos son A=0,10; B=0,40; C=0,20 y D=0,80, el top-2 exacto es A y C. Si ANN devuelve A y B, recuperó uno de los dos vecinos exactos: su recall de vecinos es 1/2 = 0,50. Para saber si A y C son útiles para una persona se necesita otra evaluación, con juicios de relevancia.

### Cómo explicarlo durante la exposición

“La búsqueda exacta nos sirve como referencia. La aproximada intenta recuperar casi los mismos vecinos con menos trabajo. La decisión consiste en aceptar una posible pérdida de cobertura a cambio de recursos o tiempo.”

### Error que conviene evitar

k es la cantidad solicitada, no un umbral de calidad. Pedir cinco puede devolver cinco perfiles poco útiles si existen candidatos y no hay una regla adicional de abstención. La aplicación no implementa un umbral semántico que garantice una respuesta pertinente. [L2]

## 7
### Base teórica para preparar esta diapositiva

HNSW significa Hierarchical Navigable Small World. Es un índice basado en un grafo de proximidad con varias capas. Los nodos representan vectores y las aristas permiten visitar otros nodos. La capa inferior contiene todos los elementos; las superiores contienen subconjuntos cada vez menores. Durante la construcción se asignan niveles de manera aleatoria, con menor probabilidad de alcanzar niveles altos. [T3]

La búsqueda comienza por un punto de entrada en una capa superior, se desplaza hacia nodos más cercanos a la consulta y desciende conservando una buena ubicación. En la capa inferior explora candidatos para seleccionar vecinos. Este diseño facilita desplazamientos amplios antes de refinar la búsqueda. Las conexiones representan proximidad; no son relaciones como “pertenece al mismo club”. [T3]

### Parámetros para responder preguntas

M controla la conectividad del grafo. Mayor conectividad suele requerir más memoria. ef_construction controla la amplitud de búsqueda al construirlo: aumentar ese trabajo puede mejorar la estructura y encarecer la ingesta. ef, también llamado ef_search en algunas interfaces, controla la amplitud durante una consulta: ampliarla suele mejorar la recuperación de vecinos a costa de tiempo. No es lo mismo que k, que limita los resultados pedidos. Los nombres y restricciones concretos dependen de la implementación. [T4, T6]

### Qué muestra nuestra animación

El laboratorio tiene un recorrido fijo por A, D, F y E, con descensos de capa. Sirve para señalar entrada, exploración y refinamiento. Su distancia es euclídea didáctica y su secuencia es determinista. No ejecuta HNSW real ni permite deducir su recall. El índice de Chroma no se inspecciona mediante ese gráfico. [L2]

### Error que conviene evitar

Encontrar un nodo donde ya no mejora el paso visible no demuestra haber encontrado el vecino global. La búsqueda real maneja conjuntos de candidatos y visitados; la animación simplifica esas operaciones. No atribuir tiempos ni garantía de exactitud al dibujo.

## 8
### Base teórica para preparar esta diapositiva

Un filtro de metadatos expresa una condición sobre campos almacenados. Puede combinar igualdad, rangos y condiciones lógicas. Por ejemplo: entidad = player Y plays_ST = verdadero Y edad ≤ 25. El filtro determina elegibilidad; la medida determina cercanía; k indica el máximo de resultados solicitado. Chroma permite expresar condiciones de metadatos con operadores de comparación y combinaciones lógicas. [T8, L2]

### Ejemplo resuelto

Supongamos cuatro perfiles: A es ST de 22 años y distancia 0,30; B es CM de 23 y distancia 0,10; C es ST de 29 y distancia 0,20; D es ST de 24 y distancia 0,40. Con ST, edad máxima 25 y k=3, sólo A y D son elegibles. Se devuelven esos dos; B no puede entrar aunque sea el más cercano y no se inventa un tercero.

### Orden lógico y ejecución física

“Filtrar y elegir vecinos” describe el resultado buscado. El motor puede combinar filtros e índice de distintas formas. Filtrar después de pedir pocos vecinos globales puede dejar menos resultados y omitir elegibles que estaban más abajo. Por eso no debe inferirse la estrategia interna sólo observando la interfaz. En el laboratorio se filtra el conjunto y después se calculan todas las distancias exactamente. [L1, L2]

### Distinción que deben poder defender

Combinar vectores con filtros no equivale por sí solo a búsqueda híbrida léxica y densa. Esa búsqueda combinaría señales de recuperación textual y vectorial. Además, escribir “joven” en la frase no impone una edad máxima en esta aplicación: hay que activar el control correspondiente. [L1, L2]

## 9
### Base teórica para preparar esta diapositiva

Persistencia significa conservar los registros para reutilizarlos después de cerrar el proceso. No equivale a disponer de una copia de seguridad ni a tolerar cualquier fallo. Una administración completa debe contemplar altas, consultas, modificaciones, bajas, copias y restauración. [L1]

Si cambia sólo un metadato que no interviene en el texto representado, puede bastar con actualizar ese campo. Si cambia el contenido que se vectoriza, hace falta regenerar su embedding y actualizar el registro. Si cambia el modelo o el modo de construir perfiles, se debe revisar la compatibilidad de toda la colección. En nuestro código, una huella del corpus, una versión y el conteo permiten detectar diferencias y pedir reconstrucción; no hay sincronización automática incremental de cualquier CSV modificado. [L2]

### Memoria: cálculo que conviene saber explicar

Para N vectores de D componentes float32, los componentes ocupan aproximadamente N × D × 4 bytes. Con 20.421 × 384 × 4 = 31.366.656 bytes: unos 31,37 MB decimales, o 29,91 MiB. Esto no mide el consumo total: faltan grafo, documentos, metadatos, estructuras auxiliares y modelo. [L1, L2]

### Escala y administración

Escalar verticalmente es agregar recursos a una máquina. Particionar reparte datos entre unidades; replicar mantiene copias. Una copia no reemplaza un backup histórico: una eliminación puede propagarse. Cuantizar reduce la precisión usada para representar componentes y puede ahorrar espacio, a cambio de cambios en la aproximación. Son decisiones generales, no funciones demostradas por nuestro prototipo local. [L1]

Hay que controlar quién consulta, quién modifica y qué registros puede ver cada usuario. Los filtros de la demostración expresan criterios deportivos; no implementan un sistema completo de autorización.

## 10
### Base teórica para preparar esta diapositiva

La ingesta prepara información para consultas posteriores. Su secuencia conceptual es: leer fuentes, validar y limpiar, elegir unidades de contenido, generar embeddings y guardar registros con trazabilidad. Una unidad demasiado extensa puede mezclar temas; una demasiado pequeña puede perder contexto. En documentos largos suele emplearse fragmentación o chunking. No existe un tamaño universal correcto. [L1]

En nuestro corpus principal se construye un perfil por entidad del snapshot. El texto destinado al embedding describe características y omite nombres y URLs; el documento mostrado conserva identidad y fuente. Esta decisión separa representación de evidencia. No corresponde explicar la demo como si extrajera páginas de un reglamento PDF. [L2]

La consulta tiene otra secuencia: validar el pedido, generar un vector compatible, aplicar condiciones, recuperar candidatos y presentar los resultados. Puede añadirse reordenamiento y, después, generación. Persistir el índice evita volver a vectorizar todo el corpus en cada consulta. [L1, L2]

### Ejemplo para explicar la arquitectura

“La ingesta se parece a preparar el catálogo de una biblioteca. Consultar es usar ese catálogo. No volvemos a catalogar todos los libros cada vez que alguien pide uno.” La analogía explica la separación de tareas; no implica que el índice sea un catálogo alfabético.

### Rendimiento y trazabilidad

Separar tiempos permite ubicar un cuello de botella. Medir collection.query no mide únicamente saltos del grafo: también intervienen filtros y lectura de resultados. Hay que registrar modelo, configuración, datos y condiciones del ensayo. Para verificar una respuesta, conservar ID, fuente y fecha junto a la ficha. [L2]

## 11
### Base teórica para preparar esta diapositiva

Una biblioteca de vecinos se ocupa principalmente de indexar y buscar representaciones. Un gestor agrega operaciones y administración de datos. Una plataforma completa puede sumar servicios de despliegue y operación. Antes de comparar productos hay que identificar qué responsabilidades cubre cada uno. [L1]

En esta solución, Chroma administra la colección; MiniLM produce los embeddings; Streamlit muestra la interfaz y Python coordina el proceso. pgvector incorpora búsqueda de similitud a PostgreSQL y admite búsqueda exacta e índices aproximados. Su existencia permite explicar la complementariedad con datos relacionales. Qdrant es otra alternativa tratada en el informe; no fue el motor probado en esta demo. [T5, L1, L2]

### Cómo conectar tecnología y necesidad

Para elegir una solución hay que conocer cantidad de vectores, dimensión, crecimiento, frecuencia de actualización, condiciones de consulta y requisitos de operación. Después se compara rendimiento con la misma carga y calidad requerida. Una lista de funcionalidades no reemplaza ese ensayo. [L1]

La recuperación por similitud puede usarse para localizar documentos, encontrar productos parecidos, agrupar contenido o proponer candidatos para recomendación. Con textos, imágenes o audio se necesitan representaciones adecuadas a cada tarea. Recomendación implica además criterios de negocio, disponibilidad y evaluación: cercanía sola no resuelve todo el problema. [L1]

### Qué decir sobre los casos del informe

Usar los casos empresariales como ejemplos de decisiones de arquitectura y evaluación. No presentar sus resultados como mediciones del buscador. En especial, una biblioteca de vecinos y una solución de respuestas con evidencia no son el mismo tipo de componente. Las fuentes particulares de esos casos permanecen en las notas originales. [L1]

## 12
### Base teórica para preparar esta diapositiva

RAG significa Retrieval-Augmented Generation: generación aumentada mediante recuperación. La idea es proporcionar al generador información externa recuperada para la consulta. Se separa el conocimiento almacenado en parámetros del modelo del material consultable que se aporta como contexto. El artículo original combina componentes de recuperación y generación; las aplicaciones actuales pueden organizarlos de diferentes maneras. [T7]

En el esquema de nuestra aplicación, primero se recuperan perfiles, después se prepara el contexto y sólo entonces un generador opcional redacta una respuesta. La base vectorial interviene en la recuperación; no redacta. El LLM no recibe toda la colección por el hecho de estar conectado al sistema. La recuperación también podría ser léxica o combinar varias señales. [L1, L2]

### Ejemplo para explicarlo con palabras propias

“Si queremos un informe comparativo, buscamos las fichas y se las entregamos al modelo junto con la pregunta. La respuesta debería apoyarse en esas fichas. Si buscamos sin generador, podemos mostrar directamente la evidencia y explicar nosotros la comparación.”

### Límites y administración

Una respuesta puede fallar porque se recuperaron documentos equivocados, porque el contexto quedó incompleto o porque el generador interpretó mal la evidencia. Agregar recuperación no garantiza eliminar invenciones. Deben evaluarse por separado los resultados recuperados y la fidelidad de lo redactado. Un texto recuperado es una fuente de datos; no debe adquirir autoridad para cambiar las instrucciones del sistema. [L1]

Si se envía el contexto a una API remota, salen del equipo los datos incluidos en esa solicitud. Embeddings locales no garantizan procesamiento completamente local. Con generador none, esta demostración comprueba recuperación y reordenamiento sin generar un reporte LLM. [L2]

## 13
### Base teórica para preparar esta diapositiva

El caso práctico tiene tres representaciones que no deben confundirse: la ficha legible del jugador, su embedding semántico de 384 componentes y los atributos numéricos de los metadatos. El vector no es una lista de las 384 mejores estadísticas ni se usa como sustituto de las valoraciones originales. [L2]

La colección contiene 20.421 perfiles: 18.350 jugadores, 702 equipos y 1.369 técnicos. Son registros del snapshot FIFA/EA FC 24, actualización 2, con fecha 22/09/2023. La consulta de la demo filtra jugadores que admiten ST y excluye arqueros; el conjunto resultante tiene 3.194 registros en la evidencia guardada. No se está buscando únicamente entre las cinco personas mostradas. [L2, L3]

### Por qué se agrega reordenamiento

Representar una frase por similitud no garantiza comparar correctamente números como regate 92 y regate 41. El código reconoce términos de atributos y, si hay datos disponibles, ordena el pool por el promedio de sus percentiles. Un percentil ubica un valor con respecto al grupo de referencia; no es una probabilidad de rendimiento deportivo. [L2]

Los empates se resuelven con valoraciones originales y luego similitud. Cuando no se reconoce un atributo utilizable, se conserva el orden vectorial. El reordenador trabaja sólo con candidatos recuperados; no puede rescatar un jugador ausente del pool. El límite de recuperación es 5.000. [L2]

### Idea que debe quedar clara

Esta aplicación permite explicar la colaboración entre representación semántica, restricciones exactas y ordenamiento numérico. Si la necesidad fuera únicamente ordenar todos los delanteros por regate, una consulta estructurada podría resolverla sin embeddings. [L1, L2]

## 14
### Base teórica para interpretar la demostración

Cada control responde a una pregunta diferente: la posición determina elegibilidad; la consulta orienta la recuperación y permite reconocer atributos; k fija cuántos se muestran; el reordenamiento decide el criterio final entre candidatos; none desactiva la generación. Nombrarlos antes de ejecutar evita atribuir todo a una supuesta decisión de la inteligencia artificial. [L2]

### Lectura de los resultados registrados

En la consulta guardada, Mbappé tiene regate 92 y distancia aproximada 0,5458; Griezmann tiene regate 88 y distancia 0,4895. Por distancia coseno, Griezmann está más cerca. Por el criterio final de regate, Mbappé queda primero. No hay contradicción: se están utilizando dos órdenes distintos. [L3]

Score = 1 - distancia permite expresar similitud en lugar de distancia. No convierte la medida en confianza. “Ajuste atributos” resume percentiles y “valoración media” resume los valores originales usados en el desempate. Ninguno representa la probabilidad de que un fichaje sea exitoso. [L2]

### Cobertura y límites de lo demostrado

En esta evidencia, el pool recuperó los 3.194 elegibles: el orden por atributos pudo considerar a todo ese subconjunto. En una consulta más amplia, el límite de 5.000 puede dejar candidatos afuera. Por eso no se promete que todo ranking final examine siempre el corpus entero. [L3]

Desactivar reordenamiento muestra qué cambia al usar sólo distancia. Las diferencias de orden sirven para enseñar criterios; no prueban por sí solas que un embedding sea bueno o malo para toda consulta. Tampoco una medición aislada permite comparar tecnologías. La búsqueda LIKE de la aplicación es un escaneo léxico en pandas, no un experimento contra un servidor SQL. [L1, L2]

### Frase útil al cerrar la demo

“Pudimos seguir el camino desde la consulta hasta la ficha original. Eso hace verificable el resultado. La interpretación deportiva depende de la calidad y vigencia de la fuente.”

## 15
### Base teórica para construir la conclusión

La utilidad de una base vectorial depende de varias decisiones: qué contenido se representa, con qué modelo, cómo se mide cercanía, qué índice se utiliza, qué condiciones se aplican y cómo se administra la colección. Un fallo en una etapa puede limitar el sistema aunque las otras funcionen correctamente. [L1]

### Cómo evaluar la recuperación

Con juicios de relevancia, Precision@k indica qué proporción de los primeros k resultados es pertinente. Si cuatro de cinco son relevantes, P@5 = 4/5 = 0,80. Recall@k indica qué proporción de todos los relevantes conocidos se recuperó: si existen diez relevantes y aparecen cuatro, R@5 = 4/10 = 0,40. MRR promedia el inverso de la posición del primer resultado relevante en cada consulta. Si aparece primero, aporta 1; si aparece tercero, 1/3. [L1]

El recall de vecinos ANN se compara contra un top-k exacto del mismo espacio. Es distinto del recall de relevancia humana. Para medir rendimiento se necesitan consultas representativas, repeticiones, condiciones comparables y registro de latencia y recursos. Si se usa generación, se agrega evaluación de respaldo factual y correspondencia con las fuentes. [L1]

### Qué permite concluir nuestro trabajo

La evidencia demuestra una implementación funcional de recuperación, filtros y reordenamiento sobre un corpus identificado. Las pruebas de software verifican comportamientos, no equivalen a una evaluación exhaustiva de pertinencia. Las valoraciones históricas de un videojuego tampoco validan una recomendación de scouting actual. [L2, L3]

### Cierre oral sugerido

“Las bases vectoriales incorporan consultas por cercanía a los sistemas de información. Su valor depende de la representación, de la administración de los datos y de una evaluación adecuada. Nuestro buscador muestra cómo integrarlas con filtros y atributos exactos, y permite incorporar generación como una etapa opcional.”
