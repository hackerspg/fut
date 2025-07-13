from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager

# Import our modules
from scrapers.scraper_manager import ScraperManager
from prediction.prediction_engine import PredictionEngine
from models.database_models import *
from utils.scheduler import SchedulerManager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Global instances
scraper_manager = None
prediction_engine = None
scheduler_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper_manager, prediction_engine, scheduler_manager
    
    # Initialize services
    scraper_manager = ScraperManager(db)
    prediction_engine = PredictionEngine(db)
    scheduler_manager = SchedulerManager(db, scraper_manager, prediction_engine)
    
    # Start scheduler
    scheduler_manager.start()
    
    logger.info("🚀 Bahis Tahmin Sistemi başlatıldı!")
    
    yield
    
    # Cleanup
    scheduler_manager.stop()
    client.close()
    logger.info("🔴 Sistem kapatıldı!")

# Create the main app
app = FastAPI(
    title="Bahis Tahmin Sistemi",
    description="50+ Ligden Veri Toplayan AI Destekli Bahis Tahmin Sistemi",
    version="1.0.0",
    lifespan=lifespan
)

# Create API router
api_router = APIRouter(prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ROUTES =====

@api_router.get("/")
async def root():
    return {
        "message": "🎯 Bahis Tahmin Sistemi API'ye Hoşgeldiniz!",
        "version": "1.0.0",
        "status": "active"
    }

@api_router.get("/system/status")
async def get_system_status():
    """Sistem durumunu kontrol et"""
    try:
        # Database connection check
        await db.command("ping")
        
        # Check collections
        leagues_count = await db.leagues.count_documents({})
        teams_count = await db.teams.count_documents({})
        matches_count = await db.matches.count_documents({})
        predictions_count = await db.predictions.count_documents({})
        
        return {
            "status": "healthy",
            "database": "connected",
            "collections": {
                "leagues": leagues_count,
                "teams": teams_count,
                "matches": matches_count,
                "predictions": predictions_count
            },
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Sistem durumu kontrolü hatası: {e}")
        raise HTTPException(status_code=500, detail="Sistem durumu kontrol edilemiyor")

@api_router.get("/leagues")
async def get_leagues():
    """Desteklenen ligleri getir"""
    try:
        leagues = await db.leagues.find({"active": True}).to_list(1000)
        # ObjectId'leri string'e çevir
        for league in leagues:
            league['_id'] = str(league['_id'])
        return {"leagues": leagues, "count": len(leagues)}
    except Exception as e:
        logger.error(f"Ligler getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Ligler getirilemedi")

@api_router.get("/leagues/{league_id}/teams")
async def get_teams_by_league(league_id: str):
    """Belirtilen ligin takımlarını getir"""
    try:
        teams = await db.teams.find({"league_id": league_id}).to_list(1000)
        return {"teams": teams, "count": len(teams)}
    except Exception as e:
        logger.error(f"Takımlar getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Takımlar getirilemedi")

@api_router.get("/matches/upcoming")
async def get_upcoming_matches(days: int = 7):
    """Gelecek X gün içindeki maçları getir"""
    try:
        end_date = datetime.utcnow() + timedelta(days=days)
        matches = await db.matches.find({
            "match_date": {"$gte": datetime.utcnow(), "$lte": end_date}
        }).sort("match_date", 1).to_list(1000)
        
        return {"matches": matches, "count": len(matches)}
    except Exception as e:
        logger.error(f"Yaklaşan maçlar getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Yaklaşan maçlar getirilemedi")

@api_router.get("/predictions/today")
async def get_today_predictions():
    """Bugünkü tahminleri getir"""
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        predictions = await db.predictions.find({
            "match_date": {"$gte": today_start, "$lt": today_end}
        }).sort("confidence", -1).to_list(1000)
        
        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error(f"Bugünkü tahminler getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Bugünkü tahminler getirilemedi")

@api_router.get("/predictions/match/{match_id}")
async def get_match_prediction(match_id: str):
    """Belirli bir maç için tahmin getir"""
    try:
        prediction = await db.predictions.find_one({"match_id": match_id})
        if not prediction:
            raise HTTPException(status_code=404, detail="Tahmin bulunamadı")
        
        return {"prediction": prediction}
    except Exception as e:
        logger.error(f"Maç tahmini getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Maç tahmini getirilemedi")

@api_router.post("/scraper/run")
async def trigger_scraper(background_tasks: BackgroundTasks):
    """Veri toplama işlemini manuel olarak başlat"""
    try:
        if not scraper_manager:
            raise HTTPException(status_code=503, detail="Scraper servisi hazır değil")
        
        background_tasks.add_task(scraper_manager.run_scraping_job, None)
        
        return {
            "message": "Veri toplama işlemi başlatıldı",
            "leagues": "all",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Scraper başlatılamadı: {e}")
        raise HTTPException(status_code=500, detail="Scraper başlatılamadı")

@api_router.post("/prediction/generate")
async def generate_predictions(background_tasks: BackgroundTasks):
    """Tahmin üretme işlemini manuel olarak başlat"""
    try:
        if not prediction_engine:
            raise HTTPException(status_code=503, detail="Tahmin servisi hazır değil")
        
        background_tasks.add_task(prediction_engine.generate_predictions, None)
        
        return {
            "message": "Tahmin üretme işlemi başlatıldı",
            "matches": "all",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Tahmin üretme başlatılamadı: {e}")
        raise HTTPException(status_code=500, detail="Tahmin üretme başlatılamadı")

@api_router.get("/stats/performance")
async def get_performance_stats():
    """Sistem performans istatistiklerini getir"""
    try:
        # Son 30 günün tahmin performansını hesapla
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        total_predictions = await db.predictions.count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
        
        correct_predictions = await db.predictions.count_documents({
            "created_at": {"$gte": thirty_days_ago},
            "actual_result": {"$exists": True},
            "is_correct": True
        })
        
        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
        return {
            "period": "last_30_days",
            "total_predictions": total_predictions,
            "correct_predictions": correct_predictions,
            "accuracy_percentage": round(accuracy, 2),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Performans istatistikleri getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Performans istatistikleri getirilemedi")

# Include the router in the main app
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)