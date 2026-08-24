#!/bin/bash

# Titanium Generator MCP server setup script
echo "Setting up Titanium Generator MCP server..."

# Check if we're in the right directory
if [ ! -f "mcp_server.py" ]; then
    echo "❌ Error: Please run this script from the titanium-generator directory"
    exit 1
fi

# Create a virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# Activate the virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install package in development mode
echo "🔧 Installing titanium-generator in development mode..."
pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment:"
echo "source .venv/bin/activate"
echo ""
echo "To test the MCP server:"
echo "python mcp_server.py test"
echo ""
echo "To test with a Titanium.yaml file:"
echo "python mcp_server.py test ../Titanium.yaml"
echo ""
