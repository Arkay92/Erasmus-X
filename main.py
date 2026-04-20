import sys
from core import config
from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph
from core.agent import NeurosymbolicAgent
from utils.web_search import WebSearcher
from utils.visualize_graph import generate_visual_graph

def main():
    print("Connecting to the Neurosymbolic Agent Pipeline...")
    
    # Initialize Core Components
    # Using Unified Brain storage (.pt) as the source of truth
    brain = HypervectorDB(filename=config.BRAIN_STORAGE_PATH, dim=config.HV_DIMENSIONS)
    kg = KnowledgeGraph(storage=brain)
    searcher = WebSearcher()
    
    # Initialize the Agent Engine (DIP - Dependency Inversion)
    agent = NeurosymbolicAgent(brain=brain, kg=kg, searcher=searcher)

    print("\nConnected successfully! Agent Brain is online.")
    print("Neurosymbolic System Active! Ready for chat.")
    print("-" * 50)

    turn_counter = 0

    while True:
        try:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ['exit', 'quit']:
                print("[*] Persisting Brain before exit...")
                brain.save()
                break
                
            if not user_input.strip():
                continue
            
            # Use the Agent to handle the reasoning loop (SRP - Single Responsibility)
            raw_response, clean_ans = agent.chat(user_input)
            
            if clean_ans:
                print("Gemma: " + raw_response)
                
                # Throttled Persistence & Visualization (Optimization)
                turn_counter += 1
                if turn_counter % 3 == 0:
                    print("[*] Performing background persistence...")
                    generate_visual_graph(graph_data=brain.graph_data)
                    brain.save()
            else:
                # Handle errors (raw_response contains the error message)
                print(f"Gemma: {raw_response}")

        except KeyboardInterrupt:
            print("\nExiting...")
            brain.save()
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
