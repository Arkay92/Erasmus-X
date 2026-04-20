---
name: API_Integration
type: skill
trigger: "connect to api|fetch endpoint|rest interaction"
---

# API Integration Skill Execution Protocol
You are authorized to design network interactions against external REST APIs.

## Protocol Steps:
1. **Authentication Verification:** Check if the integration requires a Bearer token, API Key, or Basic authentication. Define placeholders for these (e.g., `<YOUR_API_KEY>`).
2. **Method Selection:** Strictly use explicit HTTP methods (GET, POST, PUT, DELETE).
3. **Error Handling Check:** Ensure all generation attempts gracefully catch `Timeout` and `ConnectionError` scenarios instead of breaking the main thread.
4. **Validation:** Use `requests.raise_for_status()` to flag non-200 connection blocks.
