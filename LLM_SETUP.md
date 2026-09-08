# Configurar la API del LLM

## OpenAI, paso a paso

1. Obtener una clave desde [API keys](https://platform.openai.com/api-keys).
2. En la carpeta del proyecto, copiar `.env.example` a `.env`. En esta entrega local
   ya se deja creado `.env` vacío, listo para completar; no sobrescribirlo si ya tiene una clave.
3. Abrir `.env` en un editor y completar:

```dotenv
OPENAI_API_KEY=tu_clave_real
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

4. Guardar y abrir la aplicación. En la barra lateral elegir **Generador → openai**
   y pulsar **Buscar evidencia FIFA**. `none` sólo recupera evidencia, no llama al LLM.
   En el modo sintético la opción se llama **OpenAI / compatible**.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

La clave no va en `app.py`, en el texto de búsqueda ni en GitHub. `.env` está
excluido del repositorio. La configuración se relee en cada búsqueda; si la aplicación
estaba abierta durante una actualización del código, pulsar **Rerun** o recargarla.
Las variables definidas en la terminal tienen prioridad sobre `.env`.

En consola:

```powershell
.\.venv\Scripts\python.exe main.py --dataset fifa --provider openai --query "Lateral que avanza por dentro" --benchmark
```

La recuperación y los embeddings son locales. El proveedor recibe la consulta y
los fragmentos recuperados para redactar el reporte. Referencia:
[documentación oficial de OpenAI](https://developers.openai.com/api/docs/quickstart).

## OpenRouter

OpenRouter expone el mismo protocolo que OpenAI, así que se usa con el generador
**openai** cambiando dos variables. Es la configuración que trae esta entrega:

```dotenv
OPENAI_API_KEY=sk-or-v1-tu_clave
OPENAI_MODEL=nvidia/nemotron-3-super-120b-a12b:free
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

**Conviene fijar un modelo de chat concreto y no un router.** `openrouter/free`
existe, pero elige cualquier modelo gratuito disponible: en una prueba de este
proyecto le tocó `nemotron-3.5-content-safety`, un clasificador de moderación, que
al ver nombres de jugadores en el contexto respondió `User Safety: unsafe /
Safety Categories: PII/Privacy` en lugar de redactar el informe. La llamada se
completa con éxito, así que el fallo no se distingue de un reporte válido salvo
leyéndolo.

Los modelos `:free` tienen límites de tasa compartidos y a veces devuelven 429 o un
error del proveedor. En esos casos la aplicación conserva la búsqueda vectorial y
muestra el aviso. La lista vigente está en
[openrouter.ai/models](https://openrouter.ai/models); con crédito cargado,
`openrouter/auto` elige un modelo de pago adecuado a cada consulta.

## Ollama o servidor compatible

Para Ollama, iniciar su servidor, descargar `llama3.2:3b` con `ollama pull llama3.2:3b`
y seleccionar **ollama**. No necesita una clave de OpenAI. Se usan `OLLAMA_MODEL`
y `OLLAMA_BASE_URL` de `.env`, por defecto `http://localhost:11434/v1`.

Para otro servidor compatible, elegir **openai** y configurar `OPENAI_BASE_URL`,
`OPENAI_MODEL` y la clave de ese proveedor. La URL debe apuntar al endpoint compatible
(habitualmente termina en `/v1`).

## Si no genera el reporte

- **Falta OPENAI_API_KEY:** verificar que el archivo se llame `.env`, no `.env.txt`,
  y esté junto a `app.py`; completar la clave y guardar.
- **401:** revisar la clave y que corresponda al proveedor configurado.
- **429:** revisar la cuota y límites de la cuenta del proveedor.
- **Modelo no disponible:** usar un modelo habilitado para esa cuenta.
- **Responde algo que no es un informe** (por ejemplo `User Safety: unsafe`):
  `OPENAI_MODEL` apunta a un router o a un clasificador, no a un modelo de chat.
  Fijar un slug concreto.
- **Ollama no conecta:** comprobar que el servidor esté iniciado y el modelo descargado.

Ante un error del LLM se conserva la recuperación vectorial y se muestra un aviso.
Las pruebas automatizadas usan un transporte HTTP simulado; no validan tu clave ni
consumen crédito. Sólo una consulta con el generador activado comprueba tu acceso real.
