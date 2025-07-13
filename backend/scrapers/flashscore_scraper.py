import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc

from models.database_models import League, Team, Match

logger = logging.getLogger(__name__)

class FlashscoreScraper:
    def __init__(self, db):
        self.db = db
        self.base_url = "https://www.flashscore.com"
        self.driver = None
        
        # Flashscore league URLs
        self.league_urls = {
            'EPL': '/football/england/premier-league/',
            'LALIGA': '/football/spain/laliga/',
            'SERIEA': '/football/italy/serie-a/',
            'BUNDESLIGA': '/football/germany/bundesliga/',
            'LIGUE1': '/football/france/ligue-1/',
            'UCL': '/football/europe/champions-league/',
            'UEL': '/football/europe/europa-league/',
            'SUPERLIG': '/football/turkey/super-lig/',
            'EREDIVISIE': '/football/netherlands/eredivisie/',
            'LIGANOS': '/football/portugal/primeira-liga/',
            'CHAMPIONSHIP': '/football/england/championship/',
            'MLS': '/football/usa/mls/',
            'BRASILEIRAO': '/football/brazil/serie-a/',
            'PRIMERA': '/football/argentina/primera-division/',
            'LIGA_MX': '/football/mexico/liga-mx/'
        }
    
    async def initialize_driver(self):
        """WebDriver'ı başlat"""
        if self.driver:
            return
        
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Undetected Chrome kullan
            self.driver = uc.Chrome(options=options)
            self.driver.implicitly_wait(10)
            
            logger.info("Flashscore WebDriver başlatıldı")
            
        except Exception as e:
            logger.error(f"Flashscore WebDriver başlatılamadı: {e}")
            raise e
    
    async def close_driver(self):
        """WebDriver'ı kapat"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Flashscore WebDriver kapatıldı")
            except Exception as e:
                logger.error(f"Flashscore WebDriver kapatılamadı: {e}")
    
    async def scrape_teams(self, league_ids: List[str]) -> int:
        """Takım verilerini çek"""
        teams_scraped = 0
        
        try:
            await self.initialize_driver()
            leagues = await self.db.leagues.find({"id": {"$in": league_ids}}).to_list(1000)
            
            for league in leagues:
                league_code = league['league_code']
                
                if league_code not in self.league_urls:
                    logger.warning(f"Flashscore'da desteklenmeyen lig: {league_code}")
                    continue
                
                try:
                    # Takım verilerini çek
                    teams = await self._fetch_teams_data(league_code)
                    
                    for team_data in teams:
                        # Takım var mı kontrol et
                        existing_team = await self.db.teams.find_one({
                            "league_id": league['id'],
                            "name": team_data['name']
                        })
                        
                        if not existing_team:
                            team = Team(
                                name=team_data['name'],
                                league_id=league['id'],
                                country=league['country'],
                                external_ids={"flashscore": team_data.get('id', '')},
                                alternative_names=team_data.get('alternative_names', [])
                            )
                            
                            await self.db.teams.insert_one(team.dict())
                            teams_scraped += 1
                            logger.info(f"Takım eklendi (Flashscore): {team_data['name']}")
                        else:
                            # Mevcut takımı güncelle
                            await self.db.teams.update_one(
                                {"_id": existing_team["_id"]},
                                {
                                    "$set": {
                                        "updated_at": datetime.utcnow()
                                    }
                                }
                            )
                    
                    await asyncio.sleep(5)  # Cloudflare bypass için bekleme
                    
                except Exception as e:
                    logger.error(f"Flashscore takım çekme hatası ({league_code}): {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Flashscore takım scraping hatası: {e}")
        finally:
            await self.close_driver()
        
        return teams_scraped
    
    async def scrape_matches(self, league_ids: List[str]) -> int:
        """Maç verilerini çek"""
        matches_scraped = 0
        
        try:
            await self.initialize_driver()
            leagues = await self.db.leagues.find({"id": {"$in": league_ids}}).to_list(1000)
            
            for league in leagues:
                league_code = league['league_code']
                
                if league_code not in self.league_urls:
                    continue
                
                try:
                    # Maç verilerini çek
                    matches = await self._fetch_matches_data(league_code)
                    
                    for match_data in matches:
                        # Takımları bul (isim benzerliği ile)
                        home_team = await self._find_team_by_name(
                            league['id'], 
                            match_data['home_team_name']
                        )
                        
                        away_team = await self._find_team_by_name(
                            league['id'], 
                            match_data['away_team_name']
                        )
                        
                        if not home_team or not away_team:
                            logger.warning(f"Takım bulunamadı (Flashscore): {match_data}")
                            continue
                        
                        # Maç var mı kontrol et
                        existing_match = await self.db.matches.find_one({
                            "league_id": league['id'],
                            "home_team_id": home_team['id'],
                            "away_team_id": away_team['id'],
                            "match_date": match_data['match_date']
                        })
                        
                        if not existing_match:
                            match = Match(
                                league_id=league['id'],
                                home_team_id=home_team['id'],
                                away_team_id=away_team['id'],
                                match_date=match_data['match_date'],
                                season=league['season'],
                                home_score=match_data.get('home_score'),
                                away_score=match_data.get('away_score'),
                                odds_1x2=match_data.get('odds_1x2'),
                                odds_over_under=match_data.get('odds_over_under'),
                                status=match_data.get('status', 'scheduled'),
                                external_ids={"flashscore": match_data.get('id', '')}
                            )
                            
                            await self.db.matches.insert_one(match.dict())
                            matches_scraped += 1
                            logger.info(f"Maç eklendi (Flashscore): {home_team['name']} vs {away_team['name']}")
                        else:
                            # Mevcut maçı güncelle
                            update_data = {
                                "home_score": match_data.get('home_score'),
                                "away_score": match_data.get('away_score'),
                                "odds_1x2": match_data.get('odds_1x2'),
                                "odds_over_under": match_data.get('odds_over_under'),
                                "status": match_data.get('status', 'scheduled'),
                                "updated_at": datetime.utcnow()
                            }
                            
                            await self.db.matches.update_one(
                                {"_id": existing_match["_id"]},
                                {"$set": update_data}
                            )
                    
                    await asyncio.sleep(10)  # Cloudflare bypass için daha uzun bekleme
                    
                except Exception as e:
                    logger.error(f"Flashscore maç çekme hatası ({league_code}): {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Flashscore maç scraping hatası: {e}")
        finally:
            await self.close_driver()
        
        return matches_scraped
    
    async def _fetch_teams_data(self, league_code: str) -> List[Dict[str, Any]]:
        """Takım verilerini çek"""
        teams = []
        
        try:
            url = f"{self.base_url}{self.league_urls[league_code]}standings/"
            self.driver.get(url)
            
            # Cloudflare bypass bekle
            await asyncio.sleep(10)
            
            # Takım isimlerini çek
            team_elements = self.driver.find_elements(By.CSS_SELECTOR, ".standings__row .team")
            
            for element in team_elements:
                try:
                    team_name = element.text.strip()
                    if team_name:
                        teams.append({
                            'name': team_name,
                            'alternative_names': [team_name]
                        })
                except Exception as e:
                    logger.warning(f"Takım elementi parse edilemedi: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Flashscore teams fetch hatası ({league_code}): {e}")
        
        return teams
    
    async def _fetch_matches_data(self, league_code: str) -> List[Dict[str, Any]]:
        """Maç verilerini çek"""
        matches = []
        
        try:
            url = f"{self.base_url}{self.league_urls[league_code]}"
            self.driver.get(url)
            
            # Cloudflare bypass bekle
            await asyncio.sleep(10)
            
            # Maç elementlerini çek
            match_elements = self.driver.find_elements(By.CSS_SELECTOR, ".event__match")
            
            for element in match_elements:
                try:
                    match_data = self._parse_match_element(element)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    logger.warning(f"Maç elementi parse edilemedi: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Flashscore matches fetch hatası ({league_code}): {e}")
        
        return matches
    
    def _parse_match_element(self, element) -> Optional[Dict[str, Any]]:
        """Maç elementini parse et"""
        try:
            # Takım isimlerini çek
            home_team_elem = element.find_element(By.CSS_SELECTOR, ".event__participant--home")
            away_team_elem = element.find_element(By.CSS_SELECTOR, ".event__participant--away")
            
            home_team_name = home_team_elem.text.strip()
            away_team_name = away_team_elem.text.strip()
            
            # Maç tarihini çek
            time_elem = element.find_element(By.CSS_SELECTOR, ".event__time")
            time_text = time_elem.text.strip()
            
            # Skor bilgisi
            score_elem = element.find_element(By.CSS_SELECTOR, ".event__score")
            score_text = score_elem.text.strip()
            
            home_score = None
            away_score = None
            
            if score_text and ':' in score_text:
                scores = score_text.split(':')
                if len(scores) == 2:
                    home_score = int(scores[0].strip())
                    away_score = int(scores[1].strip())
            
            return {
                'home_team_name': home_team_name,
                'away_team_name': away_team_name,
                'match_date': self._parse_match_time(time_text),
                'home_score': home_score,
                'away_score': away_score,
                'status': 'finished' if home_score is not None else 'scheduled'
            }
            
        except Exception as e:
            logger.error(f"Flashscore match parse hatası: {e}")
            return None
    
    def _parse_match_time(self, time_text: str) -> datetime:
        """Maç zamanını parse et"""
        try:
            # Basit zaman parsing (geliştirilmesi gerekebilir)
            if ':' in time_text:
                # Bugünkü maçlar için
                return datetime.utcnow()
            else:
                # Geçmiş maçlar için
                return datetime.utcnow() - timedelta(days=1)
        except Exception:
            return datetime.utcnow()
    
    async def _find_team_by_name(self, league_id: str, team_name: str) -> Optional[Dict[str, Any]]:
        """Takım ismini benzerlik ile bul"""
        try:
            teams = await self.db.teams.find({"league_id": league_id}).to_list(1000)
            
            for team in teams:
                if team['name'].lower() == team_name.lower():
                    return team
                
                # Alternative names'de de ara
                for alt_name in team.get('alternative_names', []):
                    if alt_name.lower() == team_name.lower():
                        return team
            
            return None
            
        except Exception as e:
            logger.error(f"Takım bulma hatası: {e}")
            return None