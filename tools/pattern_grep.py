import os
import sys
import re

def grep_pattern(pattern, root_dir=".", extensions=None):
    """Searches for a regex pattern across specified file types."""
    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'memories', 'scratch'}
    if extensions is None:
        extensions = {'.py', '.md', '.tsx', '.ts', '.js', '.json', '.txt', '.html', '.css'}

    regex = re.compile(pattern, re.IGNORECASE)
    print(f"[*] Grep Search: Searching for '{pattern}' in {extensions} files...")
    
    match_count = 0
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = os.path.relpath(path, root_dir)
                                print(f"{rel_path}:{line_num}: {line.strip()}")
                                match_count += 1
                except OSError:
                    pass

    print(f"\n[GREP COMPLETE] Found {match_count} matches.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pattern_grep.py <pattern>")
        sys.exit(1)
    grep_pattern(sys.argv[1])
