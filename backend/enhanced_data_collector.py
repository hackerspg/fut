import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
import json
from models.database_models import League, Team, Match, TeamStats, Prediction

logger = logging.getLogger(__name__)

class EnhancedDataCollector:
    def __init__(self, db):
        self.db = db
        
    async def generate_realistic_data(self):
        """Gerçekçi demo verisi oluştur"""
        try:
            logger.info("🔄 Gerçekçi demo verisi oluşturuluyor...")
            
            # Premier League için detaylı veri oluştur
            epl_league = await self.db.leagues.find_one({"league_code": "EPL"})
            if not epl_league:
                return
            
            # Premier League takımları
            epl_teams = [
                {"name": "Manchester City", "city": "Manchester", "founded": 1880, "stadium": "Etihad Stadium"},
                {"name": "Arsenal", "city": "London", "founded": 1886, "stadium": "Emirates Stadium"},
                {"name": "Liverpool", "city": "Liverpool", "founded": 1892, "stadium": "Anfield"},
                {"name": "Chelsea", "city": "London", "founded": 1905, "stadium": "Stamford Bridge"},
                {"name": "Manchester United", "city": "Manchester", "founded": 1878, "stadium": "Old Trafford"},
                {"name": "Tottenham", "city": "London", "founded": 1882, "stadium": "Tottenham Hotspur Stadium"},
                {"name": "Newcastle United", "city": "Newcastle", "founded": 1892, "stadium": "St. James' Park"},
                {"name": "Brighton", "city": "Brighton", "founded": 1901, "stadium": "Amex Stadium"},
                {"name": "Fulham", "city": "London", "founded": 1879, "stadium": "Craven Cottage"},
                {"name": "Brentford", "city": "London", "founded": 1889, "stadium": "Brentford Community Stadium"},
                {"name": "Crystal Palace", "city": "London", "founded": 1905, "stadium": "Selhurst Park"},
                {"name": "Aston Villa", "city": "Birmingham", "founded": 1874, "stadium": "Villa Park"},
                {"name": "Nottingham Forest", "city": "Nottingham", "founded": 1865, "stadium": "City Ground"},
                {"name": "Luton Town", "city": "Luton", "founded": 1885, "stadium": "Kenilworth Road"},
                {"name": "Burnley", "city": "Burnley", "founded": 1882, "stadium": "Turf Moor"},
                {"name": "Sheffield United", "city": "Sheffield", "founded": 1889, "stadium": "Bramall Lane"},
                {"name": "West Ham", "city": "London", "founded": 1895, "stadium": "London Stadium"},
                {"name": "Everton", "city": "Liverpool", "founded": 1878, "stadium": "Goodison Park"},
                {"name": "Bournemouth", "city": "Bournemouth", "founded": 1899, "stadium": "Vitality Stadium"},
                {"name": "Wolves", "city": "Wolverhampton", "founded": 1877, "stadium": "Molineux Stadium"}
            ]
            
            # Takımları ekle
            team_ids = []
            for team_data in epl_teams:
                existing_team = await self.db.teams.find_one({
                    "league_id": epl_league['id'],
                    "name": team_data['name']
                })
                
                if not existing_team:
                    from models.database_models import Team
                    team = Team(
                        name=team_data['name'],
                        league_id=epl_league['id'],
                        country="England",
                        alternative_names=[team_data['name']],
                        external_ids={"demo": f"team_{len(team_ids)}"}
                    )
                    result = await self.db.teams.insert_one(team.dict())
                    team_ids.append(team.id)
                else:
                    team_ids.append(existing_team['id'])
            
            # Son 5 hafta ve gelecek 2 hafta maçları oluştur
            await self._create_realistic_matches(epl_league['id'], team_ids)
            
            # Takım istatistikleri oluştur
            await self._create_team_statistics(epl_league['id'], team_ids)
            
            # Tahminler oluştur
            await self._create_realistic_predictions(epl_league['id'], team_ids)
            
            logger.info("✅ Demo verisi başarıyla oluşturuldu!")
            
        except Exception as e:
            logger.error(f"Demo veri oluşturma hatası: {e}")
    
    async def _create_realistic_matches(self, league_id: str, team_ids: List[str]):
        """Gerçekçi maçlar oluştur"""
        try:
            # Son 5 hafta (tamamlanmış maçlar)
            for week in range(-5, 0):
                match_date = datetime.utcnow() + timedelta(weeks=week)
                
                # Her hafta 10 maç
                for i in range(0, len(team_ids), 2):
                    if i + 1 < len(team_ids):
                        home_team = team_ids[i]
                        away_team = team_ids[i + 1]
                        
                        # Gerçekçi skor üret
                        home_score = random.choices([0, 1, 2, 3, 4], weights=[10, 30, 35, 20, 5])[0]
                        away_score = random.choices([0, 1, 2, 3, 4], weights=[15, 35, 30, 15, 5])[0]
                        
                        # xG değerleri
                        home_xg = round(random.uniform(0.5, 3.5), 2)
                        away_xg = round(random.uniform(0.5, 3.5), 2)
                        
                        from models.database_models import Match
                        match = Match(
                            league_id=league_id,
                            home_team_id=home_team,
                            away_team_id=away_team,
                            match_date=match_date,
                            season="2024-25",
                            gameweek=week + 6,
                            home_score=home_score,
                            away_score=away_score,
                            home_xg=home_xg,
                            away_xg=away_xg,
                            home_shots=random.randint(8, 20),
                            away_shots=random.randint(6, 18),
                            home_shots_on_target=random.randint(3, 8),
                            away_shots_on_target=random.randint(2, 7),
                            home_corners=random.randint(2, 12),
                            away_corners=random.randint(2, 10),
                            home_yellow_cards=random.randint(0, 4),
                            away_yellow_cards=random.randint(0, 4),
                            home_red_cards=random.randint(0, 1),
                            away_red_cards=random.randint(0, 1),
                            status="finished",
                            odds_1x2={"1": round(random.uniform(1.5, 4.5), 2), 
                                     "X": round(random.uniform(2.8, 4.2), 2), 
                                     "2": round(random.uniform(1.8, 5.0), 2)},
                            odds_over_under={"over": round(random.uniform(1.7, 2.3), 2), 
                                           "under": round(random.uniform(1.7, 2.3), 2)},
                            odds_btts={"yes": round(random.uniform(1.6, 2.2), 2), 
                                      "no": round(random.uniform(1.6, 2.2), 2)}
                        )
                        
                        existing_match = await self.db.matches.find_one({
                            "home_team_id": home_team,
                            "away_team_id": away_team,
                            "match_date": match_date
                        })
                        
                        if not existing_match:
                            await self.db.matches.insert_one(match.dict())
            
            # Gelecek 2 hafta (planlanmış maçlar)
            for week in range(1, 3):
                match_date = datetime.utcnow() + timedelta(weeks=week)
                
                # Her hafta 10 maç
                for i in range(0, len(team_ids), 2):
                    if i + 1 < len(team_ids):
                        home_team = team_ids[i]
                        away_team = team_ids[i + 1]
                        
                        from models.database_models import Match
                        match = Match(
                            league_id=league_id,
                            home_team_id=home_team,
                            away_team_id=away_team,
                            match_date=match_date,
                            season="2024-25",
                            gameweek=week + 5,
                            status="scheduled",
                            odds_1x2={"1": round(random.uniform(1.5, 4.5), 2), 
                                     "X": round(random.uniform(2.8, 4.2), 2), 
                                     "2": round(random.uniform(1.8, 5.0), 2)},
                            odds_over_under={"over": round(random.uniform(1.7, 2.3), 2), 
                                           "under": round(random.uniform(1.7, 2.3), 2)},
                            odds_btts={"yes": round(random.uniform(1.6, 2.2), 2), 
                                      "no": round(random.uniform(1.6, 2.2), 2)}
                        )
                        
                        existing_match = await self.db.matches.find_one({
                            "home_team_id": home_team,
                            "away_team_id": away_team,
                            "match_date": match_date
                        })
                        
                        if not existing_match:
                            await self.db.matches.insert_one(match.dict())
                            
        except Exception as e:
            logger.error(f"Maç oluşturma hatası: {e}")
    
    async def _create_team_statistics(self, league_id: str, team_ids: List[str]):
        """Takım istatistikleri oluştur"""
        try:
            for team_id in team_ids:
                # Takımın maçlarını al
                team_matches = await self.db.matches.find({
                    "$or": [{"home_team_id": team_id}, {"away_team_id": team_id}],
                    "status": "finished"
                }).to_list(1000)
                
                if not team_matches:
                    continue
                
                # İstatistikleri hesapla
                stats = {
                    "matches_played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0,
                    "home_matches_played": 0, "home_wins": 0, "home_draws": 0, "home_losses": 0,
                    "home_goals_for": 0, "home_goals_against": 0,
                    "away_matches_played": 0, "away_wins": 0, "away_draws": 0, "away_losses": 0,
                    "away_goals_for": 0, "away_goals_against": 0,
                    "clean_sheets": 0, "last_5_form": []
                }
                
                for match in team_matches:
                    is_home = match['home_team_id'] == team_id
                    our_score = match.get('home_score', 0) if is_home else match.get('away_score', 0)
                    opp_score = match.get('away_score', 0) if is_home else match.get('home_score', 0)
                    
                    stats["matches_played"] += 1
                    stats["goals_for"] += our_score
                    stats["goals_against"] += opp_score
                    
                    if is_home:
                        stats["home_matches_played"] += 1
                        stats["home_goals_for"] += our_score
                        stats["home_goals_against"] += opp_score
                    else:
                        stats["away_matches_played"] += 1
                        stats["away_goals_for"] += our_score
                        stats["away_goals_against"] += opp_score
                    
                    # Sonuç
                    if our_score > opp_score:
                        stats["wins"] += 1
                        if is_home: stats["home_wins"] += 1
                        else: stats["away_wins"] += 1
                        stats["last_5_form"].append("W")
                    elif our_score == opp_score:
                        stats["draws"] += 1
                        if is_home: stats["home_draws"] += 1
                        else: stats["away_draws"] += 1
                        stats["last_5_form"].append("D")
                    else:
                        stats["losses"] += 1
                        if is_home: stats["home_losses"] += 1
                        else: stats["away_losses"] += 1
                        stats["last_5_form"].append("L")
                    
                    if opp_score == 0:
                        stats["clean_sheets"] += 1
                
                # Son 5 maç formunu sınırla
                stats["last_5_form"] = stats["last_5_form"][-5:]
                
                # Ortalamalar
                if stats["matches_played"] > 0:
                    stats["avg_goals_for"] = round(stats["goals_for"] / stats["matches_played"], 2)
                    stats["avg_goals_against"] = round(stats["goals_against"] / stats["matches_played"], 2)
                
                from models.database_models import TeamStats
                team_stats = TeamStats(
                    team_id=team_id,
                    league_id=league_id,
                    season="2024-25",
                    **stats
                )
                
                # Mevcut istatistik var mı kontrol et
                existing_stats = await self.db.team_stats.find_one({
                    "team_id": team_id,
                    "season": "2024-25"
                })
                
                if existing_stats:
                    await self.db.team_stats.update_one(
                        {"_id": existing_stats["_id"]},
                        {"$set": team_stats.dict()}
                    )
                else:
                    await self.db.team_stats.insert_one(team_stats.dict())
                    
        except Exception as e:
            logger.error(f"Takım istatistikleri oluşturma hatası: {e}")
    
    async def _create_realistic_predictions(self, league_id: str, team_ids: List[str]):
        """Gerçekçi tahminler oluştur"""
        try:
            # Gelecek maçları al
            upcoming_matches = await self.db.matches.find({
                "league_id": league_id,
                "status": "scheduled",
                "match_date": {"$gte": datetime.utcnow()}
            }).to_list(100)
            
            bet_types = ["1X2", "O/U2.5", "BTTS"]
            
            for match in upcoming_matches:
                for bet_type in bet_types:
                    # Gerçekçi tahmin oluştur
                    if bet_type == "1X2":
                        outcomes = ["1", "X", "2"]
                        probabilities = [0.4, 0.3, 0.3]  # Home bias
                        predicted_outcome = random.choices(outcomes, weights=probabilities)[0]
                        confidence = random.uniform(60, 85)
                        
                    elif bet_type == "O/U2.5":
                        outcomes = ["Over 2.5", "Under 2.5"]
                        predicted_outcome = random.choice(outcomes)
                        confidence = random.uniform(55, 80)
                        
                    else:  # BTTS
                        outcomes = ["Yes", "No"]
                        predicted_outcome = random.choice(outcomes)
                        confidence = random.uniform(50, 75)
                    
                    # Takım isimlerini al
                    home_team = await self.db.teams.find_one({"id": match['home_team_id']})
                    away_team = await self.db.teams.find_one({"id": match['away_team_id']})
                    
                    from models.database_models import Prediction
                    prediction = Prediction(
                        match_id=match['id'],
                        league_id=league_id,
                        home_team_id=match['home_team_id'],
                        away_team_id=match['away_team_id'],
                        match_date=match['match_date'],
                        bet_type=bet_type,
                        predicted_outcome=predicted_outcome,
                        confidence=round(confidence, 1),
                        probability=round(confidence / 100, 3),
                        model_version="Enhanced_v1.0",
                        model_features={"demo": True, "enhanced": True}
                    )
                    
                    # Mevcut tahmin var mı kontrol et
                    existing_prediction = await self.db.predictions.find_one({
                        "match_id": match['id'],
                        "bet_type": bet_type
                    })
                    
                    if not existing_prediction:
                        await self.db.predictions.insert_one(prediction.dict())
                        
        except Exception as e:
            logger.error(f"Tahmin oluşturma hatası: {e}")