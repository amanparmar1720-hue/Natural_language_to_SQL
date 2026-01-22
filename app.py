import streamlit as st
import pandas as pd
import tempfile
import os

from nl_to_sql import (
    get_sql_query_via_gemini,
    execute_query,
    build_sqlite_db_from_csvs,
    get_gemini_client_from_env_or_secrets,
)

st.set_page_config(page_title="Natural Language → SQL (Gemini)", page_icon="🧠", layout="centered")
st.title("🧠 Natural Language → SQL ")
st.caption("Built by **AMAN KUMAR PARMAR**")
st.write(
    "Upload your CSV files, paste your prompt/schema, ask a question → get SQL "
    "(and optionally execute it on the uploaded data)."
)

# -----------------------------
# API Key (safe: works with or without secrets.toml)
# -----------------------------
st.sidebar.header("🔐 API Key")

api_key = ""

try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = st.sidebar.text_input("GOOGLE_API_KEY", type="password")

model = st.sidebar.selectbox("Gemini model", ["gemini-2.5-flash", "gemini-1.5-flash"], index=0)

# -----------------------------
# Prompt / Schema
# -----------------------------
st.subheader("1) Paste your Prompt / Schema")
prompt = st.text_area(
    "Prompt / Schema",
    height=260,
    placeholder="Describe your database schema, tables, and relationships here..."
)

# -----------------------------
# Upload CSVs (generic)
# -----------------------------
st.subheader("2) Upload CSV Files")

uploaded_files = st.file_uploader(
    "Upload one or more CSV files (each file will be treated as a table)",
    type=["csv"],
    accept_multiple_files=True
)

st.caption(
    "📌 Each uploaded CSV is treated as a separate table. "
    "The table name will be the file name (without .csv)."
)

# -----------------------------
# Question
# -----------------------------
st.subheader("3) Ask in English")
question = st.text_input("Your question", placeholder="e.g., Show top 10 products by total sales")

run_sql = st.checkbox("Also execute SQL on the uploaded data (SQLite)", value=True)

# -----------------------------
# Action
# -----------------------------
if st.button("✨ Generate SQL", use_container_width=True):
    if not api_key:
        st.error("Please provide GOOGLE_API_KEY (sidebar or Streamlit Secrets).")
        st.stop()

    if not prompt.strip():
        st.error("Prompt/Schema is empty. Please paste your schema or prompt.")
        st.stop()

    if not question.strip():
        st.error("Question is empty.")
        st.stop()

    # Gemini client
    try:
        client = get_gemini_client_from_env_or_secrets(api_key)
    except Exception as e:
        st.error(f"Gemini client error: {e}")
        st.stop()

    # Generate SQL
    with st.spinner("Generating SQL..."):
        sql = get_sql_query_via_gemini(client, prompt, question, model=model)

    st.subheader("✅ Generated SQL")
    st.code(sql, language="sql")
    st.caption("⚠️ Tip: This demo is intended for SELECT-style analytics queries.")

    # Execute if requested
    if run_sql:
        if not uploaded_files:
            st.warning("To execute SQL, upload at least one CSV file. (You can still generate SQL without uploading.)")
            st.stop()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "data.db")

            # Build DB dynamically from uploaded CSVs
            build_sqlite_db_from_csvs(db_path=db_path, csv_files=uploaded_files)

            with st.spinner("Executing SQL on SQLite..."):
                result_df = execute_query(sql, db_path)

            if result_df is None:
                st.error("SQL execution failed. Check SQL and schema/prompt alignment.")
            else:
                st.subheader("📊 Query Output")
                st.dataframe(result_df, use_container_width=True)

                st.download_button(
                    "⬇️ Download results as CSV",
                    data=result_df.to_csv(index=False).encode("utf-8"),
                    file_name="query_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
