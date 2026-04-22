# Project: Planet Explorer

## Goal
Develop a multi-file Python application capable of managing planetary data, persisting data via JSON, and generating procedural planet names.

## Architecture
The architecture will follow a modular structure.
1. **Data Module:** Handles all interactions with planetary data, utilizing JSON serialization/deserialization for persistence.
2. **Generator Module:** Contains logic for generating unique or procedural planet names based on input parameters.
3. **Main Entry Point:** Orchestrates the usage of the data and generator modules, handling I/O and program flow.

## File Structure
- main.py — Entry point, responsible for initialization, data loading, and generator usage.
- data_manager.py — Module for handling JSON persistence operations (saving and loading planetary data).
- planet_generator.py — Module containing functions for procedural planet name generation.
- config.json — Configuration file for initial setup or settings.

## Implementation Details
- Stack: Python 3.x
- Patterns: Object-Oriented Design (OOP) for data management, separation of concerns (data handling vs. generation logic).