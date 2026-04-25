import re
import os

def check_fidelity(contract, file_map):
    """
    Elite V18: Compares current project state against Capability Contract.
    Returns (score, list of targets: {file, reason})
    """
    targets = []
    
    # 1. Critical File Check
    critical_files = contract.get('critical_files', [])
    for cf in critical_files:
        cf_norm = cf.replace('\\', '/').lstrip('./')
        # Check for path variants (api/auth vs api/auth/[...nextauth])
        found = False
        if cf_norm in file_map: found = True
        else:
            cf_base = os.path.basename(cf_norm)
            for existing in file_map.keys():
                if cf_base == os.path.basename(existing) and (os.path.dirname(cf_norm) in existing):
                    found = True; break
        
        if not found:
            targets.append({
                "file": cf_norm,
                "reason": f"Contract Fidelity: Critical file '{cf_norm}' is MISSING on disk."
            })

    # 2. Tech Stack Drift & Hollow Skeletons (Hard Enforcement V19)
    stack = contract.get('stack', '').lower()
    for name, content in file_map.items():
        # Hollow skeleton / placeholder detection
        hollow_markers = ['[Placeholder Component]', 'Ready for Implementation', 'export const placeholder = true']
        if any(marker in content for marker in hollow_markers):
             targets.append({"file": name, "reason": f"Fidelity Failure: File contains hollow scaffolding or placeholder. Must be deeply implemented."})
        elif len(content.split()) < 10 and not name.endswith('.json') and not name.endswith('.css'):
             targets.append({"file": name, "reason": f"Fidelity Failure: File '{name}' is suspiciously short. Provide actual feature logic."})
             
        # Prisma vs SQLite drift
        if 'prisma' in stack and 'sqlite3' in content and '@prisma/client' not in content:
             targets.append({"file": name, "reason": "CONTRACT VIOLATION: Project uses SQLite3 directly but contract MANDATES Prisma."})
        
        # Next.js App Router vs Pages Router drift
        if 'app-router' in stack and 'react-router-dom' in content:
             targets.append({"file": name, "reason": "CONTRACT VIOLATION: Found react-router-dom in App Router project."})

    # 3. Ghost File Detection (Referenced but missing)
    for name, content in file_map.items():
        all_local_imports = re.findall(r"from\s+['\"](@/.*?)['\"]|from\s+['\"](\./.*?)['\"]", content)
        for i_at, i_dot in all_local_imports:
             imp = i_at or i_dot
             norm = imp.replace('@/', '').lstrip('./').lstrip('../')
             # Match against existing files (basename check)
             base = os.path.basename(norm).split('.')[0]
             exists = any(base == os.path.basename(f).split('.')[0] for f in file_map.keys())
             if not exists and not any(base in lib for lib in ['react', 'next', 'lucide']):
                  induced_path = norm + (".ts" if "lib" in norm or "api" in norm else ".tsx")
                  targets.append({"file": induced_path, "reason": f"Ghost File Induction: Referenced in {name} but missing from source."})

    score = 100 if not targets else 70
    return score, targets
