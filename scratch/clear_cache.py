import torch
import os

path = "memories/agent_brain.pt"
if os.path.exists(path):
    data = torch.load(path, weights_only=False)
    data['prompt_cache'] = {}
    data['cache_tensor'] = None
    torch.save(data, path)
    print("Prompt cache cleared.")
else:
    print("Brain file not found.")
