"""
Enhanced Gateway Configuration with AgentCore Identity
Sets up Amazon Bedrock AgentCore Gateway with Cognito-based Identity management
"""

import json
import boto3
from typing import Dict, List

# Initialize clients
agentcore_client = boto3.client('bedrock-agentcore-control')
cognito_client = boto3.client('cognito-idp')
iam_client = boto3.client('iam')

# Configuration
AWS_REGION = 'us-west-2'
LAMBDA_FUNCTION_ARN = 'arn:aws:lambda:us-west-2:123456789012:function:athena-query-lambda'
GATEWAY_NAME = 'athena-analytics-gateway'
IDENTITY_NAME = 'athena-analytics-identity'


def create_cognito_user_pool():
    """
    Create a Cognito User Pool for Gateway authentication and Identity management.
    """
    response = cognito_client.create_user_pool(
        PoolName=f'{GATEWAY_NAME}-user-pool',
        Policies={
            'PasswordPolicy': {
                'MinimumLength': 8,
                'RequireUppercase': True,
                'RequireLowercase': True,
                'RequireNumbers': True,
                'RequireSymbols': False
            }
        },
        AutoVerifiedAttributes=['email'],
        UsernameAttributes=['email'],
        Schema=[
            {
                'Name': 'email',
                'AttributeDataType': 'String',
                'Required': True,
                'Mutable': False
            },
            {
                'Name': 'name',
                'AttributeDataType': 'String',
                'Required': True,
                'Mutable': True
            },
            {
                'Name': 'custom:role',
                'AttributeDataType': 'String',
                'Mutable': True
            }
        ],
        UserAttributeUpdateSettings={
            'AttributesRequireVerificationBeforeUpdate': ['email']
        }
    )
    
    user_pool_id = response['UserPool']['Id']
    
    # Create app client for machine-to-machine (agent)
    agent_client_response = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f'{GATEWAY_NAME}-agent-client',
        GenerateSecret=True,
        ExplicitAuthFlows=[
            'ALLOW_USER_PASSWORD_AUTH',
            'ALLOW_REFRESH_TOKEN_AUTH'
        ],
        AllowedOAuthFlows=['client_credentials'],
        AllowedOAuthScopes=['openid', 'email', 'profile'],
        AllowedOAuthFlowsUserPoolClient=True
    )
    
    # Create app client for Streamlit UI
    ui_client_response = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f'{GATEWAY_NAME}-ui-client',
        GenerateSecret=True,
        ExplicitAuthFlows=[
            'ALLOW_USER_PASSWORD_AUTH',
            'ALLOW_REFRESH_TOKEN_AUTH',
            'ALLOW_USER_SRP_AUTH'
        ],
        PreventUserExistenceErrors='ENABLED',
        ReadAttributes=['email', 'name', 'custom:role'],
        WriteAttributes=['name', 'custom:role']
    )
    
    # Create domain for hosted UI (optional)
    try:
        cognito_client.create_user_pool_domain(
            Domain=f'{GATEWAY_NAME.replace("_", "-")}-{user_pool_id[:8]}',
            UserPoolId=user_pool_id
        )
    except Exception as e:
        print(f"Warning: Could not create domain: {e}")
    
    return {
        'user_pool_id': user_pool_id,
        'agent_client_id': agent_client_response['UserPoolClient']['ClientId'],
        'agent_client_secret': agent_client_response['UserPoolClient']['ClientSecret'],
        'ui_client_id': ui_client_response['UserPoolClient']['ClientId'],
        'ui_client_secret': ui_client_response['UserPoolClient']['ClientSecret']
    }


def create_demo_users(user_pool_id: str):
    """
    Create demo users for testing.
    """
    demo_users = [
        {
            'username': 'analyst@example.com',
            'password': 'TempPass123!',
            'name': 'Data Analyst',
            'role': 'analyst'
        },
        {
            'username': 'manager@example.com',
            'password': 'TempPass123!',
            'name': 'Sales Manager',
            'role': 'manager'
        }
    ]
    
    created_users = []
    
    for user in demo_users:
        try:
            # Create user
            response = cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=user['username'],
                UserAttributes=[
                    {'Name': 'email', 'Value': user['username']},
                    {'Name': 'name', 'Value': user['name']},
                    {'Name': 'custom:role', 'Value': user['role']},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                TemporaryPassword=user['password'],
                MessageAction='SUPPRESS'
            )
            
            # Set permanent password
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=user['username'],
                Password=user['password'],
                Permanent=True
            )
            
            created_users.append({
                'username': user['username'],
                'password': user['password'],
                'role': user['role']
            })
            
            print(f"Created user: {user['username']} (role: {user['role']})")
            
        except Exception as e:
            print(f"Warning: Could not create user {user['username']}: {e}")
    
    return created_users


def create_gateway_iam_role():
    """
    Create IAM role for the Gateway to invoke Lambda functions.
    """
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Create role
    role_response = iam_client.create_role(
        RoleName=f'{GATEWAY_NAME}-execution-role',
        AssumeRolePolicyDocument=json.dumps(assume_role_policy),
        Description='Execution role for Bedrock AgentCore Gateway'
    )
    
    # Attach policy to invoke Lambda
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": LAMBDA_FUNCTION_ARN
            }
        ]
    }
    
    iam_client.put_role_policy(
        RoleName=f'{GATEWAY_NAME}-execution-role',
        PolicyName='LambdaInvokePolicy',
        PolicyDocument=json.dumps(policy_document)
    )
    
    return role_response['Role']['Arn']


def create_identity_iam_role():
    """
    Create IAM role for AgentCore Identity to assume when accessing AWS services.
    """
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Create role
    role_response = iam_client.create_role(
        RoleName=f'{IDENTITY_NAME}-role',
        AssumeRolePolicyDocument=json.dumps(assume_role_policy),
        Description='Role for AgentCore Identity to access AWS services'
    )
    
    # Attach policies for accessing various AWS services
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::*-data-bucket",
                    "arn:aws:s3:::*-data-bucket/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": "arn:aws:dynamodb:*:*:table/*"
            }
        ]
    }
    
    iam_client.put_role_policy(
        RoleName=f'{IDENTITY_NAME}-role',
        PolicyName='AWSServiceAccessPolicy',
        PolicyDocument=json.dumps(policy_document)
    )
    
    return role_response['Role']['Arn']


def get_tool_schemas() -> List[Dict]:
    """
    Define tool schemas for each Athena query.
    """
    return [
        {
            "name": "get_sales_summary",
            "description": "Get a summary of sales data for the last 6 months, grouped by month",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_top_customers",
            "description": "Get top customers by lifetime value with their order statistics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "string",
                        "description": "Number of top customers to return (default: 10)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_product_performance",
            "description": "Get product performance metrics including units sold and revenue",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "months": {
                        "type": "string",
                        "description": "Number of months to analyze (e.g., '3', '6', '12')"
                    },
                    "limit": {
                        "type": "string",
                        "description": "Number of products to return (default: 20)"
                    }
                },
                "required": ["months"]
            }
        },
        {
            "name": "get_regional_breakdown",
            "description": "Get sales breakdown by region with customer and revenue metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "months": {
                        "type": "string",
                        "description": "Number of months to analyze (e.g., '3', '6', '12')"
                    }
                },
                "required": ["months"]
            }
        },
        {
            "name": "get_inventory_status",
            "description": "Get current inventory status for a specific warehouse",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "warehouse_id": {
                        "type": "string",
                        "description": "The warehouse ID to check inventory for"
                    }
                },
                "required": ["warehouse_id"]
            }
        },
        {
            "name": "get_order_details",
            "description": "Get detailed information about a specific order including line items",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to retrieve details for"
                    }
                },
                "required": ["order_id"]
            }
        }
    ]


def create_identity(cognito_config: Dict, identity_role_arn: str):
    """
    Create AgentCore Identity with Cognito integration.
    """
    identity_response = agentcore_client.create_identity(
        name=IDENTITY_NAME,
        description='Identity management for Athena analytics with Cognito',
        identityConfiguration={
            'cognito': {
                'userPoolArn': f"arn:aws:cognito-idp:{AWS_REGION}:{boto3.client('sts').get_caller_identity()['Account']}:userpool/{cognito_config['user_pool_id']}",
                'clientIds': [
                    cognito_config['agent_client_id'],
                    cognito_config['ui_client_id']
                ]
            }
        },
        # Optional: Configure role assumption for AWS service access
        identityRoleConfiguration={
            'roleArn': identity_role_arn
        }
    )
    
    identity_id = identity_response['identityId']
    print(f"Created Identity: {identity_id}")
    
    return identity_id


def create_gateway_with_identity_and_targets(
    cognito_config: Dict,
    gateway_role_arn: str,
    identity_id: str
):
    """
    Create the AgentCore Gateway with Identity integration and Lambda targets.
    """
    # Create the gateway with Identity
    gateway_response = agentcore_client.create_gateway(
        name=GATEWAY_NAME,
        description='Gateway for Athena analytics queries with Identity management',
        inboundAuthorizationConfiguration={
            'oauth2Authorization': {
                'allowedClientIds': [
                    cognito_config['agent_client_id'],
                    cognito_config['ui_client_id']
                ],
                'allowedAudiences': [
                    cognito_config['agent_client_id'],
                    cognito_config['ui_client_id']
                ],
                'issuerUrl': f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{cognito_config['user_pool_id']}"
            }
        },
        # Link to Identity
        identityConfiguration={
            'identityId': identity_id
        }
    )
    
    gateway_id = gateway_response['gatewayId']
    print(f"Created Gateway: {gateway_id}")
    
    # Create Lambda target with all tools
    target_response = agentcore_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name='athena-queries',
        description='Athena database query tools',
        credentialProviderConfiguration={
            'gatewayIamRole': {
                'roleArn': gateway_role_arn
            }
        },
        targetConfiguration={
            'mcp': {
                'lambdaEndpoint': {
                    'functionArn': LAMBDA_FUNCTION_ARN
                },
                'toolSchema': {
                    'inlinePayloads': get_tool_schemas()
                }
            }
        }
    )
    
    print(f"Created Target: {target_response['targetId']}")
    
    # Get the Gateway URL
    gateway_url = f"https://{gateway_id}.gateway.bedrock-agentcore.{AWS_REGION}.amazonaws.com/mcp"
    
    return {
        'gateway_id': gateway_id,
        'gateway_url': gateway_url,
        'target_id': target_response['targetId']
    }


def main():
    """
    Main setup function.
    """
    print("=" * 80)
    print("Setting up Bedrock AgentCore Gateway with Identity (Cognito)")
    print("=" * 80)
    
    # Step 1: Create Cognito resources
    print("\n[1/5] Creating Cognito User Pool...")
    cognito_config = create_cognito_user_pool()
    print(f"✓ User Pool ID: {cognito_config['user_pool_id']}")
    
    # Step 2: Create demo users
    print("\n[2/5] Creating demo users...")
    demo_users = create_demo_users(cognito_config['user_pool_id'])
    print(f"✓ Created {len(demo_users)} demo users")
    
    # Step 3: Create IAM roles
    print("\n[3/5] Creating IAM roles...")
    gateway_role_arn = create_gateway_iam_role()
    identity_role_arn = create_identity_iam_role()
    print(f"✓ Gateway Role: {gateway_role_arn}")
    print(f"✓ Identity Role: {identity_role_arn}")
    
    # Step 4: Create Identity
    print("\n[4/5] Creating AgentCore Identity...")
    identity_id = create_identity(cognito_config, identity_role_arn)
    print(f"✓ Identity ID: {identity_id}")
    
    # Step 5: Create Gateway and targets
    print("\n[5/5] Creating Gateway and targets...")
    gateway_config = create_gateway_with_identity_and_targets(
        cognito_config,
        gateway_role_arn,
        identity_id
    )
    print(f"✓ Gateway URL: {gateway_config['gateway_url']}")
    
    # Save configuration
    config = {
        **cognito_config,
        **gateway_config,
        'identity_id': identity_id,
        'region': AWS_REGION,
        'demo_users': demo_users,
        'issuer_url': f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{cognito_config['user_pool_id']}"
    }
    
    with open('gateway_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n" + "=" * 80)
    print("✅ Setup complete!")
    print("=" * 80)
    print(f"\nGateway URL: {gateway_config['gateway_url']}")
    print(f"Identity ID: {identity_id}")
    print(f"\nConfiguration saved to: gateway_config.json")
    print("\nDemo Users Created:")
    for user in demo_users:
        print(f"  - {user['username']} (password: {user['password']}, role: {user['role']})")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
