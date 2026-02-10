import json
import boto3
import time
import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Athena client
athena_client = boto3.client('athena')

# Configuration
ATHENA_DATABASE = 'your_database_name'
ATHENA_OUTPUT_LOCATION = 's3://your-athena-results-bucket/query-results/'

# Define your predefined queries
PREDEFINED_QUERIES = {
    'get_sales_summary': """
        SELECT 
            DATE_TRUNC('month', order_date) as month,
            SUM(total_amount) as total_sales,
            COUNT(DISTINCT order_id) as order_count
        FROM sales_table
        WHERE order_date >= DATE_ADD('month', -6, CURRENT_DATE)
        GROUP BY DATE_TRUNC('month', order_date)
        ORDER BY month DESC
    """,
    
    'get_top_customers': """
        SELECT 
            customer_id,
            customer_name,
            SUM(total_amount) as lifetime_value,
            COUNT(order_id) as order_count
        FROM sales_table
        WHERE order_date >= DATE_ADD('year', -1, CURRENT_DATE)
        GROUP BY customer_id, customer_name
        ORDER BY lifetime_value DESC
        LIMIT {limit}
    """,
    
    'get_product_performance': """
        SELECT 
            product_id,
            product_name,
            SUM(quantity) as units_sold,
            SUM(total_amount) as revenue,
            AVG(unit_price) as avg_price
        FROM sales_table
        WHERE order_date >= DATE_ADD('month', -{months}, CURRENT_DATE)
        GROUP BY product_id, product_name
        ORDER BY revenue DESC
        LIMIT {limit}
    """,
    
    'get_regional_breakdown': """
        SELECT 
            region,
            COUNT(DISTINCT customer_id) as unique_customers,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM sales_table
        WHERE order_date >= DATE_ADD('month', -{months}, CURRENT_DATE)
        GROUP BY region
        ORDER BY total_revenue DESC
    """,
    
    'get_inventory_status': """
        SELECT 
            product_id,
            product_name,
            current_stock,
            reorder_level,
            CASE 
                WHEN current_stock <= reorder_level THEN 'LOW'
                WHEN current_stock <= reorder_level * 1.5 THEN 'MEDIUM'
                ELSE 'GOOD'
            END as stock_status
        FROM inventory_table
        WHERE warehouse_id = '{warehouse_id}'
        ORDER BY stock_status, current_stock ASC
    """,
    
    'get_order_details': """
        SELECT 
            o.order_id,
            o.order_date,
            o.customer_name,
            o.total_amount,
            o.status,
            oi.product_name,
            oi.quantity,
            oi.unit_price
        FROM orders_table o
        JOIN order_items_table oi ON o.order_id = oi.order_id
        WHERE o.order_id = '{order_id}'
    """
}


def execute_athena_query(query: str) -> Dict[str, Any]:
    """
    Execute an Athena query and wait for results.
    
    Args:
        query: SQL query to execute
        
    Returns:
        Dictionary containing query results
    """
    try:
        # Start query execution
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': ATHENA_DATABASE},
            ResultConfiguration={'OutputLocation': ATHENA_OUTPUT_LOCATION}
        )
        
        query_execution_id = response['QueryExecutionId']
        logger.info(f"Started query execution: {query_execution_id}")
        
        # Wait for query to complete
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            query_status = athena_client.get_query_execution(
                QueryExecutionId=query_execution_id
            )
            
            status = query_status['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                # Get query results
                result = athena_client.get_query_results(
                    QueryExecutionId=query_execution_id,
                    MaxResults=100
                )
                
                # Parse results
                columns = [col['Label'] for col in result['ResultSet']['ResultSetMetadata']['ColumnInfo']]
                rows = []
                
                # Skip header row
                for row in result['ResultSet']['Rows'][1:]:
                    row_data = {}
                    for i, col in enumerate(columns):
                        value = row['Data'][i].get('VarCharValue', '')
                        row_data[col] = value
                    rows.append(row_data)
                
                return {
                    'success': True,
                    'columns': columns,
                    'rows': rows,
                    'row_count': len(rows)
                }
                
            elif status in ['FAILED', 'CANCELLED']:
                error_message = query_status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                logger.error(f"Query failed: {error_message}")
                return {
                    'success': False,
                    'error': error_message
                }
            
            # Query still running, wait and retry
            time.sleep(1)
            attempt += 1
        
        return {
            'success': False,
            'error': 'Query timeout - exceeded maximum wait time'
        }
        
    except Exception as e:
        logger.error(f"Error executing Athena query: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for AgentCore Gateway.
    Executes predefined Athena queries based on tool name.
    
    Args:
        event: Contains parameters from the tool invocation
        context: Lambda context with AgentCore metadata
        
    Returns:
        Query results in JSON format
    """
    try:
        # Extract tool name from context
        delimiter = "___"
        original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        logger.info(f"Processing tool: {tool_name}")
        logger.info(f"Event parameters: {json.dumps(event)}")
        
        # Get the query template
        if tool_name not in PREDEFINED_QUERIES:
            return {
                'success': False,
                'error': f'Unknown tool: {tool_name}'
            }
        
        query_template = PREDEFINED_QUERIES[tool_name]
        
        # Format query with parameters from event
        try:
            query = query_template.format(**event)
        except KeyError as e:
            return {
                'success': False,
                'error': f'Missing required parameter: {str(e)}'
            }
        
        logger.info(f"Executing query: {query}")
        
        # Execute the query
        result = execute_athena_query(query)
        
        # Format response for the agent
        if result['success']:
            return {
                'status': 'success',
                'data': result['rows'],
                'metadata': {
                    'columns': result['columns'],
                    'row_count': result['row_count']
                }
            }
        else:
            return {
                'status': 'error',
                'error': result['error']
            }
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }
