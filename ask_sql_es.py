import subprocess, json, requests, re

SQL_INSTANCE = r"localhost\SQLEXPRESS"
DATABASE     = "AdventureWorksLT2022"
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:latest"   

def run_sqlcmd(query: str):
    cmd = ["sqlcmd", "-S", SQL_INSTANCE, "-d", DATABASE, "-W", "-s", ",", "-Q", query]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error SQL:\n{res.stderr}")
    return res.stdout.strip()

def ask_ollama(model: str, prompt: str):
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    return r.json().get("response", "")

if __name__ == "__main__":
    pregunta = input("❓ Escribe tu pregunta en español: ")

    
    prompt = f"""
Eres un asistente de análisis de datos que entiende español y trabaja con SQL Server.
Convierte las siguientes preguntas en español a consultas T-SQL válidas para la base AdventureWorksLT2022.

Responde únicamente con el código SQL, sin explicaciones, sin texto extra, ni frases como "La respuesta sería" o "Aquí tienes".
Ejemplos:
- "¿Cuáles son los tres productos más vendidos?" →
  SELECT TOP 3 p.Name, SUM(sod.LineTotal) AS TotalSales
  FROM SalesLT.SalesOrderDetail sod
  JOIN SalesLT.Product p ON sod.ProductID = p.ProductID
  GROUP BY p.Name
  ORDER BY TotalSales DESC;

- "¿Cuánto se vendió en total?" →
  SELECT SUM(LineTotal) AS TotalSales FROM SalesLT.SalesOrderDetail;

- "¿Qué producto tuvo más ventas?" →
  SELECT TOP 1 p.Name, SUM(sod.LineTotal) AS TotalSales
  FROM SalesLT.SalesOrderDetail sod
  JOIN SalesLT.Product p ON sod.ProductID = p.ProductID
  GROUP BY p.Name
  ORDER BY TotalSales DESC;

Ahora convierte la siguiente pregunta a SQL:
{pregunta}
"""

   
    sql_query = ask_ollama(OLLAMA_MODEL, prompt)

    # Limpieza más avanzada
    sql_query = sql_query.replace("```sql", "").replace("```", "")
    sql_query = sql_query.replace("La respuesta sería:", "")
    sql_query = sql_query.replace("Respuesta:", "")
    sql_query = sql_query.replace("SQL:", "")
    sql_query = sql_query.strip()

   
    if "SELECT" in sql_query.upper():
        sql_query = sql_query[sql_query.upper().index("SELECT"):]


    sql_query = re.sub(r"SUM\s+([a-zA-Z0-9_.]+)", r"SUM(\1)", sql_query)

    print("\n--- SQL Generado ---\n")
    print(sql_query)

    try:
        resultado = run_sqlcmd(sql_query)
        print("\n=== RESULTADO SQL ===\n")
        print(resultado)

        #  Pedirle al modelo que interprete el resultado
        resumen = f"""
Explica en español, de forma breve y clara, qué muestran estos resultados obtenidos desde SQL Server:

Pregunta original:
{pregunta}

Resultados:
{resultado}
"""
        texto = ask_ollama(OLLAMA_MODEL, resumen)
        print("\n=== RESPUESTA EN ESPAÑOL ===\n")
        print(texto)

    except Exception as e:
        print(f"\n⚠️ Error ejecutando SQL: {e}")
