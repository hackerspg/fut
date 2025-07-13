import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import aiohttp
import json
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import random
import time

from scrapers.understat_scraper import UnderstatScraper
from scrapers.sofascore_scraper import SofascoreScraper
from scrapers.flashscore_scraper import FlashscoreScraper
from models.database_models import League, Team, Match, ScrapingJob, SystemLog

logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self, db):
        self.db = db
        self.ua = UserAgent()
        self.scrapers = {
            'understat': UnderstatScraper(db),
            'sofascore': SofascoreScraper(db),
            'flashscore': FlashscoreScraper(db)
        }
        
        # Desteklenen ligler - Dinamik olarak genişletilebilir
        self.supported_leagues = {
            'EPL': {'name': 'Premier League', 'country': 'England', 'priority': 1},
            'LALIGA': {'name': 'La Liga', 'country': 'Spain', 'priority': 1},
            'SERIEA': {'name': 'Serie A', 'country': 'Italy', 'priority': 1},
            'BUNDESLIGA': {'name': 'Bundesliga', 'country': 'Germany', 'priority': 1},
            'LIGUE1': {'name': 'Ligue 1', 'country': 'France', 'priority': 1},
            'UCL': {'name': 'UEFA Champions League', 'country': 'Europe', 'priority': 1},
            'UEL': {'name': 'UEFA Europa League', 'country': 'Europe', 'priority': 2},
            'EREDIVISIE': {'name': 'Eredivisie', 'country': 'Netherlands', 'priority': 2},
            'LIGANOS': {'name': 'Liga NOS', 'country': 'Portugal', 'priority': 2},
            'SUPERLIG': {'name': 'Süper Lig', 'country': 'Turkey', 'priority': 2},
            'CHAMPIONSHIP': {'name': 'Championship', 'country': 'England', 'priority': 2},
            'LIGA2': {'name': 'La Liga 2', 'country': 'Spain', 'priority': 3},
            'SERIEB': {'name': 'Serie B', 'country': 'Italy', 'priority': 3},
            'BUNDESLIGA2': {'name': '2. Bundesliga', 'country': 'Germany', 'priority': 3},
            'LIGUE2': {'name': 'Ligue 2', 'country': 'France', 'priority': 3},
            'MLS': {'name': 'Major League Soccer', 'country': 'USA', 'priority': 2},
            'BRASILEIRAO': {'name': 'Brasileirão', 'country': 'Brazil', 'priority': 2},
            'PRIMERA': {'name': 'Primera División', 'country': 'Argentina', 'priority': 2},
            'LIGA_MX': {'name': 'Liga MX', 'country': 'Mexico', 'priority': 2},
            'ALLSVENSKAN': {'name': 'Allsvenskan', 'country': 'Sweden', 'priority': 3},
            'SUPERLIGA': {'name': 'Superliga', 'country': 'Denmark', 'priority': 3},
            'JUPILER': {'name': 'Jupiler Pro League', 'country': 'Belgium', 'priority': 3},
            'AUSTRIA': {'name': 'Austrian Bundesliga', 'country': 'Austria', 'priority': 3},
            'CZECH': {'name': 'Czech First League', 'country': 'Czech Republic', 'priority': 3},
            'POLAND': {'name': 'Ekstraklasa', 'country': 'Poland', 'priority': 3},
            'ROMANIA': {'name': 'Liga I', 'country': 'Romania', 'priority': 3},
            'GREECE': {'name': 'Super League', 'country': 'Greece', 'priority': 3},
            'SCOTLAND': {'name': 'Scottish Premiership', 'country': 'Scotland', 'priority': 3},
            'NORWAY': {'name': 'Eliteserien', 'country': 'Norway', 'priority': 3},
            'SWITZERLAND': {'name': 'Super League', 'country': 'Switzerland', 'priority': 3},
            'CROATIA': {'name': 'HNL', 'country': 'Croatia', 'priority': 3},
            'SERBIA': {'name': 'SuperLiga', 'country': 'Serbia', 'priority': 3},
            'UKRAINE': {'name': 'Premier League', 'country': 'Ukraine', 'priority': 3},
            'BULGARIA': {'name': 'First League', 'country': 'Bulgaria', 'priority': 3},
            'JLEAGUE': {'name': 'J-League', 'country': 'Japan', 'priority': 3},
            'KLEAGUE': {'name': 'K-League', 'country': 'South Korea', 'priority': 3},
            'CSL': {'name': 'Chinese Super League', 'country': 'China', 'priority': 3},
            'AUSTRALIAN': {'name': 'A-League', 'country': 'Australia', 'priority': 3},
            'CHILE': {'name': 'Primera División', 'country': 'Chile', 'priority': 3},
            'COLOMBIA': {'name': 'Liga BetPlay', 'country': 'Colombia', 'priority': 3},
            'ECUADOR': {'name': 'Serie A', 'country': 'Ecuador', 'priority': 3},
            'PERU': {'name': 'Liga 1', 'country': 'Peru', 'priority': 3},
            'URUGUAY': {'name': 'Primera División', 'country': 'Uruguay', 'priority': 3},
            'VENEZUELA': {'name': 'Primera División', 'country': 'Venezuela', 'priority': 3},
            'BOLIVIA': {'name': 'Liga de Fútbol Profesional', 'country': 'Bolivia', 'priority': 3},
            'PARAGUAY': {'name': 'Primera División', 'country': 'Paraguay', 'priority': 3},
            'MOROCCO': {'name': 'Botola', 'country': 'Morocco', 'priority': 3},
            'EGYPT': {'name': 'Premier League', 'country': 'Egypt', 'priority': 3},
            'SOUTH_AFRICA': {'name': 'Premier Division', 'country': 'South Africa', 'priority': 3},
            'TUNISIA': {'name': 'Ligue Professionnelle 1', 'country': 'Tunisia', 'priority': 3},
            'ALGERIA': {'name': 'Ligue Professionnelle 1', 'country': 'Algeria', 'priority': 3},
            'GHANA': {'name': 'Premier League', 'country': 'Ghana', 'priority': 3},
            'NIGERIA': {'name': 'Professional Football League', 'country': 'Nigeria', 'priority': 3},
            'INDIA': {'name': 'Indian Super League', 'country': 'India', 'priority': 3},
            'THAILAND': {'name': 'Thai League 1', 'country': 'Thailand', 'priority': 3},
            'MALAYSIA': {'name': 'Super League', 'country': 'Malaysia', 'priority': 3},
            'SINGAPORE': {'name': 'Premier League', 'country': 'Singapore', 'priority': 3},
            'INDONESIA': {'name': 'Liga 1', 'country': 'Indonesia', 'priority': 3}
        }
        
        self.proxy_list = []
        self.current_proxy_index = 0
        
    async def initialize_leagues(self):
        """Desteklenen ligleri veritabanına kaydet"""
        try:
            for league_code, info in self.supported_leagues.items():
                existing_league = await self.db.leagues.find_one({"league_code": league_code})
                
                if not existing_league:
                    league = League(
                        name=info['name'],
                        country=info['country'],
                        season="2024-25",
                        league_code=league_code,
                        source_urls={},
                        active=True
                    )
                    
                    await self.db.leagues.insert_one(league.dict())
                    logger.info(f"Liga eklendi: {info['name']} ({info['country']})")
            
            logger.info(f"Toplam {len(self.supported_leagues)} liga destekleniyor")
            
        except Exception as e:
            logger.error(f"Ligler başlatılırken hata: {e}")
            await self.log_error("scraper_manager", f"Liga başlatma hatası: {e}")
    
    async def run_scraping_job(self, league_ids: Optional[List[str]] = None):
        """Ana scraping işlemini çalıştır"""
        job = ScrapingJob(
            job_type="full_scrape",
            source="all",
            league_ids=league_ids or [],
            status="running",
            started_at=datetime.utcnow()
        )
        
        job_id = await self.db.scraping_jobs.insert_one(job.dict())
        
        try:
            # 1. Ligleri başlat
            await self.initialize_leagues()
            
            # 2. Eğer league_ids belirtilmemişse, priorite sırasına göre al
            if not league_ids:
                leagues = await self.db.leagues.find({"active": True}).to_list(1000)
                # Priorite sırasına göre sırala
                leagues.sort(key=lambda x: self.supported_leagues.get(x['league_code'], {}).get('priority', 999))
                league_ids = [league['id'] for league in leagues[:20]]  # İlk 20 ligden başla
            
            # 3. Her scraper için veri toplama
            total_scraped = 0
            errors = []
            
            for scraper_name, scraper in self.scrapers.items():
                try:
                    logger.info(f"🔄 {scraper_name} ile veri toplama başladı...")
                    
                    # Teams ve matches'i scrape et
                    teams_scraped = await scraper.scrape_teams(league_ids)
                    matches_scraped = await scraper.scrape_matches(league_ids)
                    
                    total_scraped += teams_scraped + matches_scraped
                    
                    logger.info(f"✅ {scraper_name}: {teams_scraped} takım, {matches_scraped} maç")
                    
                    # Scrapers arasında bekleme
                    await asyncio.sleep(random.uniform(5, 15))
                    
                except Exception as e:
                    error_msg = f"{scraper_name} scraper hatası: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    await self.log_error("scraper_manager", error_msg)
            
            # 4. Job'u tamamla
            await self.db.scraping_jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "completed",
                        "items_scraped": total_scraped,
                        "errors": errors,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"🎉 Scraping tamamlandı: {total_scraped} item, {len(errors)} hata")
            
        except Exception as e:
            logger.error(f"Scraping job hatası: {e}")
            await self.db.scraping_jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "errors": [str(e)],
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            await self.log_error("scraper_manager", f"Scraping job hatası: {e}")
    
    async def get_proxy(self):
        """Proxy rotasyonu"""
        if not self.proxy_list:
            return None
            
        if self.current_proxy_index >= len(self.proxy_list):
            self.current_proxy_index = 0
            
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index += 1
        
        return proxy
    
    async def get_session(self, use_proxy: bool = True):
        """HTTP session oluştur"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        if use_proxy:
            proxy = await self.get_proxy()
            if proxy:
                return aiohttp.ClientSession(
                    headers=headers,
                    connector=connector,
                    timeout=timeout,
                    trust_env=True,
                    proxy=proxy
                )
        
        return aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout,
            trust_env=True
        )
    
    async def safe_request(self, url: str, max_retries: int = 3):
        """Güvenli HTTP request"""
        for attempt in range(max_retries):
            try:
                async with await self.get_session() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.text()
                        elif response.status == 429:
                            # Rate limit - bekle ve tekrar dene
                            await asyncio.sleep(random.uniform(10, 30))
                            continue
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
            except Exception as e:
                logger.error(f"Request attempt {attempt + 1} failed for {url}: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(2, 8))
                else:
                    raise e
        
        return None
    
    async def log_error(self, module: str, message: str, details: Dict[str, Any] = None):
        """Hata logla"""
        log_entry = SystemLog(
            level="ERROR",
            module=module,
            message=message,
            details=details or {}
        )
        
        await self.db.system_logs.insert_one(log_entry.dict())
        logger.error(f"[{module}] {message}")
    
    async def log_info(self, module: str, message: str, details: Dict[str, Any] = None):
        """Bilgi logla"""
        log_entry = SystemLog(
            level="INFO",
            module=module,
            message=message,
            details=details or {}
        )
        
        await self.db.system_logs.insert_one(log_entry.dict())
        logger.info(f"[{module}] {message}")
    
    async def get_scraping_stats(self):
        """Scraping istatistikleri"""
        try:
            # Son 24 saatteki joblar
            since = datetime.utcnow() - timedelta(hours=24)
            
            jobs = await self.db.scraping_jobs.find({
                "created_at": {"$gte": since}
            }).to_list(1000)
            
            stats = {
                "total_jobs": len(jobs),
                "completed_jobs": len([j for j in jobs if j["status"] == "completed"]),
                "failed_jobs": len([j for j in jobs if j["status"] == "failed"]),
                "running_jobs": len([j for j in jobs if j["status"] == "running"]),
                "total_items_scraped": sum(j.get("items_scraped", 0) for j in jobs),
                "timestamp": datetime.utcnow()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Scraping istatistikleri alınamadı: {e}")
            return {}