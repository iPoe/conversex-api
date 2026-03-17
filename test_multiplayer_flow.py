import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

async def test_flow():
    async with httpx.AsyncClient() as client:
        print("--- Simulación de flujo Conversex (Estructura Refinada) ---")

        # 1. Host crea una sala
        print("\n1. Host creando sala (POST /rooms)...")
        host_request = {
            "hostName": "Carlos (Host)",
            "hostAvatar": "avatar-3"
        }
        response = await client.post(f"{BASE_URL}/rooms", json=host_request)
        
        if response.status_code != 200:
            print(f"Error al crear sala: {response.text}")
            return

        room_data = response.json()
        room_code = room_data["roomCode"]
        game_id = room_data["gameId"]
        print(f"Sala creada exitosamente!")
        print(f"Código: {room_code}")
        print(f"Estado: {room_data['status']}")
        print(f"Jugadores: {len(room_data['players'])}")

        # 2. Invitado se une a la sala
        print(f"\n2. Invitado uniéndose a la sala {room_code} (POST /rooms/{{code}}/join)...")
        guest_request = {
            "playerName": "María (Invitada)",
            "playerAvatar": "avatar-5"
        }
        response = await client.post(f"{BASE_URL}/rooms/{room_code}/join", json=guest_request)
        
        if response.status_code == 200:
            join_data = response.json()
            print(f"Jugador unido con éxito. Lista de jugadores:")
            for p in join_data["players"]:
                role = "(Host)" if p["isHost"] else "(Invitado)"
                print(f" - {p['name']} {role} | Avatar: {p['avatar']}")
        else:
            print(f"Error al unirse: {response.text}")
            return

        # 3. Host inicia la partida
        print("\n3. Host iniciando la partida (POST /rooms/{{code}}/start)...")
        start_request = {
            "totalTurns": 12,
            "pointsToWin": 50,
            "isTimerEnabled": True
        }
        response = await client.post(f"{BASE_URL}/rooms/{room_code}/start", json=start_request)
        
        if response.status_code == 200:
            game_state = response.json()
            print("¡Partida iniciada! Estado del juego (LiveGameState):")
            print(f" - ID del juego: {game_state['gameId']}")
            print(f" - Estado: {game_state['status']}")
            print(f" - Configuración: {game_state['totalTurns']} turnos, {game_state['pointsToWin']} puntos para ganar")
            print(f" - Turno actual: {game_state['currentTurnIndex']}")
            print(f" - Jugadores inicializados:")
            for p in game_state["players"]:
                print(f"   * {p['name']}: Score {p['score']}, Posición {p['boardPosition']}")
        else:
            print(f"Error al iniciar partida: {response.text}")

        print("\n--- Simulación de flujo completada con éxito ---")

if __name__ == "__main__":
    print("Asegúrate de que el servidor esté corriendo en http://127.0.0.1:8000")
    try:
        asyncio.run(test_flow())
    except Exception as e:
        print(f"Error al ejecutar el test: {e}")
        print("¿Olvidaste iniciar el servidor con 'fastapi dev app/main.py'?")
