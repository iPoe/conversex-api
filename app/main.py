from fastapi import FastAPI
from app.routes import rooms

app = FastAPI(title="Conversex API")

app.include_router(rooms.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Conversex API"}
