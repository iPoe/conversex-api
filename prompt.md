Master Prompt: Backend API & Real-time Lobby (Conversex)
Role: Lead Backend Engineer & Architect.
Context: Build a robust API for a multiplayer serious game called "Conversex" using Python/FastAPI (or Node.js), Git for version control, and Supabase as the core BaaS (Database + Real-time).

Objective: Implement the initial lifecycle of a game session: Create Room -> Join Lobby -> Setup -> Wait for Player.

1. Database Schema (Supabase):

Table rooms: id (UUID), room_code (String, unique, 6 chars), status (waiting/playing/finished), created_at, config (JSON for turns/intensity).

Table players: id (UUID), room_id (FK), name (String), avatar_id (String), is_host (Boolean), online_status (Boolean).

2. Core API Endpoints:

POST /create-room: Generates a unique 6-digit code, creates a record in rooms, and adds the creator as is_host = true.

POST /join-room: Validates if room_code exists and if the room has < 2 players. Adds the new player.

PATCH /update-setup: Allows the host to modify game parameters (turns/intensity) before starting.

3. Real-time Logic:

Use Supabase Realtime (Postgres Changes) to broadcast events.

When a new row is inserted in players, broadcast to the specific room_id so the Frontend (Lovable) updates the player list automatically.

4. Git & Project Structure:

Initialize a Git repository with a .gitignore for environment variables.

Structure: /app (routes, models, schemas), /core (supabase config), /tests (unit tests for room creation).

Instructions for Gemini-CLI:

Generate the requirements.txt (including supabase, fastapi, uvicorn).

Provide a README.md explaining how to set up the Supabase environment variables (SUPABASE_URL, SUPABASE_KEY).

Create a Python script test_multiplayer_flow.py that simulates two clients joining the same room and verifying the list update.