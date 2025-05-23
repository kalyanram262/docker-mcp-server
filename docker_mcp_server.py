import os
import logging
import datetime
import docker
import json
import logging
import sys
import time
from datetime import datetime as dt
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

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

# Initialize MCP server
mcp = FastMCP(
    "docker-manager", 
    description="MCP server for managing Docker containers, images, networks, and volumes", 
    version="1.0.0"
)

# Health check function with @mcp.tool() decorator
@mcp.tool()
async def health_check() -> dict:
    """Check if the server is running and can connect to Docker."""
    try:
        client = docker.from_env()
        client.ping()
        return {
            "status": "healthy",
            "docker_connected": True,
            "timestamp": dt.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "docker_connected": False,
            "error": str(e),
            "timestamp": dt.utcnow().isoformat()
        }

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
async def remove_container(container_id: str, force: bool = False):
    """Remove a container."""
    try:
        container = client.containers.get(container_id)
        container.remove(force=force)
        return {'status': 'success', 'message': f'Container {container_id} removed'}
    except docker.errors.NotFound:
        raise ValueError(f'No such container: {container_id}')
    except Exception as e:
        logger.error(f"Error removing container {container_id}: {e}")
        raise

@mcp.tool()
async def inspect_container(container_id: str) -> Dict[str, Any]:
    """Get detailed information about a container.
    
    Args:
        container_id: The ID or name of the container to inspect
        
    Returns:
        Dict containing detailed container information
    """
    try:
        container = client.containers.get(container_id)
        return container.attrs
    except docker.errors.NotFound:
        raise ValueError(f'No such container: {container_id}')
    except Exception as e:
        logger.error(f"Error inspecting container {container_id}: {e}")
        raise

@mcp.tool()
async def get_container_stats(container_id: str, stream: bool = False) -> Dict[str, Any]:
    """Get real-time statistics for a container.
    
    Args:
        container_id: The ID or name of the container
        stream: If True, returns a generator that yields stats. If False, returns a single stats reading.
               Default is False.
               
    Returns:
        Dict containing container statistics including CPU, memory, network, and disk I/O
    """
    try:
        container = client.containers.get(container_id)
        
        if stream:
            def generate_stats():
                try:
                    for stats in container.stats(stream=True, decode=True):
                        yield stats
                except Exception as e:
                    logger.error(f"Error in stats stream for container {container_id}: {e}")
                    raise
            
            # Return the first stats immediately and keep streaming
            first_stats = next(container.stats(stream=True, decode=True))
            return {
                'container_id': container_id,
                'first_stats': first_stats,
                'stream': generate_stats()
            }
        else:
            return container.stats(stream=False, decode=True)
            
    except docker.errors.NotFound:
        raise ValueError(f'No such container: {container_id}')
    except Exception as e:
        logger.error(f"Error getting stats for container {container_id}: {e}")
        raise

# Image Operations
# Commented out build_image function as it's not part of the current release
# @mcp.tool()
# async def build_image(
#     path: str,
#     tag: Optional[str] = None,
#     dockerfile: Optional[str] = None,
#     build_args: Optional[Dict[str, str]] = None,
#     labels: Optional[Dict[str, str]] = None,
#     pull: bool = False,
#     no_cache: bool = False,
#     rm: bool = True,
#     timeout: int = 3600
# ) -> Dict[str, Any]:
#     """Build a Docker image from a Dockerfile.
#     
#     Args:
#         path: Path to the directory containing the Dockerfile
#         tag: Name and optionally a tag in 'name:tag' format
#         dockerfile: Path to the Dockerfile relative to the build path
#         build_args: Dictionary of build-time variables
#         labels: Dictionary of metadata for the image
#         pull: Pull the image even if an older image exists locally
#         no_cache: Do not use cache when building the image
#         rm: Remove intermediate containers after a successful build
#         timeout: Build timeout in seconds
#         
#     Returns:
#         Dict containing build status and image information
#     """
#     try:
#         logger.info(f"Building image from {path}")
#         
#         # Convert path to absolute if it's not already
#         abs_path = os.path.abspath(os.path.expanduser(path))
#         
#         # Build the image
#         image, logs = client.images.build(
#             path=abs_path,
#             tag=tag,
#             dockerfile=dockerfile,
#             buildargs=build_args,
#             labels=labels,
#             pull=pull,
#             nocache=no_cache,
#             rm=rm,
#             timeout=timeout
#         )
#         
#         # Process build logs
#         build_logs = []
#         for chunk in logs:
#             if 'stream' in chunk:
#                 log = chunk['stream'].strip()
#                 if log:
#                     build_logs.append(log)
#                     logger.info(f"Build log: {log}")
#         
#         return {
#             'status': 'success',
#             'message': f'Successfully built {tag or image.id}',
#             'image_id': image.id,
#             'tags': image.tags,
#             'short_id': image.short_id,
#             'logs': build_logs
#         }
#         
#     except docker.errors.BuildError as e:
#         error_msg = f"Build failed: {str(e)}"
#         logger.error(error_msg)
#         logger.error(f"Build logs: {e.build_log}")
#         raise ValueError(error_msg)
#     except Exception as e:
#         error_msg = f"Error building image: {str(e)}"
#         logger.error(error_msg)
#         raise ValueError(error_msg)

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
    """Pull an image from a remote registry.
    
    Args:
        repository: The repository to pull from (e.g., 'nginx' or 'docker.io/library/nginx')
        tag: The image tag to pull (default: 'latest')
        
    Returns:
        Dict containing image details including id, tags, and short_id
    """
    try:
        image = client.images.pull(repository, tag=tag)
        return {
            'id': image.id,
            'tags': image.tags,
            'short_id': image.short_id,
            'status': 'success',
            'message': f'Successfully pulled {repository}:{tag}'
        }
    except Exception as e:
        error_msg = f"Error pulling image {repository}:{tag}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

@mcp.tool()
async def tag_image(image_reference: str, repository: str, tag: str = "latest") -> Dict[str, Any]:
    """Tag a local image with a new repository and tag.
    
    Args:
        image_reference: The image ID, name, or tag to tag
        repository: The repository name to tag the image with
        tag: The tag to apply (default: 'latest')
        
    Returns:
        Dict with status and image information
    """
    try:
        image = client.images.get(image_reference)
        new_tag = f"{repository}:{tag}"
        result = image.tag(repository=repository, tag=tag)
        if not result:
            raise ValueError(f"Failed to tag image {image_reference} as {new_tag}")
            
        # Get the updated image to return complete info
        updated_image = client.images.get(f"{repository}:{tag}")
        return {
            'status': 'success',
            'message': f'Successfully tagged {image_reference} as {new_tag}',
            'image_id': updated_image.id,
            'tags': updated_image.tags,
            'short_id': updated_image.short_id,
            'new_reference': new_tag
        }
    except docker.errors.ImageNotFound:
        error_msg = f"Image not found: {image_reference}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error tagging image {image_reference} as {repository}:{tag}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

@mcp.tool()
async def push_image(repository: str, tag: str = "latest", auth_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Push an image to a registry.
    
    Args:
        repository: The repository to push to (e.g., 'myusername/myimage' or 'registry.example.com/myimage')
        tag: The tag to push (default: 'latest')
        auth_config: Optional dictionary with 'username' and 'password' for private registries
        
    Returns:
        Dict with push status and logs
    """
    image_ref = f"{repository}:{tag}"
    try:
        # First check if the image exists locally
        try:
            image = client.images.get(image_ref)
        except docker.errors.ImageNotFound:
            error_msg = f"Local image not found: {image_ref}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Push the image
        logger.info(f"Pushing {image_ref} to registry...")
        
        # Use auth_config if provided, otherwise try to use default docker config
        push_logs = []
        for line in client.images.push(
            repository=repository,
            tag=tag,
            stream=True,
            decode=True,
            auth_config=auth_config
        ):
            log_entry = line.get('status', '').strip()
            if log_entry:
                push_logs.append(log_entry)
                logger.info(f"Push log: {log_entry}")
        
        return {
            'status': 'success',
            'message': f'Successfully pushed {image_ref}',
            'image_id': image.id,
            'tags': image.tags,
            'logs': push_logs
        }
        
    except docker.errors.APIError as e:
        error_msg = f"Docker API error pushing {image_ref}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error pushing {image_ref}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

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

@mcp.tool()
async def health_check() -> dict:
    """
    Check if the server is running and can connect to Docker.
    
    Returns:
        dict: A dictionary containing the health status, Docker connection status,
              and any error messages if applicable.
    """
    try:
        # Try to connect to Docker
        client = docker.from_env()
        client.ping()
        
        # Check if we can list containers (more thorough check)
        try:
            client.containers.list(limit=1)
            containers_accessible = True
        except Exception as e:
            containers_accessible = False
            return {
                "status": "unhealthy",
                "docker_connected": True,
                "containers_accessible": containers_accessible,
                "error": f"Could not list containers: {str(e)}"
            }
            
        return {
            "status": "healthy", 
            "docker_connected": True,
            "containers_accessible": containers_accessible,
            "timestamp": dt.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "docker_connected": False, 
            "error": str(e),
            "timestamp": dt.utcnow().isoformat()
        }

def parse_args():
    """Parse command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Docker MCP Server')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to bind the server to')
    parser.add_argument('--transport', type=str, choices=['stdio', 'http'], default='http',
                        help='Transport mode (stdio or http)')
    parser.add_argument('--timeout', type=int, default=30, 
                       help='Request timeout in seconds')
    
    return parser.parse_args()

def main():
    """Main entry point for the MCP server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    logger = logging.getLogger('docker-mcp')
    
    args = parse_args()
    
    # Initialize Docker client
    try:
        logger.info("Initializing Docker client...")
        docker_client = docker.from_env(timeout=args.timeout)
        logger.info(f"Docker client connected: {docker_client.ping()}")
    except Exception as e:
        logger.error(f"Error initializing Docker client: {e}")
        sys.exit(1)
    
    # Print startup information
    print(f"Starting Docker MCP server in {args.transport} mode...", file=sys.stderr)
    if args.transport == 'http':
        print(f"HTTP server will be available at http://{args.host}:{args.port}", file=sys.stderr)
    
    # Test Docker connection
    try:
        client = docker.from_env()
        client.ping()
        print(f"Docker client connected: {client is not None}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to connect to Docker: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print server startup message
    print("Docker MCP server is starting...", file=sys.stderr)
    
    if args.transport == 'http':
        logger.info(f"Starting HTTP server on {args.host}:{args.port}")
        
        try:
            import uvicorn
            from fastapi import FastAPI, Request, Response
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI()
            
            # Add CORS middleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            @app.middleware("http")
            async def log_requests(request: Request, call_next):
                logger.info(f"Request: {request.method} {request.url}")
                try:
                    response = await call_next(request)
                    logger.info(f"Response: {response.status_code}")
                    return response
                except Exception as e:
                    logger.error(f"Error processing request: {e}", exc_info=True)
                    raise
            
            @app.get("/health")
            async def health():
                try:
                    # Check Docker daemon connectivity
                    docker_client.ping()
                    return {"status": "ok", "docker": "connected"}
                except Exception as e:
                    logger.error(f"Health check failed: {e}")
                    return Response(
                        content={"status": "error", "message": str(e)},
                        status_code=500,
                        media_type="application/json"
                    )
            
            # Add a simple root endpoint
            @app.get("/")
            async def root():
                return {"message": "Docker MCP Server is running"}
            
            # Configure and run the server
            config = uvicorn.Config(
                app,
                host=args.host,
                port=args.port,
                log_level="info",
                timeout_keep_alive=args.timeout,
                timeout_graceful_shutdown=args.timeout,
            )
            server = uvicorn.Server(config)
            
            # Run the server in a separate function to handle the event loop
            async def run_server():
                await server.serve()
            
            # Run the async function
            import asyncio
            asyncio.run(run_server())
            
        except Exception as e:
            logger.error(f"Error starting HTTP server: {e}", exc_info=True)
            sys.exit(1)
    else:
        # In stdio mode, just run the MCP server
        logger.info("Starting in stdio mode")
        try:
            mcp.run(transport="stdio")
        except Exception as e:
            logger.error(f"Error in stdio mode: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    import sys
    
    # Run the main function
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        sys.exit(0)
