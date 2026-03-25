import asyncio
import httpx
import json
import random
from core.database import supabase

BASE_URL = "http://127.0.0.1:8000"

async def setup_test_data():
    """Ensure we have at least one case in each zone for testing"""
    print("\n--- Pre-populating Cases for Test ---")
    zones = [1, 2, 3, 4, 5]
    for z in zones:
        test_case = {
            "zone": z,
            "description": f"Test Case for Zone {z}",
            "rubric": [
                {"id": "A", "text": "Excellent", "points": 5},
                {"id": "B", "text": "Good", "points": 3},
                {"id": "C", "text": "Bad", "points": 0}
            ]
        }
        # Upsert by zone description to avoid duplicates (just for this test)
        res = supabase.table("cases").select("*").eq("description", test_case["description"]).execute()
        if not res.data:
            supabase.table("cases").insert(test_case).execute()
            print(f"✅ Added case for Zone {z}")

async def test_full_graph_flow():
    async with httpx.AsyncClient() as client:
        print("\n--- 🏁 STARTING GRAPH-BASED FLOW TEST ---")

        # 1. Setup Room
        print("\n1. Creating room...")
        host_res = await client.post(f"{BASE_URL}/rooms", json={"hostName": "Carlos", "hostAvatar": "av-1"})
        room = host_res.json()
        room_code = room["roomCode"]
        print(f"   * Room {room_code} created.")

        print("\n2. Joining Guest...")
        await client.post(f"{BASE_URL}/rooms/{room_code}/join", json={"playerName": "Maria", "playerAvatar": "av-2"})
        
        print("\n3. Starting Game...")
        start_res = await client.post(f"{BASE_URL}/rooms/{room_code}/start", json={"totalTurns": 5})
        game_state = start_res.json()
        print(f"   * Game Status: {game_state['status']}, Phase: {game_state['phase']}")
        
        # Verify initial position
        for p in game_state["players"]:
            print(f"   * {p['name']} starts at {p['boardPosition']['nodeId']}")

        # 4. Movement Simulation (Carlos moves from Park -> Branch-1)
        print("\n4. Carlos Rolls Dice (Target: Branch 1)...")
        # Park -> Branch-1 distance is 5
        roll_val = 5
        
        print(f"   * Requesting Move for Carlos with {roll_val} steps...")
        move_res = await client.post(f"{BASE_URL}/rooms/{room_code}/move", json={
            "playerName": "Carlos",
            "diceValue": roll_val
        })
        move_data = move_res.json()
        print(f"   * Move Status: {move_data['status']}")
        
        if move_data["status"] == "waiting_choice":
            print(f"   * 🔀 Branch Reached! Options: {move_data['options']}")
            # Choice: Let's go to e-b1-b2a (toward Hospital)
            choice = "e-b1-b2a"
            print(f"   * Carlos chooses path: {choice}")
            move_res = await client.post(f"{BASE_URL}/rooms/{room_code}/move", json={
                "playerName": "Carlos",
                "diceValue": 0, # Just making the choice
                "choiceEdgeId": choice
            })
            move_data = move_res.json()
            print(f"   * New Position: {move_data['newPosition']['edgeId']} at step {move_data['newPosition']['edgeProgress']}")

        # 5. Testing Automated Voting results
        print("\n5. Testing Argument and Voting...")
        # Manually set room to arguing to test voting broadcast
        supabase.table("rooms").update({
            "phase": "arguing",
            "current_zone_id": "hospital"
        }).eq("room_code", room_code).execute()
        
        print("   * Requesting Case...")
        case_res = await client.get(f"{BASE_URL}/rooms/{room_code}/case")
        case_data = case_res.json()
        print(f"   * Case Received: {case_data['description']}")

        # NEW: Submit Argument
        print("   * Carlos submits an argument...")
        arg_res = await client.post(f"{BASE_URL}/rooms/{room_code}/argue", json={
            "playerName": "Carlos",
            "argument": "I believe we should always ask for clear consent."
        })
        print(f"   * Argument Status: {arg_res.json()['status']}")

        print("   * Carlos votes A...")
        await client.post(f"{BASE_URL}/rooms/{room_code}/vote", json={"voterName": "Carlos", "optionId": "A"})
        
        print("   * Maria votes A (This should trigger the transition)...")
        vote_res = await client.post(f"{BASE_URL}/rooms/{room_code}/vote", json={"voterName": "Maria", "optionId": "A"})
        vote_data = vote_res.json()
        print(f"   * Vote Response: {vote_data['status']}")
        
        # Check Room State (Should be rolling for Maria now)
        room_check = supabase.table("rooms").select("*").eq("room_code", room_code).execute()
        final_room = room_check.data[0]
        print(f"   * Final Room Phase: {final_room['phase']} (Expected: rolling)")
        print(f"   * Turn History Length: {len(final_room['config'].get('turnHistory', []))}")

        print("\n--- ✅ GRAPH FLOW TEST COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(setup_test_data())
    asyncio.run(test_full_graph_flow())
