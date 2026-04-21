import os
import shutil
import tempfile
from pathlib import Path

class SandboxManager:
    """Manages isolated build environments for autonomous coding."""
    
    def __init__(self, root_dir=None):
        if not root_dir:
            # Fallback to local 'sandboxes' folder
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            root_dir = os.path.join(base_path, 'sandboxes')
        
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)
        print(f"[*] Sandbox Manager initialized at: {self.root_dir}")

    def create_sandbox(self, name):
        """Creates a new isolated directory for a project."""
        sandbox_path = os.path.join(self.root_dir, name)
        os.makedirs(sandbox_path, exist_ok=True)
        return sandbox_path

    def is_safe_path(self, sandbox_name, target_path):
        """Prevents path traversal outside the sandbox."""
        sandbox_path = os.path.abspath(os.path.join(self.root_dir, sandbox_name))
        target_abs = os.path.abspath(target_path)
        return target_abs.startswith(sandbox_path)

    def cleanup(self, sandbox_name):
        """Removes a sandbox directory."""
        sandbox_path = os.path.join(self.root_dir, sandbox_name)
        if os.path.exists(sandbox_path):
            shutil.rmtree(sandbox_path)
            print(f"[*] Sandbox '{sandbox_name}' cleaned up.")

    def get_audit(self, sandbox_name):
        """Returns a list of files in the sandbox."""
        sandbox_path = os.path.join(self.root_dir, sandbox_name)
        if not os.path.exists(sandbox_path):
            return []
        
        files = []
        for root, _, filenames in os.walk(sandbox_path):
            for f in filenames:
                rel_path = os.path.relpath(os.path.join(root, f), sandbox_path)
                files.append(rel_path)
        return files
