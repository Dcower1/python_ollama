import subprocess
import re
import streamlit as st

# --- CONFIGURACIÓN BASE ---
SQL_INSTANCE = r"localhost\SQLEXPRESS"
DATABASE     = "AdventureWorksLT2022"
OLLAMA_MODEL = "llama3-sql"

# --- TABLAS VÁLIDAS ---
VALID_TABLES = [
    "SalesLT.Customer", "SalesLT.SalesOrderDetail", "SalesLT.SalesOrderHeader",
    "SalesLT.Product", "SalesLT.ProductCategory", "SalesLT.ProductModel",
    "SalesLT.Address", "SalesLT.CustomerAddress"
]

# --- FUNCIONES ---
def run_sqlcmd(query: str):
    cmd = ["sqlcmd", "-S", SQL_INSTANCE, "-d", DATABASE, "-W", "-s", ",", "-Q", query]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if res.returncode != 0:
        return f"⚠️ Error SQL:\n{res.stderr}"
    return res.stdout.strip()

def ask_ollama(model: str, prompt: str):
    cmd = ["ollama", "run", model, prompt]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.stdout.strip()

def is_related_to_database(sql_query: str) -> bool:
    upper_query = sql_query.upper()
    return any(tbl.upper() in upper_query for tbl in VALID_TABLES)

def ejecutar_sql_seguro(sql_query: str, producto_buscar: str = None):
    """Ejecuta SQL y devuelve resultado o mensaje genérico si no hay coincidencias."""
    resultado = run_sqlcmd(sql_query)

    # Si no hay filas afectadas o la tabla está vacía
    if not resultado or "rows affected" not in resultado.lower():
        return f"⚠️ No se encontraron resultados para la consulta."

    # Separar líneas de resultado
    lineas = [linea.strip() for linea in resultado.splitlines() if linea.strip()]
    if len(lineas) <= 2:  # solo cabecera o vacío
        return f"⚠️ No se encontraron resultados para la consulta."

    # Si se especifica un producto, chequear coincidencia
    if producto_buscar:
        encontrado = any(producto_buscar.lower() in linea.lower() for linea in lineas[2:])
        if not encontrado:
            return f"⚠️ No se encontró ningún producto que coincida con '{producto_buscar}'."

    return resultado

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Asistente SQL con Ollama", layout="centered")
st.title("💬 Asistente SQL con Llama3 (local)")
st.caption("Consulta en lenguaje natural la base de datos AdventureWorksLT2022 usando Ollama y SQL Server")

if "chat" not in st.session_state:
    st.session_state.chat = []

# Mostrar historial
for msg in st.session_state.chat:
    st.chat_message(msg["role"]).markdown(msg["text"])

# Entrada del usuario
if prompt := st.chat_input("Haz una pregunta en español sobre la base de datos o la IA..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.chat.append({"role": "user", "text": prompt})

    # --- PREGUNTAS SOBRE LA IA ---
    if "ia" in prompt.lower() or "inteligencia artificial" in prompt.lower():
        respuesta = "🤖 Esta IA es un asistente diseñado para generar consultas T-SQL y responder preguntas sobre la base AdventureWorksLT2022. No inventa resultados y no modifica datos."
        st.chat_message("assistant").markdown(respuesta)
        st.session_state.chat.append({"role": "assistant", "text": respuesta})
    else:
        # --- GENERAR SQL ---
        with st.spinner("🧠 Generando consulta SQL con Llama3..."):
            conversion_prompt = f"""
Eres un asistente de análisis de datos que entiende español y trabaja con SQL Server. 
Convierte la pregunta siguiente a una consulta T-SQL válida para la base AdventureWorksLT2022. 
Responde únicamente con el código SQL, sin explicaciones ni texto extra. Usa solo tablas y columnas existentes en SalesLT.

Pregunta:
{prompt}
"""
            sql_query = ask_ollama(OLLAMA_MODEL, conversion_prompt)
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            if "SELECT" in sql_query.upper():
                sql_query = sql_query[sql_query.upper().index("SELECT"):]
            sql_query = re.sub(r"SUM\s+([a-zA-Z0-9_.]+)", r"SUM(\1)", sql_query)

        st.chat_message("assistant").markdown(f"🧩 **Consulta SQL generada:**\n```sql\n{sql_query}\n```")

        # --- VALIDAR RELEVANCIA ---
        if not is_related_to_database(sql_query):
            msg = "⚠️ La consulta generada no parece estar relacionada con la base de datos AdventureWorksLT2022."
            st.chat_message("assistant").markdown(msg)
            st.session_state.chat.append({"role": "assistant", "text": msg})
        else:
            # --- EJECUTAR SQL DE FORMA SEGURA ---
            producto_buscar = None
            # Detectar palabras clave de productos (ejemplo simple)
            for palabra in ["hamburguesa", "pizza", "gaseosa"]:
                if palabra in prompt.lower():
                    producto_buscar = palabra
                    break

            with st.spinner("⚙️ Ejecutando consulta en SQL Server..."):
                resultado = ejecutar_sql_seguro(sql_query, producto_buscar=producto_buscar)

            st.chat_message("assistant").markdown(f"📊 **Resultado SQL:**\n```\n{resultado}\n```")

            # --- INTERPRETAR RESULTADOS SOLO SI HAY DATOS ---
            if "⚠️" not in resultado:
                with st.spinner("💬 Interpretando resultados con Ollama..."):
                    resumen_prompt = f"""
Explica en español, de forma breve y clara, qué muestran estos resultados obtenidos desde SQL Server:

Pregunta original:
{prompt}

Resultados:
{resultado}
"""
                    respuesta = ask_ollama(OLLAMA_MODEL, resumen_prompt)
                st.chat_message("assistant").markdown(f"**Interpretación:** {respuesta}")
                st.session_state.chat.append({"role": "assistant", "text": respuesta})
