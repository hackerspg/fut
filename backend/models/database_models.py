from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class MatchResult(str, Enum):
    HOME_WIN = "1"
    DRAW = "X"
    AWAY_WIN = "2"

class BetType(str, Enum):
    MATCH_RESULT = "1X2"
    OVER_UNDER_2_5 = "O/U2.5"
    BOTH_TEAMS_SCORE = "BTTS"
    FIRST_HALF_RESULT = "1H1X2"
    HANDICAP = "HANDICAP"

class League(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    country: str
    season: str
    league_code: str  # Premier League: "EPL", La Liga: "LALIGA", etc.
    source_urls: Dict[str, str]  # {"flashscore": "url", "sofascore": "url"}
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Team(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    league_id: str
    country: str
    logo_url: Optional[str] = None
    alternative_names: List[str] = []  # Farklı sitelerdeki isim varyasyonları
    external_ids: Dict[str, str] = {}  # {"flashscore": "id", "sofascore": "id"}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Match(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    league_id: str
    home_team_id: str
    away_team_id: str
    match_date: datetime
    season: str
    gameweek: Optional[int] = None
    
    # Maç Sonucu
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    result: Optional[MatchResult] = None
    status: str = "scheduled"  # scheduled, live, finished, cancelled
    
    # Detaylı İstatistikler
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_yellow_cards: Optional[int] = None
    away_yellow_cards: Optional[int] = None
    home_red_cards: Optional[int] = None
    away_red_cards: Optional[int] = None
    
    # xG Verileri
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None
    
    # Bahis Oranları
    odds_1x2: Optional[Dict[str, float]] = None  # {"1": 2.5, "X": 3.2, "2": 2.8}
    odds_over_under: Optional[Dict[str, float]] = None  # {"over": 1.9, "under": 1.9}
    odds_btts: Optional[Dict[str, float]] = None  # {"yes": 1.8, "no": 2.0}
    
    # Metadata
    external_ids: Dict[str, str] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TeamStats(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str
    league_id: str
    season: str
    
    # Genel Form
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    
    # Ev Sahibi Form
    home_matches_played: int = 0
    home_wins: int = 0
    home_draws: int = 0
    home_losses: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0
    
    # Deplasman Form
    away_matches_played: int = 0
    away_wins: int = 0
    away_draws: int = 0
    away_losses: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0
    
    # Son 5 Maç Formu
    last_5_form: List[str] = []  # ["W", "D", "L", "W", "W"]
    
    # Gelişmiş İstatistikler
    avg_goals_for: float = 0.0
    avg_goals_against: float = 0.0
    avg_xg_for: float = 0.0
    avg_xg_against: float = 0.0
    clean_sheets: int = 0
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Prediction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    league_id: str
    home_team_id: str
    away_team_id: str
    match_date: datetime
    
    # Tahmin Detayları
    bet_type: BetType
    predicted_outcome: str
    confidence: float  # 0-100 arası
    probability: float  # 0-1 arası
    
    # Model Bilgileri
    model_version: str
    model_features: Dict[str, Any]
    
    # Önerilen Bahis
    suggested_bet: Optional[str] = None
    suggested_odds: Optional[float] = None
    
    # Sonuç Takibi
    actual_result: Optional[str] = None
    is_correct: Optional[bool] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    evaluated_at: Optional[datetime] = None

class ScrapingJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str  # "leagues", "teams", "matches", "stats"
    source: str  # "flashscore", "sofascore", "understat"
    league_ids: List[str]
    status: str = "pending"  # pending, running, completed, failed
    
    # Sonuçlar
    items_scraped: int = 0
    items_failed: int = 0
    errors: List[str] = []
    
    # Zaman Takibi
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SystemLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    level: str  # INFO, WARNING, ERROR, CRITICAL
    module: str  # scraper, prediction, scheduler
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)