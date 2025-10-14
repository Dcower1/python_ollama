import subprocess
import re
import streamlit as st

# --- CONFIGURACIÓN BASE ---
SQL_INSTANCE = r"localhost\SQLEXPRESS"
DATABASE     = "AdventureWorksLT2022"
OLLAMA_MODEL = "llama3-sql"

# --- FUNCIONES ---
def run_sqlcmd(query: str):
    """Ejecuta una consulta SQL en SQL Server y devuelve el resultado como texto."""
    cmd = ["sqlcmd", "-S", SQL_INSTANCE, "-d", DATABASE, "-W", "-s", ",", "-Q", query]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return f"⚠️ Error SQL:\n{res.stderr}"
    return res.stdout.strip()

def ask_ollama(model: str, prompt: str):
    """Ejecuta un prompt con Ollama local usando subprocess (sin API HTTP)."""
    cmd = ["ollama", "run", model, prompt]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Asistente SQL con Ollama", layout="centered")
st.title("💬 Asistente SQL con Llama3 (local)")
st.caption("Consulta en lenguaje natural la base de datos AdventureWorksLT2022 usando Ollama y SQL Server")


if "chat" not in st.session_state:
    st.session_state.chat = []


for msg in st.session_state.chat:
    st.chat_message(msg["role"]).markdown(msg["text"])

# Entrada del usuario
if prompt := st.chat_input("Haz una pregunta en español sobre la base de datos..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.chat.append({"role": "user", "text": prompt})

    with st.spinner("🧠 Generando consulta SQL con Llama3..."):
        conversion_prompt =f""" Eres un asistente de análisis de datos que entiende español y trabaja con SQL Server. 
        Convierte las siguientes preguntas en español a consultas T-SQL válidas para la base AdventureWorksLT2022. 
        Responde únicamente con el código SQL, sin explicaciones, sin texto extra, ni frases como "La respuesta sería" o "Aquí tienes". 
        Ejemplos: - "¿Cuáles son los tres productos más vendidos?" → 
        SELECT TOP 3 p.Name, SUM(sod.LineTotal) AS TotalSales FROM SalesLT.SalesOrderDetail sod 
        JOIN SalesLT.Product p ON sod.ProductID = p.ProductID GROUP BY p.Name ORDER BY TotalSales DESC; 

        - "¿Cuánto se vendió en total?" → 
        SELECT SUM(LineTotal) AS TotalSales FROM SalesLT.SalesOrderDetail; 
        - "¿Qué producto tuvo más ventas?" → 
        SELECT TOP 1 p.Name, SUM(sod.LineTotal) AS TotalSales FROM SalesLT.SalesOrderDetail sod 
        JOIN SalesLT.Product p ON sod.ProductID = p.ProductID GROUP BY p.Name ORDER BY TotalSales DESC; 

        Ahora convierte la siguiente pregunta a SQL: {prompt} """
        sql_query = ask_ollama(OLLAMA_MODEL, conversion_prompt)
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        if "SELECT" in sql_query.upper():
            sql_query = sql_query[sql_query.upper().index("SELECT"):]
        sql_query = re.sub(r"SUM\s+([a-zA-Z0-9_.]+)", r"SUM(\1)", sql_query)

    st.chat_message("assistant").markdown(f"🧩 **Consulta SQL generada:**\n```sql\n{sql_query}\n```")

    # --- Paso 2: Ejecutar SQL en la base ---
    with st.spinner("⚙️ Ejecutando consulta en SQL Server..."):
        resultado = run_sqlcmd(sql_query)

    st.chat_message("assistant").markdown(f"📊 **Resultado SQL:**\n```\n{resultado}\n```")

    # --- Paso 3: Interpretar resultados ---
    with st.spinner("💬 Interpretando resultados con Ollama..."):
        resumen_prompt = f"""
Explica en español, de forma breve y clara, qué muestran estos resultados obtenidos desde SQL Server:

Pregunta original:
{prompt}

Resultados:
{resultado}
"""
        respuesta = ask_ollama(OLLAMA_MODEL, resumen_prompt)

    st.chat_message("assistant").markdown(f" **Interpretación:** {respuesta}")
    st.session_state.chat.append({"role": "assistant", "text": respuesta})