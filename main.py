import argparse
import os
import subprocess
import sys
from pathlib import Path

from core import config
from core.agent import NeurosymbolicAgent
from core.knowledge_graph import KnowledgeGraph
from core.model_clients import create_model_client
from core.vector_store import HypervectorDB
from utils.visualize_graph import generate_visual_graph
from utils.web_search import WebSearcher


PROJECT_ROOT = Path(__file__).resolve().parent


def build_agent() -> tuple[NeurosymbolicAgent, HypervectorDB]:
    print("Connecting to the Neurosymbolic Agent Pipeline...")
    brain = HypervectorDB(filename=config.BRAIN_STORAGE_PATH, dim=config.HV_DIMENSIONS)
    kg = KnowledgeGraph(storage=brain)
    searcher = WebSearcher()
    client = create_model_client("main")
    agent_client = create_model_client("agent")
    agent = NeurosymbolicAgent(client=client, brain=brain, kg=kg, searcher=searcher, agent_client=agent_client)
    print("\nConnected successfully. Agent Brain is online.")
    return agent, brain


def run_chat() -> None:
    agent, brain = build_agent()
    print("Neurosymbolic System Active. Ready for chat.")
    print("-" * 50)

    turn_counter = 0
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit", "menu"]:
                print("[*] Persisting Brain before exit...")
                brain.save()
                break
            if not user_input.strip():
                continue

            result = agent.chat(user_input)
            raw_response, clean_ans = result
            print("Erasmus X: " + (raw_response if clean_ans else str(raw_response)))

            turn_counter += 1
            if turn_counter % 3 == 0:
                print("[*] Performing background persistence...")
                generate_visual_graph(graph_data=brain.graph_data)
                brain.save()
        except KeyboardInterrupt:
            print("\nExiting chat...")
            brain.save()
            break
        except EOFError:
            print("\n[*] Input stream closed. Persisting Brain before exit...")
            brain.save()
            break
        except Exception as exc:
            print(f"\nError: {exc}")


def run_seed(limit: int | None = None) -> None:
    from tools.seed import PROJECT_ROOT as SEED_ROOT
    from tools.seed import SeedingEngine

    curriculum_path = str(SEED_ROOT / "shards" / "questions" / "world_curriculum.md")
    if limit is None:
        raw_limit = input("Seed limit (blank for all): ").strip()
        limit = int(raw_limit) if raw_limit else None
    engine = SeedingEngine(curriculum_path)
    if not engine.questions:
        print("No questions found in curriculum. Check shards/questions/world_curriculum.md.")
        return
    engine.run(limit=limit)


def run_api(host: str, port: int) -> None:
    from api_server import run

    run(host, port)


def run_tests() -> None:
    subprocess.run([sys.executable, "test/run_all_tests.py"], cwd=PROJECT_ROOT, check=False)


def run_benchmarks() -> None:
    subprocess.run([sys.executable, "test/benchmark/automated_benchmarks.py"], cwd=PROJECT_ROOT, check=False)


def print_config_summary() -> None:
    print("\nCurrent Model Configuration")
    print(f"  Main provider : {config.MODEL_PROVIDER}")
    print(f"  Main model    : {config.MODEL_NAME}")
    print(f"  Main API URL  : {config.API_BASE_URL}")
    print(f"  Agent provider: {config.AGENT_MODEL_PROVIDER}")
    print(f"  Agent model   : {config.AGENT_MODEL_NAME}")
    print(f"  Agent API URL : {config.AGENT_API_BASE_URL}")
    print(f"  Local LLM     : {'enabled' if config.ENABLE_LOCAL_LLM else 'disabled'}")
    print(f"  Local server  : {'enabled' if config.USE_LOCAL_LLM_SERVER else 'disabled'}")
    if config.USE_LOCAL_LLM_SERVER:
        server_url = config.LOCAL_LLM_SERVER_API_BASE_URL or (
            config.OLLAMA_API_BASE_URL if config.LOCAL_LLM_SERVER_TYPE == "ollama" else config.LMSTUDIO_API_BASE_URL
        )
        print(f"  Server type   : {config.LOCAL_LLM_SERVER_TYPE}")
        print(f"  Server URL    : {server_url}")
    else:
        print(f"  Python loader : {config.LOCAL_LLM_TYPE}")
    print(f"  Runtime root  : {config.RUNTIME_ROOT}\n")


def prompt_menu_choice() -> str:
    print("\nErasmus X")
    print("1. Chat with agent")
    print("2. Run seed ingestion")
    print("3. Run HTTP API server")
    print("4. Run test suite")
    print("5. Run benchmark suite")
    print("6. Show config")
    print("0. Exit")
    return input("Select an option: ").strip().lower()


def run_menu(host: str = "127.0.0.1", port: int = 8008) -> None:
    while True:
        choice = prompt_menu_choice()
        if choice in {"1", "chat", "c"}:
            run_chat()
        elif choice in {"2", "seed", "s"}:
            run_seed()
        elif choice in {"3", "api", "server"}:
            run_api(host, port)
        elif choice in {"4", "test", "tests"}:
            run_tests()
        elif choice in {"5", "benchmark", "bench"}:
            run_benchmarks()
        elif choice in {"6", "config", "cfg"}:
            print_config_summary()
        elif choice in {"0", "exit", "quit", "q"}:
            print("Goodbye.")
            return
        else:
            print("Unknown option. Choose 0-6.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Erasmus X.")
    parser.add_argument("--api", action="store_true", help="Run lightweight HTTP API instead of the startup menu.")
    parser.add_argument("--chat", action="store_true", help="Open chat directly instead of the startup menu.")
    parser.add_argument("--seed", action="store_true", help="Run seed ingestion directly instead of the startup menu.")
    parser.add_argument("--seed-limit", type=int, default=None, help="Limit the number of seed questions processed.")
    parser.add_argument("--tests", action="store_true", help="Run the test suite directly instead of the startup menu.")
    parser.add_argument("--benchmarks", action="store_true", help="Run benchmarks directly instead of the startup menu.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8008)
    args = parser.parse_args()

    if args.api:
        run_api(args.host, args.port)
    elif args.chat:
        run_chat()
    elif args.seed:
        run_seed(limit=args.seed_limit)
    elif args.tests:
        run_tests()
    elif args.benchmarks:
        run_benchmarks()
    else:
        run_menu(args.host, args.port)


if __name__ == "__main__":
    main()
