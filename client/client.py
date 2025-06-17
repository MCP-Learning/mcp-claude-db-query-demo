import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import logging
import json
import os
from google.protobuf.json_format import MessageToDict
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import google.generativeai as genai
from dotenv import load_dotenv

logging.basicConfig(
    filename='client.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

load_dotenv()  # load environment variables from .env
logger.info("GOOGLE_API_KEY: %s", os.getenv("GOOGLE_API_KEY"))

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        logger.info("Connected to server with tools: %s", [tool.name for tool in tools])

    def filter_schema(self, schema: dict) -> dict:
        if isinstance(schema, dict):
            if 'type' in schema and schema['type'] == 'object':
                return {
                    'type': schema['type'].upper(),
                    'properties': {
                        prop: self.filter_schema(schema['properties'][prop])
                        for prop in schema.get('properties', {})
                    },
                    'required': schema.get('required', [])
                }
            elif 'type' in schema:
                return {
                    'type': schema['type'].upper(),
                    'description': schema.get('description', '')
                }
            else:
                return {k: self.filter_schema(v) for k, v in schema.items() if k != 'title'}
        elif isinstance(schema, list):
            return [self.filter_schema(item) for item in schema]
        else:
            return schema

    async def process_query(self, query: str) -> str:
        logger.info("Processing query: %s", query)
        
        # Fetch available tools from the server
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        logger.info("Available tools raw schemas: %s", available_tools)
        
        # Filter and format tools for the Gemini API
        gemini_tools = [{
            "name": tool["name"],
            "description": tool["description"],
            "parameters": self.filter_schema(tool["input_schema"])
        } for tool in available_tools]
        logger.info("Gemini tools filtered schemas: %s", json.dumps(gemini_tools, indent=2))
        
        # Initialize conversation history with a system message
        history = [
            {"role": "model", "parts": [{"text": "I am an assistant that uses tools to answer questions about crops and farms. For any query about a specific crop—like 'how many wheat' (meaning wheat crops) or 'tell me about corn'—I will use the 'get_crop_info' tool to provide details, including counts if asked."}]},
            {"role": "user", "parts": [{"text": query}]}
        ]
        logger.info("Initialized history with refined instruction: %s", history[0]["parts"][0]["text"])
        
        final_text = []  # Collect all text parts for the final response

        while True:
            try:
                # Generate content using the Gemini model
                response = self.model.generate_content(history, tools=gemini_tools)
                if not response.candidates:
                    logger.error("No candidates in response")
                    raise ValueError("No candidates in response")
                model_content = response.candidates[0].content
                text_parts = [part.text for part in model_content.parts if hasattr(part, 'text')]
                logger.info("Gemini response text parts: %s", text_parts)
            except Exception as e:
                logger.exception("Error in generate_content: %s", str(e))
                raise
            
            # Append model content to history
            history.append(model_content)
            
            # Check for function calls (tool usage)
            function_calls = [part.function_call for part in model_content.parts if part.function_call]
            logger.info("Function calls: %s", [fc.name for fc in function_calls] if function_calls else "None")

            if not function_calls:
                # No tools were called; check for vague 'how many' queries
                logger.info("No tool called for query: '%s'. Model response: '%s'", query, text_parts)
                if "how many" in query.lower() and any(crop in query.lower() for crop in ["wheat", "corn"]):
                    logger.info("Detected 'how many' query with crop type: %s. Forcing tool call.", query)
                    crop_type = next(crop for crop in ["wheat", "corn"] if crop in query.lower())
                    result = await self.session.call_tool("get_crop_info", {"crop_type": crop_type})
                    logger.info("Forced tool call result: content=%s, isError=%s", result.content, result.isError)
                    if not result.isError:
                        tool_response_text = result.content.text if hasattr(result.content, 'text') else str(result.content)
                        crop_count = len([line for line in tool_response_text.split('\n') if line.strip()])
                        fallback_response = f"There are {crop_count} {crop_type} crops."
                        final_text.append(fallback_response)
                        logger.info("Fallback triggered; using response: %s instead of clarification", fallback_response)
                    else:
                        final_text.append(f"Error fetching {crop_type} info: {result.content}")
                        logger.info("Fallback error for crop '%s': %s", crop_type, result.content)
                else:
                    # No fallback needed; use the model's response
                    final_text.extend(text_parts)
                    logger.info("No fallback triggered; using model response: %s", text_parts)
                break  # Exit the loop since no tools are being called
            
            # Process each tool call
            for function_call in function_calls:
                tool_name = function_call.name
                tool_args = dict(function_call.args)
                logger.info("Calling tool %s with args: %s", tool_name, tool_args)
                try:
                    result = await self.session.call_tool(tool_name, tool_args)
                    logger.info("Tool %s returned: content=%s, isError=%s", tool_name, str(result.content), result.isError)
                    if result.isError:
                        logger.error("Tool error: %s", result.content)
                        final_text.append(f"Error from tool {tool_name}: {result.content}")
                        break
                    tool_response_text = result.content.text if hasattr(result.content, 'text') else str(result.content)
                    logger.info("Extracted tool response text for %s: %s", tool_name, tool_response_text)
                    if "how many" in query.lower() and tool_name == "get_crop_info":
                        crop_count = len([line for line in tool_response_text.split('\n') if line.strip()])
                        response_text = f"There are {crop_count} {tool_args['crop_type']} crops."
                        logger.info("Processed 'how many' query: %s", response_text)
                    else:
                        response_text = tool_response_text
                    history.append({
                        "role": "model",
                        "parts": [{
                            "function_response": {
                                "name": tool_name,
                                "response": {
                                    "content": response_text
                                }
                            }
                        }]
                    })
                    final_text.append(response_text)
                except Exception as e:
                    logger.error("Error calling tool %s: %s", tool_name, str(e))
                    raise

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())