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
  phase text check (phase in ('rolling', 'moving', 'arguing', 'voting', 'finished')) default 'rolling',
  current_case_id uuid,
  current_zone_id text, -- Tracking de zona por ID (Hospital, Wifi, etc)
  current_argument text, -- Almacenamiento de argumentación para votación
  dice_value int,
  config jsonb default '{"totalTurns": 10, "pointsToWin": 40, "isTimerEnabled": false, "turnHistory": []}'::jsonb,
  created_at timestamp with time zone default now()
);

-- Tabla de Casos (Cases)
create table cases (
  id uuid default gen_random_uuid() primary key,
  zone int not null, -- 1: Consentimiento, 2: Diversidad, 3: Salud, etc.
  description text not null,
  rubric jsonb not null -- Array de {id: string, text: string, points: int}
);

-- Tabla de Votos (Votes)
create table votes (
  id uuid default gen_random_uuid() primary key,
  room_id uuid references rooms(id) on delete cascade,
  voter_name text not null,
  option_id text not null, -- Referencia al ID de la rúbrica
  created_at timestamp with time zone default now(),
  unique(room_id, voter_name) -- Un voto por persona por sala (se limpia cada turno)
);

-- Tabla de Jugadores (Players)
create table players (
  id uuid default gen_random_uuid() primary key,
  room_id uuid references rooms(id) on delete cascade,
  name text not null,
  avatar_id text not null,
  is_host boolean default false,
  online_status boolean default true,
  current_position jsonb default '{"nodeId": "park", "edgeId": null, "edgeProgress": 0}'::jsonb, -- Tracking de posición en grafo
  created_at timestamp with time zone default now()
);

-- 2. Habilitar Realtime para sincronización con el Frontend
alter publication supabase_realtime add table rooms;
alter publication supabase_realtime add table players;
alter publication supabase_realtime add table votes;
```

## 🚀 Instalación y Uso

1. **Clonar e Instalar:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Variables de Env:**
   Copia `.env.example` a `.env` y rellena `SUPABASE_URL` y `SUPABASE_KEY`.

3. **Ejecutar Servidor:**
   ```bash
   python3 -m uvicorn app.main:app --reload
   ```
   *Accede a la documentación en: `http://127.0.0.1:8000/docs`*

## 🔌 Endpoints Destacados

| Método | Endpoint | Propósito |
|---|---|---|
| `POST` | `/rooms` | Crear sala y asignar Host |
| `POST` | `/rooms/{code}/join` | Unirse a una sala existente (máx. 2) |
| `POST` | `/rooms/{code}/move` | Moverse por el grafo (Server-Driven) |
| `POST` | `/rooms/{code}/argue` | Enviar argumento (Trigger de votación) |
| `POST` | `/rooms/{code}/vote` | Votar (Calcula resultados auto al terminar) |

## 🧪 Pruebas y Validación

Hemos organizado los scripts de prueba en la carpeta `tests/`:

1. **Flujo de Grafo (`tests/test_graph_flow.py`):** Valida el ciclo completo de "Game Master".
2. **Flujo Básico (`tests/test_multiplayer_flow.py`):** Valida creación y unión.
3. **Robusta (`tests/stress_test_flow.py`):** Valida casos borde y errores controlados.

Para ejecutar las pruebas:
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 -m tests.test_graph_flow
```

## 📝 Notas de Desarrollo
- La API utiliza **camelCase** en sus esquemas Pydantic para Lovable/React.
- El servidor es ahora el "Game Master", controlando las fases (`phase`) y turnos.
