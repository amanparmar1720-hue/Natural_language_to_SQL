import os
import sqlite3
import pandas as pd
import google.generativeai as genai


# -----------------------------
# Gemini client helper
# -----------------------------
def get_gemini_client_from_env_or_secrets(api_key: str | None = None):
    key = api_key or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("Missing GOOGLE_API_KEY")
    genai.configure(api_key=key)
    return genai


# -----------------------------
# LLM: Natural Language -> SQL
# -----------------------------
def get_sql_query_via_gemini(
    genai_module,
    prompt: str,
    user_query: str,
    model: str = "gemini-1.5-flash"
) -> str:
    contents = (
        f"{prompt}\n\n"
        f"User question (English):\n{user_query}\n\n"
        f"Return only the SQL query. Do not include markdown fences or explanations."
    )

    model_obj = genai_module.GenerativeModel(model)
    response = model_obj.generate_content(contents)

    output = (response.text or "").replace("```sql", "").replace("```", "").strip()
    return output


# -----------------------------
# SQLite execution
# -----------------------------
def execute_query(query: str, db_path: str) -> pd.DataFrame | None:
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)

        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        results_as_dict = [dict(zip(columns, row)) for row in results] if columns else []
        return pd.DataFrame(results_as_dict)

    except sqlite3.Error as e:
        print(f"Database error executing query: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error executing query: {e}")
        return None
    finally:
        if conn:
            conn.close()


# -----------------------------
# Build SQLite DB dynamically from any CSVs
# -----------------------------
def build_sqlite_db_from_csvs(db_path: str, csv_files: list) -> None:
    """
    Create a fresh SQLite DB and load each uploaded CSV as a table.
    Table name = file name without extension.
    """
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    try:
        for f in csv_files:
            table_name = os.path.splitext(f.name)[0]
            df = pd.read_csv(f)

            # Make column names SQLite-friendly
            df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]

            df.to_sql(table_name, conn, if_exists="replace", index=False)

        conn.commit()
    finally:
        conn.close()
