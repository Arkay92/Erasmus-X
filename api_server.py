import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import config
from core.agent import NeurosymbolicAgent
from core.knowledge_graph import KnowledgeGraph
from core.model_clients import create_model_client
from core.vector_store import HypervectorDB
from utils.web_search import WebSearcher


def build_agent() -> NeurosymbolicAgent:
    brain = HypervectorDB(filename=config.BRAIN_STORAGE_PATH, dim=config.HV_DIMENSIONS)
    kg = KnowledgeGraph(storage=brain)
    client = create_model_client("main")
    agent_client = create_model_client("agent")
    return NeurosymbolicAgent(client=client, brain=brain, kg=kg, searcher=WebSearcher(), agent_client=agent_client)


class AgentAPIHandler(BaseHTTPRequestHandler):
    agent = None

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"status": "error", "errors": ["Not found"]})

    def do_POST(self):
        if self.path.rstrip("/") != "/chat":
            self._send_json(404, {"status": "error", "errors": ["Not found"]})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            message = payload.get("message") or payload.get("prompt") or ""
            if not message.strip():
                self._send_json(400, {"status": "error", "errors": ["Missing message"], "answer": "", "files": [], "metadata": {}})
                return
            result = self.agent.chat(message, mode_override=payload.get("mode"))
            self._send_json(200, result.to_dict())
        except Exception as exc:
            self._send_json(500, {"status": "error", "errors": [str(exc)], "answer": "", "files": [], "metadata": {}})


def run(host="127.0.0.1", port=8008):
    AgentAPIHandler.agent = build_agent()
    server = ThreadingHTTPServer((host, port), AgentAPIHandler)
    print(f"Agent API listening on http://{host}:{port}")
    print("POST /chat with JSON: {\"message\": \"...\"}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Erasmus Cell lightweight HTTP API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()
    run(args.host, args.port)
