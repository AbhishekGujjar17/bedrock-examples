# Athena Analytics Agent with Gateway Identity & Streamlit UI

A complete, production-ready AI analytics assistant built with:
- **Strands Agent** deployed on AWS Bedrock AgentCore Runtime
- **AgentCore Gateway** with Lambda tools for Athena queries
- **AgentCore Identity** using Cognito for user authentication
- **Streamlit UI** for interactive chat interface

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Streamlit Web UI                       │
│  - User login via Cognito                               │
│  - Chat interface                                       │
│  - Quick query buttons                                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ OAuth Token (Access Token)
                 ▼
┌─────────────────────────────────────────────────────────┐
│              AWS Cognito User Pool                      │
│  - User authentication                                  │
│  - Token management                                     │
│  - User attributes (name, email, role)                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Linked via Identity
                 ▼
┌─────────────────────────────────────────────────────────┐
│         AgentCore Identity                              │
│  - Manages user identity across services                │
│  - Role-based access control                            │
│  - IAM role assumption                                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ User context
                 ▼
┌─────────────────────────────────────────────────────────┐
│         Strands Agent (AgentCore Runtime)               │
│  - Claude Sonnet 4 model                                │
│  - Analytics assistant logic                            │
│  - Tool orchestration                                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ MCP Protocol
                 ▼
┌─────────────────────────────────────────────────────────┐
│              AgentCore Gateway                          │
│  - OAuth authentication check                           │
│  - Tool discovery & invocation                          │
│  - Request/response handling                            │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Lambda invocation
                 ▼
┌─────────────────────────────────────────────────────────┐
│            Lambda Function                              │
│  - 6 predefined Athena queries                          │
│  - Query execution & result formatting                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ SQL queries
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Amazon Athena                              │
│  - Sales data                                           │
│  - Customer data                                        │
│  - Product & inventory data                             │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Identity & Authentication
- ✅ **Cognito Integration**: Secure user authentication with AWS Cognito
- ✅ **Role-Based Access**: Custom user attributes (analyst, manager roles)
- ✅ **Token Management**: Automatic token refresh for long sessions
- ✅ **Identity Propagation**: User context flows through entire stack

### Gateway & Tools
- ✅ **6 Analytics Tools**: Pre-built queries for common business intelligence
- ✅ **MCP Protocol**: Modern tool discovery and invocation
- ✅ **OAuth Security**: All Gateway requests authenticated
- ✅ **Lambda Backend**: Serverless query execution

### User Interface
- ✅ **Streamlit Chat**: Modern, responsive chat interface
- ✅ **Quick Queries**: Pre-defined query buttons for common tasks
- ✅ **User Profile**: Display user info and role
- ✅ **Session Management**: Automatic token refresh
- ✅ **Real-time Streaming**: Live response streaming from agent

### Analytics Capabilities
- 📊 Sales trend analysis
- 👥 Customer insights and segmentation
- 📦 Product performance metrics
- 🗺️ Regional sales breakdown
- 📋 Inventory management
- 🔍 Order detail tracking

## 📋 Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Python 3.9+
- Access to Amazon Bedrock (Claude Sonnet 4)
- An existing Athena database

## 🛠️ Setup Instructions

### Step 1: Deploy Lambda Function

```bash
# Create Lambda function
cd /path/to/lambda
zip function.zip athena_query_lambda.py

aws lambda create-function \
    --function-name athena-query-lambda \
    --runtime python3.11 \
    --handler athena_query_lambda.lambda_handler \
    --zip-file fileb://function.zip \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-athena-role \
    --timeout 300 \
    --memory-size 512
```

Update the Lambda ARN in `setup_gateway_with_identity.py`.

### Step 2: Setup Gateway, Identity, and Cognito

```bash
# Install dependencies
pip install boto3

# Run setup script
python setup_gateway_with_identity.py
```

This creates:
1. **Cognito User Pool** with two app clients (agent and UI)
2. **Demo Users** (analyst@example.com and manager@example.com)
3. **IAM Roles** for Gateway and Identity
4. **AgentCore Identity** linked to Cognito
5. **AgentCore Gateway** with Lambda targets
6. **Configuration file** (gateway_config.json)

Output example:
```
[1/5] Creating Cognito User Pool...
✓ User Pool ID: us-west-2_XXXXXXXXX

[2/5] Creating demo users...
Created user: analyst@example.com (role: analyst)
Created user: manager@example.com (role: manager)
✓ Created 2 demo users

[3/5] Creating IAM roles...
✓ Gateway Role: arn:aws:iam::...
✓ Identity Role: arn:aws:iam::...

[4/5] Creating AgentCore Identity...
✓ Identity ID: identity-XXXXXXXXXX

[5/5] Creating Gateway and targets...
✓ Gateway URL: https://gateway-xxx.bedrock-agentcore.us-west-2.amazonaws.com/mcp

✅ Setup complete!
```

### Step 3: Deploy Strands Agent

```bash
# Install agent dependencies
pip install -r requirements_complete.txt

# Deploy to AgentCore Runtime
./deploy.sh
```

Note the **Agent ARN** from the output - you'll need this for the Streamlit app.

### Step 4: Launch Streamlit UI

```bash
# Make sure gateway_config.json exists from Step 2
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## 🔐 Authentication Flow

### 1. User Login
```
User enters credentials → Cognito authenticates → Returns tokens
```

### 2. Token Storage
```python
{
    'access_token': 'eyJra...',  # For API authentication
    'id_token': 'eyJra...',      # User identity claims
    'refresh_token': 'eyJra...',  # For token refresh
    'username': 'analyst@example.com',
    'name': 'Data Analyst',
    'role': 'analyst'
}
```

### 3. Agent Invocation
```
Streamlit → AgentCore Runtime (with access_token) → Identity verifies → Gateway → Lambda
```

## 💻 Using the Streamlit UI

### Login Page
1. Open the app
2. Use demo credentials:
   - **Analyst**: `analyst@example.com` / `TempPass123!`
   - **Manager**: `manager@example.com` / `TempPass123!`
3. Click "Login"

### Chat Interface

**Main Area**: Chat with the agent
- Type questions in the chat input
- View responses with formatted data
- Chat history preserved during session

**Sidebar**:
- **User Profile**: Shows name, email, role
- **Agent ARN**: Configure your deployed agent
- **Quick Queries**: Pre-defined query buttons
- **Logout**: End session

### Example Queries

**Sales Analysis**:
```
"Show me sales trends for the last 6 months"
"What were our best performing months?"
```

**Customer Insights**:
```
"Who are our top 10 customers?"
"Show me customers with lifetime value over $10,000"
```

**Product Performance**:
```
"Analyze product performance for the last 3 months"
"Which products have the highest revenue?"
```

**Regional Analysis**:
```
"Compare sales across all regions for the past 6 months"
"Which region has the best average order value?"
```

**Inventory**:
```
"Check inventory for warehouse WH001"
"Show me products with low stock"
```

**Order Details**:
```
"Get details for order ORD-12345"
"Show me recent orders for customer CUST-456"
```

## 🔧 Configuration

### gateway_config.json
Created by setup script, contains:
```json
{
  "user_pool_id": "us-west-2_XXXXXXXXX",
  "agent_client_id": "...",
  "agent_client_secret": "...",
  "ui_client_id": "...",
  "ui_client_secret": "...",
  "gateway_id": "gateway-XXXXXXXX",
  "gateway_url": "https://...",
  "identity_id": "identity-XXXXXXXX",
  "region": "us-west-2",
  "demo_users": [...]
}
```

### Environment Variables (Optional)
```bash
export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/..."
export AWS_REGION="us-west-2"
```

## 🎨 Customization

### Adding New Users

```python
import boto3

cognito = boto3.client('cognito-idp')

cognito.admin_create_user(
    UserPoolId='us-west-2_XXXXXXXXX',
    Username='newuser@example.com',
    UserAttributes=[
        {'Name': 'email', 'Value': 'newuser@example.com'},
        {'Name': 'name', 'Value': 'New User'},
        {'Name': 'custom:role', 'Value': 'analyst'},
        {'Name': 'email_verified', 'Value': 'true'}
    ],
    TemporaryPassword='TempPass123!'
)
```

### Adding New Queries

1. **Update Lambda** (`athena_query_lambda.py`):
```python
PREDEFINED_QUERIES['new_query'] = """
    SELECT ... FROM table WHERE ...
"""
```

2. **Update Gateway** (`setup_gateway_with_identity.py`):
```python
{
    "name": "new_query",
    "description": "Description of what this does",
    "inputSchema": {...}
}
```

3. **Redeploy Gateway**:
```bash
python setup_gateway_with_identity.py
```

### Customizing UI

Edit `streamlit_app.py`:

**Change Theme**:
```python
st.set_page_config(
    page_title="My Custom Title",
    page_icon="🎯",
    layout="wide"
)
```

**Add Quick Queries**:
```python
quick_queries = [
    "Your custom query here",
    # ... more queries
]
```

**Modify Chat Styling**:
Use Streamlit's markdown and custom CSS for styling.

## 📊 Monitoring & Debugging

### View Logs

**Gateway Logs**:
```bash
aws logs tail /aws/bedrock-agentcore/gateways/gateway-XXXXXXXX --follow
```

**Lambda Logs**:
```bash
aws logs tail /aws/lambda/athena-query-lambda --follow
```

**Agent Runtime Logs**:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/athena-analytics-agent-XXX --follow
```

### Enable Tracing

In `streamlit_app.py`:
```python
response = agentcore_runtime.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    inputText=prompt,
    enableTrace=True  # Enable detailed traces
)
```

### Debug Authentication

Add debug logging to Cognito auth:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔒 Security Best Practices

### 1. Cognito Configuration
- ✅ Use strong password policies
- ✅ Enable MFA for production
- ✅ Set token expiration appropriately
- ✅ Use HTTPS for token exchange

### 2. Identity & Access
- ✅ Implement least privilege IAM policies
- ✅ Use separate roles for different user types
- ✅ Audit access logs regularly
- ✅ Rotate credentials periodically

### 3. Gateway Security
- ✅ OAuth token validation on every request
- ✅ Rate limiting on Gateway endpoints
- ✅ Monitor for unusual access patterns
- ✅ Use VPC endpoints where possible

### 4. Data Protection
- ✅ Encrypt data at rest (S3, Athena)
- ✅ Encrypt data in transit (TLS)
- ✅ Implement column-level security in Athena
- ✅ Mask sensitive data in responses

## 💰 Cost Optimization

### Estimate Monthly Costs
- **Cognito**: Free tier (50,000 MAUs), then $0.0055/MAU
- **AgentCore Runtime**: Pay per session
- **AgentCore Gateway**: Pay per request
- **Lambda**: $0.20 per 1M requests + compute time
- **Athena**: $5 per TB scanned
- **Bedrock**: ~$3 per 1M input tokens, ~$15 per 1M output tokens

### Optimization Tips
1. **Use Athena Partitions**: Reduce data scanned
2. **Cache Results**: Store frequent queries in DynamoDB
3. **Optimize Lambda**: Right-size memory allocation
4. **Compress Data**: Use Parquet format in S3
5. **Set Query Limits**: Prevent expensive queries

## 🐛 Troubleshooting

### Issue: "Configuration file not found"
**Solution**: Run `setup_gateway_with_identity.py` first to create `gateway_config.json`

### Issue: "Invalid credentials"
**Solution**: 
- Check username/password are correct
- Verify Cognito user pool settings
- Check if user needs password reset

### Issue: "Agent ARN not configured"
**Solution**: 
- Deploy agent with `./deploy.sh`
- Copy Agent ARN to Streamlit sidebar
- Or set `AGENT_ARN` environment variable

### Issue: "Token expired"
**Solution**: 
- App auto-refreshes tokens after 50 minutes
- If expired, logout and login again
- Check refresh token configuration

### Issue: "Lambda timeout"
**Solution**:
- Increase Lambda timeout in configuration
- Optimize Athena queries
- Check Athena query execution time

### Issue: "Gateway returns 403"
**Solution**:
- Verify OAuth token is valid
- Check Gateway allows client ID
- Confirm Identity is linked to Gateway

## 🚀 Deployment to Production

### 1. Infrastructure as Code
Use the provided CloudFormation template:
```bash
aws cloudformation create-stack \
    --stack-name athena-analytics \
    --template-body file://cloudformation-template.yaml \
    --parameters ParameterKey=AthenaDatabaseName,ParameterValue=my_db
```

### 2. Deploy Streamlit to ECS/EKS
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements_complete.txt .
RUN pip install -r requirements_complete.txt
COPY streamlit_app.py gateway_config.json ./
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
```

### 3. Use Application Load Balancer
- Set up ALB with HTTPS
- Configure health checks
- Enable sticky sessions

### 4. Secrets Management
```python
import boto3

secrets = boto3.client('secretsmanager')
config = json.loads(
    secrets.get_secret_value(SecretId='athena-analytics-config')['SecretString']
)
```

### 5. Multi-Environment Setup
- Development: `gateway_config.dev.json`
- Staging: `gateway_config.staging.json`
- Production: `gateway_config.prod.json`

## 📚 Additional Resources

- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Amazon Athena Best Practices](https://docs.aws.amazon.com/athena/latest/ug/best-practices.html)

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues or questions:
- Review the troubleshooting section
- Check CloudWatch logs
- Open an issue on GitHub
- Contact AWS Support for service-specific issues
