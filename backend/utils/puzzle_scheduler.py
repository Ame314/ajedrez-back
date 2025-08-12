import asyncio
import logging
from datetime import datetime, time
from dependencies import get_database
from utils.puzzle_database import get_puzzle_database

logger = logging.getLogger(__name__)

class PuzzleScheduler:
    """Programador para actualización automática de puzzles"""
    
    def __init__(self):
        self.running = False
        self.daily_task = None
        self.weekly_task = None
        self.database = None
        self.puzzle_db = None
        
    async def initialize(self):
        """Inicializa la conexión a la base de datos"""
        try:
            self.database = await get_database()
            self.puzzle_db = get_puzzle_database(self.database)
            logger.info("Scheduler de puzzles inicializado")
        except Exception as e:
            logger.error(f"Error inicializando scheduler: {e}")
    
    async def start(self):
        """Inicia el scheduler"""
        if self.running:
            return
            
        await self.initialize()
        self.running = True
        
        # Iniciar tareas de programación
        self.daily_task = asyncio.create_task(self._daily_scheduler())
        self.weekly_task = asyncio.create_task(self._weekly_scheduler())
        
        logger.info("Scheduler de puzzles iniciado")
    
    async def stop(self):
        """Detiene el scheduler"""
        self.running = False
        
        if self.daily_task:
            self.daily_task.cancel()
            try:
                await self.daily_task
            except asyncio.CancelledError:
                pass
                
        if self.weekly_task:
            self.weekly_task.cancel()
            try:
                await self.weekly_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Scheduler de puzzles detenido")
    
    async def _daily_scheduler(self):
        """Programador diario - actualiza puzzles cada día a medianoche UTC"""
        while self.running:
            try:
                now = datetime.utcnow()
                # Calcular tiempo hasta la próxima medianoche UTC
                next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                if now.time() >= time(0, 0):
                    next_midnight = next_midnight.replace(day=now.day + 1)
                
                time_until_midnight = (next_midnight - now).total_seconds()
                
                # Esperar hasta medianoche
                await asyncio.sleep(time_until_midnight)
                
                if self.puzzle_db:
                    # Actualizar puzzle diario
                    await self.puzzle_db.update_daily_puzzle()
                    logger.info("Puzzle diario actualizado programáticamente")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en programador diario: {e}")
                # Esperar 1 hora antes de intentar de nuevo
                await asyncio.sleep(3600)
    
    async def _weekly_scheduler(self):
        """Programador semanal - actualiza puzzles cada lunes a medianoche UTC"""
        while self.running:
            try:
                now = datetime.utcnow()
                # Calcular días hasta el próximo lunes (0 = lunes)
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and now.time() >= time(0, 0):
                    days_until_monday = 7
                
                next_monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
                next_monday = next_monday.replace(day=now.day + days_until_monday)
                
                time_until_monday = (next_monday - now).total_seconds()
                
                # Esperar hasta el lunes
                await asyncio.sleep(time_until_monday)
                
                if self.puzzle_db:
                    # Actualizar puzzles semanales
                    await self.puzzle_db.update_weekly_puzzles()
                    logger.info("Puzzles semanales actualizados programáticamente")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en programador semanal: {e}")
                # Esperar 1 día antes de intentar de nuevo
                await asyncio.sleep(86400)

# Instancia global del scheduler
puzzle_scheduler = PuzzleScheduler()
