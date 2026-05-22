# Step1: Extract Schema
from sqlalchemy import create_engine, inspect
import json
import re
import sqlite3

# Step2: LangChain + Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM


db_url = "sqlite:///amazon.db"


# Extract database schema
def extract_schema(db_url):

    engine = create_engine(db_url)
    inspector = inspect(engine)

    schema = {}

    for table_name in inspector.get_table_names():

        columns = inspector.get_columns(table_name)

        schema[table_name] = [col['name'] for col in columns]

    return json.dumps(schema)


# Convert text to SQL
def text_to_sql(schema, prompt):

    SYSTEM_PROMPT = """
    You are an expert SQL generator.

    Generate ONLY valid SQLite SQL queries.

    Rules:
    - Only use tables and columns from schema
    - Do not explain anything
    - Do not use markdown
    - Do not use <think> tags
    - Return ONLY SQL query
    """

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "Schema:\n{schema}\n\nQuestion: {user_prompt}\n\nSQL Query:")
    ])

    # Ollama Model
    model = OllamaLLM(
    model="phi3",
    temperature=0,
    num_ctx=512
)

    chain = prompt_template | model

    # Generate raw response
    raw_response = chain.invoke({
        "schema": schema,
        "user_prompt": prompt
    })

    # Remove <think> tags
    cleaned_response = re.sub(
        r"<think>.*?</think>",
        "",
        raw_response,
        flags=re.DOTALL
    ).strip()

    # Remove markdown formatting
    cleaned_response = cleaned_response.replace(
        "```sql", ""
    ).replace(
        "```", ""
    )

    return cleaned_response.strip()


# Run SQL query on database
def get_data_from_database(prompt):

    schema = extract_schema(db_url)

    sql_query = text_to_sql(schema, prompt)

    print("Generated SQL:", sql_query)

    conn = sqlite3.connect("amazon.db")

    cursor = conn.cursor()

    try:

        res = cursor.execute(sql_query)

        results = res.fetchall()

    except Exception as e:

        results = f"SQL Error: {str(e)}"

    conn.close()

    return results