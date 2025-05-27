#!/usr/bin/env python3

from docker_scout import get_image_vulnerabilities
import json

def main():
    image_reference = "kalyanram262/mcp-test:latest"
    print(f"Scanning image: {image_reference}")
    
    try:
        result = get_image_vulnerabilities(image_reference)
        
        # Print a summary
        print("\n=== Scan Results ===")
        print(f"Status: {result.get('status', 'unknown')}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            return
            
        if 'warning' in result:
            print(f"Warning: {result['warning']}")
            
        print(f"\nTotal vulnerabilities: {result.get('vulnerability_count', 0)}")
        print("Severity breakdown:")
        for severity, count in result.get('severity_counts', {}).items():
            print(f"  - {severity.capitalize()}: {count}")
            
        # Print first few vulnerabilities as samples
        print("\nSample vulnerabilities:")
        for i, vuln in enumerate(result.get('vulnerabilities', [])[:3]):
            print(f"\n{i+1}. {vuln.get('id', 'Unknown')} - {vuln.get('title', 'No title')}")
            print(f"   Severity: {vuln.get('severity', 'unknown')}")
            print(f"   Package: {vuln.get('package', 'unknown')} {vuln.get('version', '')}")
            if vuln.get('fixed_version'):
                print(f"   Fixed in: {vuln['fixed_version']}")
            print(f"   More info: {vuln.get('urls', [''])[0]}")
            
        # Save full results to a file
        with open('vulnerability_scan.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\nFull results saved to 'vulnerability_scan.json'")
        
    except Exception as e:
        print(f"Error during scan: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
