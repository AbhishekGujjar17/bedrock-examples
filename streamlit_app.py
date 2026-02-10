"""
Streamlit UI for Athena Analytics Agent
Provides user authentication via Cognito and chat interface with the agent
"""

import streamlit as st
import boto3
import json
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Athena Analytics Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
@st.cache_data
def load_config():
    """Load gateway configuration"""
    try:
        with open('gateway_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("⚠️ Configuration file not found. Please run setup_gateway_with_identity.py first.")
        st.stop()

CONFIG = load_config()

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name=CONFIG['region'])
agentcore_runtime = boto3.client('bedrock-agentcore-runtime', region_name=CONFIG['region'])


class CognitoAuth:
    """Handle Cognito authentication"""
    
    @staticmethod
    def get_secret_hash(username: str, client_id: str, client_secret: str) -> str:
        """Generate secret hash for Cognito"""
        message = username + client_id
        dig = hmac.new(
            client_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()
    
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with Cognito
        Returns access token and user info if successful
        """
        try:
            secret_hash = CognitoAuth.get_secret_hash(
                username,
                CONFIG['ui_client_id'],
                CONFIG['ui_client_secret']
            )
            
            response = cognito_client.initiate_auth(
                ClientId=CONFIG['ui_client_id'],
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': secret_hash
                }
            )
            
            # Get user attributes
            user_info = cognito_client.get_user(
                AccessToken=response['AuthenticationResult']['AccessToken']
            )
            
            # Parse user attributes
            attributes = {attr['Name']: attr['Value'] 
                         for attr in user_info['UserAttributes']}
            
            return {
                'access_token': response['AuthenticationResult']['AccessToken'],
                'id_token': response['AuthenticationResult']['IdToken'],
                'refresh_token': response['AuthenticationResult']['RefreshToken'],
                'expires_in': response['AuthenticationResult']['ExpiresIn'],
                'username': username,
                'email': attributes.get('email', ''),
                'name': attributes.get('name', ''),
                'role': attributes.get('custom:role', 'user')
            }
            
        except cognito_client.exceptions.NotAuthorizedException:
            return None
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return None
    
    @staticmethod
    def refresh_token(refresh_token: str) -> Optional[Dict]:
        """Refresh access token"""
        try:
            response = cognito_client.initiate_auth(
                ClientId=CONFIG['ui_client_id'],
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            return {
                'access_token': response['AuthenticationResult']['AccessToken'],
                'id_token': response['AuthenticationResult']['IdToken'],
                'expires_in': response['AuthenticationResult']['ExpiresIn']
            }
        except Exception:
            return None


def login_page():
    """Display login page"""
    st.title("📊 Athena Analytics Assistant")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Email", placeholder="user@example.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both email and password")
                else:
                    with st.spinner("Authenticating..."):
                        auth_result = CognitoAuth.authenticate(username, password)
                        
                        if auth_result:
                            # Store in session state
                            st.session_state['authenticated'] = True
                            st.session_state['auth_data'] = auth_result
                            st.session_state['login_time'] = datetime.now()
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials. Please try again.")
        
        # Show demo credentials
        st.info("**Demo Accounts:**\n\n"
                "**Analyst:** analyst@example.com / TempPass123!\n\n"
                "**Manager:** manager@example.com / TempPass123!")


def invoke_agent(prompt: str, access_token: str) -> str:
    """
    Invoke the deployed agent with user's prompt
    """
    try:
        # The agent ARN should be loaded from config or environment
        # For now, using a placeholder
        agent_arn = st.session_state.get('agent_arn', '')
        
        if not agent_arn:
            return "⚠️ Agent ARN not configured. Please set it in the sidebar."
        
        response = agentcore_runtime.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            inputText=prompt,
            enableTrace=False,
            # Pass the Cognito access token for identity verification
            sessionContext={
                'accessToken': access_token
            }
        )
        
        # Stream the response
        event_stream = response['completion']
        full_response = ""
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text
        
        return full_response
        
    except Exception as e:
        return f"❌ Error invoking agent: {str(e)}"


def chat_interface():
    """Display chat interface"""
    
    # Sidebar
    with st.sidebar:
        st.title("👤 User Profile")
        auth_data = st.session_state['auth_data']
        
        st.info(f"**Name:** {auth_data['name']}\n\n"
                f"**Email:** {auth_data['email']}\n\n"
                f"**Role:** {auth_data['role'].title()}")
        
        st.markdown("---")
        
        st.subheader("⚙️ Settings")
        
        # Agent ARN input
        agent_arn = st.text_input(
            "Agent ARN",
            value=st.session_state.get('agent_arn', ''),
            help="Enter your deployed agent's ARN"
        )
        st.session_state['agent_arn'] = agent_arn
        
        st.markdown("---")
        
        # Quick queries
        st.subheader("💡 Quick Queries")
        
        quick_queries = [
            "Show me sales trends for the last 6 months",
            "Who are our top 10 customers?",
            "Analyze product performance for last 3 months",
            "Compare regional sales breakdown",
            "Check inventory for warehouse WH001",
            "Get details for order ORD-12345"
        ]
        
        for query in quick_queries:
            if st.button(query, key=query, use_container_width=True):
                st.session_state['selected_query'] = query
        
        st.markdown("---")
        
        # Session info
        login_time = st.session_state.get('login_time', datetime.now())
        session_duration = datetime.now() - login_time
        st.caption(f"Session: {int(session_duration.total_seconds() / 60)} minutes")
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main chat area
    st.title("💬 Athena Analytics Chat")
    st.markdown("Ask questions about your data and get AI-powered insights!")
    
    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [
            {
                "role": "assistant",
                "content": f"Hello {auth_data['name']}! 👋 I'm your Athena Analytics Assistant. I can help you analyze sales data, customer insights, product performance, and more. What would you like to know?"
            }
        ]
    
    # Display chat messages
    for message in st.session_state['messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Check for selected quick query
    if 'selected_query' in st.session_state:
        prompt = st.session_state['selected_query']
        del st.session_state['selected_query']
    else:
        # Chat input
        prompt = st.chat_input("Ask a question about your data...")
    
    if prompt:
        # Add user message to chat
        st.session_state['messages'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = invoke_agent(prompt, auth_data['access_token'])
                st.markdown(response)
        
        # Add assistant response to chat
        st.session_state['messages'].append({"role": "assistant", "content": response})


def main():
    """Main application logic"""
    
    # Check authentication
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        login_page()
    else:
        # Check if token needs refresh
        login_time = st.session_state.get('login_time', datetime.now())
        if datetime.now() - login_time > timedelta(minutes=50):  # Refresh before 1 hour
            auth_data = st.session_state['auth_data']
            new_tokens = CognitoAuth.refresh_token(auth_data['refresh_token'])
            
            if new_tokens:
                auth_data.update(new_tokens)
                st.session_state['auth_data'] = auth_data
                st.session_state['login_time'] = datetime.now()
            else:
                # Refresh failed, logout
                st.error("Session expired. Please login again.")
                time.sleep(2)
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        chat_interface()


if __name__ == '__main__':
    main()
