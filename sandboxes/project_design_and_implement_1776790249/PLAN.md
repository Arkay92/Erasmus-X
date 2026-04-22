# Project: Planet Explorer

## Goal
To create a multi-file Python application capable of managing planetary data, persisting it via JSON, and generating procedural planet names.

## Architecture
The application will follow a modular structure.
1. **Data Module:** Handles all interactions with planetary data structures, ensuring persistence (loading/saving JSON).
2. **Generator Module:** Handles the procedural generation of planet names using random selection, ensuring modularity.
3. **Main Entry Point:** Orchestrates the initialization, data loading, and usage of the generator.

## File Structure
- `main.py` — Entry point, responsible for application setup and driving the system.
- `data_manager.py` — Module for handling JSON persistence operations (saving/loading planet data).
- `name_generator.py` — Module for generating procedural planet names.
- `data.json` — Persistent storage file (data structure).