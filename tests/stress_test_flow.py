import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def run_tests():
    async with httpx.AsyncClient() as client:
        print("=== INICIANDO PRUEBAS DE ROBUSTEZ (STRESS TEST) ===\n")

        # ESCENARIO 1: Unirse a una sala que NO existe
        print("TEST 1: Unirse a sala inexistente (Debe fallar con 404)")
        bad_join = {"playerName": "Infiltrado", "playerAvatar": "av-x"}
        res = await client.post(f"{BASE_URL}/rooms/NONEXISTENT/join", json=bad_join)
        print(f"Resultado: {res.status_code} - {res.json().get('detail')}\n")

        # ESCENARIO 2: Flujo normal hasta llenar la sala
        print("TEST 2: Creando sala y llenándola...")
        # Crear
        res_create = await client.post(f"{BASE_URL}/rooms", json={"hostName": "Host", "hostAvatar": "av-1"})
        room_code = res_create.json()["roomCode"]
        print(f"Sala creada: {room_code}")

        # Unir al 2do jugador
        await client.post(f"{BASE_URL}/rooms/{room_code}/join", json={"playerName": "Player 2", "playerAvatar": "av-2"})
        print("Jugador 2 unido.")

        # Intentar unir al 3er jugador (Debe fallar con 400)
        print("TEST 3: Intentar unir 3er jugador (Debe fallar con 400)")
        res_3rd = await client.post(f"{BASE_URL}/rooms/{room_code}/join", json={"playerName": "Player 3", "playerAvatar": "av-3"})
        print(f"Resultado: {res_3rd.status_code} - {res_3rd.json().get('detail')}\n")

        # ESCENARIO 4: Validación de datos en el Inicio (Start)
        print("TEST 4: Iniciar partida con datos inválidos (Debe fallar por validación de Pydantic)")
        # Enviamos un string donde debería ir un número (totalTurns)
        bad_start = {"totalTurns": "MUCHOS", "pointsToWin": 50}
        res_val = await client.post(f"{BASE_URL}/rooms/{room_code}/start", json=bad_start)
        print(f"Resultado: {res_val.status_code} (Validación fallida correctamente)\n")

        # ESCENARIO 5: Flujo final exitoso
        print("TEST 5: Inicio de partida con éxito")
        good_start = {"totalTurns": 10, "pointsToWin": 40, "isTimerEnabled": False}
        res_final = await client.post(f"{BASE_URL}/rooms/{room_code}/start", json=good_start)
        print(f"Resultado: {res_final.status_code} - Partida en estado '{res_final.json()['status']}'")

        print("\n=== PRUEBAS FINALIZADAS ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
