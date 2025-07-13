import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import aiohttp
from fake_useragent import UserAgent

from models.database_models import League, Team, Match, TeamStats

logger = logging.getLogger(__name__)

class SofascoreScraper:
    def __init__(self, db):
        self.db = db
        self.base_url = "https://api.sofascore.com/api/v1"
        self.headers = {
            'User-Agent': UserAgent().chrome,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.sofascore.com/',
            'Origin': 'https://www.sofascore.com'
        }
        
        # SofaScore tournament IDs
        self.tournament_mapping = {
            'EPL': 17,
            'LALIGA': 8,
            'SERIEA': 23,
            'BUNDESLIGA': 35,
            'LIGUE1': 34,
            'UCL': 7,
            'UEL': 679,
            'SUPERLIG': 52,
            'EREDIVISIE': 37,
            'LIGANOS': 238,
            'CHAMPIONSHIP': 18,
            'MLS': 242,
            'BRASILEIRAO': 325,
            'PRIMERA': 155,
            'LIGA_MX': 352
        }
    
    async def scrape_teams(self, league_ids: List[str]) -> int:
        """Takım verilerini çek"""
        teams_scraped = 0
        
        try:
            leagues = await self.db.leagues.find({"id": {"$in": league_ids}}).to_list(1000)
            
            for league in leagues:
                league_code = league['league_code']
                
                if league_code not in self.tournament_mapping:
                    logger.warning(f"SofaScore'da desteklenmeyen lig: {league_code}")
                    continue
                
                tournament_id = self.tournament_mapping[league_code]
                season_id = await self._get_current_season_id(tournament_id)
                
                if not season_id:
                    logger.warning(f"SofaScore'da sezon bulunamadı: {league_code}")
                    continue
                
                try:
                    # Takım verilerini çek
                    teams = await self._fetch_teams_data(tournament_id, season_id)
                    
                    for team_data in teams:
                        # Takım var mı kontrol et
                        existing_team = await self.db.teams.find_one({
                            "league_id": league['id'],
                            "external_ids.sofascore": str(team_data['id'])
                        })
                        
                        if not existing_team:
                            team = Team(
                                name=team_data['name'],
                                league_id=league['id'],
                                country=league['country'],
                                external_ids={"sofascore": str(team_data['id'])},
                                alternative_names=team_data.get('alternative_names', [])
                            )
                            
                            await self.db.teams.insert_one(team.dict())
                            teams_scraped += 1
                            logger.info(f"Takım eklendi (SofaScore): {team_data['name']}")
                        else:
                            # Mevcut takımı güncelle
                            await self.db.teams.update_one(
                                {"_id": existing_team["_id"]},
                                {
                                    "$set": {
                                        "external_ids.sofascore": str(team_data['id']),
                                        "updated_at": datetime.utcnow()
                                    }
                                }
                            )
                    
                    await asyncio.sleep(3)  # API rate limit
                    
                except Exception as e:
                    logger.error(f"SofaScore takım çekme hatası ({league_code}): {e}")
                    continue
        
        except Exception as e:
            logger.error(f"SofaScore takım scraping hatası: {e}")
        
        return teams_scraped
    
    async def scrape_matches(self, league_ids: List[str]) -> int:
        """Maç verilerini çek"""
        matches_scraped = 0
        
        try:
            leagues = await self.db.leagues.find({"id": {"$in": league_ids}}).to_list(1000)
            
            for league in leagues:
                league_code = league['league_code']
                
                if league_code not in self.tournament_mapping:
                    continue
                
                tournament_id = self.tournament_mapping[league_code]
                season_id = await self._get_current_season_id(tournament_id)
                
                if not season_id:
                    continue
                
                try:
                    # Maç verilerini çek
                    matches = await self._fetch_matches_data(tournament_id, season_id)
                    
                    for match_data in matches:
                        # Takımları bul
                        home_team = await self.db.teams.find_one({
                            "league_id": league['id'],
                            "external_ids.sofascore": str(match_data['home_team_id'])
                        })
                        
                        away_team = await self.db.teams.find_one({
                            "league_id": league['id'],
                            "external_ids.sofascore": str(match_data['away_team_id'])
                        })
                        
                        if not home_team or not away_team:
                            logger.warning(f"Takım bulunamadı (SofaScore): {match_data}")
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
                                home_shots=match_data.get('home_shots'),
                                away_shots=match_data.get('away_shots'),
                                home_shots_on_target=match_data.get('home_shots_on_target'),
                                away_shots_on_target=match_data.get('away_shots_on_target'),
                                home_corners=match_data.get('home_corners'),
                                away_corners=match_data.get('away_corners'),
                                status=match_data.get('status', 'scheduled'),
                                external_ids={"sofascore": str(match_data['id'])}
                            )
                            
                            await self.db.matches.insert_one(match.dict())
                            matches_scraped += 1
                            logger.info(f"Maç eklendi (SofaScore): {home_team['name']} vs {away_team['name']}")
                        else:
                            # Mevcut maçı güncelle
                            update_data = {
                                "home_score": match_data.get('home_score'),
                                "away_score": match_data.get('away_score'),
                                "home_shots": match_data.get('home_shots'),
                                "away_shots": match_data.get('away_shots'),
                                "home_shots_on_target": match_data.get('home_shots_on_target'),
                                "away_shots_on_target": match_data.get('away_shots_on_target'),
                                "home_corners": match_data.get('home_corners'),
                                "away_corners": match_data.get('away_corners'),
                                "status": match_data.get('status', 'scheduled'),
                                "updated_at": datetime.utcnow()
                            }
                            
                            await self.db.matches.update_one(
                                {"_id": existing_match["_id"]},
                                {"$set": update_data}
                            )
                    
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"SofaScore maç çekme hatası ({league_code}): {e}")
                    continue
        
        except Exception as e:
            logger.error(f"SofaScore maç scraping hatası: {e}")
        
        return matches_scraped
    
    async def _get_current_season_id(self, tournament_id: int) -> Optional[int]:
        """Mevcut sezon ID'sini al"""
        try:
            url = f"{self.base_url}/tournament/{tournament_id}/seasons"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        seasons = data.get('seasons', [])
                        
                        # En son sezonu al
                        if seasons:
                            return seasons[0]['id']
                    else:
                        logger.error(f"SofaScore seasons request failed: {response.status}")
        
        except Exception as e:
            logger.error(f"SofaScore season ID fetch hatası: {e}")
        
        return None
    
    async def _fetch_teams_data(self, tournament_id: int, season_id: int) -> List[Dict[str, Any]]:
        """Takım verilerini API'den çek"""
        try:
            url = f"{self.base_url}/tournament/{tournament_id}/season/{season_id}/standings/total"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        standings = data.get('standings', [])
                        
                        teams = []
                        for group in standings:
                            for row in group.get('rows', []):
                                team = row.get('team', {})
                                teams.append({
                                    'id': team.get('id'),
                                    'name': team.get('name'),
                                    'alternative_names': [team.get('name'), team.get('shortName', '')]
                                })
                        
                        return teams
                    else:
                        logger.error(f"SofaScore teams request failed: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"SofaScore teams fetch hatası: {e}")
            return []
    
    async def _fetch_matches_data(self, tournament_id: int, season_id: int) -> List[Dict[str, Any]]:
        """Maç verilerini API'den çek"""
        matches = []
        
        try:
            # Son 30 gün ve gelecek 30 gün
            start_date = datetime.utcnow() - timedelta(days=30)
            end_date = datetime.utcnow() + timedelta(days=30)
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                url = f"{self.base_url}/tournament/{tournament_id}/season/{season_id}/events/round/1"
                
                async with aiohttp.ClientSession(headers=self.headers) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            events = data.get('events', [])
                            
                            for event in events:
                                if event.get('tournament', {}).get('id') == tournament_id:
                                    match_data = self._parse_match_data(event)
                                    if match_data:
                                        matches.append(match_data)
                        
                        await asyncio.sleep(1)  # Rate limiting
                
                current_date += timedelta(days=1)
        
        except Exception as e:
            logger.error(f"SofaScore matches fetch hatası: {e}")
        
        return matches
    
    def _parse_match_data(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Maç verisini parse et"""
        try:
            return {
                'id': event.get('id'),
                'home_team_id': event.get('homeTeam', {}).get('id'),
                'away_team_id': event.get('awayTeam', {}).get('id'),
                'match_date': datetime.fromtimestamp(event.get('startTimestamp', 0)),
                'home_score': event.get('homeScore', {}).get('current'),
                'away_score': event.get('awayScore', {}).get('current'),
                'status': event.get('status', {}).get('type', 'scheduled'),
                'home_shots': event.get('statistics', {}).get('homeShots'),
                'away_shots': event.get('statistics', {}).get('awayShots'),
                'home_shots_on_target': event.get('statistics', {}).get('homeShotsOnTarget'),
                'away_shots_on_target': event.get('statistics', {}).get('awayShotsOnTarget'),
                'home_corners': event.get('statistics', {}).get('homeCorners'),
                'away_corners': event.get('statistics', {}).get('awayCorners')
            }
        except Exception as e:
            logger.error(f"SofaScore match parse hatası: {e}")
            return None