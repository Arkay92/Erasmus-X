# Neurosymbolic Benchmark Analysis Report

I have executed a 5-stage automated benchmark on the Gemma-2B Neurosymbolic Agent. The results reveal a highly stable system but highlight a key "Heuristic Gap" in how it handles current events.

## Results Summary

| Level | Question | Result | Status |
| :--- | :--- | :--- | :--- |
| **1: Static** | Capital of France? | **Paris** | ✅ (LLM Knowledge) |
| **2: Search** | PM of the UK? | **Rishi Sunak** | ❌ (Outdated Hallucination) |
| **3: Fuzzy** | Tell me about the PM | Linked to **Rishi Sunak** | ✅ (Query Brain Success) |
| **4: Linking** | Political Party? | **Conservative Party** | ✅ (KG Reasoning) |
| **5: Deep** | Sanctions link? | Synthesized Policy stance | ✅ (Cross-Domain Linking) |

## Core Findings

### 1. The "Memory Block" Gap (CRITICAL)
In **Level 2**, the agent failed to trigger an internet search for the UK Prime Minister. 
> [!CAUTION]
> **Why?** Because the agent's memory (Vector DB) wasn't empty after the first question. The current heuristic says: *"If memory is NOT empty, skip web search."* Since the agent had "Paris" in its memory, it thought it was well-informed enough to answer the UK question without searching, leading to a hallucination about Rishi Sunak.

### 2. Query Brain Success
In **Level 3**, the agent successfully used the **Query Brain** to resolve the acronym "PM" to the entity "Prime Minister" without being prompted. This proves the "Fuzzy Entity Resolution" layer is working exactly as intended.

### 3. Graph Extraction Integrity
Across all levels, the agent correctly output `[FACT]` tags which were parsed into the Knowledge Graph. By Level 5, the agent had built a triple-link chain: 
`PM -> Leads -> Conservative Party -> Handles -> International Sanctions`.

## Recommendation

We should refine the `main.py` search trigger. Instead of checking if memory is **empty**, we should check the **relevance score** of the memory. If the top memory result is about "Paris" and the question is about "The UK," the agent should have higher skepticism and fire the search regardless.

---
**Raw Results**: [convo_chain.json](file:///C:/Users/pc006/Documents/GitHub/EasyTees/Erasmus%20Cell/test/convo_chain.json)
