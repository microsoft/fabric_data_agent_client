#!/usr/bin/env python3
"""
Simple usage example for the Fabric Data Agent Client

This script demonstrates how to use the FabricDataAgentClient to call
a Fabric Data Agent from outside of the Fabric environment.
"""

import os
from fabric_data_agent_client import FabricDataAgentClient

def main():
    """
    Example usage of the Fabric Data Agent Client
    """
    # Set your configuration here or in environment variables
    TENANT_ID = os.getenv("TENANT_ID", "your-tenant-id-here")
    DATA_AGENT_URL = os.getenv("DATA_AGENT_URL", "your-data-agent-url-here")
    
    # Check if configuration is set
    if TENANT_ID == "your-tenant-id-here" or DATA_AGENT_URL == "your-data-agent-url-here":
        print("❌ Please set your TENANT_ID and DATA_AGENT_URL")
        print("\nOptions:")
        print("1. Set environment variables:")
        print("   export TENANT_ID='your-actual-tenant-id'")
        print("   export DATA_AGENT_URL='your-actual-data-agent-url'")
        print("\n2. Edit this script and replace the placeholder values")
        print("\n3. Create a .env file with these variables")
        return
    
    try:
        print("🚀 Starting Fabric Data Agent Client Example")
        print("=" * 60)
        
        # Initialize the client (this will trigger browser authentication)
        client = FabricDataAgentClient(
            tenant_id=TENANT_ID,
            data_agent_url=DATA_AGENT_URL
        )
        
        # Example 1: Simple question
        print("\n📋 Example 1: Simple Data Query")
        response = client.ask("What data is available in the lakehouse?")
        print(f"💬 Response: {response}")
        
        # Example 2: Another simple query
        print("\n📋 Example 2: Table Information Query")
        response = client.ask("Show me information about the tables in the lakehouse")
        print(f"💬 Response: {response}")
        
        # Example 3: Get detailed run information with SQL query extraction
        print("\n📋 Example 3: Detailed Run Analysis with SQL Query Extraction and Raw Markdown Tables")
        print("    (Now extracts raw markdown tables directly from agent responses when available)")
        run_details = client.get_run_details("Show me the top 5 records from any available table")
        
        if "error" not in run_details:
            print(f"✅ Run Status: {run_details['run_status']}")
            print(f"📊 Steps Count: {len(run_details['run_steps']['data'])}")
            print(f"📝 Messages Count: {len(run_details['messages']['data'])}")
            
            # Show the assistant's final response
            messages = run_details.get('messages', {}).get('data', [])
            assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
            if assistant_messages:
                print(f"\n💬 Agent Response:")
                latest_message = assistant_messages[-1]
                content = latest_message.get('content', [])
                if content and len(content) > 0:
                    # Handle different content types
                    if hasattr(content[0], 'text'):
                        print(f"   {content[0].text.value}")
                    elif isinstance(content[0], dict) and 'text' in content[0]:
                        if isinstance(content[0]['text'], dict) and 'value' in content[0]['text']:
                            print(f"   {content[0]['text']['value']}")
                        else:
                            print(f"   {content[0]['text']}")
                    else:
                        print(f"   {str(content[0])}")
            
            # Show the SQL query that retrieved data and its preview
            if "data_retrieval_query" in run_details and run_details["data_retrieval_query"]:
                print(f"\n🎯 SQL Query Used:")
                print(f"   {run_details['data_retrieval_query']}")
                
                # Show data preview if available
                if "sql_data_previews" in run_details and run_details["sql_data_previews"]:
                    data_retrieval_index = run_details.get("data_retrieval_query_index", 1) - 1
                    if 0 <= data_retrieval_index < len(run_details["sql_data_previews"]):
                        preview = run_details["sql_data_previews"][data_retrieval_index]
                        if preview:
                            print(f"\n📊 Data Preview:")
                            # Check if this is a raw markdown table (single item with newlines and pipes)
                            if len(preview) == 1 and '\n' in preview[0] and '|' in preview[0]:
                                # Raw markdown table - print directly with proper indentation
                                table_lines = preview[0].split('\n')
                                for line in table_lines:
                                    if line.strip():  # Skip empty lines
                                        print(f"   {line}")
                            else:
                                # Regular parsed data - print line by line
                                for line in preview[:10]:  # Show first 10 lines
                                    print(f"   {line}")
                                if len(preview) > 10:
                                    print(f"   ... and {len(preview) - 10} more lines")
                        else:
                            print(f"\n📊 No data preview available")
            elif "sql_queries" in run_details and run_details["sql_queries"]:
                print(f"\n🗃️ Lakehouse data source detected, but could not identify the specific data retrieval query")
                # Show just the first/main query instead of all
                if run_details["sql_queries"]:
                    print(f"\n🎯 SQL Query Used:")
                    print(f"   {run_details['sql_queries'][0]}")
                    
                    # Try to show data preview from any available source
                    preview_shown = False
                    if "sql_data_previews" in run_details and run_details["sql_data_previews"]:
                        for preview in run_details["sql_data_previews"]:
                            if preview:
                                print(f"\n📊 Data Preview:")
                                # Check if this is a raw markdown table
                                if len(preview) == 1 and '\n' in preview[0] and '|' in preview[0]:
                                    # Raw markdown table - print directly with proper indentation
                                    table_lines = preview[0].split('\n')
                                    for line in table_lines:
                                        if line.strip():  # Skip empty lines
                                            print(f"   {line}")
                                else:
                                    # Regular parsed data
                                    for line in preview[:10]:
                                        print(f"   {line}")
                                    if len(preview) > 10:
                                        print(f"   ... and {len(preview) - 10} more lines")
                                preview_shown = True
                                break
                    
                    if not preview_shown:
                        print(f"\n📊 No structured data preview available")
            else:
                print(f"\n📄 No lakehouse data source detected")
        else:
            print(f"❌ Error in detailed run: {run_details['error']}")
        
        print("\n✅ All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting tips:")
        print("- Ensure you have the required packages installed: pip install -r requirements.txt")
        print("- Check that your TENANT_ID and DATA_AGENT_URL are correct")
        print("- Make sure you have access to the Fabric Data Agent")
        print("- Verify your Azure account has the necessary permissions")

if __name__ == "__main__":
    main()
