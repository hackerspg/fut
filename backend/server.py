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
from enhanced_data_collector import EnhancedDataCollector

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
data_collector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper_manager, prediction_engine, scheduler_manager, data_collector
    
    # Initialize services
    scraper_manager = ScraperManager(db)
    prediction_engine = PredictionEngine(db)
    scheduler_manager = SchedulerManager(db, scraper_manager, prediction_engine)
    data_collector = EnhancedDataCollector(db)
    
    # Start scheduler
    scheduler_manager.start()
    
    logger.info("🚀 Gelişmiş Bahis Tahmin Sistemi başlatıldı!")
    
    yield
    
    # Cleanup
    scheduler_manager.stop()
    client.close()
    logger.info("🔴 Sistem kapatıldı!")

# Create the main app
app = FastAPI(
    title="Gelişmiş Bahis Tahmin Sistemi",
    description="58+ Ligden Veri Toplayan AI Destekli Gelişmiş Bahis Tahmin Sistemi",
    version="2.0.0",
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

# ===== ENHANCED ROUTES =====

@api_router.get("/")
async def root():
    return {
        "message": "🎯 Gelişmiş Bahis Tahmin Sistemi API'ye Hoşgeldiniz!",
        "version": "2.0.0",
        "status": "active",
        "features": ["Enhanced Data Collection", "Advanced ML Models", "Real-time Predictions", "Comprehensive Analytics"]
    }

@api_router.get("/system/status")
async def get_system_status():
    """Gelişmiş sistem durumunu kontrol et"""
    try:
        await db.command("ping")
        
        # Detaylı koleksiyon bilgileri
        leagues_count = await db.leagues.count_documents({})
        active_leagues = await db.leagues.count_documents({"active": True})
        teams_count = await db.teams.count_documents({})
        matches_count = await db.matches.count_documents({})
        finished_matches = await db.matches.count_documents({"status": "finished"})
        upcoming_matches = await db.matches.count_documents({"status": "scheduled"})
        predictions_count = await db.predictions.count_documents({})
        team_stats_count = await db.team_stats.count_documents({})
        
        # Son 24 saatteki aktivite
        since_24h = datetime.utcnow() - timedelta(hours=24)
        recent_predictions = await db.predictions.count_documents({
            "created_at": {"$gte": since_24h}
        })
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": "2.0.0",
            "collections": {
                "leagues": {"total": leagues_count, "active": active_leagues},
                "teams": teams_count,
                "matches": {"total": matches_count, "finished": finished_matches, "upcoming": upcoming_matches},
                "predictions": predictions_count,
                "team_stats": team_stats_count
            },
            "recent_activity": {
                "predictions_24h": recent_predictions
            },
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Sistem durumu kontrolü hatası: {e}")
        raise HTTPException(status_code=500, detail="Sistem durumu kontrol edilemiyor")

@api_router.get("/leagues")
async def get_leagues():
    """Gelişmiş lig bilgileri"""
    try:
        leagues = await db.leagues.find({"active": True}).to_list(1000)
        
        enhanced_leagues = []
        for league in leagues:
            league['_id'] = str(league['_id'])
            
            # Her lig için takım sayısını ekle
            teams_count = await db.teams.count_documents({"league_id": league['id']})
            matches_count = await db.matches.count_documents({"league_id": league['id']})
            predictions_count = await db.predictions.count_documents({"league_id": league['id']})
            
            league['statistics'] = {
                "teams": teams_count,
                "matches": matches_count,
                "predictions": predictions_count
            }
            
            enhanced_leagues.append(league)
        
        return {"leagues": enhanced_leagues, "count": len(enhanced_leagues)}
    except Exception as e:
        logger.error(f"Ligler getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Ligler getirilemedi")

@api_router.get("/leagues/{league_id}/teams")
async def get_teams_by_league(league_id: str):
    """Belirtilen ligin takımlarını detaylı bilgilerle getir"""
    try:
        teams = await db.teams.find({"league_id": league_id}).to_list(1000)
        
        enhanced_teams = []
        for team in teams:
            team['_id'] = str(team['_id'])
            
            # Takım istatistiklerini ekle
            team_stats = await db.team_stats.find_one({
                "team_id": team['id'],
                "season": "2024-25"
            })
            
            if team_stats:
                team_stats['_id'] = str(team_stats['_id'])
                team['current_season_stats'] = team_stats
            
            # Son 5 maçı ekle
            recent_matches = await db.matches.find({
                "$or": [{"home_team_id": team['id']}, {"away_team_id": team['id']}],
                "status": "finished"
            }).sort("match_date", -1).limit(5).to_list(5)
            
            team['recent_matches'] = len(recent_matches)
            enhanced_teams.append(team)
        
        return {"teams": enhanced_teams, "count": len(enhanced_teams)}
    except Exception as e:
        logger.error(f"Takımlar getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Takımlar getirilemedi")

@api_router.get("/matches/upcoming")
async def get_upcoming_matches(days: int = 7):
    """Gelecek X gün içindeki maçları detaylı bilgilerle getir"""
    try:
        end_date = datetime.utcnow() + timedelta(days=days)
        matches = await db.matches.find({
            "match_date": {"$gte": datetime.utcnow(), "$lte": end_date}
        }).sort("match_date", 1).to_list(1000)
        
        enhanced_matches = []
        for match in matches:
            match['_id'] = str(match['_id'])
            
            # Takım isimlerini ekle
            home_team = await db.teams.find_one({"id": match['home_team_id']})
            away_team = await db.teams.find_one({"id": match['away_team_id']})
            
            if home_team and away_team:
                match['home_team_name'] = home_team['name']
                match['away_team_name'] = away_team['name']
                
                # Lig bilgisini ekle
                league = await db.leagues.find_one({"id": match['league_id']})
                if league:
                    match['league_name'] = league['name']
                
                # Bu maç için tahminleri ekle
                predictions = await db.predictions.find({
                    "match_id": match['id']
                }).to_list(10)
                
                match['predictions'] = []
                for pred in predictions:
                    pred['_id'] = str(pred['_id'])
                    match['predictions'].append(pred)
                
                enhanced_matches.append(match)
        
        return {"matches": enhanced_matches, "count": len(enhanced_matches)}
    except Exception as e:
        logger.error(f"Yaklaşan maçlar getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Yaklaşan maçlar getirilemedi")

@api_router.get("/matches/recent")
async def get_recent_matches(days: int = 7):
    """Son X gün içindeki tamamlanmış maçları getir"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        matches = await db.matches.find({
            "match_date": {"$gte": start_date, "$lte": datetime.utcnow()},
            "status": "finished"
        }).sort("match_date", -1).to_list(1000)
        
        enhanced_matches = []
        for match in matches:
            match['_id'] = str(match['_id'])
            
            # Takım isimlerini ekle
            home_team = await db.teams.find_one({"id": match['home_team_id']})
            away_team = await db.teams.find_one({"id": match['away_team_id']})
            
            if home_team and away_team:
                match['home_team_name'] = home_team['name']
                match['away_team_name'] = away_team['name']
                
                # Lig bilgisini ekle
                league = await db.leagues.find_one({"id": match['league_id']})
                if league:
                    match['league_name'] = league['name']
                
                enhanced_matches.append(match)
        
        return {"matches": enhanced_matches, "count": len(enhanced_matches)}
    except Exception as e:
        logger.error(f"Son maçlar getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Son maçlar getirilemedi")

@api_router.get("/predictions/today")
async def get_today_predictions():
    """Bugünkü gelişmiş tahminleri getir"""
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        predictions = await db.predictions.find({
            "match_date": {"$gte": today_start, "$lt": today_end}
        }).sort("confidence", -1).to_list(1000)
        
        enhanced_predictions = []
        for prediction in predictions:
            prediction['_id'] = str(prediction['_id'])
            
            # Takım ve lig bilgilerini ekle
            home_team = await db.teams.find_one({"id": prediction['home_team_id']})
            away_team = await db.teams.find_one({"id": prediction['away_team_id']})
            league = await db.leagues.find_one({"id": prediction['league_id']})
            
            if home_team and away_team and league:
                prediction['home_team_name'] = home_team['name']
                prediction['away_team_name'] = away_team['name']
                prediction['league_name'] = league['name']
                
                # Maç bilgilerini ekle
                match = await db.matches.find_one({"id": prediction['match_id']})
                if match:
                    prediction['match_time'] = match['match_date']
                    prediction['odds'] = {
                        "1x2": match.get('odds_1x2'),
                        "over_under": match.get('odds_over_under'),
                        "btts": match.get('odds_btts')
                    }
                
                enhanced_predictions.append(prediction)
        
        return {"predictions": enhanced_predictions, "count": len(enhanced_predictions)}
    except Exception as e:
        logger.error(f"Bugünkü tahminler getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Bugünkü tahminler getirilemedi")

@api_router.get("/predictions/all")
async def get_all_predictions(limit: int = 50):
    """Tüm tahminleri gelişmiş bilgilerle getir"""
    try:
        predictions = await db.predictions.find({}).sort("created_at", -1).limit(limit).to_list(limit)
        
        enhanced_predictions = []
        for prediction in predictions:
            prediction['_id'] = str(prediction['_id'])
            
            # Takım ve lig bilgilerini ekle
            home_team = await db.teams.find_one({"id": prediction['home_team_id']})
            away_team = await db.teams.find_one({"id": prediction['away_team_id']})
            league = await db.leagues.find_one({"id": prediction['league_id']})
            
            if home_team and away_team and league:
                prediction['home_team_name'] = home_team['name']
                prediction['away_team_name'] = away_team['name']
                prediction['league_name'] = league['name']
                
                enhanced_predictions.append(prediction)
        
        return {"predictions": enhanced_predictions, "count": len(enhanced_predictions)}
    except Exception as e:
        logger.error(f"Tüm tahminler getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Tüm tahminler getirilemedi")

@api_router.get("/predictions/match/{match_id}")
async def get_match_prediction(match_id: str):
    """Belirli bir maç için tüm tahminleri getir"""
    try:
        predictions = await db.predictions.find({"match_id": match_id}).to_list(10)
        
        if not predictions:
            raise HTTPException(status_code=404, detail="Bu maç için tahmin bulunamadı")
        
        enhanced_predictions = []
        for prediction in predictions:
            prediction['_id'] = str(prediction['_id'])
            enhanced_predictions.append(prediction)
        
        # Maç bilgilerini de ekle
        match = await db.matches.find_one({"id": match_id})
        if match:
            match['_id'] = str(match['_id'])
            
            # Takım isimlerini ekle
            home_team = await db.teams.find_one({"id": match['home_team_id']})
            away_team = await db.teams.find_one({"id": match['away_team_id']})
            
            if home_team and away_team:
                match['home_team_name'] = home_team['name']
                match['away_team_name'] = away_team['name']
        
        return {
            "match": match,
            "predictions": enhanced_predictions,
            "count": len(enhanced_predictions)
        }
    except Exception as e:
        logger.error(f"Maç tahmini getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Maç tahmini getirilemedi")

@api_router.post("/data/generate-demo")
async def generate_demo_data(background_tasks: BackgroundTasks):
    """Gelişmiş demo verisi oluştur"""
    try:
        if not data_collector:
            raise HTTPException(status_code=503, detail="Veri toplama servisi hazır değil")
        
        background_tasks.add_task(data_collector.generate_realistic_data)
        
        return {
            "message": "Gelişmiş demo verisi oluşturma işlemi başlatıldı",
            "description": "Premier League takımları, maçları, istatistikleri ve tahminleri oluşturuluyor",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Demo veri oluşturma başlatılamadı: {e}")
        raise HTTPException(status_code=500, detail="Demo veri oluşturma başlatılamadı")

@api_router.post("/scraper/run")
async def trigger_scraper(background_tasks: BackgroundTasks):
    """Gelişmiş veri toplama işlemini manuel olarak başlat"""
    try:
        if not scraper_manager:
            raise HTTPException(status_code=503, detail="Scraper servisi hazır değil")
        
        # Önce demo veri oluştur, sonra scraper çalıştır
        background_tasks.add_task(data_collector.generate_realistic_data)
        background_tasks.add_task(scraper_manager.run_scraping_job, None)
        
        return {
            "message": "Gelişmiş veri toplama işlemi başlatıldı",
            "description": "Demo verisi oluşturulup, gerçek veri toplama da başlatıldı",
            "leagues": "all",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Scraper başlatılamadı: {e}")
        raise HTTPException(status_code=500, detail="Scraper başlatılamadı")

@api_router.post("/prediction/generate")
async def generate_predictions(background_tasks: BackgroundTasks):
    """Gelişmiş tahmin üretme işlemini manuel olarak başlat"""
    try:
        if not prediction_engine:
            raise HTTPException(status_code=503, detail="Tahmin servisi hazır değil")
        
        background_tasks.add_task(prediction_engine.generate_predictions, None)
        
        return {
            "message": "Gelişmiş tahmin üretme işlemi başlatıldı",
            "description": "AI modelleri ile detaylı tahminler üretiliyor",
            "matches": "all",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Tahmin üretme başlatılamadı: {e}")
        raise HTTPException(status_code=500, detail="Tahmin üretme başlatılamadı")

@api_router.get("/stats/performance")
async def get_performance_stats():
    """Gelişmiş sistem performans istatistikleri"""
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # 30 günlük performans
        total_predictions_30d = await db.predictions.count_documents({
            "created_at": {"$gte": thirty_days_ago}
        })
        
        correct_predictions_30d = await db.predictions.count_documents({
            "created_at": {"$gte": thirty_days_ago},
            "actual_result": {"$exists": True},
            "is_correct": True
        })
        
        # 7 günlük performans
        total_predictions_7d = await db.predictions.count_documents({
            "created_at": {"$gte": seven_days_ago}
        })
        
        correct_predictions_7d = await db.predictions.count_documents({
            "created_at": {"$gte": seven_days_ago},
            "actual_result": {"$exists": True},
            "is_correct": True
        })
        
        # Bahis türüne göre performans
        bet_type_stats = {}
        for bet_type in ["1X2", "O/U2.5", "BTTS"]:
            total = await db.predictions.count_documents({
                "bet_type": bet_type,
                "created_at": {"$gte": thirty_days_ago}
            })
            correct = await db.predictions.count_documents({
                "bet_type": bet_type,
                "created_at": {"$gte": thirty_days_ago},
                "actual_result": {"$exists": True},
                "is_correct": True
            })
            
            accuracy = (correct / total * 100) if total > 0 else 0
            bet_type_stats[bet_type] = {
                "total": total,
                "correct": correct,
                "accuracy": round(accuracy, 2)
            }
        
        accuracy_30d = (correct_predictions_30d / total_predictions_30d * 100) if total_predictions_30d > 0 else 0
        accuracy_7d = (correct_predictions_7d / total_predictions_7d * 100) if total_predictions_7d > 0 else 0
        
        return {
            "overall_performance": {
                "last_30_days": {
                    "total_predictions": total_predictions_30d,
                    "correct_predictions": correct_predictions_30d,
                    "accuracy_percentage": round(accuracy_30d, 2)
                },
                "last_7_days": {
                    "total_predictions": total_predictions_7d,
                    "correct_predictions": correct_predictions_7d,
                    "accuracy_percentage": round(accuracy_7d, 2)
                }
            },
            "bet_type_performance": bet_type_stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Performans istatistikleri getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Performans istatistikleri getirilemedi")

@api_router.get("/stats/league/{league_id}")
async def get_league_stats(league_id: str):
    """Belirli bir lig için detaylı istatistikler"""
    try:
        league = await db.leagues.find_one({"id": league_id})
        if not league:
            raise HTTPException(status_code=404, detail="Lig bulunamadı")
        
        # Lig istatistikleri
        teams_count = await db.teams.count_documents({"league_id": league_id})
        matches_count = await db.matches.count_documents({"league_id": league_id})
        finished_matches = await db.matches.count_documents({"league_id": league_id, "status": "finished"})
        predictions_count = await db.predictions.count_documents({"league_id": league_id})
        
        # Son 10 maç
        recent_matches = await db.matches.find({
            "league_id": league_id,
            "status": "finished"
        }).sort("match_date", -1).limit(10).to_list(10)
        
        # Gol ortalamaları
        total_goals = 0
        for match in recent_matches:
            if match.get('home_score') is not None and match.get('away_score') is not None:
                total_goals += match['home_score'] + match['away_score']
        
        avg_goals = round(total_goals / len(recent_matches), 2) if recent_matches else 0
        
        return {
            "league": {
                "id": league['id'],
                "name": league['name'],
                "country": league['country'],
                "season": league['season']
            },
            "statistics": {
                "teams": teams_count,
                "total_matches": matches_count,
                "finished_matches": finished_matches,
                "predictions": predictions_count,
                "avg_goals_per_match": avg_goals
            },
            "recent_matches": len(recent_matches),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Lig istatistikleri getirilemedi: {e}")
        raise HTTPException(status_code=500, detail="Lig istatistikleri getirilemedi")

# Include the router in the main app
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)