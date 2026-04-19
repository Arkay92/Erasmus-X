@echo off
echo Starting Gemma Local Server...
echo This will stay open in the background to handle the AI chat.
echo -------------------------------------------------------------
"C:\Users\pc006\.gemini\antigravity\scratch\llama-bin-vulkan\llama-server.exe" -m "E:/LMStudio/Models/unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-UD-IQ2_M.gguf" -c 2048 -ngl 999 --port 12345 -fa on -ctk q8_0 -ctv q8_0
pause
