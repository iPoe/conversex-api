from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import rooms

app = FastAPI(title="Conversex API")

# Configurar CORS
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    # Puedes añadir "*" si quieres permitir cualquier origen durante el desarrollo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todos los orígenes para facilitar el desarrollo con Lovable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Conversex API"}
