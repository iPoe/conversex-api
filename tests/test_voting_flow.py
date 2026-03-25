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
    # Intentar insertar (si ya existe por ID no importa, pero aquí dejamos que genere uno nuevo)
    res = supabase.table("cases").insert(test_case).execute()
    if res.data:
        print(f"✅ Caso de prueba creado: {res.data[0]['id']}")
        return res.data[0]["id"]
    return None

async def test_voting_flow():
    async with httpx.AsyncClient() as client:
        print("--- Simulación de Argumentación y Votación (Conversex) ---")

        # 0. Seed
        await seed_test_case()

        # 1. Setup Sala
        print("\n1. Configurando sala...")
        host_res = await client.post(f"{BASE_URL}/rooms", json={"hostName": "Carlos", "hostAvatar": "av-1"})
        room = host_res.json()
        room_code = room["roomCode"]

        await client.post(f"{BASE_URL}/rooms/{room_code}/join", json={"playerName": "María", "playerAvatar": "av-2"})
        await client.post(f"{BASE_URL}/rooms/{room_code}/start", json={"totalTurns": 5, "pointsToWin": 20})
        print(f"✅ Sala {room_code} lista y partida iniciada.")

        # 2. Lanzar Dado
        print("\n2. Carlos lanza el dado...")
        await client.post(f"{BASE_URL}/rooms/{room_code}/roll", json={"playerName": "Carlos"})
        
        # 3. Obtener Caso
        print("\n3. Obteniendo caso para la zona actual...")
        case_res = await client.get(f"{BASE_URL}/rooms/{room_code}/case")
        if case_res.status_code == 200:
            case_data = case_res.json()
            print(f"📋 Caso Recibido: {case_data['description']}")
            for opt in case_data['rubric']:
                print(f"   [{opt['id']}] {opt['text']} ({opt['points']} pts)")
        else:
            print(f"❌ Error al obtener caso: {case_res.text}")
            return

        # 4. Votación
        print("\n4. María vota por la opción A (Excelente)...")
        vote_res = await client.post(f"{BASE_URL}/rooms/{room_code}/vote", json={
            "voterName": "María",
            "optionId": "A"
        })
        if vote_res.status_code == 200:
            print("✅ Voto registrado con éxito.")

        # 5. Calcular Resultados
        print("\n5. Calculando resultados finales del turno...")
        results_res = await client.get(f"{BASE_URL}/rooms/{room_code}/vote-results")
        if results_res.status_code == 200:
            results = results_res.json()
            print(f"🏆 Ganador: Opción {results['winnerOption']}")
            print(f"💰 Puntos Ganados: {results['pointsEarned']}")
            print(f"📊 Desglose de votos: {results['voteCount']}")
        else:
            print(f"❌ Error al calcular resultados: {results_res.text}")

        print("\n--- Test de Votación Finalizado con Éxito ---")

if __name__ == "__main__":
    try:
        asyncio.run(test_voting_flow())
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        print("¿Está el servidor corriendo?")
