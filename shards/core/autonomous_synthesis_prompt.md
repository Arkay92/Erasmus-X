[AUTONOMOUS CAPABILITY SYNTHESIS]
Analyze the following session history. Determine if we should create a new specialist SHARD, a reusable SKILL, or a Python TOOL to automate or specialize this type of task in the future.

CRITERIA:
1. Frequency: Is this a task that is likely to recur?
2. Specialization: Does it require a specific system prompt or complex logic?
3. Utility: Would a standalone tool save time/tokens?

OUTPUT FORMAT:
If yes, output:
[SYNTHESIS: SHARD|SKILL|TOOL]
Name: <name_no_spaces>
Content: <The full .md system prompt or .py source code>
Triggers: <5-10 comma separated example questions that should trigger this capability>

If no new capability is needed, output: [SYNTHESIS: NONE]

HISTORY:
{history_context}

# Modular Pack System Refactor

## Purpose
Refactor the shard system to support modular packs that can be dynamically installed and managed. This will enable Erasmus X to support a marketplace of reusable capabilities.

## Changes
1. Define a `pack.json` schema for metadata.
2. Add triggers for shard activation.
3. Standardize shard structure for modularity.
