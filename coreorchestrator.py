"""
Master Orchestrator - Coordinates all trading agents and manages the evolution cycle.
Architectural Choice: Event-driven state machine with rollback capability for fault tolerance.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import traceback

from config.firebase_config import firebase_client
from core.agents import DataAgent, ResearchAgent, ExecutionAgent

logger = logging.getLogger(__name__)


class EvolutionState(Enum):
    """State machine for evolution cycle."""
    IDLE = "idle"
    DATA_COLLECTION = "data_collection"
    RESEARCH = "strategy_research"
    BACKTESTING = "backtesting"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    ERROR = "error"


class Orchestrator:
    """Master coordinator for autonomous trading evolution."""
    
    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id
        self.state = EvolutionState.IDLE
        self.cycle_id: Optional[str] = None
        self.error_count = 0
        self.max_errors = 3
        
        # Initialize agents
        self.data_agent = DataAgent(exchange_id)
        self.research_agent = ResearchAgent()
        self.execution_agent = ExecutionAgent()
        
        # State document reference
        self.state_ref = firebase_client.db.collection('orchestrator_state').document('current')
        
        logger.info(f"Orchestrator initialized for exchange: {exchange_id}")
    
    async def start_evolution_cycle(self) -> str:
        """Initiate a complete evolution cycle with rollback capability."""
        try:
            self.cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            logger.info(f"Starting evolution cycle {self.cycle_id}")
            
            # Record cycle start in Firebase
            cycle_doc = firebase_client.db.collection('evolution_cycles').document(self.cycle_id)
            cycle_doc.set({
                'start_time': datetime.utcnow(),
                'state': 'running',
                'exchange': self.exchange_id
            })
            
            # Execute evolution pipeline
            await self._execute_safe_pipeline()
            
            # Mark cycle as completed
            cycle_doc.update({
                'end_time': datetime.utcnow(),
                'state': 'completed',
                'error_count': self.error_count
            })
            
            logger.info(f"Evolution cycle {self.cycle_id} completed successfully")
            return self.cycle_id
            
        except Exception as e:
            logger.error(f"Evolution cycle failed: {e}")
            await self._handle_critical_failure(e)
            raise
    
    async def _execute_safe_pipeline(self) -> None:
        """Execute evolution pipeline with rollback on failure."""
        pipeline = [
            (