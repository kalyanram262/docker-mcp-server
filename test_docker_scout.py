#!/usr/bin/env python3
"""
Test script for Docker Scout integration.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title: str, width: int = 50):
    """Print a formatted section header."""
    print(f"\n{title}")
    print("=" * len(title))

async def test_scan_image(image_reference: str) -> bool:
    """Test scanning a Docker image for vulnerabilities."""
    try:
        from docker_mcp_server import scan_image
        
        print_section(f"🔍 Scanning image: {image_reference}")
        print("This may take a few moments...")
        
        # Run the scan
        result = await scan_image(image_reference)
        
        # Handle errors
        if result.get("status") == "error":
            print(f"❌ Error: {result.get('error')}")
            if "suggestion" in result:
                print(f"💡 Suggestion: {result['suggestion']}")
            return False
        
        # Print scan summary
        print_section("📊 Scan Results")
        print(f"Image:          {result.get('image', 'N/A')}")
        print(f"Status:         {result.get('status', 'unknown')}")
        print(f"Timestamp:      {result.get('timestamp', 'N/A')}")
        
        # Check for warnings first
        if "warning" in result:
            print_section("⚠️  Warning")
            print(result["warning"])
        
        # Print vulnerability summary
        summary = result.get('summary', {})
        if summary:
            print_section("📋 Vulnerability Summary")
            severities = [
                ('critical', '🔴'),
                ('high', '🟠'),
                ('medium', '🟡'),
                ('low', '🔵'),
                ('negligible', '⚪'),
                ('unknown', '⚫')
            ]
            
            for severity, icon in severities:
                count = summary.get(severity, 0)
                if count > 0:
                    print(f"{icon} {severity.capitalize()}: {count}")
            
            total = summary.get('total', 0)
            print(f"\n📊 Total: {total} vulnerabilities")
        
        # Print a sample of vulnerabilities if any
        vulnerabilities = result.get('vulnerabilities', [])
        if vulnerabilities:
            print_section("🔍 Vulnerabilities Found")
            
            # Group vulnerabilities by package
            packages = {}
            for vuln in vulnerabilities:
                pkg_name = vuln.get('package', 'unknown')
                if pkg_name not in packages:
                    packages[pkg_name] = []
                packages[pkg_name].append(vuln)
            
            # Print vulnerabilities by package
            for pkg_name, vulns in packages.items():
                print(f"\n📦 Package: {pkg_name}")
                if vulns and 'version' in vulns[0]:
                    print(f"   Version: {vulns[0]['version']}")
                
                for i, vuln in enumerate(vulns, 1):
                    print(f"\n   {i}. {vuln.get('title', 'Vulnerability')}")
                    print(f"      Severity: {vuln.get('severity', 'unknown').capitalize()}")
                    if vuln.get('cve'):
                        print(f"      CVE: {vuln['cve']}")
                    if vuln.get('fixed_version'):
                        print(f"      Fixed in version: {vuln['fixed_version']}")
                    if vuln.get('description'):
                        desc = vuln['description']
                        if len(desc) > 100:  # Truncate long descriptions
                            desc = desc[:97] + '...'
                        print(f"      Description: {desc}")
        
        # Print recommendations if available
        recommendations = result.get('recommendations')
        if recommendations and isinstance(recommendations, str) and recommendations.strip():
            print_section("💡 Recommendations")
            print(recommendations)
        elif not vulnerabilities:
            print("\n✅ No vulnerabilities found!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importing modules: {e}")
        print("Make sure you're in the correct directory and have installed all requirements.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function to run tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_docker_scout.py <image_reference>")
        print("Example: python test_docker_scout.py nginx:latest")
        print("\nYou can also scan multiple images by providing multiple arguments.")
        print("Example: python test_docker_scout.py nginx:latest python:3.9-alpine")
        sys.exit(1)
    
    image_references = sys.argv[1:]
    
    print("🚀 Docker Scout Integration Tester")
    print("=" * 50)
    
    # Check Docker and Docker Scout availability
    try:
        from docker_scout import is_docker_installed, is_docker_running, is_docker_scout_installed
        
        if not is_docker_installed():
            print("❌ Docker is not installed or not in PATH")
            print("Please install Docker from https://www.docker.com/")
            sys.exit(1)
        
        if not is_docker_running():
            print("❌ Docker daemon is not running")
            print("Please start Docker and try again")
            sys.exit(1)
        
        if not is_docker_scout_installed():
            print("❌ Docker Scout is not available")
            print("Docker Scout is included in Docker Desktop by default.")
            print("If you're using Docker Engine, you may need to install it separately.")
            sys.exit(1)
            
        print("✅ Docker and Docker Scout are available")
        
    except Exception as e:
        print(f"❌ Error checking Docker and Docker Scout: {e}")
        sys.exit(1)
    
    # Test each image
    success_count = 0
    for i, image_ref in enumerate(image_references):
        if i > 0:
            print("\n" + "-" * 50)
        success = await test_scan_image(image_ref)
        if success:
            success_count += 1
    
    # Print final summary
    print("\n" + "=" * 50)
    print(f"Tests completed: {success_count} out of {len(image_references)} successful")
    
    if success_count < len(image_references):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
