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

### 🔄 DB Migration (run after initial setup)

If your `players` table was created before **2026-03-26**, run this migration in your Supabase SQL Editor:

```sql
-- Add score and turns_played columns (idempotent)
alter table players add column if not exists score int default 0;
alter table players add column if not exists turns_played int default 0;
```


## 💻 Entorno de Desarrollo Local (Docker)

Para evitar que tu proyecto de Supabase en la nube se pause y para acelerar el desarrollo, puedes correr todo el stack de base de datos en tu laptop.

### 1. Requisitos Previos
- **Docker Desktop** instalado y en ejecución.
- **Supabase CLI**: `brew install supabase/tap/supabase` (Mac) o `npm install supabase --save-dev` (NPM).

### 2. Configuración Inicial
```bash
npx supabase init  # Inicia el proyecto (solo la primera vez)
npx supabase start # Levanta los contenedores y aplica migraciones automáticas
```

### 3. El "Switch" de la API
La API puede alternar entre la nube y tu local usando la variable `ENV` en tu archivo `.env`:
- `ENV=local`: Apunta al Docker local (`http://127.0.0.1:54321`).
- `ENV=cloud`: Apunta a tu proyecto real en Supabase Cloud.

### 4. Carga de Datos en Local
Una vez que `supabase start` termine, carga las preguntas del juego:
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 scripts/seed_cases_from_excel.py
```
*Puedes ver y gestionar tus datos locales en: [http://localhost:54323](http://localhost:54323)*


## 🚀 Instalación y Uso

1. **Clonar e Instalar:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Variables de Entorno:**
   Copia `.env.example` a `.env` y asegúrate de configurar las siguientes variables:
   - `SUPABASE_URL`: La URL de tu proyecto de Supabase.
   - `SUPABASE_KEY`: El API Key (anon/public) de tu proyecto.

3. **Ejecutar Servidor:**
   ```bash
   python3 -m uvicorn app.main:app --reload
   ```
   *Accede a la documentación en: `http://127.0.0.1:8000/docs`*

## 🗳️ Carga de Datos (Seeding)

Para cargar los casos y preguntas del juego desde un archivo Excel a Supabase:

1. Asegúrate de tener el archivo `cases.xlsx` en la raíz.
2. Ejecuta el script de seeding:
   ```bash
   python3 seed_cases_from_excel.py
   ```
   *Este script parseará automáticamente las hojas (Hospital, Internet, etc.) y subirá la rúbrica de puntos a la tabla `cases`.*


## 🔌 Endpoints Destacados

| Método | Endpoint | Propósito |
|---|---|---|
| `POST` | `/rooms` | Crear sala y asignar Host |
| `POST` | `/rooms/{code}/join` | Unirse a una sala existente (máx. 2) |
| `POST` | `/rooms/{code}/start` | Iniciar la partida y configurar parámetros |
| `GET` | `/rooms/{code}` | Obtener el estado completo en tiempo real (`LiveGameState`) |
| `POST` | `/rooms/{code}/roll` | Tirar el dado (Sincronización vía Realtime) |
| `POST` | `/rooms/{code}/move` | Moverse por el grafo (Incluye `caseData` al llegar a zona) |
| `POST` | `/rooms/{code}/argue` | Enviar argumento (Inicia fase de votación) |
| `POST` | `/rooms/{code}/vote` | Emitir voto (Cálculo automático de resultados) |
| `GET` | `/rooms/{code}/vote-results` | Consultar resultado de la última votación |
| `POST` | `/rooms/{code}/reset` | Reiniciar sala y jugadores al estado inicial |

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

### Arquitectura del Proyecto
- `app/enums.py`: **Máquina de Estados**. Enums centralizados para `RoomStatus` y `GamePhase`.
- `app/routes`: Endpoints REST delgados que delegan la lógica al `game_service`.
- `app/schema`: Modelos Pydantic con validación de entrada (`Field`).
- `app/services/game_service.py`: **Capa de Servicio**. Contiene toda la lógica de negocio pura (dados, turnos, votación) desacoplada de la API.
- `core/board.py`: **Motor de Movimiento**. Gestiona el grafo y la navegación por celdas.

### 🧪 Pruebas Unitarias e Integración
Además de las pruebas de flujo, contamos con una suite de pruebas unitarias para la lógica del juego:

```bash
# Ejecutar todas las pruebas unitarias (Service Layer)
python3 -m pytest tests/test_game_service.py -v
```

### 🐞 Sistema de Debug (Frontend Sync)
Para facilitar el desarrollo con el equipo de Frontend, la API incluye un sistema de logs locales:
- `POST /debug/log`: Permite enviar logs desde el cliente para que se guarden en archivos `.txt` en el servidor.
- `POST /debug/reset`: Limpia los archivos de log.

### Sincronización en Tiempo Real
- El servidor es el **"Game Master"**, controlando las fases (`phase`) e índices de turno (`current_turn_index`).
- **Source of Truth**: El estado de los turnos y la historia se gestionan exclusivamente dentro del objeto `config` (JSONB) en la tabla `rooms`.
- Las actualizaciones atómicas se realizan mediante el RPC `commit_player_move` en Supabase.
