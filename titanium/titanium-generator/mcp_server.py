"""
MCP Server for Titanium Template Modifier.

This server provides a file-based interface to the Titanium Template Modifier,
allowing AI agents to interact with the same functionality as the CLI tool.
"""

import json
import logging
import os
import sys
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MCPResponse:
    """Standard response structure for MCP tools."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary, filtering out None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


class MCPError(Exception):
    """Base exception for MCP server errors."""
    pass


class ToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, handler: Callable, metadata: Optional[Dict[str, Any]] = None):
        """
        Register a tool with the server.
        
        Args:
            name: Tool name
            handler: Function that handles the tool request
            metadata: Optional metadata about the tool (description, parameters, etc.)
        """
        if name in self.tools:
            raise MCPError(f"Tool '{name}' is already registered")
        
        self.tools[name] = handler
        self.tool_metadata[name] = metadata or {}
        logger.info(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a registered tool handler."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their metadata."""
        return [
            {
                "name": name,
                "metadata": self.tool_metadata.get(name, {})
            }
            for name in self.tools.keys()
        ]


class TitaniumMCPServer:
    """
    MCP Server for Titanium Template Modifier.
    
    This server provides file-based tools for AI agents to parse Titanium configurations
    and modify CloudFormation templates using the same logic as the CLI tool.
    """
    
    def __init__(self):
        """Initialize the MCP server."""
        self.registry = ToolRegistry()
        self._register_default_tools()
        logger.info("Titanium MCP Server initialized")
    
    def _register_default_tools(self):
        """Register default tools provided by the server."""
        # Import tool functions
        try:
            # Parse tool
            from titanium_generator.mcp_tools.parse_titanium import parse_titanium_config
            self.registry.register(
                "parse_titanium_config",
                parse_titanium_config,
                {
                    "description": "Parse and validate a Titanium YAML configuration file",
                    "parameters": {
                        "titanium_path": {
                            "type": "string",
                            "description": "Path to the Titanium.yaml file",
                            "required": True
                        }
                    },
                    "returns": {
                        "config": "Parsed configuration object",
                        "sections": "List of available configuration sections",
                        "validation_errors": "List of validation errors if any",
                        "file_path": "The input file path for reference"
                    }
                }
            )
            
            # Modify template tool
            from titanium_generator.mcp_tools.modify_template import modify_template
            self.registry.register(
                "modify_template",
                modify_template,
                {
                    "description": "Generate a single CloudFormation template by parsing Titanium configuration",
                    "parameters": {
                        "titanium_path": {
                            "type": "string",
                            "description": "Path to the Titanium.yaml file",
                            "required": True
                        },
                        "template_path": {
                            "type": "string",
                            "description": "Path to the CloudFormation template",
                            "required": True
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Optional output path (defaults to template_path with .modified suffix)",
                            "required": False
                        }
                    },
                    "returns": {
                        "input_template": "Path to the input template",
                        "output_template": "Path to the modified template",
                        "modifications": "List of modifications made",
                        "parameters_modified": "Number of parameters modified",
                        "section": "The section type processed"
                    }
                }
            )
            
            # Process all templates tool
            from titanium_generator.mcp_tools.process_templates import process_all_templates
            self.registry.register(
                "process_all_templates",
                process_all_templates,
                {
                    "description": "Generate complete set of CloudFormation templates based on Titanium configuration YAML file",
                    "parameters": {
                        "titanium_path": {
                            "type": "string",
                            "description": "Path to the Titanium.yaml file",
                            "required": True
                        },

                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for modified templates",
                            "required": True
                        },
                        "sections": {
                            "type": "array",
                            "description": "Optional list of sections to process (processes all if not specified)",
                            "required": False
                        }
                    },
                    "returns": {
                        "summary": "Processing summary with counts",
                        "modified_templates": "List of modified template paths",
                        "errors": "List of any errors encountered",
                        "report_path": "Path to the generated report"
                    }
                }
            )
            
        except ImportError as e:
            logger.warning(f"Could not import MCP tools: {e}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming MCP request.
        
        Args:
            request: Request dictionary with 'tool' and 'arguments' keys
            
        Returns:
            Response dictionary with results or error information
        """
        try:
            # Validate request structure
            if not isinstance(request, dict):
                return self._error_response("Request must be a dictionary")
            
            tool_name = request.get("tool")
            if not tool_name:
                return self._error_response("Missing 'tool' field in request")
            
            # Get tool handler
            handler = self.registry.get_tool(tool_name)
            if not handler:
                available_tools = [tool["name"] for tool in self.registry.list_tools()]
                return self._error_response(
                    f"Unknown tool: {tool_name}",
                    {"available_tools": available_tools}
                )
            
            # Get and validate arguments
            arguments = request.get("arguments", {})
            if not isinstance(arguments, dict):
                return self._error_response("Arguments must be a dictionary")
            
            # Execute tool
            logger.info(f"Executing tool: {tool_name}")
            try:
                result = handler(**arguments)
                
                # Ensure result is an MCPResponse
                if isinstance(result, MCPResponse):
                    return result.to_dict()
                elif isinstance(result, dict):
                    return MCPResponse(success=True, data=result).to_dict()
                else:
                    return MCPResponse(
                        success=True,
                        data={"result": result}
                    ).to_dict()
                    
            except TypeError as e:
                return self._error_response(
                    f"Invalid arguments for tool '{tool_name}': {str(e)}",
                    {"tool_metadata": self.registry.tool_metadata.get(tool_name, {})}
                )
            except FileNotFoundError as e:
                return self._error_response(
                    f"File not found: {str(e)}",
                    {"error_type": "FileNotFoundError"}
                )
            except PermissionError as e:
                return self._error_response(
                    f"Permission denied: {str(e)}",
                    {"error_type": "PermissionError"}
                )
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
                return self._error_response(f"Tool execution failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error handling request: {str(e)}", exc_info=True)
            return self._error_response(f"Internal server error: {str(e)}")
    
    def _error_response(self, error_message: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a standardized error response."""
        return MCPResponse(
            success=False,
            error=error_message,
            metadata=metadata
        ).to_dict()
    
    def list_tools(self) -> Dict[str, Any]:
        """List all available tools."""
        return MCPResponse(
            success=True,
            data={
                "tools": self.registry.list_tools(),
                "server_info": {
                    "name": "Titanium MCP Server",
                    "version": "1.0.0",
                    "description": "File-based MCP server for Titanium Template Modifier"
                }
            }
        ).to_dict()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the server."""
        tool_count = len(self.registry.tools)
        
        # Check if we can access the file system
        can_access_fs = True
        try:
            os.listdir(".")
        except Exception:
            can_access_fs = False
        
        return MCPResponse(
            success=True,
            data={
                "status": "healthy" if can_access_fs else "degraded",
                "tool_count": tool_count,
                "tools_loaded": tool_count > 0,
                "file_system_access": can_access_fs
            }
        ).to_dict()


def create_server() -> TitaniumMCPServer:
    """Create and return a configured MCP server instance."""
    return TitaniumMCPServer()


async def main():
    """Main entry point for the MCP server."""
    server = create_server()
    
    # Example of handling a request (for testing)
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode - list available tools
        result = server.list_tools()
        print(json.dumps(result, indent=2))
        
        # Test health check
        health = server.health_check()
        print("\nHealth check:")
        print(json.dumps(health, indent=2))
        
        # Test parse tool with sample request
        if len(sys.argv) > 2:
            test_request = {
                "tool": "parse_titanium_config",
                "arguments": {
                    "titanium_path": sys.argv[2]
                }
            }
            print(f"\nTesting parse tool with: {sys.argv[2]}")
            result = server.handle_request(test_request)
            print(json.dumps(result, indent=2))
    else:
        # Run the actual MCP server
        from mcp.server.stdio import stdio_server
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        
        # Create MCP server instance
        mcp_server = Server("titanium-generator")
        
        # Register tools
        @mcp_server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="parse_titanium_config",
                    description="Parse and validate a Titanium YAML configuration file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "titanium_path": {
                                "type": "string",
                                "description": "Path to the Titanium.yaml file"
                            }
                        },
                        "required": ["titanium_path"]
                    }
                ),
                Tool(
                    name="modify_template",
                    description="Generate a single CloudFormation template based on Titanium YAML configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "titanium_path": {
                                "type": "string",
                                "description": "Path to the Titanium.yaml file"
                            },
                            "template_path": {
                                "type": "string",
                                "description": "Path to the CloudFormation template"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Optional output path (defaults to template_path with .modified suffix)"
                            }
                        },
                        "required": ["titanium_path", "template_path"]
                    }
                ),
                Tool(
                    name="process_all_templates",
                    description="Generate complete set of CloudFormation templates based on Titanium configuration YAML file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "titanium_path": {
                                "type": "string",
                                "description": "Path to the Titanium.yaml file"
                            },

                            "output_dir": {
                                "type": "string",
                                "description": "Output directory for modified templates"
                            },
                            "sections": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of sections to process (processes all if not specified)"
                            }
                        },
                        "required": ["titanium_path", "output_dir"]
                    }
                )
            ]
        
        @mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict):
            """Handle tool calls."""
            try:
                # Use the internal server's request handler which we know works
                request = {
                    "tool": name,
                    "arguments": arguments
                }
                
                result = server.handle_request(request)
                
                return [TextContent(
                    type="text", 
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {str(e)}", exc_info=True)
                error_result = {
                    "success": False,
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments
                }
                return [TextContent(
                    type="text",
                    text=json.dumps(error_result, indent=2)
                )]
        
        # Run the server
        logger.info("Starting Titanium MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
