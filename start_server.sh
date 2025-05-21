#!/bin/bash
set -e  # Exit on error

echo "🚀 Starting Docker MCP Server Setup..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created"
else
    source venv/bin/activate
    echo "✅ Using existing virtual environment"
fi

# Install/update dependencies
echo "📦 Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Check Docker is running
echo "🐳 Verifying Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker daemon is not running"
    exit 1
fi
echo "✅ Docker daemon is running"

# Start the MCP server
echo "🚀 Starting Docker MCP server..."
echo "   - Press Ctrl+C to stop the server"
echo "   - Server will be available in Claude Desktop"
echo ""
echo "🔗 Configuration for Claude Desktop:"
echo '{
  "mcpServers": {
    "docker-mcp": {
      "command": "'$(which python3)'",
      "args": ["'$(pwd)/docker_mcp_server.py'"],
      "transport": { "type": "stdio" },
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}'
echo ""
echo "Starting Docker MCP Server..."
python docker_mcp_server.py
