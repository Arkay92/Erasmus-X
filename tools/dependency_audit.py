import os
import sys
import json

def audit_dependencies(root_dir="."):
    """Checks package.json and requirements.txt for status."""
    print("--- Dependency Audit ---")
    
    # 1. Check Node.js dependencies
    pkg_json = os.path.join(root_dir, 'package.json')
    if os.path.exists(pkg_json):
        print(f"[*] Found package.json. Analyzing...")
        try:
            with open(pkg_json, 'r') as f:
                data = json.load(f)
                deps = data.get('dependencies', {})
                dev_deps = data.get('devDependencies', {})
                print(f"    - Dependencies: {len(deps)}")
                for d, v in deps.items():
                    print(f"      {d}: {v}")
                print(f"    - Dev Dependencies: {len(dev_deps)}")
        except Exception as e:
            print(f"    [!] Error reading package.json: {e}")
            
    # 2. Check Python dependencies
    req_txt = os.path.join(root_dir, 'requirements.txt')
    if os.path.exists(req_txt):
        print(f"[*] Found requirements.txt. Analyzing...")
        try:
            with open(req_txt, 'r') as f:
                reqs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                print(f"    - Requirements: {len(reqs)}")
                for r in reqs:
                    print(f"      {r}")
        except Exception as e:
            print(f"    [!] Error reading requirements.txt: {e}")
            
    if not os.path.exists(pkg_json) and not os.path.exists(req_txt):
        print("[!] No standard dependency files found in root.")

if __name__ == "__main__":
    audit_dependencies()
