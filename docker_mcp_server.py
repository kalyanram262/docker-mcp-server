import docker
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Docker client
try:
    client = docker.from_env()
    client.ping()
except Exception as e:
    logger.error(f"Failed to connect to Docker: {e}")
    raise

# Initialize FastMCP
mcp = FastMCP("docker-manager", description="MCP server for managing Docker containers, images, networks, and volumes", version="1.0.0")

# Models (Pydantic models are not strictly needed with FastMCP but can be used for documentation)

# Container Operations
@mcp.tool()
async def list_containers(all_containers: bool = False) -> List[Dict[str, Any]]:
    """List all containers (running and stopped)."""
    try:
        containers = client.containers.list(all=all_containers)
        return [{
            'id': c.short_id,
            'name': c.name,
            'status': c.status,
            'image': c.image.tags[0] if c.image.tags else c.image.id,
            'created': c.attrs['Created'],
            'ports': c.ports
        } for c in containers]
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        raise

@mcp.tool()
async def create_container(
    image: str,
    command: Optional[str] = None,
    name: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
    ports: Optional[Dict[str, Any]] = None,
    volumes: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Create a new container from a specified image and command."""
    try:
        container = client.containers.create(
            image=image,
            command=command,
            name=name,
            environment=environment or {},
            ports=ports or {},
            volumes=volumes or {},
            detach=True
        )
        return {
            'id': container.id,
            'name': container.name,
            'status': 'created',
            'warnings': container.attrs.get('Warnings', [])
        }
    except Exception as e:
        logger.error(f"Error creating container: {e}")
        raise

@mcp.tool()
async def run_container(
    image: str,
    command: Optional[str] = None,
    name: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
    ports: Optional[Dict[str, Any]] = None,
    volumes: Optional[Dict[str, Dict[str, str]]] = None,
    detach: bool = True
) -> Dict[str, Any]:
    """Create and start a container in one step."""
    try:
        container = client.containers.run(
            image=image,
            command=command,
            name=name,
            environment=environment or {},
            ports=ports or {},
            volumes=volumes or {},
            detach=detach
        )
        return {
            'id': container.id,
            'name': container.name,
            'status': container.status,
            'logs': container.logs().decode() if not detach else None
        }
    except Exception as e:
        logger.error(f"Error running container: {e}")
        raise

@mcp.tool()
async def start_container(container_id: str) -> Dict[str, Any]:
    """Start a stopped container."""
    try:
        container = client.containers.get(container_id)
        container.start()
        return {
            'id': container.id,
            'name': container.name,
            'status': container.status
        }
    except Exception as e:
        logger.error(f"Error starting container {container_id}: {e}")
        raise

@mcp.tool()
async def stop_container(container_id: str, timeout: int = 10) -> Dict[str, Any]:
    """Stop a running container."""
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=timeout)
        return {
            'id': container.id,
            'name': container.name,
            'status': container.status
        }
    except Exception as e:
        logger.error(f"Error stopping container {container_id}: {e}")
        raise

@mcp.tool()
async def remove_container(container_id: str, force: bool = False) -> Dict[str, Any]:
    """Remove a container."""
    try:
        container = client.containers.get(container_id)
        container.remove(force=force)
        return {
            'id': container_id,
            'success': True
        }
    except Exception as e:
        logger.error(f"Error removing container {container_id}: {e}")
        raise

# Image Operations
@mcp.tool()
async def list_images() -> List[Dict[str, Any]]:
    """List all local images."""
    try:
        images = client.images.list()
        return [{
            'id': img.short_id,
            'tags': img.tags,
            'created': img.attrs['Created'],
            'size': img.attrs['Size']
        } for img in images]
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        raise

@mcp.tool()
async def pull_image(repository: str, tag: str = "latest") -> Dict[str, Any]:
    """Pull an image from a remote registry."""
    try:
        image = client.images.pull(repository, tag=tag)
        return {
            'id': image.short_id,
            'tags': image.tags,
            'status': 'pulled'
        }
    except Exception as e:
        logger.error(f"Error pulling image {repository}:{tag}: {e}")
        raise

# Network Operations
@mcp.tool()
async def list_networks() -> List[Dict[str, Any]]:
    """List all Docker networks."""
    try:
        networks = client.networks.list()
        return [{
            'id': net.id,
            'name': net.name,
            'driver': net.attrs['Driver'],
            'scope': net.attrs['Scope'],
            'containers': list(net.attrs['Containers'].keys()) if 'Containers' in net.attrs else []
        } for net in networks]
    except Exception as e:
        logger.error(f"Error listing networks: {e}")
        raise

# Volume Operations
@mcp.tool()
async def list_volumes() -> Dict[str, Any]:
    """List all Docker volumes."""
    try:
        volumes = client.volumes.list()
        return {
            'volumes': [{
                'name': vol.name,
                'driver': vol.attrs['Driver'],
                'mountpoint': vol.attrs['Mountpoint']
            } for vol in volumes.volumes]
        }
    except Exception as e:
        logger.error(f"Error listing volumes: {e}")
        raise

def main():
    try:
        # Log to stderr for better error visibility in Claude Desktop
        import sys
        print("Starting Docker MCP server...", file=sys.stderr)
        print(f"Docker client connected: {client.ping()}", file=sys.stderr)
        print("Available tools:", file=sys.stderr)
        for tool in [list_containers, create_container, run_container, 
                    start_container, stop_container, remove_container,
                    list_images, pull_image, list_networks, list_volumes]:
            print(f"- {tool.__name__}: {tool.__doc__.strip()}", file=sys.stderr)
        print("Server is running in stdio mode", file=sys.stderr)
        
        # Use stdio transport for Claude Desktop
        mcp.run(transport='stdio')
    except Exception as e:
        print(f"Error in Docker MCP server: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
