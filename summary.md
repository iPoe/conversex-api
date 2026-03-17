# Conversex API - Project Compression Summary 🧊

## 🎯 Objetivo
Backend multijugador 1vs1 para el "serious game" **Conversex** (Educación Sexual). Gestiona lobbies, sincronización de estados y lógica de turnos.

## 🛠️ Stack Tecnológico
- **Framework:** FastAPI (Python 3.9+)
- **Base de Datos:** Supabase (PostgreSQL + Realtime)
- **Modelado:** Pydantic (camelCase para Frontend)
- **Servidor:** Uvicorn con soporte CORS

## 🏗️ Arquitectura de Archivos
- `app/main.py`: Punto de entrada, Middleware CORS.
- `app/routes/rooms.py`: Endpoints (`/rooms`, `/rooms/{code}/join`, `/rooms/{code}/start`, `/rooms/{code}/turn`).
- `app/schemas/schemas.py`: Modelos de datos (Requests/Responses).
- `core/`: Configuración (`config.py`) y Cliente Supabase (`database.py`).
- `tests/`: Scripts de simulación (`test_multiplayer_flow.py`, `stress_test_flow.py`).

## 🔄 Flujo de Datos (Room Lifecycle)
1. **WAITING:** `POST /rooms` -> Crea sala (Host). `POST /rooms/{code}/join` -> Une al 2do jugador.
2. **IN_PROGRESS:** `POST /rooms/{code}/start` -> Inicializa `LiveGameState` y cambia status en DB.
3. **PLAYING:** `POST /rooms/{code}/turn` -> Registra jugadas, actualiza puntajes y `boardPosition`.
4. **FINISHED:** Se activa automáticamente cuando se alcanzan los `totalTurns`.

## ✅ Estado Actual (V2)
- [x] CRUD de Salas y Jugadores.
- [x] Soporte para Realtime vía Supabase.
- [x] Validación de Robustez (CORS, 404, Room Full).
- [x] Documentación Swagger operativa.

## 🔜 Próximos Pasos
- Implementar lógica de reconexión (`online_status`).
- Refinar cálculo de puntajes en el endpoint de turnos.
- Integración final con Lovable Frontend.
