# Project: Planet Explorer

## Goal
To create a multi-file application that manages planetary data using JSON persistence and generates procedural planet names.

## Architecture
The application will follow a modular structure.
- **Data Layer:** Responsible for handling data serialization and deserialization (JSON) for storing planetary data.
- **Generator Layer:** Responsible for generating unique, procedural planet names based on input parameters.
- **Main Module:** Handles the application flow, interaction, and orchestrates the data and generator components.

## File Structure
- `main.py` — Entry point for application execution and interaction.
- `data_manager.py` — Module for managing JSON persistence operations.
- `planet_generator.py` — Module for procedural generation logic.
- `data.json` — Data storage file (handled by `data_manager`).