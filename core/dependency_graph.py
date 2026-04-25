import re
import os

class DependencyGraph:
    def __init__(self, manifest):
        self.manifest = set(manifest)
        self.graph = {} # {file: [dependencies]}
        self.exports = {} # {file: {exported_names}}

    def update_file(self, filename, code):
        """Parses file code to extract imports and exports."""
        deps = []
        
        # Next.js / JS Imports
        js_imports = re.findall(r"from\s+['\"](.*?)['\"]", code)
        for imp in js_imports:
            res = imp.replace('@/', '')
            target = self._resolve_path(filename, res)
            if target:
                deps.append(target)

        # Python Imports
        py_imports = re.findall(r"^import\s+(\w+)|^from\s+(\w+)\s+import", code, re.MULTILINE)
        for p1, p2 in py_imports:
            mod = p1 if p1 else p2
            target = self._resolve_path(filename, mod)
            if target:
                deps.append(target)

        self.graph[filename] = list(set(deps))

    def _resolve_path(self, current_file, import_path):
        """Heuristic resolver for local imports, handling @/ and basenames."""
        norm_imp = import_path.replace('@/', '').lstrip('./').lstrip('../')
        import_base = os.path.basename(norm_imp).split('.')[0]
        
        if norm_imp in self.manifest: return norm_imp
        
        for m in self.manifest:
            m_base = os.path.basename(m).split('.')[0]
            if m_base == import_base:
                return m
        return None

    def validate(self):
        """Checks if all internal dependencies resolve to a manifest target."""
        errors = []
        for f, deps in self.graph.items():
            for d in deps:
                if d not in self.graph and d not in self.manifest:
                    errors.append(f"Unresolved dependency: {f} -> {d}")
        return errors

    def get_progressive_status(self):
        """Returns a snapshot of graph health."""
        if not self.manifest: return "No manifest"
        linked = len([f for f, d in self.graph.items() if d])
        total = len(self.manifest)
        return f"{linked}/{total} nodes linked"

    def find_unresolved_imports(self, code):
        """Returns list of local file paths that are imported but not in manifest."""
        missing = []
        std_libs = {
            'path', 'fs', 'os', 'crypto', 'events', 'http', 'https', 'util', 'url', 'querystring', 'stream',
            'sys', 'json', 're', 'subprocess', 'time', 'ast', 'collections', 'datetime', 'itertools',
            'next', 'react', 'react-dom', 'next-auth', 'sqlite3', 'zod', 'lucide-react', 'clsx', 'tailwind-merge'
        }
        
        js_imports = re.findall(r"from\s+['\"](.*?)['\"]|import\s+['\"](.*?)['\"]", code)
        for i_from, i_imp in js_imports:
            imp = i_from or i_imp
            if not imp: continue
            
            is_local = imp.startswith(('./', '../', '@/'))
            if not is_local: continue
            
            norm = imp.replace('@/', '').lstrip('./').lstrip('../')
            base_name = os.path.basename(norm).split('.')[0]
            
            if base_name in std_libs: continue
            
            found = False
            for m in self.manifest:
                if m == norm or os.path.basename(m).split('.')[0] == base_name:
                    found = True
                    break
            
            if not found:
                 if any(norm.endswith(ext) for ext in ['.ts', '.tsx', '.js', '.jsx', '.css', '.scss', '.json', '.svg']):
                      missing.append(norm)
                 else:
                      ext = ".tsx" if "components" in norm or "app/" in norm or "page" in norm else ".ts"
                      missing.append(norm + ext)
                     
        return list(set(missing))
