from app.routes import rooms, debug

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
app.include_router(debug.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Conversex API"}
