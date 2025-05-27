"""
Docker Scout integration for MCP server.
Provides vulnerability scanning and analysis for Docker images.
"""

import json
import logging
import subprocess
import sys
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class DockerScoutError(Exception):
    """Custom exception for Docker Scout related errors."""
    pass

def is_docker_installed() -> bool:
    """Check if Docker is installed and available in PATH."""
    try:
        subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def is_docker_running() -> bool:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def is_docker_scout_installed() -> bool:
    """Check if Docker Scout is available via Docker CLI."""
    if not is_docker_installed() or not is_docker_running():
        return False
    
    try:
        result = subprocess.run(
            ["docker", "scout", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Check if the command executed successfully and contains expected output
        return result.returncode == 0 and "Docker Scout" in result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def run_command(cmd: List[str], check: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return the result."""
    logger.debug(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with code {e.returncode}: {e.stderr}")
        if check:
            raise DockerScoutError(f"Command failed: {e.stderr}") from e
        return e.returncode, e.stdout, e.stderr
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        if check:
            raise DockerScoutError(f"Error running command: {str(e)}") from e
        return -1, "", str(e)

def run_docker_scout_command(args: List[str]) -> Union[Dict, List[Dict]]:
    """
    Run a Docker Scout command and return the parsed JSON output.
    
    Args:
        args: List of arguments to pass to 'docker scout'
        
    Returns:
        Parsed JSON output as a dictionary or list
    """
    if not is_docker_scout_installed():
        raise RuntimeError("Docker Scout is not installed or not in PATH")
    
    try:
        # Ensure we have the --format json flag
        if "--format" not in args and "-f" not in args:
            args.extend(["--format", "json"])
            
        # Build the full command
        cmd = ["docker", "scout", *args]
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(
            cmd,
            check=False,  # Don't raise exception on non-zero exit code
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Check for version warning in stderr
        version_warning = None
        if result.stderr:
            for line in result.stderr.splitlines():
                if "new version" in line.lower() and "available" in line.lower():
                    version_warning = line.strip()
                    logger.warning(f"Docker Scout version notice: {version_warning}")
                elif line.strip() and not line.startswith('[') and not line.startswith(' '):
                    # Log other non-empty stderr lines that aren't just formatting
                    logger.warning(f"Docker Scout stderr: {line}")
        
        # If command failed, return error
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Command failed with exit code {result.returncode}"
            logger.error(f"Docker Scout command failed: {error_msg}")
            return {"error": error_msg}
        
        # Check if we have any output
        if not result.stdout.strip():
            # If we have a version warning but no other output, return it
            if version_warning:
                return {"warning": version_warning}
            return {}
            
        # Try to parse the JSON output
        try:
            output = json.loads(result.stdout)
            
            # If we got a version warning, include it in the output
            if version_warning and isinstance(output, dict):
                output["warning"] = version_warning
                
            return output
            
        except json.JSONDecodeError as e:
            # If we have a version warning and the output is empty, return empty dict
            if version_warning and not result.stdout.strip():
                return {"warning": version_warning}
                
            logger.error(f"Failed to parse JSON output: {e}")
            logger.debug(f"Command output: {result.stdout}")
            return {"error": f"Failed to parse command output: {str(e)}"}
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error running Docker Scout command: {error_msg}", exc_info=True)
        return {"error": f"Error running Docker Scout: {error_msg}"}
    except Exception as e:
        error_msg = f"Error running Docker Scout: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}

def get_image_vulnerabilities(image_reference: str) -> Dict[str, Any]:
    """
    Get vulnerabilities for a Docker image using 'docker scout cves'.
    
    Args:
        image_reference: Docker image reference (name:tag or digest)
        
    Returns:
        Dict containing vulnerability information
    """
    try:
        # First, pull the image if it's not available locally
        try:
            logger.info(f"Pulling image {image_reference}...")
            pull_result = subprocess.run(
                ["docker", "pull", image_reference],
                capture_output=True,
                text=True,
                check=False
            )
            if pull_result.returncode != 0:
                logger.warning(f"Failed to pull image {image_reference}, using local copy: {pull_result.stderr}")
        except Exception as e:
            logger.warning(f"Error pulling image {image_reference}: {str(e)}")
        
        # Run the docker scout command with text output
        logger.debug(f"Running 'docker scout cves {image_reference}'")
        return_code, stdout, stderr = run_command(
            ["docker", "scout", "cves", image_reference],
            check=False
        )
        
        # Check for errors
        if return_code != 0:
            error_msg = stderr.strip() or f"Command failed with exit code {return_code}"
            logger.error(f"Docker Scout command failed: {error_msg}")
            return {
                "vulnerabilities": [],
                "error": error_msg,
                "vulnerability_count": 0
            }
        
        # Parse the text output
        vulnerabilities = []
        current_package = None
        current_vuln = None
        
        # Regular expressions for parsing
        import re
        pkg_pattern = re.compile(r'\s*(\d+)C\s+(\d+)H\s+(\d+)M\s+(\d+)L\s+(\S+)\s+(\S+)')
        vuln_pattern = re.compile(r'✗\s+(\w+)\s+(CVE-\d+-\d+)(?:\s+\[(.+?)\])?')
        fixed_version_pattern = re.compile(r'Fixed version\s+:\s+(.+)')
        affected_range_pattern = re.compile(r'Affected range\s+:\s+(.+)')
        
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for package line (e.g., "0C     2H     0M     0L  setuptools 65.5.1")
            pkg_match = pkg_pattern.match(line)
            if pkg_match:
                current_package = {
                    'name': pkg_match.group(5),
                    'version': pkg_match.group(6),
                    'critical': int(pkg_match.group(1)),
                    'high': int(pkg_match.group(2)),
                    'medium': int(pkg_match.group(3)),
                    'low': int(pkg_match.group(4))
                }
                continue
                
            # Check for vulnerability line (e.g., "✗ HIGH CVE-2025-47273 [Improper Limitation...]")
            vuln_match = vuln_pattern.match(line)
            if vuln_match and current_package:
                if current_vuln and current_vuln not in vulnerabilities:
                    vulnerabilities.append(current_vuln)
                
                severity = vuln_match.group(1).lower()
                cve = vuln_match.group(2)
                title = vuln_match.group(3) or "Vulnerability in " + current_package['name']
                
                current_vuln = {
                    'id': cve,
                    'severity': severity,
                    'title': title,
                    'package': current_package['name'],
                    'version': current_package['version'],
                    'fixed_version': '',
                    'affected_range': '',
                    'description': '',
                    'urls': [f"https://scout.docker.com/v/{cve}"]
                }
                continue
                
            # Check for fixed version
            fixed_match = fixed_version_pattern.match(line)
            if fixed_match and current_vuln:
                current_vuln['fixed_version'] = fixed_match.group(1).strip()
                
            # Check for affected range
            affected_match = affected_range_pattern.match(line)
            if affected_match and current_vuln:
                current_vuln['affected_range'] = affected_match.group(1).strip()
        
        # Add the last vulnerability if exists
        if current_vuln and current_vuln not in vulnerabilities:
            vulnerabilities.append(current_vuln)
        
        # Count vulnerabilities by severity
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'unknown': 0
        }
        
        for vuln in vulnerabilities:
            severity = vuln.get('severity', 'unknown')
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Prepare the result
        result = {
            'vulnerabilities': vulnerabilities,
            'vulnerability_count': len(vulnerabilities),
            'severity_counts': severity_counts,
            'status': 'success'
        }
        
        # Add version warning if present in stderr
        version_warning = None
        for line in stderr.split('\n'):
            if 'new version' in line.lower() and 'available' in line.lower():
                version_warning = line.strip()
                break
                
        if version_warning:
            result['warning'] = version_warning
            
        return result
        
        # Handle error cases for JSON output
        if isinstance(result, dict) and "error" in result:
            error_msg = result["error"]
            # If the error is just a version warning, continue processing
            if "new version" in error_msg.lower() and "available" in error_msg.lower():
                logger.warning(f"Docker Scout version notice: {error_msg}")
                # If we have no other data, return empty results with warning
                if not result.get("vulnerabilities"):
                    return {
                        "vulnerabilities": [],
                        "warning": error_msg,
                        "vulnerability_count": 0
                    }
            else:
                logger.error(f"Docker Scout error: {error_msg}")
                return {"vulnerabilities": [], "error": error_msg}
        
        # Extract vulnerabilities from the result
        vulnerabilities = []
        warning = None
        
        # Check if we have a warning from the version check
        if isinstance(result, dict) and "warning" in result:
            warning = result["warning"]
            logger.warning(f"Docker Scout version notice: {warning}")
        
        # Case 1: Direct list of vulnerabilities
        if isinstance(result, list):
            vulnerabilities = result
        # Case 2: Nested under 'vulnerabilities' key
        elif isinstance(result, dict) and "vulnerabilities" in result and isinstance(result["vulnerabilities"], list):
            vulnerabilities = result["vulnerabilities"]
        # Case 3: Single vulnerability object
        elif isinstance(result, dict) and "id" in result and "severity" in result:
            vulnerabilities = [result]
        # Case 4: Empty or unknown format
        elif result:
            logger.warning(f"Unexpected vulnerability data format: {result}")
            vulnerabilities = []
        
        # Ensure each vulnerability has the expected fields
        processed_vulns = []
        for vuln in vulnerabilities:
            if not isinstance(vuln, dict):
                continue
                
            # Standardize the vulnerability format
            processed = {
                "id": vuln.get("id") or vuln.get("name") or "unknown",
                "severity": str(vuln.get("severity", "unknown")).lower(),
                "title": vuln.get("title") or vuln.get("name") or "Vulnerability",
                "description": vuln.get("description") or vuln.get("details") or "",
                "package": vuln.get("package", {}).get("name") if isinstance(vuln.get("package"), dict) else "",
                "version": vuln.get("package", {}).get("version") if isinstance(vuln.get("package"), dict) else "",
                "fixed_version": vuln.get("fix_version") or vuln.get("fixed_version") or "",
                "cve": vuln.get("cve") or vuln.get("id") or "",
                "urls": vuln.get("urls") or []
            }
            
            # Clean up None values
            processed = {k: v for k, v in processed.items() if v is not None}
            processed_vulns.append(processed)
        
        # Prepare the result
        result = {
            "vulnerabilities": processed_vulns,
            "vulnerability_count": len(processed_vulns)
        }
        
        # Add warning if present
        if warning:
            result["warning"] = warning
            
        return result
        
    except Exception as e:
        error_msg = f"Error getting vulnerabilities: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "vulnerabilities": [], 
            "vulnerability_count": 0,
            "error": error_msg
        }

def get_image_recommendations(image_reference: str) -> Dict[str, Any]:
    """
    Get recommendations for a Docker image using 'docker scout recommendations'.
    
    Args:
        image_reference: Docker image reference (name:tag or digest)
        
    Returns:
        Dict containing recommendation information
    """
    try:
        logger.debug(f"Running 'docker scout recommendations {image_reference} --format json'")

        result = run_docker_scout_command(["recommendations", image_reference, "--format", "json"])
        
        # Handle error cases
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Docker Scout recommendations error: {result['error']}")
            return {"recommendations": [], "error": result['error']}
        
        recommendations = []
        
        # Case 1: Direct list of recommendations
        if isinstance(result, list):
            recommendations = result
        # Case 2: Nested under 'recommendations' key
        elif isinstance(result, dict) and "recommendations" in result and isinstance(result["recommendations"], list):
            recommendations = result["recommendations"]
        # Case 3: Single recommendation object
        elif isinstance(result, dict) and ("current" in result or "recommended" in result):
            recommendations = [result]
        # Case 4: Empty or unknown format
        elif result:
            logger.warning(f"Unexpected recommendations data format: {result}")
            recommendations = []
        
        # Process each recommendation to standardize the format
        processed_recs = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
                
            # Extract common fields
            rec_type = rec.get("type", "recommendation").lower()
            current = rec.get("current") or rec.get("from") or ""
            recommended = rec.get("recommended") or rec.get("to") or ""
            reason = rec.get("reason") or rec.get("description") or ""
            
            # Create a standardized recommendation
            processed = {
                "type": rec_type,
                "current": current,
                "recommended": recommended,
                "reason": reason or "Update available",
                "severity": rec.get("severity", "info").lower(),
                "package": rec.get("package") or ""
            }
            
            # Add any additional fields
            for key, value in rec.items():
                if key not in processed and not key.startswith('_'):
                    processed[key] = value
            
            # Clean up None values
            processed = {k: v for k, v in processed.items() if v is not None}
            processed_recs.append(processed)
        
        return {
            "recommendations": processed_recs,
            "recommendation_count": len(processed_recs)
        }
        
    except Exception as e:
        error_msg = f"Error getting recommendations: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "recommendations": [],
            "error": error_msg
        }

def get_summary_stats(vulnerabilities: Dict[str, Any]) -> Dict[str, int]:
    """
    Get summary statistics from vulnerability data.
    
    Args:
        vulnerabilities: Vulnerability data from Docker Scout
        
    Returns:
        Dict with severity counts
    """
    summary = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "negligible": 0,
        "unknown": 0,
        "total": 0
    }
    
    if not vulnerabilities or not isinstance(vulnerabilities, dict):
        return summary
    
    try:
        # Handle different response formats
        vulns = []
        
        # Case 1: Direct list of vulnerabilities
        if isinstance(vulnerabilities, list):
            vulns = vulnerabilities
        # Case 2: Nested under 'vulnerabilities' key
        elif "vulnerabilities" in vulnerabilities and isinstance(vulnerabilities["vulnerabilities"], list):
            vulns = vulnerabilities["vulnerabilities"]
        # Case 3: Direct vulnerability object
        elif "severity" in vulnerabilities:
            vulns = [vulnerabilities]
        # Case 4: Check for other possible keys that might contain vulnerabilities
        else:
            # Look for any key that might contain a list of vulnerabilities
            for value in vulnerabilities.values():
                if isinstance(value, list) and value and isinstance(value[0], dict) and "severity" in value[0]:
                    vulns = value
                    break
        
        # Count vulnerabilities by severity
        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue
                
            # Handle different severity field names and formats
            severity = ""
            if "severity" in vuln:
                severity = str(vuln["severity"]).lower()
            elif "severity_level" in vuln:
                severity = str(vuln["severity_level"]).lower()
            elif "level" in vuln:
                severity = str(vuln["level"]).lower()
            
            # Map to standard severity levels
            if "critical" in severity:
                severity = "critical"
            elif "high" in severity:
                severity = "high"
            elif "medium" in severity or "moderate" in severity:
                severity = "medium"
            elif "low" in severity:
                severity = "low"
            elif "negligible" in severity or "info" in severity or "informational" in severity:
                severity = "negligible"
            else:
                severity = "unknown"
            
            if severity in summary:
                summary[severity] += 1
                summary["total"] += 1
        
        return summary
    except Exception as e:
        logger.error(f"Error generating summary stats: {e}", exc_info=True)
        return summary

def format_recommendations(recommendations: Dict[str, Any]) -> str:
    """
    Format recommendations into a human-readable string.
    
    Args:
        recommendations: Recommendations data from Docker Scout
        
    Returns:
        Formatted string with recommendations
    """
    if not recommendations or not isinstance(recommendations, dict):
        return "No recommendations available."
    
    try:
        output = []
        
        # Handle different recommendation formats
        if "recommendations" in recommendations and isinstance(recommendations["recommendations"], list):
            recs = recommendations["recommendations"]
        elif isinstance(recommendations, dict) and any(isinstance(v, dict) for v in recommendations.values()):
            # Handle case where recommendations is already a dict of recommendations
            recs = [v for v in recommendations.values() if isinstance(v, dict)]
        else:
            recs = []
        
        # Process each recommendation
        for rec in recs:
            if not isinstance(rec, dict):
                continue
                
            # Handle different recommendation types and formats
            rec_type = rec.get("type", "recommendation").replace("_", " ").title()
            
            # Base image update recommendation
            if "current" in rec and "recommended" in rec:
                current = rec.get("current", "unknown")
                recommended = rec.get("recommended", "unknown")
                reason = rec.get("reason", "Update available")
                
                output.append(f"{rec_type}: {current} → {recommended}")
                if reason and reason != "Update available":
                    output[-1] += f" ({reason})"
            
            # Package update recommendation
            elif "package" in rec and "version" in rec and "fix_version" in rec:
                pkg = rec["package"]
                version = rec["version"]
                fix_version = rec["fix_version"]
                output.append(f"Package Update: {pkg} {version} → {fix_version}")
            
            # Generic key-value pairs
            else:
                # Skip internal fields
                skip_fields = {"id", "type", "status", "severity"}
                items = [f"{k}: {v}" for k, v in rec.items() 
                        if k not in skip_fields and not k.startswith('_')]
                if items:
                    output.append(" • " + ", ".join(items))
        
        # Handle case where recommendations is a list at the top level
        if not output and isinstance(recommendations, list):
            for item in recommendations:
                if isinstance(item, dict):
                    output.append(" • " + ", ".join(f"{k}: {v}" for k, v in item.items() 
                                                 if not k.startswith('_')))
        
        if not output:
            # Check if there's a message field
            if "message" in recommendations:
                return str(recommendations["message"])
            return "No specific recommendations available."
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error formatting recommendations: {e}", exc_info=True)
        return f"Error formatting recommendations: {str(e)}"
