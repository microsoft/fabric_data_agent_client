import streamlit as st
import os
import time
from datetime import datetime
from fabric_data_agent_client import FabricDataAgentClient

# Configure the page
st.set_page_config(
    page_title="Fabric Data Agent Chat",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #0078d4;
        font-size: 2.2rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .config-display {
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0078d4;
        margin: 1rem 0;
        font-family: monospace;
        font-size: 0.85rem;
        border: 1px solid var(--border-color);
        background-color: var(--secondary-background-color);
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        max-width: 100%;
    }
    
    .user-message {
        background-color: rgba(33, 150, 243, 0.1);
        border-left: 4px solid #2196f3;
    }
    
    .assistant-message {
        background-color: rgba(76, 175, 80, 0.1);
        border-left: 4px solid #4caf50;
    }
    
    .error-message {
        background-color: rgba(244, 67, 54, 0.1);
        color: #f44336;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid rgba(244, 67, 54, 0.3);
    }
    
    .success-message {
        background-color: rgba(76, 175, 80, 0.1);
        color: #4caf50;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid rgba(76, 175, 80, 0.3);
    }
    
    .stButton > button {
        background-color: #0078d4;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        width: 100%;
    }
    
    .stButton > button:hover {
        background-color: #106ebe;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'client' not in st.session_state:
    st.session_state.client = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Header
st.markdown('<h1 class="main-header">🤖 Fabric Data Agent Chat</h1>', unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Load from environment or secrets (with safe secrets handling)
    def get_secret_or_env(key, default=""):
        try:
            if hasattr(st, 'secrets'):
                return st.secrets.get(key, os.getenv(key, default))
        except Exception:
            pass
        return os.getenv(key, default)
    
    default_tenant_id = get_secret_or_env("TENANT_ID")
    default_data_agent_url = get_secret_or_env("DATA_AGENT_URL")
    
    with st.form("config_form"):
        tenant_id = st.text_input(
            "Azure Tenant ID",
            value=default_tenant_id,
            help="Your Azure Active Directory tenant ID",
            type="password"
        )
        
        data_agent_url = st.text_input(
            "Data Agent URL",
            value=default_data_agent_url,
            help="Your published Fabric Data Agent URL"
        )
        
        connect_button = st.form_submit_button("🔌 Connect", type="primary")
    
    # Display current configuration
    st.subheader("📋 Current Configuration")
    
    if tenant_id:
        tenant_display = f"{tenant_id[:8]}..." if len(tenant_id) > 8 else tenant_id
        st.markdown(f"""
        <div class="config-display">
            <strong>Tenant ID:</strong><br>
            {tenant_display}
        </div>
        """, unsafe_allow_html=True)
    
    if data_agent_url:
        url_display = f"{data_agent_url[:50]}..." if len(data_agent_url) > 50 else data_agent_url
        st.markdown(f"""
        <div class="config-display">
            <strong>Data Agent URL:</strong><br>
            {url_display}
        </div>
        """, unsafe_allow_html=True)
    
    # Connection status
    if st.session_state.authenticated:
        st.markdown("""
        <div class="success-message">
            ✅ <strong>Connected</strong><br>
            Ready to ask questions!
        </div>
        """, unsafe_allow_html=True)
        
        # Session stats
        st.subheader("📊 Session Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Questions", len(st.session_state.chat_history))
        with col2:
            successful = sum(1 for chat in st.session_state.chat_history if not chat.get('error'))
            st.metric("Successful", successful)
        
        if st.button("🔄 Reconnect"):
            st.session_state.client = None
            st.session_state.authenticated = False
            st.rerun()
            
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
    else:
        st.markdown("""
        <div class="error-message">
            🔴 <strong>Not Connected</strong><br>
            Please configure and connect to start chatting.
        </div>
        """, unsafe_allow_html=True)

# Handle connection
if connect_button:
    if not tenant_id or not data_agent_url:
        st.error("❌ Please provide both Tenant ID and Data Agent URL")
    else:
        try:
            with st.spinner("🔐 Connecting to Azure and authenticating..."):
                client = FabricDataAgentClient(
                    tenant_id=tenant_id,
                    data_agent_url=data_agent_url
                )
                st.session_state.client = client
                st.session_state.authenticated = True
                st.success("✅ Successfully connected!")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")

# Main chat interface
if st.session_state.authenticated:
    # Sample questions
    st.subheader("💡 Quick Start")
    sample_questions = [
        "What data is available in the lakehouse?",
        "Show me the top 5 records from any table",
        "What are the column names and types?",
    ]
    
    cols = st.columns(len(sample_questions))
    for i, question in enumerate(sample_questions):
        with cols[i]:
            if st.button(f"📝 {question}", key=f"sample_{i}"):
                st.session_state.current_question = question
                st.rerun()
    
    # Chat input
    st.subheader("💬 Ask Your Question")
    
    # Use session state for pre-filled question
    default_question = getattr(st.session_state, 'current_question', '')
    
    question = st.text_area(
        "Type your question here:",
        value=default_question,
        height=80,
        placeholder="e.g., What trends do you see in the sales data?",
        key="question_input"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ask_button = st.button("🚀 Ask Question", type="primary")
    with col2:
        detailed_mode = st.checkbox("Show SQL", value=False)
    
    # Process question
    if ask_button and question.strip():
        # Clear the current_question from session state after processing
        if 'current_question' in st.session_state:
            del st.session_state.current_question
        timestamp = datetime.now()
        
        with st.spinner("🤔 Thinking..."):
            try:
                start_time = time.time()
                
                if detailed_mode:
                    # Get detailed response
                    result = st.session_state.client.get_run_details(question)
                    response_time = time.time() - start_time
                    
                    # Extract answer from messages
                    answer = "I've analyzed your request."
                    if 'messages' in result:
                        messages_data = result['messages'].get('data', [])
                        for msg in messages_data:
                            if msg.get('role') == 'assistant':
                                content = msg.get('content', [])
                                if content:
                                    if isinstance(content[0], dict) and 'text' in content[0]:
                                        text_data = content[0]['text']
                                        if isinstance(text_data, dict) and 'value' in text_data:
                                            answer = text_data['value']
                                        break
                    
                    chat_entry = {
                        'timestamp': timestamp,
                        'question': question,
                        'answer': answer,
                        'details': result,
                        'response_time': response_time,
                        'detailed': True
                    }
                else:
                    # Get simple response
                    answer = st.session_state.client.ask(question)
                    response_time = time.time() - start_time
                    
                    chat_entry = {
                        'timestamp': timestamp,
                        'question': question,
                        'answer': answer,
                        'response_time': response_time,
                        'detailed': False
                    }
                
                st.session_state.chat_history.append(chat_entry)
                st.rerun()
                
            except Exception as e:
                error_entry = {
                    'timestamp': timestamp,
                    'question': question,
                    'error': str(e)
                }
                st.session_state.chat_history.append(error_entry)
                st.rerun()
    
    # Display chat history
    if st.session_state.chat_history:
        st.subheader("💬 Chat History")
        
        # Reverse to show most recent first
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            # Question
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>🙋‍♀️ You</strong> <small>({chat['timestamp'].strftime('%H:%M:%S')})</small><br>
                {chat['question']}
            </div>
            """, unsafe_allow_html=True)
            
            # Response
            if 'error' in chat:
                st.markdown(f"""
                <div class="chat-message error-message">
                    <strong>❌ Error</strong><br>
                    {chat['error']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>🤖 Assistant</strong> <small>({chat['response_time']:.2f}s)</small><br>
                    {chat['answer']}
                </div>
                """, unsafe_allow_html=True)
                
                # Show SQL details if available
                if chat.get('detailed') and 'details' in chat:
                    details = chat['details']
                    
                    if 'data_retrieval_query' in details and details['data_retrieval_query']:
                        with st.expander("🔍 SQL Query Used"):
                            st.code(details['data_retrieval_query'], language='sql')
                    
                    if 'sql_data_previews' in details and details['sql_data_previews']:
                        with st.expander("📊 Data Preview"):
                            for preview in details['sql_data_previews']:
                                if preview:
                                    if len(preview) == 1 and '\n' in preview[0] and '|' in preview[0]:
                                        # Raw markdown table
                                        st.markdown(preview[0])
                                    else:
                                        # Show first few rows
                                        for line in preview[:5]:
                                            st.text(line)
                                    break

else:
    # Not connected - show welcome
    st.markdown("""
    ## 👋 Welcome!
    
    This is a simple chat interface for your Microsoft Fabric Data Agent.
    
    ### 🚀 To get started:
    
    1. **Enter your configuration** in the sidebar:
       - Azure Tenant ID
       - Data Agent URL
    
    2. **Click "Connect"** to authenticate with Azure
    
    3. **Start asking questions** about your data!
    
    ### 💡 Tips:
    
    - You can set `TENANT_ID` and `DATA_AGENT_URL` environment variables
    - Use the sample questions to get started quickly
    - Enable "Show SQL" to see the queries generated
    - Your chat history is maintained during the session
    
    ---
    
    🔗 **Need help finding your configuration?**
    - **Tenant ID**: Go to portal.azure.com → Azure Active Directory → Overview
    - **Data Agent URL**: Publish your data agent in Fabric and copy the URL
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; margin-top: 2rem;">
    🤖 <strong>Fabric Data Agent Chat</strong> | 
    Built with Streamlit | 
    <a href="https://github.com/microsoft/fabric_data_agent_client" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
