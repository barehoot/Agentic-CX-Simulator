from fastapi import FastAPI
from database.setup import init_db, seed_database
from apis.routes import router

app = FastAPI(title="Agentic CX Simulator Server")

def startup_event():
    init_db()
    seed_database()

app.include_router(router)

import uvicorn

def main():
    """Entry point for the OpenEnv multi-mode deployment."""
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()