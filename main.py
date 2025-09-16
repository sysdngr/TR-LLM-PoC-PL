import streamlit as st
import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

endpoint   = os.environ.get("AZURE_OPENAI_MAIN_ENDPOINT")
key        = os.environ.get("AZURE_OPENAI_MAIN_KEY")
deployment = os.environ.get("AZURE_OPENAI_MAIN_DEPLOYMENT")
api_version= os.environ.get("AZURE_OPENAI_MAIN_API_VERSION")
model      = os.environ.get("OPENAI_MODEL_MAIN")

st.title("Main GPT Chat")

if "history" not in st.session_state:
    st.session_state.history = []
if "input_value" not in st.session_state:
    st.session_state.input_value = ""

def submit():
    user_input = st.session_state.input_value
    if user_input:
        st.session_state.history.append(("You", user_input))
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {"Content-Type": "application/json", "api-key": key}
        
        # Build messages with basic context (last few exchanges)
        messages = []
        recent_history = st.session_state.history[-6:]  # Last 3 exchanges (6 messages)
        
        for speaker, text in recent_history:
            if speaker == "You":
                messages.append({"role": "user", "content": text})
            else:
                messages.append({"role": "assistant", "content": text})
        
        payload = {
            "messages": messages,
            "max_tokens": 800,
            "model": model
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.ok:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"]
            st.session_state.history.append(("Assistant", answer))
        else:
            st.session_state.history.append(("Assistant", f"[ERROR] {resp.text}"))
        st.session_state.input_value = ""  # Clear input

# Show chat history first (top to bottom)
for speaker, text in st.session_state.history:
    st.markdown(f"**{speaker}:** {text}")

# Add a hidden anchor for autoscroll
import streamlit.components.v1 as components
components.html("""
<div id='bottom'></div>
<script>
    var bottom = document.getElementById('bottom');
    if(bottom){ bottom.scrollIntoView({behavior: 'smooth'}); }
</script>
""", height=0)

# Input at the bottom
st.text_input("Ask something:", key="input_value", on_change=submit)