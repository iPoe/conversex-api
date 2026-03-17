# GEMINI Context: Conversex API (Backend) 🚀

Este archivo proporciona el contexto técnico esencial para trabajar en el backend del juego multijugador **Conversex**.

## 📝 Resumen del Proyecto
**Conversex** es un "serious game" multijugador diseñado para la educación sexual y el consentimiento. Esta API gestiona el ciclo de vida de las salas, la sincronización de jugadores y el estado del juego en tiempo real mediante Supabase.

- **Tecnologías:** FastAPI (Python 3.9+), Supabase (PostgreSQL + Realtime), Pydantic.
- **Arquitectura:** REST API modular con separación de rutas (`app/routes`), esquemas (`app/schemas`) y configuración centralizada (`core/`).

## 🛠️ Comandos de Ejecución y Desarrollo

### Configuración Inicial
```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar entorno
cp .env.example .env  # Luego rellenar SUPABASE_URL y SUPABASE_KEY
```

### Ejecución del Servidor
```bash
# Iniciar con recarga automática
python -m uvicorn app.main:app --reload --port 8000
```
- **Documentación:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger UI).

### Pruebas y Validación
```bash
# Simulación de flujo multijugador completo
python test_multiplayer_flow.py

# Pruebas de estrés y casos borde (404, 400, 422)
python stress_test_flow.py
```

## 📐 Convenciones de Desarrollo

### Integración con el Frontend
- **Formato de Datos:** Se DEBE usar **camelCase** en todos los modelos de Pydantic (`app/schemas/schemas.py`) para las respuestas y solicitudes, facilitando la integración con React/Lovable.
- **CORS:** Configurado en `app/main.py` para permitir todos los orígenes (`*`) durante el desarrollo.

### Ciclo de Vida de la Sala (Room)
- **Estados:** `waiting` -> `in_progress` -> `playing` -> `finished`.
- **Límite:** Máximo 2 jugadores por sala (1vs1).
- **Configuración:** Almacenada en la columna JSONB `config` de la tabla `rooms`.

### Sincronización en Tiempo Real
El frontend debe suscribirse a las tablas de Supabase:
- `players`: Para actualizaciones de la lista de jugadores en el lobby (INSERT/UPDATE).
- `rooms`: Para detectar el cambio de estado de `waiting` a `in_progress` y activar la transición de pantalla.

## 📂 Estructura de Archivos Clave
- `app/main.py`: Punto de entrada y configuración de Middlewares (CORS).
- `app/routes/rooms.py`: Lógica de negocio para crear salas, unirse e iniciar partidas.
- `app/schemas/schemas.py`: Definiciones de modelos Pydantic (`RoomResponse`, `LiveGameState`, etc.).
- `core/database.py`: Inicialización del cliente de Supabase.
- `README.md`: Contiene el SQL necesario para inicializar la base de datos en Supabase.

## ⚠️ Recordatorios de Seguridad
- Nunca subir el archivo `.env` al repositorio.
- Las transiciones de estado en la base de datos están protegidas por un check constraint: `rooms_status_check`.
