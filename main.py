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

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .chat-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #2a5298;
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0;
    }
    
    .assistant-message {
        background-color: white;
        border: 1px solid #e0e0e0;
        padding: 0.8rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 3px solid #2a5298;
    }
    
    .stDataFrame {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
    }
    
    div.stButton > button {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: 500;
    }
    
    .footer {
        text-align: center;
        color: #666;
        padding: 2rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

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
    """Display a list of data as a table with enhanced styling."""
    df = pd.DataFrame(data)
    df_formatted = format_dataframe_columns(df)

    st.markdown(f"### 👥 {title}")
    
    st.dataframe(
        df_formatted, 
        use_container_width=True, 
        height=min(400, len(df) * 35 + 50),
        hide_index=True
    )

    st.caption(f"📋 Showing {len(df)} players")

def display_dict(data):
    """Display a dictionary of data with enhanced styling."""
    for key, value in data.items():
        if isinstance(value, list) and value:
            display_list(value, key.replace('_', ' ').title())
        else:
            st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")

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
    if speaker == "Assistant":
        st.markdown('<div class="assistant-message">', unsafe_allow_html=True)
        
        if isinstance(response, dict):
            # Handle structured responses with summary and data
            if "summary" in response and "data" in response:
                st.markdown(f"**🤖 Assistant:** {response['summary']}")
                st.divider()
                display_data(response["data"])
            
            # Handle error responses
            elif "error" in response:
                st.error(f"❌ {response['error']}")
            
            # Handle other dictionary responses
            else:
                st.markdown("**🤖 Assistant:**")
                display_data(response)
        
        elif isinstance(response, list) and response:
            st.markdown("**🤖 Assistant:**")
            display_data(response)
        
        else:
            # Handle plain text responses
            st.markdown(f"**🤖 Assistant:** {str(response)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Header with styling
st.markdown("""
<div class="main-header">
    <h1>⚽ Premier League Query Assistant</h1>
    <p>Ask me anything about Premier League 2025/2026 season players and teams!</p>
</div>
""", unsafe_allow_html=True)

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

# Chat history container
if st.session_state.history:
    st.markdown("### 💬 Chat History")
    
    for speaker, response in st.session_state.history:
        if speaker == "You":
            st.markdown('<div class="user-message">', unsafe_allow_html=True)
            st.markdown(f"**👤 You:** {response}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            display_response(speaker, response)
        
        st.markdown("<br>", unsafe_allow_html=True)
else:
    # Welcome message when no history
    st.markdown("""
    <div class="chat-container">
        <h3>👋 Welcome!</h3>
        <p>I'm your Premier League player database assistant for the 2025/26 season. You can ask me about:</p>
        <ul>
            <li>👤 Individual player details (age, position, nationality)</li>
            <li>🏟️ Team squad lists and rosters</li>
            <li>📋 Players by position, age, or nationality</li>
            <li>🔍 Search and filter player information</li>
        </ul>
        <p><strong>Try asking:</strong> "Show me all Arsenal players" or "List all Brazilian forwards"</p>
    </div>
    """, unsafe_allow_html=True)

# Auto-scroll to bottom
import streamlit.components.v1 as components
components.html("""
<div id='bottom'></div>
<script>
    var bottom = document.getElementById('bottom');
    if(bottom){ bottom.scrollIntoView({behavior: 'smooth'}); }
</script>
""", height=0)

# Input section with better styling
st.markdown("---")
col1, col2 = st.columns([4, 1])
with col1:
    st.text_input(
        "💭 Ask me anything about Premier League...", 
        key="input_value", 
        on_change=submit,
        placeholder="e.g., Show me all Arsenal forwards"
    )
with col2:
    if st.button("Send 🚀", use_container_width=True):
        submit()

# Footer
st.markdown("""
<div class="footer">
    <p>⚽ Powered by Premier League 2025/2026 data | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)