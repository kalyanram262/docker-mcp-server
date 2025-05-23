# Docker MCP Server

A Model Context Protocol (MCP) server for managing Docker containers, images, networks, and volumes on your local machine, with FastAPI HTTP interface.

## Features

- **Container Management**: List, create, start, stop, and remove containers
- **Image Management**: List, pull, and remove Docker images
- **Network Management**: List and manage Docker networks
- **Volume Management**: List and manage Docker volumes
- **FastAPI HTTP Interface**: RESTful API endpoints for all operations
- **Health Check**: Built-in health check endpoint for monitoring

## Prerequisites

- Docker and Docker Compose installed and running on your system
- Port 8000 available for the FastAPI server

## 🚀 Installation

## 🚀 Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/docker-mcp-server.git
   cd docker-mcp-server
   ```

2. **Start the services**:
   ```bash
   docker-compose up -d
   ```
   
   This will:
   - Build the Docker image
   - Start the MCP server with FastAPI interface
   - Mount the Docker socket for container management
   - Start an example Nginx service on port 8080
   - Expose port 8000 for the FastAPI server

3. **Verify the services are running**:
   ```bash
   docker-compose ps
   ```
   
   You should see both `docker-mcp-server` and `example-service` running.

4. **Check the health status**:
   ```bash
   curl http://localhost:8000/health
   ```
   
   Should return: `{"status":"ok"}`

### Option 2: Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/docker-mcp-server.git
   cd docker-mcp-server
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**:
   ```bash
   python docker_mcp_server.py
   ```

### Building the Docker Image Manually

If you prefer to build the Docker image manually:

```bash
docker build -t docker-mcp-server .

docker run -d \
  --name docker-mcp-server \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  docker-mcp-server
```

## 📁 Project Structure

```
docker-mcp-server/
├── .dockerignore      # Docker ignore file
├── .gitignore         # Git ignore file
├── Dockerfile         # Docker configuration
├── docker-compose.yml # Docker Compose configuration
├── LICENSE            # MIT License
├── README.md          # This file
├── chart/             # Helm chart for Kubernetes deployment
│   └── docker-mcp-server/
│       ├── Chart.yaml         # Chart metadata
│       ├── values.yaml        # Default configuration values
│       └── templates/         # Kubernetes templates
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           └── serviceaccount.yaml
├── docker_mcp_server.py # Main server code
└── requirements.txt   # Python dependencies
```

## 🚀 Kubernetes Deployment with Helm

### Prerequisites

- Kubernetes cluster (Minikube, Docker Desktop, or cloud-based)
- Helm 3.x installed
- kubectl configured to communicate with your cluster

### Installation

1. **Add the chart repository** (if published):
   ```bash
   helm repo add docker-mcp-server https://your-chart-repo-url/
   helm repo update
   ```

2. **Install the chart** (from local chart):
   ```bash
   # From the project root directory
   helm install docker-mcp-server ./chart/docker-mcp-server -n docker-mcp --create-namespace
   ```

### Configuration

The following table lists the configurable parameters of the Docker MCP Server chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Docker image repository | `kalyanram262/mcp-test` |
| `image.tag` | Docker image tag | `v3` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.hosts[0].host` | Ingress hostname | `docker-mcp.local` |
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `128Mi` |

### Upgrading

To upgrade your installation with the latest chart:

```bash
# From the project root directory
helm upgrade --install docker-mcp-server ./chart/docker-mcp-server -n docker-mcp
```

### Uninstalling

To uninstall/delete the `docker-mcp-server` release:

```bash
helm uninstall docker-mcp-server -n docker-mcp
kubectl delete namespace docker-mcp
```

### Accessing the Service

#### Using Port-Forwarding

```bash
kubectl port-forward -n docker-mcp svc/docker-mcp-server 8080:80 &
curl http://localhost:8080/health
```

#### Using Minikube Service

```bash
minikube service docker-mcp-server -n docker-mcp
```

#### Using Ingress (if enabled)
1. Make sure your `ingress.hosts[0].host` (default: `docker-mcp.local`) resolves to your cluster's ingress IP
2. Access the service at `http://docker-mcp.local/health`

## 🛠️ Development

### Running Tests
```bash
docker-compose exec docker-mcp-server python -m pytest
```

### Viewing Logs
```bash
docker-compose logs -f
```

### Stopping Services
```bash
docker-compose down
```

## 🔍 Example: Using the API

### Starting an Nginx Container
```bash
curl -X POST http://localhost:8000/run_container \
  -H "Content-Type: application/json" \
  -d '{
    "image": "nginx:alpine",
    "ports": {"80/tcp": 8080},
    "name": "my-nginx"
  }'
```

### Listing Containers
```bash
curl -X POST http://localhost:8000/list_containers
```

### Viewing Container Logs
```bash
docker logs docker-mcp-server
```

## Troubleshooting

- If you get port conflicts, make sure no other instances are running:
  ```bash
  # Find and kill any existing processes
  lsof -i :8000
  kill <process_id>
  ```

- For connection issues, check Claude Desktop's logs for detailed error messages

## 📊 Monitoring

The server includes a health check endpoint at `/health` that can be used for monitoring. The Docker Compose configuration includes a health check that verifies this endpoint.

### Health Check Configuration
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 10s
```

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
- `build_image(path: str, tag: str = None, dockerfile: str = None, build_args: dict = None, labels: dict = None, pull: bool = False, no_cache: bool = False, rm: bool = True, timeout: int = 3600)`: Build a Docker image from a Dockerfile
- `list_images()`: List all local images
- `pull_image(repository: str, tag: str = "latest")`: Pull an image from a registry
- `tag_image(image_reference: str, repository: str, tag: str = "latest")`: Tag a local image
- `push_image(repository: str, tag: str = "latest", auth_config: dict = None)`: Push an image to a registry

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

- `POST /build_image` - Build an image from a Dockerfile
- `POST /list_images` - List all local images
- `POST /pull_image` - Pull an image from a registry
- `POST /tag_image` - Tag a local image
- `POST /push_image` - Push an image to a registry

### Networks

- `POST /list_networks` - List all Docker networks

### Volumes

- `POST /list_volumes` - List all Docker volumes

## 🚀 Example Usage

### Using Python Client

#### Container Operations
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
```

#### Image Operations
```python
# Build an image
build_result = await client.build_image(
    path="./my-app",
    tag="myapp:1.0",
    dockerfile="Dockerfile.prod",
    build_args={"NODE_ENV": "production"},
    labels={"version": "1.0"}
)
print(f"Built image: {build_result['tags']}")

# Tag an image
tag_result = await client.tag_image(
    image_reference="myapp:1.0",
    repository="myregistry.example.com/team/myapp",
    tag="production"
)
print(f"Tagged as: {tag_result['new_reference']}")

# Push an image (using Docker's credential store)
push_result = await client.push_image(
    repository="myregistry.example.com/team/myapp",
    tag="production"
)
print(f"Push logs: {push_result['logs']}")
```

### Using cURL

#### Get container details
```bash
curl -X POST http://localhost:8000/inspect_container \
  -H "Content-Type: application/json" \
  -d '{"container_id": "my-container"}'
```

#### Build and Push Images
```bash
# Build an image
curl -X POST http://localhost:8000/build_image \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/your/app",
    "tag": "myapp:1.0",
    "dockerfile": "Dockerfile.prod",
    "build_args": {"NODE_ENV": "production"}
  }'

# Tag an image
curl -X POST http://localhost:8000/tag_image \
  -H "Content-Type: application/json" \
  -d '{
    "image_reference": "myapp:1.0",
    "repository": "myregistry.example.com/team/myapp",
    "tag": "production"
  }'

# Push an image
curl -X POST http://localhost:8000/push_image \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "myregistry.example.com/team/myapp",
    "tag": "production"
  }'
```

#### Get container statistics
```bash
# Single stats snapshot
curl -X POST http://localhost:8000/get_container_stats \
  -H "Content-Type: application/json" \
  -d '{"container_id": "my-container"}'
```
```

## 🧪 Testing

### Running Tests

To run tests inside the container:

```bash
docker-compose exec docker-mcp-server python -m pytest
```

### Health Check

The service includes a health check endpoint:

```bash
curl http://localhost:8000/health
```

### Monitoring

You can view the container logs with:

```bash
docker-compose logs -f
```

## 🛠️ Development

### Rebuilding the Container

After making changes to the code or dependencies:

```bash
docker-compose up -d --build
```

### Accessing the Container Shell

```bash
docker-compose exec docker-mcp-server /bin/bash
```

## 🚀 Deployment

### Production Considerations

1. **Security**:
   - Use TLS for MCP communication
   - Implement proper authentication
   - Limit Docker socket access
   - Use secrets for sensitive data

2. **Scaling**:
   - The service is stateless and can be scaled horizontally
   - Use a reverse proxy (like Nginx) for load balancing

3. **Monitoring**:
   - Set up logging and monitoring
   - Configure alerts for the health check

## Testing

To test the server, you can use the included test script:

```bash
python -m pytest test_docker_mcp.py -v
```

## License

MIT
