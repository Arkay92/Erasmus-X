

<p align="center"># Erasmus X — Autonomous Neurosymbolic Agent</p>

<p align="center">
  <img width="300" height="300" alt="0412b5b5-2f23-4ce3-880a-c71b919d53bc" src="https://github.com/user-attachments/assets/cda36b40-4794-4ecb-b59e-5676a301c896" />
</p>

## Overview

Erasmus X is a modular autonomous agent framework designed to combine:
- **LLM reasoning**
- **Deterministic code generation pipelines**
- **Project scaffolding packs**
- **Memory + retrieval**
- **Benchmarking + self-evaluation**
- **Tool use + web/search workflows**
- **Multi-language software generation**

It is built to operate as a practical software-building and research agent rather than only a chat model.

---

## Core Capabilities

## 1. Conversational Intelligence

Supports:
- Simple factual Q&A
- Multi-step reasoning
- Context-aware dialogue
- Session continuity
- Fallback answers when models fail
- Dynamic routing between fast and deep reasoning modes

Examples:
- “What is HTTP?”
- “Explain Gödel’s incompleteness theorem simply.”
- “Compare capitalism vs socialism.”

---

## 2. Deep Research Mode

For complex prompts, Erasmus X can escalate into deeper reasoning workflows:

- Multi-query search expansion
- Iterative crawling of sources
- Summarisation across sources
- Contradiction detection
- Long-form synthesis
- Source ingestion into memory/vector store

Examples:
- “Research the future of fusion energy.”
- “Compare all major open-source vector databases.”
- “Investigate UK housing market trends.”

---

## 3. Autonomous Software Builder

Can generate complete software projects across stacks.

### Supported Patterns

- Python CLI tools
- Flask / FastAPI apps
- Node / Express APIs
- Next.js full-stack apps
- React frontends
- SQLite / Prisma apps
- TypeScript projects
- Utility scripts
- Multi-file structured repos

### Includes

- File generation
- Directory planning
- Dependency manifests
- Tests
- Verification scripts
- Syntax validation
- Repair loops
- Project packaging

---

## 4. Scaffold Pack System

Deterministic domain packs dramatically improve reliability.

### Included Packs

- todo
- prisma_todo
- auth
- dashboard
- db
- api-routes
- validation
- booking-system
- express-api

### What Packs Provide

- Known-good file structures
- Real implementations
- Tests
- Verify commands
- Faster builds
- Less hallucination

---

## 5. Multi-Language Coding Support

Supports generating tasks/projects in:

- Python
- JavaScript
- TypeScript
- C
- C++
- Java
- Go
- Rust
- Bash
- SQL
- HTML/CSS

Examples:
- “Write a C bubble sort.”
- “Create a Rust REST API.”
- “Generate a Go worker pool.”

---

## 6. Testing + Verification

Every serious coding task can include:

- Unit tests
- CLI execution checks
- Syntax validation
- Build verification
- Manifest checks
- Contract fidelity checks

Examples:
- `pytest`
- `npm test`
- `cargo test`
- `go test`
- `tsc --noEmit`

---

## 7. Memory + Learning

Persistent memory systems may include:

- Semantic vector memory
- Extracted facts
- Benchmark history
- Failure learning
- Retrieved web knowledge
- Context grounding when windows fill

This allows improving over time.

---

## 8. Benchmarks

Built-in benchmark suite supports:

### Query Types
- Simple Q&A
- Deep reasoning
- Search tasks
- Coding tasks
- Multi-file projects
- Long-context memory tests

### Language Benchmarks
- Python
- JS/TS
- C
- SQL
- Shell

### Metrics

- Latency
- Success rate
- Syntax pass rate
- Code execution pass rate
- Project completion
- Memory continuity
- Search quality

---

## 9. Routing Intelligence

The system can route prompts to:

### FAST Lane
Low-latency answers.

### DEEP Lane
Longer reasoning / difficult tasks.

### PROJECT Lane
Multi-file software builds.

### RESEARCH Lane
Multi-source crawling + synthesis.

---

## 10. Local + Hybrid Models

Supports replacing older local models (e.g. GPT-2) with stronger local options such as:

- Qwen
- Phi
- Mistral
- Gemma
- Llama-family models

Can run hybrid local + remote pipelines.

### API Model Providers

The runtime supports `local`, `openai`, `anthropic`, `deepseek`, and `kimi`.

Main builder model and internal agent model are configured separately so you can mix providers:

```bash
# Local/OpenAI-compatible main model
LOCAL_MODEL_PROVIDER=local
LOCAL_MODEL_TYPE=local-model
API_BASE_URL=http://localhost:12345/v1
API_KEY=local

# Optional local/internal agent model
LOCAL_AGENT_MODEL_PROVIDER=local
LOCAL_AGENT_MODEL_TYPE=tinyllama
AGENT_API_BASE_URL=http://localhost:12345/v1
AGENT_API_KEY=local

# Local helper LLM execution mode
# false = load Python/Transformers model directly
# true = call a running LM Studio or Ollama server
USE_LOCAL_LLM_SERVER=false
LOCAL_LLM_SERVER_TYPE=lmstudio
LMSTUDIO_API_BASE_URL=http://localhost:1234/v1
OLLAMA_API_BASE_URL=http://localhost:11434
LOCAL_LLM_SERVER_API_BASE_URL=
LOCAL_LLM_SERVER_API_KEY=local

# Remote main model overrides LOCAL_MODEL_TYPE when set
REMOTE_MODEL_PROVIDER=openai
REMOTE_MODEL_TYPE=gpt-4.1-mini
OPENAI_API_KEY=...

# Remote agent model overrides LOCAL_AGENT_MODEL_TYPE when set
REMOTE_AGENT_MODEL_PROVIDER=anthropic
REMOTE_AGENT_MODEL_TYPE=claude-3-5-haiku-latest
ANTHROPIC_API_KEY=...
```

DeepSeek uses `REMOTE_MODEL_PROVIDER=deepseek` and `DEEPSEEK_API_KEY`.
Kimi/Moonshot uses `REMOTE_MODEL_PROVIDER=kimi` and `KIMI_API_KEY`.
Base URLs can be overridden with `MODEL_API_BASE_URL`, `AGENT_MODEL_API_BASE_URL`, or provider-specific variables such as `DEEPSEEK_API_BASE_URL`.

---

## Persona Shards / Cognitive Shards

Erasmus Cell supports a **Shard-Based Reasoning Architecture**.

Shards are specialised internal reasoning modules that can be loaded, combined, or routed dynamically depending on the task. Instead of relying on one monolithic thinking style, the agent can distribute cognition across multiple focused personas.

### What Shards Are

A shard is a lightweight expert mode optimized for a specific domain or behavior.

Examples:

- **Code Architect Shard**  
  Designs software structure, modular systems, APIs, file trees, refactors.

- **Debugger Shard**  
  Finds bugs, traces errors, repairs failing builds, improves test pass rates.

- **Research Analyst Shard**  
  Performs deep research, compares sources, extracts facts, synthesizes findings.

- **Critic Shard**  
  Reviews generated outputs for quality, completeness, stack fidelity, missing features.

- **Product Manager Shard**  
  Converts vague prompts into structured requirements, milestones, deliverables.

- **Security Shard**  
  Reviews auth, secrets, validation, vulnerabilities, safe defaults.

- **Performance Shard**  
  Optimizes speed, memory use, query efficiency, build latency.

---

### How Shards Work

When a task arrives, the router can activate one or more shards.

Examples:

#### Prompt:
> Build a booking platform with login and admin dashboard

Activated shards:

- Product Manager  
- Code Architect  
- Auth/Security  
- Critic

#### Prompt:
> Research the future of fusion energy

Activated shards:

- Research Analyst  
- Critic  
- Memory Synthesizer

#### Prompt:
> My TypeScript app crashes on deploy

Activated shards:

- Debugger  
- Performance  
- Critic

---

### Multi-Shard Collaboration

For harder tasks, shards can work in sequence or parallel.

Example software workflow:

1. Product Manager defines requirements  
2. Architect designs structure  
3. Builder generates code  
4. Debugger repairs issues  
5. Critic scores output  
6. Security audits release

This creates a more human-like team workflow.

---

### Benefits of Shards

- Better reasoning quality
- Domain specialization
- Less hallucination
- More reliable project generation
- Faster routing to best thinking mode
- Easier future expansion
- More human team-like cognition

---

### Long-Term Vision

Shards turn Erasmus X from a single assistant into a **modular digital organization** capable of solving complex real-world tasks through coordinated specialist intelligence.

---

## Suggested Strong Upgrades

For best performance:

- `Qwen2.5-7B-Instruct`
- `Phi-4-mini`
- `Mistral 7B Instruct`
- `Gemma 2 9B`
- Quantized GGUF variants with llama.cpp

---

## Example Prompts

### Research
- Research all major browser engines and compare futures.

### Coding
- Build a FastAPI CRM with tests.

### Full Project
- Build a Prisma booking system with login/admin dashboard.

### Quick Question
- What is DNS?

### Systems Design
- Design a scalable ride-sharing backend.

---

## Running

```bash
python main.py
```

Startup menu options:

- Chat with agent
- Run seed ingestion
- Run HTTP API server
- Run test suite
- Run benchmark suite
- Show config

Direct commands:

```bash
python main.py --chat
python main.py --seed --seed-limit 10
python main.py --api --host 127.0.0.1 --port 8008
python main.py --tests
python main.py --benchmarks
```

Run benchmarks:

```bash
python test/automated_benchmarks.py
```

---

## Philosophy

Erasmus X is not just a chatbot.

It is an evolving autonomous builder, researcher, debugger and reasoning system.

---

## Status

Current state:

**Advanced prototype approaching real autonomous software engineer territory.**
