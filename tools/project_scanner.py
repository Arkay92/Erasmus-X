import os
import sys

def scan_project(root_dir="."):
    """Recursively lists files and sizes, ignoring noisy directories."""
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'memories', 'scratch'}
    file_map = []
    
    print(f"| {'File Path':<60} | {'Size (KB)':<10} |")
    print(f"|{'-'*62}|{'-'*12}|")
    
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Filter ignore dirs in-place
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            path = os.path.join(root, file)
            try:
                size_kb = os.path.getsize(path) / 1024
                rel_path = os.path.relpath(path, root_dir)
                print(f"| {rel_path:<60} | {size_kb:<10.2f} |")
                total_size += size_kb
                file_count += 1
            except OSError:
                pass
                
    print(f"\n[SCAN COMPLETE] Total Files: {file_count} | Total Size: {total_size/1024:.2f} MB")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_project(target)
