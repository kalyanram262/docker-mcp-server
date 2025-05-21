# Docker MCP Server

A Model Context Protocol (MCP) server for managing Docker containers, images, networks, and volumes on your local machine, with Claude Desktop integration.

## Features

- **Container Management**: List, create, start, stop, and remove containers
- **Image Management**: List, pull, and remove Docker images
- **Network Management**: List and manage Docker networks
- **Volume Management**: List and manage Docker volumes
- **Claude Desktop Integration**: Seamlessly connect with Claude Desktop for Docker management

## Prerequisites

- Python 3.7+
- Docker installed and running on your system
- [Claude Desktop](https://claude.ai/download) (for desktop integration)

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/docker-mcp-server.git
   cd docker-mcp-server
   ```

2. **Make the setup script executable**:
   ```bash
   chmod +x start_server.sh
   ```

3. **Run the setup script**:
   ```bash
   ./start_server.sh
   ```
   This will:
   - Create a Python virtual environment
   - Install all required dependencies
   - Verify Docker is running
   - Start the MCP server
   - Show the configuration for Claude Desktop

## 📁 Project Structure

```
docker-mcp-server/
├── .gitignore          # Git ignore file
├── LICENSE            # MIT License
├── README.md          # This file
├── docker_mcp_server.py # Main server code
├── requirements.txt    # Python dependencies
└── start_server.sh    # Setup and start script
```

## 🖥️ Running the Server

### Option 1: Using the Setup Script (Recommended)
```bash
./start_server.sh
```

### Option 2: Manual Setup
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the server:
   ```bash
   python docker_mcp_server.py
   ```

### Claude Desktop Integration

1. Make sure the server is not already running
2. Open Claude Desktop
3. Go to Settings > MCP Servers
4. Click "Add MCP Server"
5. Import the following configuration (or import from `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "docker-mcp": {
      "command": "python3",
      "args": [
        "/path/to/your/docker-mcp-server/docker_mcp_server.py"
      ],
      "transport": {
        "type": "stdio"
      },
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

6. Save the configuration
7. The Docker MCP server should now be available in Claude Desktop

## Troubleshooting

- If you get port conflicts, make sure no other instances are running:
  ```bash
  # Find and kill any existing processes
  lsof -i :8000
  kill <process_id>
  ```

- For connection issues, check Claude Desktop's logs for detailed error messages

## 🛠️ Available Tools

### Container Management
- `list_containers(all_containers: bool = False)`: List all containers
- `create_container(image: str, command: str = None, name: str = None, ports: dict = None, environment: dict = None, volumes: dict = None)`: Create a new container
- `run_container(image: str, command: str = None, name: str = None, ports: dict = None, environment: dict = None, volumes: dict = None)`: Create and start a container
- `start_container(container_id: str)`: Start a stopped container
- `stop_container(container_id: str)`: Stop a running container
- `remove_container(container_id: str, force: bool = False)`: Remove a container
- `inspect_container(container_id: str)`: Get detailed information about a container
- `get_container_stats(container_id: str, stream: bool = False)`: Get real-time container statistics (CPU, memory, network, disk I/O)

### Image Management
- `list_images()`: List all local images
- `pull_image(image: str)`: Pull an image from a registry

### Network Management
- `list_networks()`: List all Docker networks

### Volume Management
- `list_volumes()`: List all Docker volumes

The server will start on `http://0.0.0.0:8000`.

## Available Endpoints

### Containers

- `POST /list_containers` - List all containers
- `POST /create_container` - Create a new container
- `POST /run_container` - Create and start a container
- `POST /start_container` - Start a stopped container
- `POST /stop_container` - Stop a running container
- `POST /remove_container` - Remove a container
- `POST /inspect_container` - Get detailed container information
- `POST /get_container_stats` - Get container statistics (CPU, memory, etc.)

### Images

- `POST /list_images` - List all local images
- `POST /pull_image` - Pull an image from a registry

### Networks

- `POST /list_networks` - List all Docker networks

### Volumes

- `POST /list_volumes` - List all Docker volumes

## 🚀 Example Usage

### Using Python Client

```python
# Get detailed container information
container_info = await client.inspect_container("my-container")
print(f"Container IP: {container_info['NetworkSettings']['IPAddress']}")

# Get container statistics
stats = await client.get_container_stats("my-container")
print(f"CPU Usage: {stats['cpu_stats']['cpu_usage']['total_usage']}")

# Stream container stats in real-time
stats_stream = await client.get_container_stats("my-container", stream=True)
print(f"Initial CPU: {stats_stream['first_stats']['cpu_stats']['cpu_usage']['total_usage']}")
for stat in stats_stream['stream']:
    print(f"CPU: {stat['cpu_stats']['cpu_usage']['total_usage']}")
    # Process other metrics as needed
```

### Using cURL

#### Get container details
```bash
curl -X POST http://localhost:8000/inspect_container \
  -H "Content-Type: application/json" \
  -d '{"container_id": "my-container"}'
```

#### Get container statistics
```bash
# Single stats snapshot
curl -X POST http://localhost:8000/get_container_stats \
  -H "Content-Type: application/json" \
  -d '{"container_id": "my-container"}'

# Stream stats (using websockets or similar would be better for production)
# This is a simplified example:
while true; do
  curl -s -X POST http://localhost:8000/get_container_stats \
    -H "Content-Type: application/json" \
    -d '{"container_id": "my-container"}' | jq '.cpu_stats.cpu_usage.total_usage'
  sleep 1
done
```

## Testing

To test the server, you can use the included test script:

```bash
python -m pytest test_docker_mcp.py -v
```

## License

MIT
