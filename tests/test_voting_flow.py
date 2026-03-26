import asyncio
import httpx
import json
from core.database import supabase

BASE_URL = "http://127.0.0.1:8000"

async def seed_test_case():
    """Inserta un caso de prueba en la DB para que el flujo no falle"""
    print("\n--- Preparando Datos de Prueba ---")
    test_case = {
        "zone": 1,
        "description": "¿Cómo pedirías consentimiento antes de dar un beso en una primera cita?",
        "rubric": [
            {"id": "A", "text": "Preguntar directamente: '¿Puedo besarte?'", "points": 5},
            {"id": "B", "text": "Acercarse lentamente y esperar lenguaje corporal positivo", "points": 3},
            {"id": "C", "text": "Simplemente lanzarse sin preguntar", "points": 0}
        ]
    }
    # Intentar insertar (si ya existe por descripción no importa, pero aquí dejamos que genere uno nuevo)
    res = supabase.table("cases").select("*").eq("description", test_case["description"]).execute()
    if not res.data:
        res = supabase.table("cases").insert(test_case).execute()
        print(f"✅ Caso de prueba creado: {res.data[0]['id']}")
        return res.data[0]["id"]
    else:
        print(f"✅ Caso de prueba ya existe: {res.data[0]['id']}")
        return res.data[0]["id"]

async def test_voting_flow():
    async with httpx.AsyncClient() as client:
        print("--- Simulación de Argumentación y Votación (Conversex) ---")

        # 0. Seed
        test_case_id = await seed_test_case()

        # 1. Setup Sala
        print("\n1. Configurando sala...")
        host_res = await client.post(f"{BASE_URL}/rooms", json={"hostName": "Carlos", "hostAvatar": "av-1"})
        room = host_res.json()
        room_code = room["roomCode"]
        room_id = room["gameId"]

        await client.post(f"{BASE_URL}/rooms/{room_code}/join", json={"playerName": "María", "playerAvatar": "av-2"})
        await client.post(f"{BASE_URL}/rooms/{room_code}/start", json={"totalTurns": 5, "pointsToWin": 20})
        print(f"✅ Sala {room_code} lista y partida iniciada.")

        # 2. Simular llegada a Zona
        print("\n2. Simulando llegada de Carlos al Hospital...")
        # Teletransportar a Carlos
        supabase.table("players").update({
            "current_position": {"nodeId": "hospital", "edgeId": None, "edgeProgress": 0}
        }).eq("name", "Carlos").eq("room_id", room_id).execute()
        
        # Activar fase de argumentación manualmente para este test
        supabase.table("rooms").update({
            "phase": "arguing",
            "current_zone_id": "hospital",
            "current_case_id": test_case_id,
            "config": {
                "totalTurns": 5,
                "pointsToWin": 20,
                "isTimerEnabled": False,
                "turnHistory": [],
                "current_turn_index": 0,
                "completed_turns": 0,
                "current_case_id": test_case_id
            }
        }).eq("id", room_id).execute()
        
        # 3. Obtener Estado (para ver el caso)
        print("\n3. Obteniendo estado de la sala...")
        room_state_res = await client.get(f"{BASE_URL}/rooms/{room_code}")
        state = room_state_res.json()
        print(f"📋 Fase Actual: {state['phase']}")
        print(f"📋 Caso ID: {state['currentCaseId']}")

        # 4. Carlos Argumenta
        print("\n4. Carlos envía su argumento...")
        arg_res = await client.post(f"{BASE_URL}/rooms/{room_code}/argue", json={
            "playerName": "Carlos",
            "argument": "Yo preguntaría antes de hacer cualquier cosa, el respeto es lo primero."
        })
        print(f"✅ Argumento enviado: {arg_res.json()['status']}")

        # 5. María Vota
        print("\n5. María vota por la opción A (Excelente)...")
        vote_res = await client.post(f"{BASE_URL}/rooms/{room_code}/vote", json={
            "voterName": "María",
            "optionId": "A"
        })
        if vote_res.status_code == 200:
            print(f"✅ Voto registrado. Respuesta: {vote_res.json()['status']}")

        # 6. Consultar Resultados
        print("\n6. Consultando resultados del turno...")
        results_res = await client.get(f"{BASE_URL}/rooms/{room_code}/vote-results")
        if results_res.status_code == 200:
            results = results_res.json()
            print(f"🏆 Opción Ganadora: {results['winnerOption']}")
            print(f"💰 Puntos Ganados: {results['pointsEarned']}")
            print(f"🏁 Partida Finalizada: {results['isFinished']}")
        else:
            print(f"❌ Error al consultar resultados: {results_res.text}")

        print("\n--- Test de Votación Finalizado con Éxito ---")

if __name__ == "__main__":
    try:
        asyncio.run(test_voting_flow())
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        print("¿Está el servidor corriendo?")
