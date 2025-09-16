import streamlit as st
import os
import sys
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from orchestrator import LLMOrchestrator

def format_dataframe_columns(df):
    """Apply better formatting to common football data columns"""
    df_formatted = df.copy()
    
    # Format age column
    if 'age' in df_formatted.columns:
        df_formatted['age'] = df_formatted['age'].astype(str) + " years"
    
    # Capitalize column names for display
    df_formatted.columns = [col.replace('_', ' ').title() for col in df_formatted.columns]
    
    return df_formatted

def display_list(data, title="Results"):
    """Display a list of data as a table."""
    df = pd.DataFrame(data)
    df_formatted = format_dataframe_columns(df)

    st.subheader(title)
    st.dataframe(df_formatted, use_container_width=True, height=min(400, len(df) * 35 + 50))

    # Commented out the download functionality
    # csv = df.to_csv(index=False)
    # st.download_button(
    #     label=f"Download as CSV ({len(df)} rows)",
    #     data=csv,
    #     file_name=f"premier_league_data.csv",
    #     mime="text/csv",
    #     key=f"download_{len(st.session_state.history)}"
    # )

    # Show row count
    st.caption(f"Showing {len(df)} results")

def display_dict(data):
    """Display a dictionary of data."""
    for key, value in data.items():
        if isinstance(value, list) and value:
            display_list(value, key.replace('_', ' ').title())
        else:
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

def display_data(data):
    """Handle all types of data and display appropriately."""
    if isinstance(data, list):
        display_list(data)
    elif isinstance(data, dict):
        display_dict(data)
    else:
        st.markdown(str(data))

def display_response(speaker, response):
    """Handle all types of responses with proper formatting"""
    st.markdown(f"**{speaker}:**")
    
    if isinstance(response, dict):
        # Handle structured responses with summary and data
        if "summary" in response and "data" in response:
            st.markdown(response["summary"])
            st.divider()
            display_data(response["data"])
        
        # Handle error responses
        elif "error" in response:
            st.error(f"❌ {response['error']}")
        
        # Handle other dictionary responses
        else:
            display_data(response)
    
    elif isinstance(response, list) and response:
        display_data(response)
    
    else:
        # Handle plain text responses
        st.markdown(str(response))

st.title("Premier League Query Assistant")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "input_value" not in st.session_state:
    st.session_state.input_value = ""
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = LLMOrchestrator()

# Limit session state history
if "history" in st.session_state:
    st.session_state.history = st.session_state.history[-50:]

def submit():
    """Handle user input and get response from orchestrator"""
    user_input = st.session_state.input_value
    if user_input:
        # Add user message to UI history
        st.session_state.history.append(("You", user_input))
        
        try:
            # Process query through orchestrator
            response = st.session_state.orchestrator.process_query(user_input)
            st.session_state.history.append(("Assistant", response))
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            st.error(error_msg)
            st.session_state.history.append(("Assistant", {"error": error_msg}))
        
        # Clear input
        st.session_state.input_value = ""

# Display chat history with improved formatting
for speaker, response in st.session_state.history:
    if speaker == "You":
        st.markdown(f"**{speaker}:** {response}")
    else:
        display_response(speaker, response)
    st.divider()  # Add visual separation between exchanges

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