import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from pathlib import Path
from xgboost import XGBClassifier

from models.database_models import Match, Prediction, TeamStats, BetType, MatchResult

logger = logging.getLogger(__name__)

class PredictionEngine:
    def __init__(self, db):
        self.db = db
        self.models = {}
        self.scalers = {}
        self.models_path = Path(__file__).parent / "models"
        self.models_path.mkdir(exist_ok=True)
        
        # Model konfigürasyonu
        self.model_configs = {
            '1X2': {
                'model_class': RandomForestClassifier,
                'params': {
                    'n_estimators': 100,
                    'max_depth': 6,
                    'random_state': 42
                },
                'target_column': 'result'
            },
            'O/U2.5': {
                'model_class': RandomForestClassifier,
                'params': {
                    'n_estimators': 100,
                    'max_depth': 8,
                    'random_state': 42
                },
                'target_column': 'over_under_2_5'
            },
            'BTTS': {
                'model_class': LogisticRegression,
                'params': {
                    'random_state': 42,
                    'max_iter': 1000
                },
                'target_column': 'both_teams_score'
            }
        }
    
    async def initialize_models(self):
        """Modelleri başlat veya yükle"""
        try:
            for bet_type in self.model_configs.keys():
                model_file = self.models_path / f"{bet_type}_model.pkl"
                scaler_file = self.models_path / f"{bet_type}_scaler.pkl"
                
                if model_file.exists() and scaler_file.exists():
                    # Mevcut modeli yükle
                    self.models[bet_type] = joblib.load(model_file)
                    self.scalers[bet_type] = joblib.load(scaler_file)
                    logger.info(f"Model yüklendi: {bet_type}")
                else:
                    # Yeni model oluştur
                    await self.train_model(bet_type)
                    logger.info(f"Yeni model oluşturuldu: {bet_type}")
            
            logger.info("Tüm tahmin modelleri hazır!")
            
        except Exception as e:
            logger.error(f"Model başlatma hatası: {e}")
            raise e
    
    async def train_model(self, bet_type: str):
        """Belirli bahis tipi için model eğit"""
        try:
            logger.info(f"Model eğitimi başlıyor: {bet_type}")
            
            # Eğitim verilerini hazırla
            X, y = await self._prepare_training_data(bet_type)
            
            if len(X) < 100:
                logger.warning(f"Yetersiz eğitim verisi: {bet_type} - {len(X)} örneklem")
                return
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scaler
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Model
            config = self.model_configs[bet_type]
            model = config['model_class'](**config['params'])
            model.fit(X_train_scaled, y_train)
            
            # Test
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Model eğitimi tamamlandı: {bet_type} - Doğruluk: {accuracy:.3f}")
            
            # Modeli kaydet
            self.models[bet_type] = model
            self.scalers[bet_type] = scaler
            
            joblib.dump(model, self.models_path / f"{bet_type}_model.pkl")
            joblib.dump(scaler, self.models_path / f"{bet_type}_scaler.pkl")
            
        except Exception as e:
            logger.error(f"Model eğitimi hatası ({bet_type}): {e}")
            raise e
    
    async def _prepare_training_data(self, bet_type: str) -> Tuple[pd.DataFrame, pd.Series]:
        """Eğitim verilerini hazırla"""
        try:
            # Tamamlanmış maçları al
            matches = await self.db.matches.find({
                "status": "finished",
                "home_score": {"$exists": True},
                "away_score": {"$exists": True}
            }).to_list(10000)
            
            if not matches:
                raise ValueError("Eğitim için tamamlanmış maç bulunamadı")
            
            # DataFrame'e çevir
            df = pd.DataFrame(matches)
            
            # Feature engineering
            features_df = await self._create_features(df)
            
            # Target variable
            target_col = self.model_configs[bet_type]['target_column']
            targets = await self._create_targets(df, target_col)
            
            # Eksik değerleri temizle
            features_df = features_df.fillna(0)
            
            return features_df, targets
            
        except Exception as e:
            logger.error(f"Eğitim verisi hazırlama hatası ({bet_type}): {e}")
            raise e
    
    async def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Feature engineering"""
        features = []
        
        for _, match in df.iterrows():
            try:
                # Temel bilgiler
                feature_dict = {
                    'home_team_id': match['home_team_id'],
                    'away_team_id': match['away_team_id'],
                    'league_id': match['league_id']
                }
                
                # Takım performans verileri
                home_stats = await self._get_team_recent_stats(
                    match['home_team_id'], 
                    match['match_date'], 
                    venue='home'
                )
                
                away_stats = await self._get_team_recent_stats(
                    match['away_team_id'], 
                    match['match_date'], 
                    venue='away'
                )
                
                # Home team features
                for key, value in home_stats.items():
                    feature_dict[f'home_{key}'] = value
                
                # Away team features
                for key, value in away_stats.items():
                    feature_dict[f'away_{key}'] = value
                
                # Head-to-head
                h2h_stats = await self._get_h2h_stats(
                    match['home_team_id'], 
                    match['away_team_id'], 
                    match['match_date']
                )
                
                for key, value in h2h_stats.items():
                    feature_dict[f'h2h_{key}'] = value
                
                # Zaman bazlı özellikler
                match_date = match['match_date']
                if isinstance(match_date, str):
                    match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                
                feature_dict['month'] = match_date.month
                feature_dict['day_of_week'] = match_date.weekday()
                feature_dict['is_weekend'] = 1 if match_date.weekday() >= 5 else 0
                
                features.append(feature_dict)
                
            except Exception as e:
                logger.warning(f"Feature oluşturma hatası: {e}")
                continue
        
        return pd.DataFrame(features).fillna(0)
    
    async def _create_targets(self, df: pd.DataFrame, target_col: str) -> pd.Series:
        """Target değişkenlerini oluştur"""
        targets = []
        
        for _, match in df.iterrows():
            home_score = match.get('home_score', 0)
            away_score = match.get('away_score', 0)
            
            if home_score is None or away_score is None:
                targets.append(0)
                continue
            
            if target_col == 'result':
                # 1X2
                if home_score > away_score:
                    targets.append(1)  # Home win
                elif home_score == away_score:
                    targets.append(0)  # Draw
                else:
                    targets.append(2)  # Away win
                    
            elif target_col == 'over_under_2_5':
                # Over/Under 2.5
                total_goals = home_score + away_score
                targets.append(1 if total_goals > 2.5 else 0)
                
            elif target_col == 'both_teams_score':
                # Both teams score
                targets.append(1 if home_score > 0 and away_score > 0 else 0)
            
            else:
                targets.append(0)
        
        return pd.Series(targets)
    
    async def _get_team_recent_stats(self, team_id: str, match_date: datetime, venue: str = 'all') -> Dict[str, float]:
        """Takımın son maçlardaki performansını al"""
        try:
            # Son 10 maçı al
            query = {
                "$or": [
                    {"home_team_id": team_id},
                    {"away_team_id": team_id}
                ],
                "match_date": {"$lt": match_date},
                "status": "finished"
            }
            
            if venue == 'home':
                query = {"home_team_id": team_id, "match_date": {"$lt": match_date}, "status": "finished"}
            elif venue == 'away':
                query = {"away_team_id": team_id, "match_date": {"$lt": match_date}, "status": "finished"}
            
            matches = await self.db.matches.find(query).sort("match_date", -1).limit(10).to_list(10)
            
            if not matches:
                return self._get_default_stats()
            
            # İstatistikleri hesapla
            stats = {
                'games_played': len(matches),
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'goals_avg': 0.0,
                'goals_against_avg': 0.0,
                'clean_sheets': 0,
                'btts_count': 0,
                'over_2_5_count': 0,
                'form_points': 0
            }
            
            for match in matches:
                is_home = match['home_team_id'] == team_id
                our_score = match['home_score'] if is_home else match['away_score']
                opponent_score = match['away_score'] if is_home else match['home_score']
                
                stats['goals_for'] += our_score
                stats['goals_against'] += opponent_score
                
                # Sonuç
                if our_score > opponent_score:
                    stats['wins'] += 1
                    stats['form_points'] += 3
                elif our_score == opponent_score:
                    stats['draws'] += 1
                    stats['form_points'] += 1
                else:
                    stats['losses'] += 1
                
                # Diğer istatistikler
                if opponent_score == 0:
                    stats['clean_sheets'] += 1
                
                if our_score > 0 and opponent_score > 0:
                    stats['btts_count'] += 1
                
                if our_score + opponent_score > 2.5:
                    stats['over_2_5_count'] += 1
            
            # Ortalamalar
            stats['goals_avg'] = stats['goals_for'] / len(matches)
            stats['goals_against_avg'] = stats['goals_against'] / len(matches)
            
            return stats
            
        except Exception as e:
            logger.error(f"Takım istatistikleri alma hatası: {e}")
            return self._get_default_stats()
    
    async def _get_h2h_stats(self, home_team_id: str, away_team_id: str, match_date: datetime) -> Dict[str, float]:
        """Head-to-head istatistiklerini al"""
        try:
            # Son 5 karşılaşmayı al
            matches = await self.db.matches.find({
                "$or": [
                    {"home_team_id": home_team_id, "away_team_id": away_team_id},
                    {"home_team_id": away_team_id, "away_team_id": home_team_id}
                ],
                "match_date": {"$lt": match_date},
                "status": "finished"
            }).sort("match_date", -1).limit(5).to_list(5)
            
            if not matches:
                return {'h2h_games': 0, 'h2h_wins': 0, 'h2h_draws': 0, 'h2h_losses': 0}
            
            stats = {
                'h2h_games': len(matches),
                'h2h_wins': 0,
                'h2h_draws': 0,
                'h2h_losses': 0
            }
            
            for match in matches:
                is_home = match['home_team_id'] == home_team_id
                our_score = match['home_score'] if is_home else match['away_score']
                opponent_score = match['away_score'] if is_home else match['home_score']
                
                if our_score > opponent_score:
                    stats['h2h_wins'] += 1
                elif our_score == opponent_score:
                    stats['h2h_draws'] += 1
                else:
                    stats['h2h_losses'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"H2H istatistikleri alma hatası: {e}")
            return {'h2h_games': 0, 'h2h_wins': 0, 'h2h_draws': 0, 'h2h_losses': 0}
    
    def _get_default_stats(self) -> Dict[str, float]:
        """Varsayılan istatistikler"""
        return {
            'games_played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goals_avg': 0.0,
            'goals_against_avg': 0.0,
            'clean_sheets': 0,
            'btts_count': 0,
            'over_2_5_count': 0,
            'form_points': 0
        }
    
    async def generate_predictions(self, match_ids: Optional[List[str]] = None):
        """Tahmin üret"""
        try:
            # Modelleri başlat
            await self.initialize_models()
            
            # Tahmin yapılacak maçları al
            query = {"status": "scheduled"}
            if match_ids:
                query["id"] = {"$in": match_ids}
            
            matches = await self.db.matches.find(query).to_list(1000)
            
            if not matches:
                logger.warning("Tahmin yapılacak maç bulunamadı")
                return
            
            predictions_generated = 0
            
            for match in matches:
                try:
                    # Her bahis tipi için tahmin yap
                    for bet_type in self.model_configs.keys():
                        if bet_type not in self.models:
                            continue
                        
                        prediction = await self._predict_match(match, bet_type)
                        
                        if prediction:
                            # Mevcut tahmin var mı kontrol et
                            existing = await self.db.predictions.find_one({
                                "match_id": match['id'],
                                "bet_type": bet_type
                            })
                            
                            if not existing:
                                await self.db.predictions.insert_one(prediction.dict())
                                predictions_generated += 1
                                logger.info(f"Tahmin oluşturuldu: {bet_type} - {prediction.predicted_outcome}")
                            else:
                                # Mevcut tahmini güncelle
                                await self.db.predictions.update_one(
                                    {"_id": existing["_id"]},
                                    {"$set": prediction.dict()}
                                )
                    
                except Exception as e:
                    logger.error(f"Maç tahmini hatası: {e}")
                    continue
            
            logger.info(f"Toplam {predictions_generated} tahmin oluşturuldu")
            
        except Exception as e:
            logger.error(f"Tahmin üretme hatası: {e}")
    
    async def _predict_match(self, match: Dict[str, Any], bet_type: str) -> Optional[Prediction]:
        """Belirli bir maç için tahmin yap"""
        try:
            # Feature'ları oluştur
            features = await self._create_match_features(match)
            
            if features is None:
                return None
            
            # Model ile tahmin yap
            model = self.models[bet_type]
            scaler = self.scalers[bet_type]
            
            # Features'ı DataFrame'e çevir
            feature_df = pd.DataFrame([features]).fillna(0)
            
            # Eksik kolonları ekle (eğitim sırasında kullanılan feature'lar)
            for col in scaler.feature_names_in_:
                if col not in feature_df.columns:
                    feature_df[col] = 0
            
            # Sıralamayı eğitim verisi ile aynı yap
            feature_df = feature_df[scaler.feature_names_in_]
            
            # Scale ve tahmin
            features_scaled = scaler.transform(feature_df)
            prediction_proba = model.predict_proba(features_scaled)[0]
            predicted_class = model.predict(features_scaled)[0]
            
            # Sonuçları yorumla
            outcome, confidence = self._interpret_prediction(bet_type, predicted_class, prediction_proba)
            
            if confidence < 0.6:  # Düşük güven seviyesi
                return None
            
            prediction = Prediction(
                match_id=match['id'],
                league_id=match['league_id'],
                home_team_id=match['home_team_id'],
                away_team_id=match['away_team_id'],
                match_date=match['match_date'],
                bet_type=bet_type,
                predicted_outcome=outcome,
                confidence=confidence * 100,
                probability=max(prediction_proba),
                model_version="1.0",
                model_features=features
            )
            
            return prediction
            
        except Exception as e:
            logger.error(f"Maç tahmin hatası ({bet_type}): {e}")
            return None
    
    async def _create_match_features(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Maç için feature'ları oluştur"""
        try:
            features = {
                'home_team_id': match['home_team_id'],
                'away_team_id': match['away_team_id'],
                'league_id': match['league_id']
            }
            
            # Takım istatistikleri
            home_stats = await self._get_team_recent_stats(
                match['home_team_id'], 
                match['match_date'], 
                venue='home'
            )
            
            away_stats = await self._get_team_recent_stats(
                match['away_team_id'], 
                match['match_date'], 
                venue='away'
            )
            
            # Features'ları ekle
            for key, value in home_stats.items():
                features[f'home_{key}'] = value
            
            for key, value in away_stats.items():
                features[f'away_{key}'] = value
            
            # H2H
            h2h_stats = await self._get_h2h_stats(
                match['home_team_id'], 
                match['away_team_id'], 
                match['match_date']
            )
            
            for key, value in h2h_stats.items():
                features[f'h2h_{key}'] = value
            
            # Zaman özellikleri
            match_date = match['match_date']
            if isinstance(match_date, str):
                match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
            
            features['month'] = match_date.month
            features['day_of_week'] = match_date.weekday()
            features['is_weekend'] = 1 if match_date.weekday() >= 5 else 0
            
            return features
            
        except Exception as e:
            logger.error(f"Match feature oluşturma hatası: {e}")
            return None
    
    def _interpret_prediction(self, bet_type: str, predicted_class: int, probabilities: np.ndarray) -> Tuple[str, float]:
        """Tahmin sonucunu yorumla"""
        if bet_type == '1X2':
            outcomes = ['X', '1', '2']  # Draw, Home win, Away win
            outcome = outcomes[predicted_class]
            confidence = probabilities[predicted_class]
            
        elif bet_type == 'O/U2.5':
            outcomes = ['Under 2.5', 'Over 2.5']
            outcome = outcomes[predicted_class]
            confidence = probabilities[predicted_class]
            
        elif bet_type == 'BTTS':
            outcomes = ['No', 'Yes']
            outcome = outcomes[predicted_class]
            confidence = probabilities[predicted_class]
            
        else:
            outcome = str(predicted_class)
            confidence = max(probabilities)
        
        return outcome, confidence
    
    async def evaluate_predictions(self):
        """Tahmin performansını değerlendir"""
        try:
            # Tamamlanmış maçları al
            finished_matches = await self.db.matches.find({
                "status": "finished",
                "home_score": {"$exists": True},
                "away_score": {"$exists": True}
            }).to_list(1000)
            
            for match in finished_matches:
                predictions = await self.db.predictions.find({
                    "match_id": match['id'],
                    "actual_result": {"$exists": False}
                }).to_list(10)
                
                for prediction in predictions:
                    # Gerçek sonucu hesapla
                    actual_result = self._calculate_actual_result(match, prediction['bet_type'])
                    is_correct = actual_result == prediction['predicted_outcome']
                    
                    # Tahmin sonucunu güncelle
                    await self.db.predictions.update_one(
                        {"_id": prediction["_id"]},
                        {
                            "$set": {
                                "actual_result": actual_result,
                                "is_correct": is_correct,
                                "evaluated_at": datetime.utcnow()
                            }
                        }
                    )
                    
                    logger.info(f"Tahmin değerlendirildi: {prediction['bet_type']} - {'✓' if is_correct else '✗'}")
            
        except Exception as e:
            logger.error(f"Tahmin değerlendirme hatası: {e}")
    
    def _calculate_actual_result(self, match: Dict[str, Any], bet_type: str) -> str:
        """Gerçek sonucu hesapla"""
        home_score = match['home_score']
        away_score = match['away_score']
        
        if bet_type == '1X2':
            if home_score > away_score:
                return '1'
            elif home_score == away_score:
                return 'X'
            else:
                return '2'
                
        elif bet_type == 'O/U2.5':
            total_goals = home_score + away_score
            return 'Over 2.5' if total_goals > 2.5 else 'Under 2.5'
            
        elif bet_type == 'BTTS':
            return 'Yes' if home_score > 0 and away_score > 0 else 'No'
        
        return 'Unknown'