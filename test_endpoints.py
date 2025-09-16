import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Main LLM
endpoint   = os.environ.get("AZURE_OPENAI_MAIN_ENDPOINT")
key        = os.environ.get("AZURE_OPENAI_MAIN_KEY")
deployment = os.environ.get("AZURE_OPENAI_MAIN_DEPLOYMENT")
api_version= os.environ.get("AZURE_OPENAI_MAIN_API_VERSION")
model      = os.environ.get("OPENAI_MODEL_MAIN")

if not all([endpoint, key, deployment, api_version, model]):
    raise SystemExit("Missing one or more required environment variables for main endpoint.")

url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
headers = {"Content-Type": "application/json", "api-key": key}
payload = {
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "max_tokens": 32,
    "model": model
}

resp = requests.post(url, headers=headers, json=payload, timeout=10)
print("MAIN LLM reply:")
try:
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    print(content)
except Exception:
    print(resp.text)

# SQL LLM
sql_endpoint   = os.environ.get("AZURE_OPENAI_SQL_ENDPOINT")
sql_key        = os.environ.get("AZURE_OPENAI_SQL_KEY")
sql_deployment = os.environ.get("AZURE_OPENAI_SQL_DEPLOYMENT")
sql_api_version= os.environ.get("AZURE_OPENAI_SQL_API_VERSION")
sql_model      = os.environ.get("OPENAI_MODEL_SQL")

if not all([sql_endpoint, sql_key, sql_deployment, sql_api_version, sql_model]):
    raise SystemExit("Missing one or more required environment variables for SQL endpoint.")

sql_url = f"{sql_endpoint}/openai/deployments/{sql_deployment}/chat/completions?api-version={sql_api_version}"
sql_headers = {"Content-Type": "application/json", "api-key": sql_key}
sql_payload = {
    "messages": [{"role": "user", "content": "What is the capital of UAE?"}],
    "max_completion_tokens": 256,
    "model": sql_model
}

sql_resp = requests.post(sql_url, headers=sql_headers, json=sql_payload, timeout=10)
print("\nSQL LLM reply:")
try:
    sql_data = sql_resp.json()
    sql_content = sql_data["choices"][0]["message"]["content"]
    print(sql_content)
except Exception:
    print(sql_resp.text)
