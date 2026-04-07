from fastapi import FastAPI
from database.setup import init_db, seed_database
from apis.routes import router

app = FastAPI(title="Agentic CX Simulator Server")

def startup_event():
    init_db()
    seed_database()

app.include_router(router)