### 1. Crear sala (POST `/rooms`)
```json
// Request
{
  "hostName": "Carlos",
  "hostAvatar": "avatar-3"
}

// Response
{
  "roomCode": "10-4A2T",
  "gameId": "uuid-here",
  "status": "waiting",
  "players": [
    { "name": "Carlos", "avatar": "avatar-3", "isHost": true }
  ]
}
```

### 2. Unirse a sala (POST `/rooms/:roomCode/join`)
```json
// Request
{ "playerName": "María", "playerAvatar": "avatar-5" }

// Response (broadcast a todos vía WebSocket)
{
  "players": [
    { "name": "Carlos", "avatar": "avatar-3", "isHost": true },
    { "name": "María", "avatar": "avatar-5", "isHost": false }
  ]
}
```

### 3. Iniciar partida (POST `/rooms/:roomCode/start`)
```json
// Request (solo el host)
{
  "selectedDecks": ["romance", "picante"],
  "totalTurns": 10,
  "pointsToWin": 40,
  "isTimerEnabled": false
}

// Response → tu LiveGameState
{
  "gameId": "uuid",
  "roomCode": "10-4A2T",
  "status": "in_progress",
  "currentTurnIndex": 0,
  "totalTurns": 10,
  "pointsToWin": 40,
  "selectedDecks": ["romance", "picante"],
  "players": [
    { "name": "Carlos", "avatarId": "avatar-3", "boardPosition": 0, "score": 0, "turnsPlayed": 0 },
    { "name": "María", "avatarId": "avatar-5", "boardPosition": 0, "score": 0, "turnsPlayed": 0 }
  ],
  "turnHistory": []
}
```

### 4. WebSocket events que recomiendo
| Evento | Dirección | Propósito |
|---|---|---|
| `player_joined` | Server → All | Actualizar lista en lobby |
| `player_left` | Server → All | Remover jugador |
| `game_started` | Server → All | Navegar todos a intro |
| `turn_update` | Server → All | Sincronizar turno/puntos |
| `game_ended` | Server → All | Mostrar resultados |

Tu `GameContext` ya tiene `GamePayload`, `LiveGameState` y `TurnRecord` que mapean perfectamente a estos endpoints. ¿Quieres que adapte el frontend para consumir estos endpoints cuando tengas la API lista?

Conectar frontend con API multiplayer
Validar código de sala con API
Sincronizar turnos en tiempo real