from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import rooms

app = FastAPI(title="Conversex API")

# Configurar CORS extendido
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todo para desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.include_router(rooms.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Conversex API"}
