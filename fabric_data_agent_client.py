#!/usr/bin/env python3
"""
Fabric Data Agent External Client

A standalone Python client for calling Microsoft Fabric Data Agents from outside
of the Fabric environment using interactive browser authentication.

Requirements:
- azure-identity
- openai
- python-dotenv (optional, for environment variables)

Usage:
1. Set your TENANT_ID and DATA_AGENT_URL in the script or environment variables
2. Run the script - it will open a browser for authentication
3. The client will fetch a bearer token and make calls to your data agent
"""

import time
import uuid
import json
import os
import warnings
from typing import Optional
from azure.identity import InteractiveBrowserCredential
from openai import OpenAI

# Suppress OpenAI Assistants API deprecation warnings
# (Fabric Data Agents don't support the newer Responses API yet)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*Assistants API is deprecated.*"
)

# Optional: Load from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class FabricDataAgentClient:
    """
    Client for calling Microsoft Fabric Data Agents from external applications.
    
    This client handles:
    - Interactive browser authentication with Azure AD
    - Automatic token refresh
    - Bearer token management for API calls
    - Proper cleanup of resources
    """
    
    def __init__(self, tenant_id: str, data_agent_url: str):
        """
        Initialize the Fabric Data Agent client.
        
        Args:
            tenant_id (str): Your Azure tenant ID
            data_agent_url (str): The published URL of your Fabric Data Agent
        """
        self.tenant_id = tenant_id
        self.data_agent_url = data_agent_url
        self.credential = None
        self.token = None
        
        # Validate inputs
        if not tenant_id:
            raise ValueError("tenant_id is required")
        if not data_agent_url:
            raise ValueError("data_agent_url is required")
        
        print(f"Initializing Fabric Data Agent Client...")
        print(f"Tenant ID: {tenant_id}")
        print(f"Data Agent URL: {data_agent_url}")
        
        self._authenticate()
    
    def _authenticate(self):
        """
        Perform interactive browser authentication and get initial token.
        """
        try:
            print("\n🔐 Starting authentication...")
            print("A browser window will open for you to sign in to your Microsoft account.")
            
            # Create credential for interactive authentication
            self.credential = InteractiveBrowserCredential(
                tenant_id=self.tenant_id,
                # Optional: specify redirect_uri if needed
                # redirect_uri="http://localhost:8400"
            )
            
            # Get initial token
            self._refresh_token()
            
            print("✅ Authentication successful!")
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            raise
    
    def _refresh_token(self):
        """
        Refresh the authentication token.
        """
        try:
            print("🔄 Refreshing authentication token...")
            if self.credential is None:
                raise ValueError("No credential available")
            self.token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
            print(f"✅ Token obtained, expires at: {time.ctime(self.token.expires_on)}")
            
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            raise
    
    def _get_openai_client(self) -> OpenAI:
        """
        Create an OpenAI client configured for Fabric Data Agent calls.
        
        Returns:
            OpenAI: Configured OpenAI client
        """
        # Check if token needs refresh (refresh 5 minutes before expiry)
        if self.token and self.token.expires_on <= (time.time() + 300):
            self._refresh_token()
        
        if not self.token:
            raise ValueError("No valid authentication token available")
        
        return OpenAI(
            api_key="",  # Not used - we use Bearer token
            base_url=self.data_agent_url,
            default_query={"api-version": "2024-05-01-preview"},
            default_headers={
                "Authorization": f"Bearer {self.token.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "ActivityId": str(uuid.uuid4())
            }
        )
    
    def ask(self, question: str, timeout: int = 120) -> str:
        """
        Ask a question to the Fabric Data Agent.
        
        Args:
            question (str): The question to ask
            timeout (int): Maximum time to wait for response in seconds
            
        Returns:
            str: The response from the data agent
        """
        if not question.strip():
            raise ValueError("Question cannot be empty")
        
        print(f"\n❓ Asking: {question}")
        
        try:
            client = self._get_openai_client()
            
            # Create assistant without specifying model or instructions
            assistant = client.beta.assistants.create(model="not used")
            
            # Create thread and send message
            thread = client.beta.threads.create()
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Start the run
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            # Monitor the run with timeout
            start_time = time.time()
            while run.status in ["queued", "in_progress"]:
                if time.time() - start_time > timeout:
                    print(f"⏰ Request timed out after {timeout} seconds")
                    break
                
                print(f"⏳ Status: {run.status}")
                time.sleep(2)
                
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            print(f"✅ Final status: {run.status}")
            
            # Get the response messages
            messages = client.beta.threads.messages.list(
                thread_id=thread.id,
                order="asc"
            )

            # Extract assistant responses
            responses = []
            for msg in messages.data:
                if msg.role == "assistant":
                    try:
                        content = msg.content[0]
                        # Handle different content types safely
                        if hasattr(content, 'text'):
                            text_content = getattr(content, 'text', None)
                            if text_content is not None and hasattr(text_content, 'value'):
                                responses.append(text_content.value)
                            elif text_content is not None:
                                responses.append(str(text_content))
                            else:
                                responses.append(str(content))
                        else:
                            responses.append(str(content))
                    except (IndexError, AttributeError):
                        responses.append(str(msg.content))
            
            # Clean up resources
            try:
                client.beta.threads.delete(thread_id=thread.id)
            except Exception as cleanup_error:
                print(f"⚠️ Cleanup warning: {cleanup_error}")
            
            # Return the response
            if responses:
                return "\n".join(responses)
            else:
                return "No response received from the data agent."
        
        except Exception as e:
            print(f"❌ Error calling data agent: {e}")
            return f"Error: {e}"
    
    def get_run_details(self, question: str) -> dict:
        """
        Ask a question and return detailed run information including steps.
        
        Args:
            question (str): The question to ask
            
        Returns:
            dict: Detailed response including run steps, metadata, and SQL queries if lakehouse data source
        """
        print(f"\n🔍 Getting detailed run info for: {question}")
        
        try:
            client = self._get_openai_client()
            
            # Create assistant and thread without specifying model or instructions
            assistant = client.beta.assistants.create(model="not used")
            thread = client.beta.threads.create()
            
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Start and monitor run
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            while run.status in ["queued", "in_progress"]:
                print(f"⏳ Status: {run.status}")
                time.sleep(2)
                run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            
            # Get detailed run steps
            steps = client.beta.threads.runs.steps.list(
                thread_id=thread.id,
                run_id=run.id
            )
            
            # Get messages
            messages = client.beta.threads.messages.list(
                thread_id=thread.id,
                order="asc"
            )
            
            # Extract SQL queries and data from steps if lakehouse data source is detected
            sql_analysis = self._extract_sql_queries_with_data(steps)
            
            # Also try the old regex method as backup
            if not sql_analysis["queries"]:
                regex_queries = self._extract_sql_queries(steps)
                if regex_queries:
                    sql_analysis["queries"] = regex_queries
                    sql_analysis["data_retrieval_query"] = regex_queries[0] if regex_queries else None
            
            # Also extract data from the final assistant message
            messages_data = messages.model_dump()
            assistant_messages = [msg for msg in messages_data.get('data', []) if msg.get('role') == 'assistant']
            if assistant_messages:
                latest_message = assistant_messages[-1]
                content = latest_message.get('content', [])
                if content and len(content) > 0:
                    # Extract text content
                    text_content = ""
                    if isinstance(content[0], dict):
                        if 'text' in content[0]:
                            if isinstance(content[0]['text'], dict) and 'value' in content[0]['text']:
                                text_content = content[0]['text']['value']
                            else:
                                text_content = str(content[0]['text'])
                    else:
                        text_content = str(content[0])
                    
                    # Extract structured data from the assistant's text response
                    if text_content:
                        text_data_preview = self._extract_data_from_text_response(text_content)
                        if text_data_preview:
                            # Add the text-based data preview
                            if sql_analysis["queries"]:
                                # If we have queries but no data previews, or empty previews, use the text-based one
                                if not sql_analysis["data_previews"] or not any(sql_analysis["data_previews"]):
                                    sql_analysis["data_previews"] = [text_data_preview]
                                else:
                                    # Add to existing previews
                                    sql_analysis["data_previews"].append(text_data_preview)
                                
                                # If we don't have a specific data retrieval query identified, use the first query
                                if not sql_analysis["data_retrieval_query"] and sql_analysis["queries"]:
                                    sql_analysis["data_retrieval_query"] = sql_analysis["queries"][0]
                                    sql_analysis["data_retrieval_query_index"] = 1
            
            # Clean up
            try:
                client.beta.threads.delete(thread_id=thread.id)
            except Exception as cleanup_error:
                print(f"⚠️ Warning: Thread cleanup failed: {cleanup_error}")
            
            result = {
                "question": question,
                "run_status": run.status,
                "run_steps": steps.model_dump(),
                "messages": messages.model_dump(),
                "timestamp": time.time()
            }
            
            # Add SQL analysis if found
            if sql_analysis["queries"]:
                result["sql_queries"] = sql_analysis["queries"]
                result["sql_data_previews"] = sql_analysis["data_previews"]
                result["data_retrieval_query"] = sql_analysis["data_retrieval_query"]
                
                print(f"🗃️ Found {len(sql_analysis['queries'])} SQL queries in lakehouse operations")
                
                for i, query in enumerate(sql_analysis["queries"], 1):
                    print(f"📄 SQL Query {i}:")
                    print(f"   {query}")
                    
                    # Show data preview if this query retrieved data
                    if i == sql_analysis["data_retrieval_query_index"]:
                        print(f"   🎯 This query retrieved the data!")
                        if sql_analysis["data_previews"][i-1]:
                            print(f"   📊 Data Preview:")
                            preview = sql_analysis["data_previews"][i-1]
                            
                            # Check if the preview is a raw markdown table (single item)
                            if len(preview) == 1 and '\n' in preview[0] and '|' in preview[0]:
                                # This is a raw markdown table, print it directly
                                print(preview[0])
                            else:
                                # This is parsed row data, print line by line
                                for line in preview[:5]:  # Show first 5 lines
                                    print(f"      {line}")
                                if len(preview) > 5:
                                    print(f"      ... and {len(preview) - 5} more lines")
                    print()  # Empty line for readability
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting run details: {e}")
            return {"error": str(e)}

    def get_raw_run_response(self, question: str, timeout: int = 120) -> dict:
        """
        Ask a question and return the complete raw response including all run details.
        This is useful when you need to parse or analyze the full response structure.
        
        Args:
            question (str): The question to ask
            timeout (int): Maximum time to wait for response in seconds
            
        Returns:
            dict: Complete raw response with run steps, messages, and metadata
        """
        if not question.strip():
            raise ValueError("Question cannot be empty")
        
        print(f"\n🔍 Getting raw response for: {question}")
        
        try:
            client = self._get_openai_client()
            
            # Create assistant and thread
            assistant = client.beta.assistants.create(model="not used")
            thread = client.beta.threads.create()
            
            # Send the question
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Start the run
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            # Monitor the run with timeout
            start_time = time.time()
            while run.status in ["queued", "in_progress"]:
                if time.time() - start_time > timeout:
                    print(f"⏰ Request timed out after {timeout} seconds")
                    break
                
                print(f"⏳ Status: {run.status}")
                time.sleep(2)
                
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            print(f"✅ Final status: {run.status}")
            
            # Get all run details
            steps = client.beta.threads.runs.steps.list(
                thread_id=thread.id,
                run_id=run.id
            )
            
            messages = client.beta.threads.messages.list(
                thread_id=thread.id,
                order="asc"
            )
            
            # Clean up resources
            try:
                client.beta.threads.delete(thread_id=thread.id)
            except Exception as cleanup_error:
                print(f"⚠️ Cleanup warning: {cleanup_error}")
            
            # Return complete raw response
            return {
                "question": question,
                "run": run.model_dump(),
                "steps": steps.model_dump(),
                "messages": messages.model_dump(),
                "timestamp": time.time(),
                "timeout": timeout,
                "success": run.status == "completed"
            }
            
        except Exception as e:
            print(f"❌ Error getting raw response: {e}")
            return {
                "question": question,
                "error": str(e),
                "timestamp": time.time(),
                "success": False
            }

    def _extract_sql_queries_with_data(self, steps) -> dict:
        """
        Extract SQL queries from run steps using direct JSON parsing and output analysis.
        
        Args:
            steps: The run steps from the OpenAI API
            
        Returns:
            dict: Contains queries, data previews, and which query retrieved data
        """
        sql_queries = []
        data_previews = []
        data_retrieval_query = None
        data_retrieval_query_index = None
        
        try:
            for step_idx, step in enumerate(steps.data):
                if hasattr(step, 'step_details') and step.step_details:
                    step_details = step.step_details
                    
                    # Check for tool calls which typically contain the SQL queries
                    if hasattr(step_details, 'tool_calls') and step_details.tool_calls:
                        for tool_idx, tool_call in enumerate(step_details.tool_calls):
                            # Extract SQL from function arguments
                            sql_from_args = self._extract_sql_from_function_args(tool_call)
                            if sql_from_args:
                                sql_queries.extend(sql_from_args)
                            
                            # Extract SQL from tool call output (where it's actually located in Fabric)
                            sql_from_output = self._extract_sql_from_output(tool_call)
                            if sql_from_output:
                                sql_queries.extend(sql_from_output)
                            
                            # Extract data from tool call output
                            data_preview = self._extract_structured_data_from_output(tool_call)
                            if data_preview:
                                # If we found data and SQL in this step, it's likely the retrieval query
                                if sql_from_args or sql_from_output:
                                    all_sql_this_call = sql_from_args + sql_from_output
                                    data_retrieval_query = all_sql_this_call[-1] if all_sql_this_call else None
                                    data_retrieval_query_index = len(sql_queries)
                            
                            data_previews.append(data_preview)
        
        except Exception as e:
            print(f"⚠️ Warning: Could not extract SQL queries: {e}")
        
        # Remove duplicates while preserving order
        unique_queries = list(dict.fromkeys(sql_queries))
        
        return {
            "queries": unique_queries,
            "data_previews": data_previews,
            "data_retrieval_query": data_retrieval_query,
            "data_retrieval_query_index": data_retrieval_query_index
        }

    def _extract_sql_from_function_args(self, tool_call) -> list:
        """
        Extract SQL queries from tool call function arguments.
        
        Args:
            tool_call: OpenAI tool call object
            
        Returns:
            list: SQL queries found
        """
        import json
        sql_queries = []
        
        try:
            if hasattr(tool_call, 'function') and tool_call.function:
                if hasattr(tool_call.function, 'arguments'):
                    args_str = tool_call.function.arguments
                    
                    # Parse the arguments JSON
                    args = json.loads(args_str)
                    
                    if isinstance(args, dict):
                        # Common keys where SQL queries are stored in Fabric Data Agents
                        sql_keys = ['sql', 'query', 'sql_query', 'statement', 'command', 'code']
                        
                        for key in sql_keys:
                            if key in args and args[key]:
                                sql_query = str(args[key]).strip()
                                if sql_query and len(sql_query) > 10:  # Basic validation
                                    sql_queries.append(sql_query)
                        
                        # Also check for nested structures
                        for key, value in args.items():
                            if isinstance(value, dict):
                                for nested_key in sql_keys:
                                    if nested_key in value and value[nested_key]:
                                        sql_query = str(value[nested_key]).strip()
                                        if sql_query and len(sql_query) > 10:
                                            sql_queries.append(sql_query)
        
        except (json.JSONDecodeError, AttributeError) as e:
            # If JSON parsing fails, fall back to basic string search
            try:
                args_str = str(tool_call.function.arguments)
                # Look for common SQL patterns in the string
                if any(keyword in args_str.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']):
                    # Use minimal regex as fallback
                    import re
                    sql_pattern = r'"(?:sql|query|statement|code)"\s*:\s*"([^"]+)"'
                    matches = re.findall(sql_pattern, args_str, re.IGNORECASE)
                    sql_queries.extend([match.strip() for match in matches if len(match.strip()) > 10])
            except Exception as parse_error:
                print(f"⚠️ Warning: Could not parse tool call arguments: {parse_error}")
        
        return sql_queries

    def _extract_sql_from_output(self, tool_call) -> list:
        """
        Extract SQL queries from tool call output.
        
        Args:
            tool_call: OpenAI tool call object
            
        Returns:
            list: SQL queries found in output
        """
        import json
        import re
        sql_queries = []
        
        try:
            if hasattr(tool_call, 'output') and tool_call.output:
                output_str = str(tool_call.output)
                
                # First try to parse as JSON
                try:
                    output_json = json.loads(output_str)
                    
                    if isinstance(output_json, dict):
                        # Look for SQL in common keys
                        sql_keys = ['sql', 'query', 'sql_query', 'statement', 'command', 'code', 'generated_code']
                        for key in sql_keys:
                            if key in output_json and output_json[key]:
                                sql_query = str(output_json[key]).strip()
                                if sql_query and len(sql_query) > 10:
                                    sql_queries.append(sql_query)
                        
                        # Check nested structures
                        for key, value in output_json.items():
                            if isinstance(value, dict):
                                for nested_key in sql_keys:
                                    if nested_key in value and value[nested_key]:
                                        sql_query = str(value[nested_key]).strip()
                                        if sql_query and len(sql_query) > 10:
                                            sql_queries.append(sql_query)
                
                except json.JSONDecodeError:
                    # If not JSON, use regex to find SQL patterns
                    pass
                
                # Always also try regex as backup/additional method
                if any(keyword in output_str.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM']):
                    # Enhanced regex patterns for SQL extraction
                    sql_patterns = [
                        r'"(?:sql|query|statement|code|generated_code)"\s*:\s*"([^"]+)"',
                        r"'(?:sql|query|statement|code|generated_code)'\s*:\s*'([^']+)'",
                        r'(SELECT\s+.*?FROM\s+.*?)(?=\s*[;}"\'\n]|\s*$)',
                        r'(INSERT\s+INTO\s+.*?)(?=\s*[;}"\'\n]|\s*$)',
                        r'(UPDATE\s+.*?SET\s+.*?)(?=\s*[;}"\'\n]|\s*$)',
                        r'(DELETE\s+FROM\s+.*?)(?=\s*[;}"\'\n]|\s*$)'
                    ]
                    
                    for pattern in sql_patterns:
                        matches = re.findall(pattern, output_str, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            clean_query = match.strip().replace('\\n', '\n').replace('\\t', '\t')
                            clean_query = re.sub(r'\s+', ' ', clean_query)
                            if len(clean_query) > 10:
                                sql_queries.append(clean_query)
        
        except Exception as e:
            print(f"⚠️ Warning: Could not extract SQL from output: {e}")
        
        return sql_queries

    def _extract_structured_data_from_output(self, tool_call) -> list:
        """
        Extract structured data from tool call output using JSON parsing.
        
        Args:
            tool_call: OpenAI tool call object
            
        Returns:
            list: Formatted data lines
        """
        import json
        data_lines = []
        
        try:
            if hasattr(tool_call, 'output') and tool_call.output:
                output_str = str(tool_call.output)
                
                # Try to parse as JSON first
                try:
                    data = json.loads(output_str)
                    
                    if isinstance(data, list) and len(data) > 0:
                        # Handle list of records (typical query result)
                        if isinstance(data[0], dict):
                            headers = list(data[0].keys())
                            data_lines.append("| " + " | ".join(headers) + " |")
                            data_lines.append("|" + "---|" * len(headers))
                            
                            for row in data[:10]:  # Limit to first 10 rows
                                values = [str(row.get(h, "")) for h in headers]
                                data_lines.append("| " + " | ".join(values) + " |")
                    
                    elif isinstance(data, dict):
                        # Handle single record or structured response
                        if 'data' in data and isinstance(data['data'], list):
                            # Nested data structure
                            return self._format_list_data(data['data'])
                        elif 'results' in data and isinstance(data['results'], list):
                            # Results structure
                            return self._format_list_data(data['results'])
                        else:
                            # Single record
                            data_lines.append("| Key | Value |")
                            data_lines.append("|---|---|")
                            for key, value in data.items():
                                data_lines.append(f"| {key} | {str(value)} |")
                
                except json.JSONDecodeError:
                    # If not JSON, look for other structured formats
                    data_lines = self._extract_data_preview(output_str)
        
        except Exception as e:
            print(f"⚠️ Warning: Could not extract structured data: {e}")
        
        return data_lines

    def _extract_markdown_table(self, text: str) -> str:
        """
        Extract raw markdown table from the assistant's text response.
        
        Args:
            text (str): The assistant's text response
            
        Returns:
            str: Raw markdown table if found, or empty string if no table found
        """
        lines = text.split('\n')
        table_lines = []
        in_table = False
        header_found = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line contains markdown table separators
            if '|' in line_stripped and ('---' in line_stripped or '-' in line_stripped and line_stripped.count('-') > 3):
                table_lines.append(line)
                in_table = True
                header_found = True
            elif '|' in line_stripped and (in_table or not header_found):
                # This is a table row (header or data row)
                table_lines.append(line)
                in_table = True
            elif in_table and line_stripped == '':
                # Empty line - might continue table, add it but don't break yet
                table_lines.append(line)
            elif in_table and '|' not in line_stripped and line_stripped != '':
                # Non-table line after we were in a table - end of table
                break
        
        # Clean up trailing empty lines
        while table_lines and table_lines[-1].strip() == '':
            table_lines.pop()
        
        # Return the raw markdown table if we found at least a header and separator
        if len(table_lines) >= 2:
            return '\n'.join(table_lines)
        else:
            return ""

    def _extract_data_from_text_response(self, text_content: str) -> list:
        """
        Extract structured data from the assistant's text response.
        First tries to find raw markdown tables, then falls back to numbered list parsing.
        
        Args:
            text_content (str): The text content from the assistant
            
        Returns:
            list: Formatted data lines (raw markdown table as single item, or parsed rows)
        """
        import re
        
        # First, try to extract a raw markdown table
        markdown_table = self._extract_markdown_table(text_content)
        if markdown_table:
            # Return the raw markdown table as a single formatted block
            return [markdown_table]
        
        # Fallback to numbered list parsing (existing logic)
        data_lines = []
        
        try:
            lines = text_content.split('\n')
            
            # Look for numbered lists with data (like the example output)
            numbered_pattern = r'^\d+\.\s+'
            data_rows = []
            
            for line in lines:
                line = line.strip()
                if re.match(numbered_pattern, line):
                    # Remove the number prefix
                    clean_line = re.sub(numbered_pattern, '', line)
                    data_rows.append(clean_line)
            
            if data_rows and len(data_rows) > 0:
                # Try to parse the structured data from the text
                first_row = data_rows[0]
                if ':' in first_row:
                    # Parse key-value format
                    # Example: "Date: 4/29/2020, State: WI, Positive: 7,660, ..."
                    
                    # Extract headers from first row
                    headers = []
                    values_first_row = []
                    
                    pairs = first_row.split(', ')
                    for pair in pairs:
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            headers.append(key.strip())
                            values_first_row.append(value.strip())
                    
                    if headers:
                        # Create table format
                        data_lines.append("| " + " | ".join(headers) + " |")
                        data_lines.append("|" + "---|" * len(headers))
                        
                        # Add first row
                        data_lines.append("| " + " | ".join(values_first_row) + " |")
                        
                        # Parse remaining rows
                        for row in data_rows[1:]:
                            values = []
                            pairs = row.split(', ')
                            for pair in pairs:
                                if ':' in pair:
                                    _, value = pair.split(':', 1)
                                    values.append(value.strip())
                            
                            if len(values) == len(headers):
                                data_lines.append("| " + " | ".join(values) + " |")
                            
                        return data_lines
                
                # If we couldn't parse structured format, return the raw rows as-is
                if not data_lines and data_rows:
                    # Just show the numbered list data
                    return [f"Row {i+1}: {row}" for i, row in enumerate(data_rows)]
            
            # Alternative: Look for table-like structures in the text
            # Check if there are lines that look like table rows
            potential_table_lines = []
            for line in lines:
                line = line.strip()
                # Look for lines with multiple separators that could be table data
                if line and ('|' in line or line.count(',') >= 2 or line.count(':') >= 2):
                    potential_table_lines.append(line)
            
            if potential_table_lines and not data_lines:
                return potential_table_lines[:10]  # Return first 10 lines
        
        except Exception as e:
            print(f"⚠️ Warning: Could not extract data from text response: {e}")
        
        return data_lines

    def _format_list_data(self, data_list) -> list:
        """
        Format a list of data records into table format.
        """
        data_lines = []
        
        if len(data_list) > 0 and isinstance(data_list[0], dict):
            headers = list(data_list[0].keys())
            data_lines.append("| " + " | ".join(headers) + " |")
            data_lines.append("|" + "---|" * len(headers))
            
            for row in data_list[:10]:  # Limit to first 10 rows
                values = [str(row.get(h, "")) for h in headers]
                data_lines.append("| " + " | ".join(values) + " |")
        
        return data_lines

    def _extract_data_preview(self, text: str) -> list:
        """
        Extract data preview from text output.
        
        Args:
            text (str): Text to search for tabular data
            
        Returns:
            list: List of data rows found
        """
        import re
        import json
        
        data_lines = []
        
        try:
            # Look for JSON-like data structures
            json_pattern = r'\[[\s\S]*?\]'
            json_matches = re.findall(json_pattern, text)
            
            for match in json_matches:
                try:
                    # Try to parse as JSON
                    data = json.loads(match)
                    if isinstance(data, list) and len(data) > 0:
                        # Convert to readable format
                        if isinstance(data[0], dict):
                            # List of dictionaries (typical query result)
                            headers = list(data[0].keys())
                            data_lines.append("| " + " | ".join(headers) + " |")
                            data_lines.append("|" + "---|" * len(headers))
                            
                            for row in data[:10]:  # Limit to first 10 rows
                                values = [str(row.get(h, "")) for h in headers]
                                data_lines.append("| " + " | ".join(values) + " |")
                        break  # Found valid JSON data
                except json.JSONDecodeError:
                    continue
            
            # If no JSON found, look for pipe-separated tables
            if not data_lines:
                lines = text.split('\n')
                table_lines = []
                
                for line in lines:
                    # Look for lines that contain multiple pipe characters (table format)
                    if line.count('|') >= 2:
                        table_lines.append(line.strip())
                    elif table_lines and line.strip() == "":
                        # End of table
                        break
                    elif table_lines and not line.strip().startswith('|'):
                        # Non-table line after table started
                        break
                
                if table_lines:
                    data_lines = table_lines[:15]  # Limit to first 15 lines
            
            # Look for CSV-like data
            if not data_lines:
                lines = text.split('\n')
                csv_lines = []
                
                for line in lines:
                    # Look for comma-separated values with consistent column count
                    if ',' in line and len(line.split(',')) >= 2:
                        csv_lines.append(line.strip())
                        if len(csv_lines) >= 10:  # Limit preview
                            break
                    elif csv_lines:
                        break
                
                if len(csv_lines) > 1:  # At least header + one data row
                    data_lines = csv_lines
        
        except Exception as e:
            print(f"⚠️ Warning: Could not extract data preview: {e}")
        
        return data_lines

    def _extract_sql_queries(self, steps) -> list:
        """
        Extract SQL queries from run steps when lakehouse data source is used.
        
        Args:
            steps: The run steps from the OpenAI API
            
        Returns:
            list: List of SQL queries found in the steps
        """
        sql_queries = []
        
        try:
            for step in steps.data:
                if hasattr(step, 'step_details') and step.step_details:
                    step_details = step.step_details
                    
                    # Check for tool calls that might contain SQL
                    if hasattr(step_details, 'tool_calls') and step_details.tool_calls:
                        for tool_call in step_details.tool_calls:
                            # Look for SQL queries in tool call details
                            if hasattr(tool_call, 'function') and tool_call.function:
                                if hasattr(tool_call.function, 'arguments'):
                                    args_str = str(tool_call.function.arguments)
                                    # Look for SQL patterns in arguments
                                    sql_queries.extend(self._find_sql_in_text(args_str))
                            
                            # Check tool call outputs for SQL
                            if hasattr(tool_call, 'output') and tool_call.output:
                                output_str = str(tool_call.output)
                                sql_queries.extend(self._find_sql_in_text(output_str))
                    
                    # Check step details for any SQL content
                    step_str = str(step_details)
                    sql_queries.extend(self._find_sql_in_text(step_str))
        
        except Exception as e:
            print(f"⚠️ Warning: Could not extract SQL queries: {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in sql_queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        return unique_queries

    def _find_sql_in_text(self, text: str) -> list:
        """
        Find SQL queries in text using pattern matching.
        
        Args:
            text (str): Text to search for SQL queries
            
        Returns:
            list: List of SQL queries found
        """
        import re
        
        sql_queries = []
        
        # Common SQL keywords that indicate a query
        sql_patterns = [
            r'(SELECT\s+.*?FROM\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\)|\s*,)',
            r'(INSERT\s+INTO\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\))',
            r'(UPDATE\s+.*?SET\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\))',
            r'(DELETE\s+FROM\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\))',
            r'(CREATE\s+TABLE\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\))',
            r'(ALTER\s+TABLE\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\))',
            r'(DROP\s+TABLE\s+.*?)(?=\s*;|\s*$|\s*\}|\s*\))'
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Clean up the SQL query
                clean_query = match.strip().replace('\n', ' ').replace('\t', ' ')
                clean_query = re.sub(r'\s+', ' ', clean_query)  # Normalize whitespace
                if len(clean_query) > 10:  # Filter out very short matches
                    sql_queries.append(clean_query)
        
        return sql_queries


def main(questions: list, raw_response: bool = False):
    """
    Example usage of the Fabric Data Agent Client.
    """
    # Configuration - Update these with your actual values
    TENANT_ID = os.getenv("TENANT_ID", "your-tenant-id-here")
    DATA_AGENT_URL = os.getenv("DATA_AGENT_URL", "your-data-agent-url-here")
    
    # Validate configuration
    if TENANT_ID == "your-tenant-id-here" or DATA_AGENT_URL == "your-data-agent-url-here":
        print("❌ Please update TENANT_ID and DATA_AGENT_URL with your actual values")
        print("\nYou can either:")
        print("1. Edit this script and update the values directly")
        print("2. Set environment variables: TENANT_ID and DATA_AGENT_URL")
        print("3. Create a .env file with these variables")
        return
    
    try:
        # Initialize the client (this will trigger authentication)
        client = FabricDataAgentClient(
            tenant_id=TENANT_ID,
            data_agent_url=DATA_AGENT_URL
        )
        
        print("\n" + "="*60)
        print("🤖 Fabric Data Agent Client - Ready!")
        print("="*60)
        
        for i, question in enumerate(questions, 1):
            if raw_response == True: #printing (mostly) raw response
                response = client.get_raw_run_response(question)
                print(f"\n💬 Response:")
                print("-" * 50)
                print(json.dumps(response, indent=2, default=str))
                print("-" * 50)
            else:
                response = client.ask(question)
                print(f"\n💬 Response:")
                print("-" * 50)
                print(response)
                print("-" * 50)
            
            # Wait between requests
            if i < len(questions):
                n = 1
                print(f"\nWaiting {n} seconds before next question...")
                time.sleep(n)
        
        print("\n✅ All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # Example questions
    questions = [
        "What data is available in the lakehouse?",
        "Show me the top 5 records from any available table",
        "What are the column names and types in the main tables?"
    ]
    main(questions, raw_response=False)
