import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class SchedulerManager:
    def __init__(self, db, scraper_manager, prediction_engine):
        self.db = db
        self.scraper_manager = scraper_manager
        self.prediction_engine = prediction_engine
        self.scheduler = AsyncIOScheduler()
        
        # Scheduler'ı yapılandır
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Scheduled job'ları kur"""
        try:
            # Günlük veri toplama (her gün saat 02:00)
            self.scheduler.add_job(
                self._daily_scraping_job,
                CronTrigger(hour=2, minute=0),
                id='daily_scraping',
                name='Günlük Veri Toplama',
                replace_existing=True
            )
            
            # Günlük tahmin üretme (her gün saat 03:00)
            self.scheduler.add_job(
                self._daily_prediction_job,
                CronTrigger(hour=3, minute=0),
                id='daily_predictions',
                name='Günlük Tahmin Üretme',
                replace_existing=True
            )
            
            # Saatlik yaklaşan maçlar için tahmin güncelleme
            self.scheduler.add_job(
                self._hourly_update_job,
                IntervalTrigger(hours=1),
                id='hourly_updates',
                name='Saatlik Güncellemeler',
                replace_existing=True
            )
            
            # Haftalık model yeniden eğitimi (Pazar 04:00)
            self.scheduler.add_job(
                self._weekly_model_training,
                CronTrigger(day_of_week=6, hour=4, minute=0),
                id='weekly_training',
                name='Haftalık Model Eğitimi',
                replace_existing=True
            )
            
            # Günlük performans değerlendirme (her gün saat 23:00)
            self.scheduler.add_job(
                self._daily_evaluation_job,
                CronTrigger(hour=23, minute=0),
                id='daily_evaluation',
                name='Günlük Performans Değerlendirme',
                replace_existing=True
            )
            
            logger.info("Scheduled job'lar kuruldu")
            
        except Exception as e:
            logger.error(f"Scheduler kurulum hatası: {e}")
    
    def start(self):
        """Scheduler'ı başlat"""
        try:
            self.scheduler.start()
            logger.info("🚀 Scheduler başlatıldı")
            
            # Mevcut job'ları listele
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                logger.info(f"📅 Scheduled job: {job.name} - {job.next_run_time}")
                
        except Exception as e:
            logger.error(f"Scheduler başlatma hatası: {e}")
    
    def stop(self):
        """Scheduler'ı durdur"""
        try:
            self.scheduler.shutdown()
            logger.info("🔴 Scheduler durduruldu")
        except Exception as e:
            logger.error(f"Scheduler durdurma hatası: {e}")
    
    async def _daily_scraping_job(self):
        """Günlük veri toplama job'u"""
        try:
            logger.info("📊 Günlük veri toplama başladı")
            
            # Tüm aktif liglerden veri topla
            await self.scraper_manager.run_scraping_job()
            
            # System log
            await self._log_job_completion("daily_scraping", "success")
            
            logger.info("✅ Günlük veri toplama tamamlandı")
            
        except Exception as e:
            logger.error(f"Günlük veri toplama hatası: {e}")
            await self._log_job_completion("daily_scraping", "error", str(e))
    
    async def _daily_prediction_job(self):
        """Günlük tahmin üretme job'u"""
        try:
            logger.info("🧠 Günlük tahmin üretme başladı")
            
            # Önümüzdeki 7 gün için tahmin üret
            await self.prediction_engine.generate_predictions()
            
            # System log
            await self._log_job_completion("daily_predictions", "success")
            
            logger.info("✅ Günlük tahmin üretme tamamlandı")
            
        except Exception as e:
            logger.error(f"Günlük tahmin üretme hatası: {e}")
            await self._log_job_completion("daily_predictions", "error", str(e))
    
    async def _hourly_update_job(self):
        """Saatlik güncellemeler"""
        try:
            logger.info("🔄 Saatlik güncellemeler başladı")
            
            # Yaklaşan maçları güncelle (önümüzdeki 24 saat)
            tomorrow = datetime.utcnow() + timedelta(days=1)
            upcoming_matches = await self.db.matches.find({
                "match_date": {"$gte": datetime.utcnow(), "$lte": tomorrow},
                "status": "scheduled"
            }).to_list(100)
            
            if upcoming_matches:
                match_ids = [match['id'] for match in upcoming_matches]
                
                # Sadece yaklaşan maçlar için scraping
                await self.scraper_manager.run_scraping_job()
                
                # Yaklaşan maçlar için tahmin güncelle
                await self.prediction_engine.generate_predictions(match_ids)
                
                logger.info(f"🎯 {len(upcoming_matches)} yaklaşan maç güncellendi")
            
            # System log
            await self._log_job_completion("hourly_updates", "success")
            
        except Exception as e:
            logger.error(f"Saatlik güncellemeler hatası: {e}")
            await self._log_job_completion("hourly_updates", "error", str(e))
    
    async def _weekly_model_training(self):
        """Haftalık model eğitimi"""
        try:
            logger.info("🎓 Haftalık model eğitimi başladı")
            
            # Tüm modelleri yeniden eğit
            for bet_type in ['1X2', 'O/U2.5', 'BTTS']:
                await self.prediction_engine.train_model(bet_type)
                logger.info(f"Model eğitildi: {bet_type}")
            
            # System log
            await self._log_job_completion("weekly_training", "success")
            
            logger.info("✅ Haftalık model eğitimi tamamlandı")
            
        except Exception as e:
            logger.error(f"Haftalık model eğitimi hatası: {e}")
            await self._log_job_completion("weekly_training", "error", str(e))
    
    async def _daily_evaluation_job(self):
        """Günlük performans değerlendirme"""
        try:
            logger.info("📈 Günlük performans değerlendirme başladı")
            
            # Tahmin performansını değerlendir
            await self.prediction_engine.evaluate_predictions()
            
            # System log
            await self._log_job_completion("daily_evaluation", "success")
            
            logger.info("✅ Günlük performans değerlendirme tamamlandı")
            
        except Exception as e:
            logger.error(f"Günlük performans değerlendirme hatası: {e}")
            await self._log_job_completion("daily_evaluation", "error", str(e))
    
    async def _log_job_completion(self, job_name: str, status: str, error_message: str = None):
        """Job tamamlanma logunu kaydet"""
        try:
            from models.database_models import SystemLog
            
            log_entry = SystemLog(
                level="INFO" if status == "success" else "ERROR",
                module="scheduler",
                message=f"Job completed: {job_name} - {status}",
                details={
                    "job_name": job_name,
                    "status": status,
                    "error_message": error_message,
                    "timestamp": datetime.utcnow()
                }
            )
            
            await self.db.system_logs.insert_one(log_entry.dict())
            
        except Exception as e:
            logger.error(f"Job log kaydetme hatası: {e}")
    
    def get_job_status(self):
        """Job durumlarını al"""
        try:
            jobs = self.scheduler.get_jobs()
            
            status = {
                "scheduler_running": self.scheduler.running,
                "total_jobs": len(jobs),
                "jobs": []
            }
            
            for job in jobs:
                job_info = {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                status["jobs"].append(job_info)
            
            return status
            
        except Exception as e:
            logger.error(f"Job status alma hatası: {e}")
            return {"error": str(e)}
    
    async def trigger_job_manually(self, job_id: str):
        """Job'u manuel olarak tetikle"""
        try:
            job = self.scheduler.get_job(job_id)
            
            if not job:
                raise ValueError(f"Job bulunamadı: {job_id}")
            
            # Job'u çalıştır
            job.modify(next_run_time=datetime.now())
            
            logger.info(f"Job manuel olarak tetiklendi: {job_id}")
            
            return {"success": True, "message": f"Job tetiklendi: {job_id}"}
            
        except Exception as e:
            logger.error(f"Job tetikleme hatası: {e}")
            return {"success": False, "error": str(e)}