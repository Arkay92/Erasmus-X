# Erasmus Cell: Logic Depth V17 (Neurosymbolic Agent)

Erasmus Cell is a state-of-the-art **Neurosymbolic Coding Agent** designed for reliable, autonomous project generation and complex reasoning. Unlike monolithic LLM wrappers, Erasmus Cell uses a modular, tiered architecture to ground reasoning in external evidence and deterministic code standards.

## 🚀 Unique Way of Working: Elite V10

Erasmus Cell operates using a **Tiered Neurosymbolic Pipeline**, combining the creative potential of Large Language Models (LLMs) with the rigorous constraints of symbolic logic.

### 1. Hardened Context & Session Architecture
- **Tiered Context Builder**: Prioritizes current objectives and session state over supplemental history to prevent context overflow.
- **Deterministic Session Manager**: Implements proactive "Spin-Downs" to persist agent memory across long-running builds.

### 2. Methodical Reasoning (Working Notes Mode)
Erasmus Cell executes tasks using a structured `Goal -> Action -> Observation -> Next` loop. Every step is narrated, and every action is verified against actual sandbox results before moving to the next objective.

### 3. Layered Validation & Authoritative Scaffolding
- **Layer 1 (Syntax)**: AST-based validation for Python and brace-balance checks for JS/TSX.
- **Layer 2 (Semantic)**: Framework contract enforcement (e.g., Next.js root layout requirements).
- **Authoritative Fallback**: If the model fails to produce a critical file, the system force-writes a verified "Known Good" skeleton from the **Template Store**.

---

## 🧩 Shard Architecture

Erasmus Cell is modular by design. Its capabilities are defined by **Shards**—specialized prompt modules that are dynamically loaded based on the task intent.

### Agent Shards (`shards/agents/`)
Specialized personas for broad task types:
- **Code Architect**: High-level system design and multi-file project scaffolding.
- **Researcher**: Optimized for web discovery and competitive technical analysis.

### Skill Shards (`shards/skills/`)
Atomic capabilities for specific technologies:
- **API Integration**: Specialist in Next.js Route Handlers and external service orchestration.
- **Data Analysis**: Expertise in SQLite schemas, data migrations, and statistical processing.

---

## 🛠️ Startup & Installation

### Prerequisites
- Python 3.10+
- An OpenAI-compatible LLM server (Local or Cloud)

### Setup
1. **Clone the project** and navigate to the root directory.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure the environment**:
   Edit `core/config.py` to set your `API_BASE_URL` and `API_KEY`.

### Running the Agent
Start the main chat loop:
```bash
python main.py
```

### Running Benchmarks
To verify the agent's performance and project-mode stability:
```bash
python test/automated_benchmarks.py
```

---

## 📁 Project Structure
- `core/`: Advanced subsystems (Router, SessionManager, ValidatorRegistry).
- `shards/`: Modular persona and skill prompts.
- `sandboxes/`: Isolated environments for autonomous code generation.
- `utils/`: Support modules for brain synchronization and web search.
- `memories/`: Persistent storage for the Hypervector DB and Knowledge Graph.
