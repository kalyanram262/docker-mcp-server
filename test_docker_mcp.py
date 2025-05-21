import pytest
import docker
import time
import requests
from docker_mcp_server import app

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGE = "alpine:3.14"
TEST_CONTAINER_NAME = "test-container"

@pytest.fixture(scope="module")
def docker_client():
    return docker.from_env()

def test_list_containers():
    response = requests.post(f"{BASE_URL}/list_containers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_pull_image():
    # First, remove the image if it exists
    try:
        client = docker.from_env()
        client.images.remove(TEST_IMAGE, force=True)
    except:
        pass
    
    response = requests.post(
        f"{BASE_URL}/pull_image",
        json={"repository": "alpine", "tag": "3.14"}
    )
    assert response.status_code == 200
    assert "id" in response.json()

def test_run_container():
    # Clean up any existing test container
    try:
        client = docker.from_env()
        container = client.containers.get(TEST_CONTAINER_NAME)
        container.remove(force=True)
    except:
        pass
    
    response = requests.post(
        f"{BASE_URL}/run_container",
        json={
            "image": TEST_IMAGE,
            "name": TEST_CONTAINER_NAME,
            "command": "sleep 30",
            "detach": True
        }
    )
    assert response.status_code == 200
    assert response.json()["name"] == TEST_CONTAINER_NAME
    
    # Verify the container is running
    client = docker.from_env()
    container = client.containers.get(TEST_CONTAINER_NAME)
    assert container.status == "running"
    
    # Clean up
    container.remove(force=True)

def test_stop_container():
    # Create a test container
    client = docker.from_env()
    container = client.containers.run(
        TEST_IMAGE,
        "sleep 60",
        name=TEST_CONTAINER_NAME,
        detach=True
    )
    
    # Wait for container to be running
    time.sleep(2)
    
    # Test stopping the container
    response = requests.post(
        f"{BASE_URL}/stop_container",
        json={"container_id": container.id}
    )
    assert response.status_code == 200
    
    # Verify the container is stopped
    container.reload()
    assert container.status == "exited"
    
    # Clean up
    container.remove()

def test_remove_container():
    # Create a test container
    client = docker.from_env()
    container = client.containers.run(
        TEST_IMAGE,
        "sleep 1",
        name=TEST_CONTAINER_NAME,
        detach=True
    )
    
    # Wait for container to exit
    time.sleep(2)
    
    # Test removing the container
    response = requests.post(
        f"{BASE_URL}/remove_container",
        json={"container_id": container.id}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify the container is removed
    with pytest.raises(docker.errors.NotFound):
        client.containers.get(container.id)

def test_list_images():
    response = requests.post(f"{BASE_URL}/list_images")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_networks():
    response = requests.post(f"{BASE_URL}/list_networks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_volumes():
    response = requests.post(f"{BASE_URL}/list_volumes")
    assert response.status_code == 200
    assert "volumes" in response.json()
    assert isinstance(response.json()["volumes"], list)
