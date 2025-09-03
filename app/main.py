from fastapi import FastAPI
from app.database import create_db_and_tables
from app.routers.worker_router import router as worker_router

app = FastAPI(title="Opening Bell API", description="Stock market data and news aggregation API")

app.include_router(worker_router)

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

@app.get("/")
async def root():
    return {"message": "Opening Bell API - Stock market data and news aggregation"}
