# Conversex API - Backend

Esta es la API para el juego serio multijugador **Conversex**, construida con FastAPI y Supabase.

## Requisitos Previos

- Python 3.9+
- Una cuenta en [Supabase](https://supabase.com/)

## Configuración de la Base de Datos (Supabase)

Ejecuta el siguiente SQL en el **SQL Editor** de tu proyecto de Supabase para crear las tablas necesarias:

```sql
-- 1. Crear las tablas necesarias
-- Tabla de Salas (Rooms)
create table rooms (
  id uuid default gen_random_uuid() primary key,
  room_code varchar(6) unique not null,
  status text check (status in ('waiting', 'playing', 'finished')) default 'waiting',
  config jsonb default '{"turns": 10, "intensity": "low"}'::jsonb,
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

-- 2. Habilitar Realtime para las tablas (solo una vez creadas)
alter publication supabase_realtime add table rooms;
alter publication supabase_realtime add table players;
```

## Instalación

1. Clona el repositorio.
2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Configura las variables de entorno:
   - Copia `.env.example` a `.env`.
   - Rellena `SUPABASE_URL` y `SUPABASE_KEY` con tus credenciales de Supabase.

## Ejecución

Para iniciar el servidor de desarrollo:
```bash
fastapi dev app/main.py
```
La API estará disponible en `http://127.0.0.1:8000`. Puedes acceder a la documentación interactiva en `/docs`.

## Pruebas

Para ejecutar el script de simulación multijugador:
```bash
python test_multiplayer_flow.py
```
