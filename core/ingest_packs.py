import os
import json
from core.vector_store import HypervectorDB
from core import config

def main():
    brain = HypervectorDB(filename=config.BRAIN_STORAGE_PATH)
    packs_dir = os.path.join(os.path.dirname(__file__), 'packs')
    
    if not os.path.exists(packs_dir):
        print("No packs to ingest.")
        return
        
    count = 0
    for f in os.listdir(packs_dir):
        if f.endswith('.json'):
            path = os.path.join(packs_dir, f)
            try:
                with open(path, 'r', encoding='utf-8') as pf:
                    pack = json.load(pf)
                    feat = pack.get('feature')
                    if feat:
                        json_str = json.dumps(pack)
                        doc = f"[FEATURE_PACK] FEATURE: {feat} CONTENT: {json_str}"
                        brain.add_document(doc)
                        count += 1
                        print(f"Ingested {feat} pack.")
            except Exception as e:
                print(f"Failed to ingest {f}: {e}")
                
    brain.save()
    print(f"Saved brain with {count} feature packs.")

if __name__ == '__main__':
    main()
