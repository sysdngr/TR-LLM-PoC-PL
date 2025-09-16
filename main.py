import streamlit as st
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from orchestrator import LLMOrchestrator

st.title("Premier League Query Assistant")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "input_value" not in st.session_state:
    st.session_state.input_value = ""
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = LLMOrchestrator()

def submit():
    """Handle user input and get response from orchestrator"""
    user_input = st.session_state.input_value
    if user_input:
        # Add user message to UI history
        st.session_state.history.append(("You", user_input))
        
        try:
            # Process query through orchestrator
            response = st.session_state.orchestrator.process_sql_query(user_input)
            st.session_state.history.append(("Assistant", response))
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            st.error(error_msg)
            st.session_state.history.append(("Assistant", f"[ERROR] {error_msg}"))
        
        # Clear input
        st.session_state.input_value = ""

# Show chat history first (top to bottom)

import pandas as pd
for speaker, text in st.session_state.history:
    if speaker == "Assistant":
        # If dict contains 'summary' and 'data', show summary as markdown and data as table
        if isinstance(text, dict) and "summary" in text and "data" in text:
            st.markdown(f"**{speaker}:**")
            st.markdown(text["summary"])
            data = text["data"]
            for key, value in data.items():
                if isinstance(value, list) and value:
                    if all(isinstance(x, dict) for x in value):
                        df = pd.DataFrame(value)
                    elif all(isinstance(x, str) for x in value):
                        df = pd.DataFrame(value, columns=[key])
                    else:
                        df = pd.DataFrame(value)
                    st.table(df)
        # If reply is a list of dicts, show as table
        elif isinstance(text, list) and text and all(isinstance(x, dict) for x in text):
            st.markdown(f"**{speaker}:**")
            df = pd.DataFrame(text)
            st.table(df)
        else:
            rendered = False
            if isinstance(text, dict):
                for key, value in text.items():
                    if isinstance(value, list) and value:
                        st.markdown(f"**{speaker}:** {key}")
                        if all(isinstance(x, dict) for x in value):
                            df = pd.DataFrame(value)
                        elif all(isinstance(x, str) for x in value):
                            df = pd.DataFrame(value, columns=[key])
                        else:
                            df = pd.DataFrame(value)
                        st.table(df)
                        rendered = True
                    elif isinstance(value, str):
                        st.markdown(f"**{speaker}:** {value}")
                        rendered = True
            if not rendered:
                st.markdown(f"**{speaker}:** {text}")
    else:
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