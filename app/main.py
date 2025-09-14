from fastapi import FastAPI, HTTPException
from app.api.v1.routes import user
from app.db import models
from app.db.session import engine
from app.db.session import SessionLocal
from app.api.v1.routes import auth, websocket, document

app = FastAPI()


def get_db():
    """FastAPI dependency that yields a DB session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


models.Base.metadata.create_all(bind=engine)
app.include_router(user.router, prefix="/api/v1", tags=["users"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"]) 
app.include_router(websocket.router, tags=["websocket"])
app.include_router(document.router, prefix="/api/v1", tags=["documents"])