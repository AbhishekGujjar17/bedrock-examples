"""
Strands Agent for Athena Analytics
Deployed on Bedrock AgentCore Runtime with Gateway tools
"""

import json
import os
from typing import Dict, Any
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore_app import BedrockAgentCoreApp
from bedrock_agentcore.mcp.client import MCPClient

# Load gateway configuration
with open('gateway_config.json', 'r') as f:
    GATEWAY_CONFIG = json.load(f)

# System prompt for the analytics agent
SYSTEM_PROMPT = """You are an intelligent data analytics assistant with access to a database through Athena queries.

You can help users with:
- Sales analysis and trends
- Customer insights and segmentation  
- Product performance metrics
- Regional breakdowns
- Inventory management
- Order details and tracking

Available tools:
1. get_sales_summary - View monthly sales trends for the last 6 months
2. get_top_customers - Find top customers by lifetime value
3. get_product_performance - Analyze product sales over time periods
4. get_regional_breakdown - Compare performance across regions
5. get_inventory_status - Check inventory levels at warehouses
6. get_order_details - Get complete details for specific orders

When responding:
- Be concise and data-driven
- Format numerical results clearly (use tables when appropriate)
- Provide insights and highlight key findings
- Ask clarifying questions when parameters are needed
- Suggest related analyses that might be helpful

Always cite which tool you used to get the data."""


def create_mcp_client() -> MCPClient:
    """
    Create and configure MCP client for Gateway connection.
    """
    client = MCPClient(
        gateway_url=GATEWAY_CONFIG['gateway_url'],
        region=GATEWAY_CONFIG['region'],
        # Authentication will be handled by the OAuth configuration
        auth_config={
            'type': 'oauth2',
            'client_id': GATEWAY_CONFIG['client_id'],
            'client_secret': GATEWAY_CONFIG['client_secret'],
            'token_endpoint': f"https://cognito-idp.{GATEWAY_CONFIG['region']}.amazonaws.com/{GATEWAY_CONFIG['user_pool_id']}/oauth2/token"
        }
    )
    
    return client


def create_agent() -> Agent:
    """
    Create the Strands agent with Bedrock model and Gateway tools.
    """
    # Initialize the Bedrock model
    model = BedrockModel(
        model_id='us.anthropic.claude-sonnet-4-20250514-v1:0',
        params={
            'max_tokens': 4096,
            'temperature': 0.1,
            'top_p': 0.95
        },
        region=GATEWAY_CONFIG['region'],
        read_timeout=600
    )
    
    # Create MCP client and get tools from Gateway
    mcp_client = create_mcp_client()
    gateway_tools = mcp_client.list_tools()
    
    # Create the agent
    agent = Agent(
        name='athena_analytics_agent',
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=gateway_tools,
        max_iterations=10
    )
    
    return agent


# Initialize the AgentCore app
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Entrypoint for AgentCore Runtime.
    
    Args:
        payload: Request payload containing the prompt
        context: Runtime context
        
    Returns:
        Agent response
    """
    try:
        # Extract the prompt from payload
        prompt = payload.get('prompt', '')
        
        if not prompt:
            return {
                'status': 'error',
                'error': 'No prompt provided'
            }
        
        # Create agent (cached in production)
        agent = create_agent()
        
        # Run the agent
        result = agent(prompt)
        
        # Format response
        return {
            'status': 'success',
            'result': str(result),
            'metadata': {
                'model': 'claude-sonnet-4',
                'tools_available': len(agent.tools)
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


if __name__ == '__main__':
    """
    For local testing
    """
    # Test the agent locally
    agent = create_agent()
    
    # Example queries
    test_queries = [
        "What were our sales like over the past 6 months?",
        "Show me the top 5 customers by revenue",
        "How are products performing in the last 3 months?",
        "What's the inventory status for warehouse WH001?",
        "Get me details for order ORD-12345"
    ]
    
    print("Testing agent locally...\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        print("=" * 80)
        result = agent(query)
        print(f"Response: {result}\n")
