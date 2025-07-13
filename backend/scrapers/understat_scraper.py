import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
from bs4 import BeautifulSoup
import aiohttp
from fuzzywuzzy import fuzz

from models.database_models import League, Team, Match, TeamStats

logger = logging.getLogger(__name__)

class UnderstatScraper:
    def __init__(self, db):
        self.db = db
        self.base_url = "https://understat.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Understat'daki liga mapping
        self.league_mapping = {
            'EPL': 'epl',
            'LALIGA': 'la_liga',
            'SERIEA': 'serie_a',
            'BUNDESLIGA': 'bundesliga',
            'LIGUE1': 'ligue_1',
            'SUPERLIG': 'rfpl'  # Rus ligi yerine Türk ligi için sonra düzenlenebilir
        }
    
    async def scrape_teams(self, league_ids: List[str]) -> int:
        """Takım verilerini çek"""
        teams_scraped = 0
        
        try:
            # League ID'leri league_code'lara çevir
            leagues = await self.db.leagues.find({"id": {"$in": league_ids}}).to_list(1000)
            
            for league in leagues:
                league_code = league['league_code']
                
                if league_code not in self.league_mapping:
                    logger.warning(f"Understat'da desteklenmeyen lig: {league_code}")
                    continue
                
                understat_league = self.league_mapping[league_code]
                
                try:
                    # Takım verilerini çek
                    teams = await self._fetch_teams_data(understat_league)
                    
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
                                external_ids={"understat": str(team_data['id'])},
                                alternative_names=team_data.get('alternative_names', [])
                            )
                            
                            await self.db.teams.insert_one(team.dict())
                            teams_scraped += 1
                            logger.info(f"Takım eklendi: {team_data['name']}")
                        else:
                            # Mevcut takımı güncelle
                            await self.db.teams.update_one(
                                {"_id": existing_team["_id"]},
                                {
                                    "$set": {
                                        "external_ids.understat": str(team_data['id']),
                                        "updated_at": datetime.utcnow()
                                    }
                                }
                            )
                    
                    # Takım istatistiklerini güncelle
                    await self._update_team_stats(league['id'], understat_league)
                    
                    # Request'ler arası bekleme
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Understat takım çekme hatası ({league_code}): {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Understat takım scraping hatası: {e}")
        
        return teams_scraped
    
    async def scrape_matches(self, league_ids: List[str]) -> int:
        """Maç verilerini çek"""
        matches_scraped = 0
        
        try:
            leagues = await self.db.leagues.find({"id": {"$in": league_ids}}).to_list(1000)
            
            for league in leagues:
                league_code = league['league_code']
                
                if league_code not in self.league_mapping:
                    continue
                
                understat_league = self.league_mapping[league_code]
                
                try:
                    # Maç verilerini çek
                    matches = await self._fetch_matches_data(understat_league)
                    
                    for match_data in matches:
                        # Takımları bul
                        home_team = await self.db.teams.find_one({
                            "league_id": league['id'],
                            "external_ids.understat": str(match_data['home_team_id'])
                        })
                        
                        away_team = await self.db.teams.find_one({
                            "league_id": league['id'],
                            "external_ids.understat": str(match_data['away_team_id'])
                        })
                        
                        if not home_team or not away_team:
                            logger.warning(f"Takım bulunamadı: {match_data}")
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
                                gameweek=match_data.get('gameweek'),
                                home_score=match_data.get('home_score'),
                                away_score=match_data.get('away_score'),
                                home_xg=match_data.get('home_xg'),
                                away_xg=match_data.get('away_xg'),
                                status=match_data.get('status', 'scheduled'),
                                external_ids={"understat": str(match_data['id'])}
                            )
                            
                            await self.db.matches.insert_one(match.dict())
                            matches_scraped += 1
                            logger.info(f"Maç eklendi: {home_team['name']} vs {away_team['name']}")
                        else:
                            # Mevcut maçı güncelle
                            update_data = {
                                "home_score": match_data.get('home_score'),
                                "away_score": match_data.get('away_score'),
                                "home_xg": match_data.get('home_xg'),
                                "away_xg": match_data.get('away_xg'),
                                "status": match_data.get('status', 'scheduled'),
                                "updated_at": datetime.utcnow()
                            }
                            
                            await self.db.matches.update_one(
                                {"_id": existing_match["_id"]},
                                {"$set": update_data}
                            )
                    
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Understat maç çekme hatası ({league_code}): {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Understat maç scraping hatası: {e}")
        
        return matches_scraped
    
    async def _fetch_teams_data(self, league: str) -> List[Dict[str, Any]]:
        """Takım verilerini API'den çek"""
        try:
            url = f"{self.base_url}/league/{league}"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Teams data'sını JavaScript'ten çıkar
                        teams_data = self._extract_teams_from_html(html)
                        return teams_data
                    else:
                        logger.error(f"Understat teams request failed: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Understat teams fetch hatası: {e}")
            return []
    
    async def _fetch_matches_data(self, league: str) -> List[Dict[str, Any]]:
        """Maç verilerini API'den çek"""
        try:
            url = f"{self.base_url}/league/{league}/2024"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Matches data'sını JavaScript'ten çıkar
                        matches_data = self._extract_matches_from_html(html)
                        return matches_data
                    else:
                        logger.error(f"Understat matches request failed: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Understat matches fetch hatası: {e}")
            return []
    
    def _extract_teams_from_html(self, html: str) -> List[Dict[str, Any]]:
        """HTML'den takım verilerini çıkar"""
        teams = []
        
        try:
            # JavaScript'teki teamsData'yı bul
            pattern = r'var teamsData = JSON\.parse\(\'(.*?)\'\);'
            match = re.search(pattern, html)
            
            if match:
                teams_json = match.group(1)
                teams_json = teams_json.replace('\\', '')
                teams_data = json.loads(teams_json)
                
                for team_id, team_info in teams_data.items():
                    teams.append({
                        'id': team_id,
                        'name': team_info['title'],
                        'alternative_names': [team_info['title']]
                    })
            
            # Eğer JavaScript'ten çıkaramazsa, HTML'den table parsing
            if not teams:
                soup = BeautifulSoup(html, 'html.parser')
                team_links = soup.find_all('a', href=re.compile(r'/team/'))
                
                for link in team_links:
                    team_name = link.text.strip()
                    if team_name and team_name not in [t['name'] for t in teams]:
                        teams.append({
                            'id': len(teams) + 1,
                            'name': team_name,
                            'alternative_names': [team_name]
                        })
        
        except Exception as e:
            logger.error(f"Understat teams extract hatası: {e}")
        
        return teams
    
    def _extract_matches_from_html(self, html: str) -> List[Dict[str, Any]]:
        """HTML'den maç verilerini çıkar"""
        matches = []
        
        try:
            # JavaScript'teki datesData'yı bul
            pattern = r'var datesData = JSON\.parse\(\'(.*?)\'\);'
            match = re.search(pattern, html)
            
            if match:
                dates_json = match.group(1)
                dates_json = dates_json.replace('\\', '')
                dates_data = json.loads(dates_json)
                
                for date_str, date_matches in dates_data.items():
                    for match_data in date_matches:
                        matches.append({
                            'id': match_data['id'],
                            'home_team_id': match_data['h']['id'],
                            'away_team_id': match_data['a']['id'],
                            'match_date': datetime.strptime(date_str, '%Y-%m-%d'),
                            'home_score': match_data.get('goals', {}).get('h'),
                            'away_score': match_data.get('goals', {}).get('a'),
                            'home_xg': float(match_data.get('xG', {}).get('h', 0)),
                            'away_xg': float(match_data.get('xG', {}).get('a', 0)),
                            'status': 'finished' if match_data.get('isResult') else 'scheduled'
                        })
        
        except Exception as e:
            logger.error(f"Understat matches extract hatası: {e}")
        
        return matches
    
    async def _update_team_stats(self, league_id: str, understat_league: str):
        """Takım istatistiklerini güncelle"""
        try:
            # Bu kısım daha detaylı implementasyon gerektirir
            # Şimdilik basit bir placeholder
            logger.info(f"Takım istatistikleri güncelleniyor: {understat_league}")
            
        except Exception as e:
            logger.error(f"Takım istatistikleri güncelleme hatası: {e}")