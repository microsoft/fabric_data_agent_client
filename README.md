# Fabric Data Agent External Client

A standalone Python client for calling Microsoft Fabric Data Agents from outside of the Fabric environment using interactive browser authentication.

⚠️This is in Preview and API can change until GA.

## Overview

This client enables you to interact with your Microsoft Fabric Data Agents from external applications, scripts, or environments. It handles Azure authentication, token management, and provides a simple interface for asking questions to your data agents. Feel free to inspect the example usage for sample client code.

## Features

- 🔐 **Interactive Browser Authentication** - Secure Azure AD authentication with automatic browser flow
- 🔄 **Automatic Token Refresh** - Handles token expiration and refresh automatically
- 🧹 **Resource Cleanup** - Properly manages OpenAI threads and resources
- ⚡ **Simple API** - Easy-to-use interface for querying your data agents
- 📊 **Detailed Responses** - Get both simple answers and detailed run information
- ⏰ **Timeout Handling** - Configurable timeouts for long-running queries
- 🛡️ **Error Handling** - Comprehensive error handling and user-friendly messages

## Requirements

- Python 3.7+
- Azure tenant with Fabric Data Agent access
- Published Fabric Data Agent URL

## Installation

1. Clone or download this repository:

```bash
git clone <repository-url>
cd fabric_data_agent_client
```

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

You can configure the client in three ways:

### Option 1: Environment Variables

```bash
export TENANT_ID=<your-azure-tenant-id>
export DATA_AGENT_URL=<your-fabric-data-agent-url>
```

### Option 2: .env File

Create a `.env` file in the project directory:

```env
TENANT_ID=<your-azure-tenant-id>
DATA_AGENT_URL=<your-fabric-data-agent-url>
```

### Option 3: Direct Configuration

Edit the values directly in your script:

```python
TENANT_ID = "<your-azure-tenant-id>"
DATA_AGENT_URL = "<your-fabric-data-agent-url>"
```

## Usage

### Basic Usage

```python
from fabric_data_agent_client import FabricDataAgentClient

# Initialize the client (will open browser for authentication)
client = FabricDataAgentClient(
    tenant_id="your-tenant-id",
    data_agent_url="your-data-agent-url"
)

# Ask a simple question
response = client.ask("What data is available in the lakehouse?")
print(response)
```

### Thread Management and Conversation Persistence

The Fabric Data Agent Client supports persistent threads, allowing you to maintain conversation context across multiple questions. This is essential for complex analysis workflows where follow-up questions depend on previous context.

#### Creating and Managing Threads

```python
# Method 1: Let the client manage thread creation
# Each call creates a new thread (no conversation history) unless you specify an existing thread name
response1 = client.ask("What data is available?")
response2 = client.ask("Show me the top 5 records")  # No context from response1

# Method 2: Use named threads for conversation persistence or managing multiple threads
thread_name = "my_data_analysis_session"

# First question creates the thread
response1 = client.ask("What data is available?", thread_name=thread_name)

# Follow-up questions maintain context
response2 = client.ask("Show me the top 5 records", thread_name=thread_name)
response3 = client.ask("What about the bottom 5?", thread_name=thread_name)
```

#### Advanced Thread Management

```python
# Explicitly create or retrieve a thread
thread = client._get_or_create_new_thread(
    data_agent_url=client.data_agent_url,
    thread_name="detailed_analysis_session"
)

print(f"Thread Name: {thread['name']}")
print(f"Thread ID: {thread['id']}")

# Use the thread for multiple related questions
questions = [
    "What tables are available in the lakehouse?",
    "Show me the schema of the largest table",
    "What's the data quality like in that table?"
]

for question in questions:
    response = client.ask(question, thread_name="detailed_analysis_session")
    print(f"Q: {question}")
    print(f"A: {response}\n")
```

#### Thread Management Best Practices

**Important**: Your client application is responsible for managing thread names. The client does not automatically persist or remember thread names between application restarts. If you do not delete a thread and ask a question without explicitly creating a new thread, you may continue a conversation on an existing thread so we recommend explicitely creating a new thread via `_get_existing_or_create_thread(data_agent_url=<data_agent_url>,
    thread_name=<thread_name>)`

### Getting Detailed Run Information with SQL Query Extraction (Experimental - relies on parsing response)

```python
# Get detailed run information including steps and SQL queries for lakehouse data sources
run_details = client.get_run_details("What are the top 5 records from any table?")

print(f"Run Status: {run_details['run_status']}")
print(f"Steps Count: {len(run_details['run_steps']['data'])}")

# Check if SQL queries were extracted (indicates lakehouse data source)
if "sql_queries" in run_details and run_details["sql_queries"]:
    print("Lakehouse Data Source Detected!")
    
    # Show which query retrieved the data and preview the results
    if "data_retrieval_query" in run_details:
        print(f"Data Retrieved By: {run_details['data_retrieval_query']}")
        
        # Show data preview
        if "sql_data_previews" in run_details:
            preview = run_details["sql_data_previews"][0]  # First preview
            if preview:
                print("Data Preview:")
                for line in preview[:5]:
                    print(f"  {line}")
    
    # Optional: Show all SQL queries executed
    # for i, query in enumerate(run_details['sql_queries'], 1):
    #     print(f"  {i}. {query}")
```
### Getting Raw Run Response

```python
# Get raw response data for advanced analysis
response = client.get_raw_run_response("Show me sales data by region")

print(f"\n💬 Response:")
print("-" * 50)
print(json.dumps(response, indent=2, default=str))
print("-" * 50)
```

### Thread Management

The client supports persistent thread management, allowing you to maintain conversation context across multiple interactions:

```python
# Create or get an existing thread
thread = client._get_or_create_new_thread(
    data_agent_url="your-data-agent-url",
    thread_name="my_analysis_session"  # Your custom thread identifier
)

print(f"Thread Name: {thread['name']}")
print(f"Thread ID: {thread['id']}")

# Use the thread for questions - maintains conversation context
response1 = client.ask("What data is available?", thread_name="my_analysis_session")
response2 = client.ask("Show me the top 5 records", thread_name="my_analysis_session")

# The second question will have context from the first question
```

**Important**: To manage threads effectively, your client application must keep track of the `thread_name`. This identifier is used to:
- Retrieve existing threads for continued conversations
- Maintain conversation context across multiple questions  
- Organize different analysis sessions

```python
# Example: Managing multiple analysis sessions
sales_thread = "sales_analysis_2024"
inventory_thread = "inventory_review_q4"

# Sales analysis session
sales_response = client.ask("Show sales trends", thread_name=sales_thread)

# Separate inventory session
inventory_response = client.ask("Check inventory levels", thread_name=inventory_thread)

# Continue sales analysis with previous context
follow_up = client.ask("What about Q3 specifically?", thread_name=sales_thread)
```

### Running the Examples

The project includes example scripts you can run:

```bash
# Run the main example
python fabric_data_agent_client.py

# Run the simple usage example
python example_usage.py
```

## API Reference

### FabricDataAgentClient

#### `__init__(tenant_id: str, data_agent_url: str)`

Initialize the client with your Azure tenant ID and Fabric Data Agent URL.

**Parameters:**
- `tenant_id` (str): Your Azure tenant ID
- `data_agent_url` (str): The published URL of your Fabric Data Agent

#### `ask(question: str, timeout: int = 120, thread_name: str = None) -> str`

Ask a question to the data agent with optional thread management.

**Parameters:**
- `question` (str): The question to ask
- `timeout` (int, optional): Maximum time to wait for response in seconds. Default: 120
- `thread_name` (str, optional): Thread identifier for conversation persistence. Default: None (creates new thread)

**Returns:**
- `str`: The response from the data agent

**Example:**
```python
# Simple question (new thread each time)
response = client.ask("What data is available?")

# Question with thread persistence
response = client.ask("Show me sales data", thread_name="sales_analysis")
followup = client.ask("What about last quarter?", thread_name="sales_analysis")
```

#### `get_run_details(question: str, thread_name: str = None) -> dict`

Ask a question and return detailed run information including steps, SQL queries, and data previews if lakehouse data source is used.

**Parameters:**
- `question` (str): The question to ask
- `thread_name` (str, optional): Thread identifier for conversation persistence

**Returns:**
- `dict`: Detailed response including:
  - `question` (str): The original question asked
  - `run_status` (str): Status of the run execution
  - `run_steps` (dict): Execution steps and metadata  
  - `messages` (dict): Complete message history
  - `sql_queries` (list): List of SQL queries executed (if lakehouse data source)
  - `sql_data_previews` (list): Preview of data returned by queries
  - `data_retrieval_query` (str): The specific SQL query that retrieved the main data
  - `data_retrieval_query_index` (int): Index of the data retrieval query in the queries list
  - `timestamp` (float): Unix timestamp when the response was generated

#### `get_raw_run_response(question: str, timeout: int = 120, thread_name: str = None) -> dict`

Ask a question and return the complete raw response including all run details for advanced analysis.

**Parameters:**
- `question` (str): The question to ask
- `timeout` (int, optional): Maximum time to wait for response in seconds. Default: 120
- `thread_name` (str, optional): Thread identifier for conversation persistence

**Returns:**
- `dict`: Complete raw response including:
  - `question` (str): The original question
  - `run` (dict): Raw run object from OpenAI API
  - `steps` (dict): Raw steps data from OpenAI API
  - `messages` (dict): Raw messages data from OpenAI API
  - `timestamp` (float): Unix timestamp when response was generated
  - `timeout` (int): The timeout value used
  - `success` (bool): Whether the run completed successfully

#### `_get_or_create_new_thread(data_agent_url: str, thread_name: str = None) -> dict`

**Internal Method**: Get an existing thread or create a new one. This method is primarily for internal use but can be called directly for advanced thread management.

**Parameters:**
- `data_agent_url` (str): The data agent URL
- `thread_name` (str, optional): Custom thread identifier. If None, generates a unique name

**Returns:**
- `dict`: Thread information containing:
  - `id` (str): The actual thread ID used by the system
  - `name` (str): The human-readable thread name (extracted from system metadata)

**Important Notes:**

- **Thread Persistence**: The `thread_name` parameter enables conversation context across multiple questions
- **Client Responsibility**: Your application must track and manage `thread_name` values
- **Thread Isolation**: Different `thread_name` values create separate conversation contexts
- **Thread Cleanup**: Threads are automatically managed by the service; no manual cleanup required

**Thread Management Best Practices:**
```python
# Use descriptive thread names for different analysis sessions
sales_analysis = "sales_analysis_2024_q4"
inventory_review = "inventory_review_december"

# Keep thread names consistent across related questions
client.ask("Show sales trends", thread_name=sales_analysis)
client.ask("Compare with last quarter", thread_name=sales_analysis)  # Has context

# Use different thread names for unrelated analysis
client.ask("Check inventory levels", thread_name=inventory_review)  # Separate context
```

## Authentication Flow

1. When you initialize the client, it will automatically open your default browser
2. Sign in with your Microsoft account that has access to the Fabric environment
3. Grant permissions when prompted
4. The client will automatically obtain and manage the authentication token
5. Tokens are automatically refreshed before expiration

## Error Handling

The client includes comprehensive error handling for common scenarios:

- Invalid configuration (missing tenant ID or data agent URL)
- Authentication failures
- Network timeouts
- API errors
- Token expiration and refresh issues

All errors are logged with helpful messages and troubleshooting tips.

## Troubleshooting

### Common Issues

#### Authentication Fails

- Ensure your Azure account has access to the Fabric environment
- Check that your tenant ID is correct
- Verify you have permissions to access the specific data agent

#### Data Agent Not Responding

- Verify the data agent URL is correct and published
- Check if the data agent is running and accessible
- Ensure your Azure account has permissions to call the data agent

#### Dependency Issues

- Make sure all required packages are installed: `pip install -r requirements.txt`
- Update to the latest versions if you encounter compatibility issues

#### Timeout Issues

- Increase the timeout parameter for complex queries
- Check if your data agent has sufficient resources allocated

### Getting Help

1. Check the error messages - they include specific troubleshooting tips
2. Verify your configuration values are correct
3. Ensure you have the necessary Azure permissions
4. Test with simple queries first before trying complex ones

## Dependencies

- **azure-identity**: Handles Azure AD authentication
- **openai**: Provides the API client for interacting with the data agent
- **python-dotenv**: Optional, for loading environment variables from .env files

## Security Notes

- Authentication tokens are handled securely and automatically refreshed
- No credentials are stored persistently
- Interactive browser authentication ensures secure login
- Bearer tokens are used for API authentication
- Resources are properly cleaned up after each request

## License

This project is provided as-is for educational and development purposes. Please ensure you comply with Microsoft's terms of service when using Fabric Data Agents.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this client.

## Changelog

### v1.0.0

- Initial release
- Interactive browser authentication
- Basic question/answer functionality
- Detailed run information
- Automatic token refresh
- Resource cleanup
- Comprehensive error handling
