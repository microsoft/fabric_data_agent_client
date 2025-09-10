#!/usr/bin/env python3
"""
Interactive Fabric Data Agent Client

A command-line interactive interface for querying Microsoft Fabric Data Agents.
Features a user-friendly terminal interface with commands, history, and real-time responses.
"""

import os
import sys
import time
import json
from datetime import datetime
from fabric_data_agent_client import FabricDataAgentClient

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class InteractiveFabricClient:
    def __init__(self):
        self.client = None
        self.connected = False
        self.history = []
        self.commands = {
            'connect': self.connect_client,
            'ask': self.ask_question,
            'detailed': self.detailed_analysis,
            'history': self.show_history,
            'clear': self.clear_history,
            'status': self.show_status,
            'help': self.show_help,
            'samples': self.show_samples,
            'config': self.show_config,
            'exit': self.exit_app,
            'quit': self.exit_app
        }
        
    def print_banner(self):
        """Print the application banner"""
        banner = f"""
{Colors.HEADER}╔══════════════════════════════════════════════════════════════╗
║                🤖 Fabric Data Agent Interactive Client       ║
║                                                              ║
║  Ask questions about your data in natural language          ║
║  Type 'help' for available commands                         ║
╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
        print(banner)
        
    def print_colored(self, message, color=Colors.ENDC):
        """Print colored message"""
        print(f"{color}{message}{Colors.ENDC}")
        
    def print_status(self, message, status_type="info"):
        """Print status message with appropriate color"""
        if status_type == "success":
            print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")
        elif status_type == "error":
            print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")
        elif status_type == "warning":
            print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")
        elif status_type == "info":
            print(f"{Colors.OKBLUE}ℹ️  {message}{Colors.ENDC}")
        else:
            print(f"{Colors.OKCYAN}🔵 {message}{Colors.ENDC}")
            
    def get_input(self, prompt, password=False):
        """Get user input with colored prompt"""
        if password:
            import getpass
            return getpass.getpass(f"{Colors.OKCYAN}{prompt}{Colors.ENDC}")
        else:
            return input(f"{Colors.OKCYAN}{prompt}{Colors.ENDC}")
            
    def connect_client(self, args=None):
        """Connect to the Fabric Data Agent"""
        print(f"\n{Colors.BOLD}🔌 Connecting to Fabric Data Agent{Colors.ENDC}")
        print("=" * 50)
        
        # Get configuration
        tenant_id = os.getenv("TENANT_ID")
        data_agent_url = os.getenv("DATA_AGENT_URL")
        
        if not tenant_id:
            tenant_id = self.get_input("Enter your Azure Tenant ID: ", password=True)
            
        if not data_agent_url:
            data_agent_url = self.get_input("Enter your Data Agent URL: ")
            
        if not tenant_id or not data_agent_url:
            self.print_status("Both Tenant ID and Data Agent URL are required", "error")
            return
            
        try:
            self.print_status("Authenticating with Azure AD...", "info")
            self.print_status("A browser window will open for authentication", "info")
            
            # Create client
            self.client = FabricDataAgentClient(
                tenant_id=tenant_id,
                data_agent_url=data_agent_url
            )
            
            self.connected = True
            self.print_status("Successfully connected to Fabric Data Agent!", "success")
            self.print_status(f"Tenant ID: {tenant_id[:8]}...", "info")
            
        except Exception as e:
            self.print_status(f"Connection failed: {str(e)}", "error")
            self.connected = False
            
    def ask_question(self, args=None):
        """Ask a simple question"""
        if not self.connected:
            self.print_status("Please connect first using 'connect' command", "warning")
            return
            
        if args:
            question = ' '.join(args)
        else:
            question = self.get_input("\n💬 Enter your question: ")
            
        if not question.strip():
            self.print_status("Please enter a question", "warning")
            return
            
        self.print_status(f"Question: {question}", "info")
        
        try:
            # Show thinking animation
            self.show_thinking_animation("Processing your question")
            
            start_time = time.time()
            response = self.client.ask(question)
            response_time = time.time() - start_time
            
            # Display results
            print(f"\n{Colors.OKGREEN}🤖 Answer:{Colors.ENDC}")
            print("─" * 60)
            print(response)
            print("─" * 60)
            self.print_status(f"Response time: {response_time:.2f} seconds", "info")
            
            # Store in history
            self.history.append({
                'timestamp': datetime.now(),
                'question': question,
                'answer': response,
                'response_time': response_time,
                'type': 'simple'
            })
            
        except Exception as e:
            self.print_status(f"Error: {str(e)}", "error")
            
    def detailed_analysis(self, args=None):
        """Perform detailed analysis with SQL queries"""
        if not self.connected:
            self.print_status("Please connect first using 'connect' command", "warning")
            return
            
        if args:
            question = ' '.join(args)
        else:
            question = self.get_input("\n🔍 Enter your question for detailed analysis: ")
            
        if not question.strip():
            self.print_status("Please enter a question", "warning")
            return
            
        self.print_status(f"Analyzing: {question}", "info")
        
        try:
            # Show thinking animation
            self.show_thinking_animation("Performing detailed analysis")
            
            start_time = time.time()
            details = self.client.get_run_details(question)
            response_time = time.time() - start_time
            
            # Display results
            print(f"\n{Colors.BOLD}📊 Detailed Analysis Results{Colors.ENDC}")
            print("=" * 60)
            
            # Basic metrics
            if 'run_status' in details:
                self.print_status(f"Run Status: {details['run_status']}", "success")
                
            if 'run_steps' in details:
                steps_count = len(details['run_steps'].get('data', []))
                self.print_status(f"Execution Steps: {steps_count}", "info")
            
            # SQL Queries
            if 'data_retrieval_query' in details and details['data_retrieval_query']:
                print(f"\n{Colors.WARNING}🎯 Main SQL Query:{Colors.ENDC}")
                print("─" * 40)
                print(f"{Colors.OKCYAN}{details['data_retrieval_query']}{Colors.ENDC}")
                print("─" * 40)
                
            # Data Preview
            if 'sql_data_previews' in details and details['sql_data_previews']:
                print(f"\n{Colors.OKGREEN}📊 Data Preview:{Colors.ENDC}")
                print("─" * 40)
                
                for preview in details['sql_data_previews']:
                    if preview:
                        if len(preview) == 1 and '\n' in preview[0] and '|' in preview[0]:
                            # Raw markdown table
                            lines = preview[0].split('\n')
                            for line in lines[:10]:  # Show first 10 lines
                                if line.strip():
                                    print(line)
                            if len(lines) > 10:
                                self.print_status(f"... and {len(lines) - 10} more lines", "info")
                        else:
                            # Parsed data
                            for i, line in enumerate(preview[:5]):
                                print(f"{i+1}. {line}")
                            if len(preview) > 5:
                                self.print_status(f"... and {len(preview) - 5} more rows", "info")
                        break
                print("─" * 40)
                
            # All SQL queries
            if 'sql_queries' in details and details['sql_queries']:
                print(f"\n{Colors.HEADER}📝 All SQL Queries Generated:{Colors.ENDC}")
                for i, query in enumerate(details['sql_queries'], 1):
                    print(f"\n{Colors.BOLD}Query {i}:{Colors.ENDC}")
                    print(f"{Colors.OKCYAN}{query}{Colors.ENDC}")
                    
            self.print_status(f"Analysis completed in {response_time:.2f} seconds", "success")
            
            # Store in history
            self.history.append({
                'timestamp': datetime.now(),
                'question': question,
                'details': details,
                'response_time': response_time,
                'type': 'detailed'
            })
            
        except Exception as e:
            self.print_status(f"Error: {str(e)}", "error")
            
    def show_history(self, args=None):
        """Show query history"""
        if not self.history:
            self.print_status("No queries in history", "info")
            return
            
        print(f"\n{Colors.BOLD}📚 Query History{Colors.ENDC}")
        print("=" * 60)
        
        for i, entry in enumerate(self.history, 1):
            timestamp = entry['timestamp'].strftime("%H:%M:%S")
            question = entry['question'][:50] + "..." if len(entry['question']) > 50 else entry['question']
            query_type = entry['type'].title()
            response_time = entry['response_time']
            
            print(f"{Colors.OKCYAN}{i:2d}. [{timestamp}] {query_type}{Colors.ENDC}")
            print(f"    Question: {question}")
            print(f"    Time: {response_time:.2f}s")
            
            if entry['type'] == 'simple' and 'answer' in entry:
                answer_preview = entry['answer'][:100] + "..." if len(entry['answer']) > 100 else entry['answer']
                print(f"    Answer: {answer_preview}")
            elif entry['type'] == 'detailed' and 'details' in entry:
                details = entry['details']
                if 'sql_queries' in details:
                    print(f"    SQL Queries: {len(details['sql_queries'])}")
            print()
            
    def clear_history(self, args=None):
        """Clear query history"""
        if self.history:
            self.history.clear()
            self.print_status("History cleared", "success")
        else:
            self.print_status("History is already empty", "info")
            
    def show_status(self, args=None):
        """Show connection and session status"""
        print(f"\n{Colors.BOLD}📊 Status Information{Colors.ENDC}")
        print("=" * 40)
        
        # Connection status
        if self.connected:
            self.print_status("Connected to Fabric Data Agent", "success")
        else:
            self.print_status("Not connected", "warning")
            
        # Session stats
        total_queries = len(self.history)
        simple_queries = len([h for h in self.history if h['type'] == 'simple'])
        detailed_queries = len([h for h in self.history if h['type'] == 'detailed'])
        
        print(f"{Colors.OKBLUE}Session Statistics:{Colors.ENDC}")
        print(f"  Total Queries: {total_queries}")
        print(f"  Simple Queries: {simple_queries}")
        print(f"  Detailed Analyses: {detailed_queries}")
        
        if self.history:
            avg_time = sum(h['response_time'] for h in self.history) / len(self.history)
            print(f"  Average Response Time: {avg_time:.2f}s")
            
        # Environment variables
        print(f"\n{Colors.OKBLUE}Configuration:{Colors.ENDC}")
        tenant_id = os.getenv("TENANT_ID")
        data_agent_url = os.getenv("DATA_AGENT_URL")
        
        if tenant_id:
            print(f"  Tenant ID: {tenant_id[:8]}... (from environment)")
        else:
            print("  Tenant ID: Not set in environment")
            
        if data_agent_url:
            print(f"  Data Agent URL: {data_agent_url[:50]}...")
        else:
            print("  Data Agent URL: Not set in environment")
            
    def show_samples(self, args=None):
        """Show sample questions"""
        samples = [
            "What data is available in the lakehouse?",
            "Show me the top 5 records from any available table",
            "What are the column names and types in the main tables?",
            "What was the total sales last month?",
            "Show me recent transactions",
            "What are the most popular products?",
            "Give me a summary of customer demographics",
            "What trends do you see in the data?"
        ]
        
        print(f"\n{Colors.BOLD}💡 Sample Questions{Colors.ENDC}")
        print("=" * 50)
        
        for i, sample in enumerate(samples, 1):
            print(f"{Colors.OKCYAN}{i:2d}. {sample}{Colors.ENDC}")
            
        print(f"\n{Colors.WARNING}Usage:{Colors.ENDC}")
        print("  ask <question>        - Ask a simple question")
        print("  detailed <question>   - Get detailed analysis with SQL")
        print("  Or just type 'ask' or 'detailed' and enter question interactively")
        
    def show_config(self, args=None):
        """Show configuration help"""
        print(f"\n{Colors.BOLD}⚙️  Configuration Help{Colors.ENDC}")
        print("=" * 50)
        
        print(f"{Colors.WARNING}Environment Variables:{Colors.ENDC}")
        print("  TENANT_ID      - Your Azure tenant ID")
        print("  DATA_AGENT_URL - Your Fabric Data Agent URL")
        
        print(f"\n{Colors.WARNING}How to get these values:{Colors.ENDC}")
        print("  1. Tenant ID:")
        print("     - Go to portal.azure.com")
        print("     - Navigate to Azure Active Directory")
        print("     - Copy the Tenant ID from overview page")
        print()
        print("  2. Data Agent URL:")
        print("     - Go to your Fabric workspace")
        print("     - Open your Data Agent")
        print("     - Click 'Publish' and copy the URL")
        
        print(f"\n{Colors.WARNING}Setting environment variables:{Colors.ENDC}")
        print('  export TENANT_ID="your-tenant-id"')
        print('  export DATA_AGENT_URL="your-data-agent-url"')
        
        print(f"\n{Colors.WARNING}Or create a .env file:{Colors.ENDC}")
        print("  TENANT_ID=your-tenant-id")
        print("  DATA_AGENT_URL=your-data-agent-url")
        
    def show_help(self, args=None):
        """Show help information"""
        print(f"\n{Colors.BOLD}📖 Available Commands{Colors.ENDC}")
        print("=" * 60)
        
        commands_help = [
            ("connect", "Connect to Fabric Data Agent with authentication"),
            ("ask [question]", "Ask a simple question (interactive or with question)"),
            ("detailed [question]", "Get detailed analysis with SQL queries and data"),
            ("history", "Show query history"),
            ("clear", "Clear query history"),
            ("status", "Show connection and session status"),
            ("samples", "Show sample questions you can ask"),
            ("config", "Show configuration help"),
            ("help", "Show this help message"),
            ("exit/quit", "Exit the application")
        ]
        
        for cmd, desc in commands_help:
            print(f"{Colors.OKCYAN}{cmd:20}{Colors.ENDC} - {desc}")
            
        print(f"\n{Colors.WARNING}Usage Examples:{Colors.ENDC}")
        print("  ask What data is available?")
        print("  detailed Show me top 5 sales records")
        print("  ask")
        print("  > What are the column names in the sales table?")
        
        print(f"\n{Colors.WARNING}Tips:{Colors.ENDC}")
        print("  - Set TENANT_ID and DATA_AGENT_URL environment variables")
        print("  - Use 'connect' first to authenticate")
        print("  - Try 'samples' for example questions")
        print("  - Use 'detailed' for SQL queries and data previews")
        
    def show_thinking_animation(self, message):
        """Show a thinking animation"""
        print(f"\n{Colors.OKCYAN}{message}", end="")
        for i in range(3):
            time.sleep(0.5)
            print(".", end="", flush=True)
        print(f"{Colors.ENDC}")
        
    def exit_app(self, args=None):
        """Exit the application"""
        print(f"\n{Colors.OKGREEN}👋 Thanks for using Fabric Data Agent Interactive Client!{Colors.ENDC}")
        
        if self.history:
            print(f"Session summary: {len(self.history)} queries processed")
            
        print(f"{Colors.OKCYAN}Goodbye!{Colors.ENDC}\n")
        sys.exit(0)
        
    def parse_command(self, user_input):
        """Parse user input into command and arguments"""
        parts = user_input.strip().split()
        if not parts:
            return None, []
            
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
        
    def run(self):
        """Main application loop"""
        self.print_banner()
        
        # Check for environment variables
        if os.getenv("TENANT_ID") and os.getenv("DATA_AGENT_URL"):
            self.print_status("Environment variables detected", "success")
            connect_now = self.get_input("Connect now? (y/n): ").lower().strip()
            if connect_now in ['y', 'yes', '']:
                self.connect_client()
        else:
            self.print_status("Set TENANT_ID and DATA_AGENT_URL environment variables for easier connection", "info")
            self.print_status("Type 'config' for help or 'connect' to start", "info")
        
        print(f"\n{Colors.BOLD}Ready! Type 'help' for commands or 'exit' to quit.{Colors.ENDC}")
        
        while True:
            try:
                # Show prompt
                status_indicator = "🟢" if self.connected else "🔴"
                user_input = input(f"\n{status_indicator} {Colors.BOLD}fabric-agent>{Colors.ENDC} ")
                
                if not user_input.strip():
                    continue
                    
                command, args = self.parse_command(user_input)
                
                if command in self.commands:
                    self.commands[command](args)
                else:
                    self.print_status(f"Unknown command: {command}", "error")
                    self.print_status("Type 'help' for available commands", "info")
                    
            except KeyboardInterrupt:
                print(f"\n\n{Colors.WARNING}Use 'exit' or 'quit' to leave gracefully{Colors.ENDC}")
            except EOFError:
                self.exit_app()

def main():
    """Main entry point"""
    try:
        app = InteractiveFabricClient()
        app.run()
    except Exception as e:
        print(f"\n{Colors.FAIL}💥 Unexpected error: {str(e)}{Colors.ENDC}")
        print(f"{Colors.WARNING}Please check your configuration and try again{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()
