---
name: Data_Analysis
type: skill
trigger: "analyze data|process csv|statistics|summarize trends"
---

# Data Analysis Skill Execution Protocol
You possess the capability to analyze structured data (e.g., JSON, CSV, SQLite). 

When executing a data analysis task, follow this strict workflow:
1. **Understand Structure:** First, verify the schema/keys of the provided dataset before doing any math.
2. **Cleanse:** Identify any null, malformed, or missing entries. Do not silently ignore them; document their omission in the final result.
3. **Compute:** Execute requested mathematical operations (averages, counts, standard deviations, trends).
4. **Present:** Output all results natively in a Markdown Table format to ensure high readability for the user.
