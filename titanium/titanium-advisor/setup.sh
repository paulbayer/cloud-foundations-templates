#!/bin/bash

# Titanium Advisor setup script
echo "Setting up Titanium Advisor MCP server..."

# Navigate to the MCP server directory
cd titanium-advisor/mcp-server

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To test the server:"
echo "python server.py --debug"
echo ""
echo "See README.md for AWS Q configuration instructions."
