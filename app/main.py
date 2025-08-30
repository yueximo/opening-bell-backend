from fastapi import FastAPI
from app.database import create_db_and_tables, seed_database

app = FastAPI(title="Opening Bell API", description="Stock market data and news aggregation API")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_database()  # This will seed the database every time the app starts

@app.get("/")
async def root():
    return {"message": "Opening Bell API - Stock market data and news aggregation"}

@app.post("/seed")
async def seed_db():
    """One-time endpoint to seed the database"""
    try:
        seed_database()
        return {"message": "Database seeded successfully!"}
    except Exception as e:
        return {"error": f"Failed to seed database: {str(e)}"}