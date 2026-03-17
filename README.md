# Conversex API - Backend 🚀

Esta es la API para el juego serio multijugador **Conversex**, construida con **FastAPI** y **Supabase**. Está diseñada para gestionar el ciclo de vida de las partidas, desde la creación del lobby hasta el inicio del juego en tiempo real.

## 🛠️ Requisitos Previos

- Python 3.9+
- Una cuenta en [Supabase](https://supabase.com/)
- Conda o Venv (entorno virtual recomendado)

## 🗄️ Configuración de la Base de Datos (Supabase)

Ejecuta el siguiente SQL en el **SQL Editor** de tu proyecto de Supabase para preparar el esquema:

```sql
-- 1. Crear las tablas necesarias
-- Tabla de Salas (Rooms)
create table rooms (
  id uuid default gen_random_uuid() primary key,
  room_code varchar(6) unique not null,
  status text check (status in ('waiting', 'in_progress', 'playing', 'finished')) default 'waiting',
  config jsonb default '{"totalTurns": 10, "pointsToWin": 40, "isTimerEnabled": false}'::jsonb,
  created_at timestamp with time zone default now()
);

-- Tabla de Jugadores (Players)
create table players (
  id uuid default gen_random_uuid() primary key,
  room_id uuid references rooms(id) on delete cascade,
  name text not null,
  avatar_id text not null,
  is_host boolean default false,
  online_status boolean default true,
  created_at timestamp with time zone default now()
);

-- 2. Habilitar Realtime para sincronización con el Frontend
alter publication supabase_realtime add table rooms;
alter publication supabase_realtime add table players;
```

## 🚀 Instalación y Uso

1. **Clonar e Instalar:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Variables de Entorno:**
   Copia `.env.example` a `.env` y rellena `SUPABASE_URL` y `SUPABASE_KEY`.

3. **Ejecutar Servidor:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```
   *Accede a la documentación en: `http://127.0.0.1:8000/docs`*

## 🔌 Endpoints de la API (v2)

| Método | Endpoint | Propósito |
|---|---|---|
| `POST` | `/rooms` | Crear sala y asignar Host |
| `POST` | `/rooms/{code}/join` | Unirse a una sala existente (máx. 2) |
| `POST` | `/rooms/{code}/start` | Iniciar partida e inicializar `LiveGameState` |

## 🧪 Pruebas y Validación

Hemos implementado scripts de prueba para asegurar la robustez del sistema:

1. **Flujo Normal (`test_multiplayer_flow.py`):** Simula el ciclo completo de creación, unión e inicio.
2. **Robustez (`stress_test_flow.py`):** Valida casos borde y errores controlados:
   - ✅ Error 404 si la sala no existe.
   - ✅ Error 400 si se intenta unir a un 3er jugador.
   - ✅ Error 422 si se envían tipos de datos inválidos.
   - ✅ Éxito en la inicialización del estado del juego.

Para ejecutar las pruebas:
```bash
python test_multiplayer_flow.py
python stress_test_flow.py
```

## 📝 Notas de Desarrollo
- La API utiliza **camelCase** para facilitar la integración con el frontend (Lovable/React).
- El estado del juego se maneja a través de un objeto centralizado llamado `LiveGameState`.
