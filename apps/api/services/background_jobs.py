"""
Background job service using configurable queue provider.
Supports both pg-boss and AWS SQS depending on configuration.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

from core.config import settings
from services.providers import get_queue_provider, get_metrics_provider

logger = logging.getLogger(__name__)


class JobType(str, Enum):
    """Available background job types."""
    SEARCH_EXECUTION = "search_execution"
    EXPORT_GENERATION = "export_generation"
    DATA_INGESTION = "data_ingestion"
    CV_PROCESSING = "cv_processing"
    CLEANUP = "cleanup"


class JobPriority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    ACTIVE = "active" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class BackgroundJobService:
    """Service for managing background jobs with configurable queue provider."""
    
    def __init__(self):
        self._queue_provider = None
        self._metrics_provider = None
        self._job_handlers: Dict[str, Callable] = {}
        
        logger.info(f"BackgroundJobService initialized with queue provider: {settings.QUEUE_PROVIDER}")
    
    @property
    def queue_provider(self):
        """Get the queue provider instance."""
        if self._queue_provider is None:
            try:
                self._queue_provider = get_queue_provider()
            except Exception as e:
                logger.error(f"Failed to initialize queue provider: {e}")
                self._queue_provider = None
        return self._queue_provider
    
    @property
    def metrics_provider(self):
        """Get the metrics provider instance."""
        if self._metrics_provider is None:
            try:
                self._metrics_provider = get_metrics_provider()
            except Exception as e:
                logger.warning(f"Failed to initialize metrics provider: {e}")
                self._metrics_provider = None
        return self._metrics_provider
    
    def register_handler(self, job_type: JobType, handler: Callable):
        """Register a handler function for a specific job type."""
        self._job_handlers[job_type.value] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")
    
    async def enqueue_job(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        priority: JobPriority = JobPriority.NORMAL,
        delay_seconds: int = 0,
        max_retries: int = 3
    ) -> str:
        """
        Enqueue a background job.
        
        Args:
            job_type: Type of job to enqueue
            payload: Job payload data
            user_id: User ID for the job
            org_id: Organization ID for the job
            priority: Job priority
            delay_seconds: Delay before job execution
            max_retries: Maximum retry attempts
            
        Returns:
            Job ID
        """
        if not self.queue_provider:
            raise RuntimeError("Queue provider not available")
        
        job_id = str(uuid.uuid4())
        
        # Prepare job data
        job_data = {
            "job_id": job_id,
            "job_type": job_type.value,
            "user_id": user_id,
            "org_id": org_id,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat(),
            "max_retries": max_retries
        }
        
        # Map priority to queue options
        priority_mapping = {
            JobPriority.LOW: {"priority": 1},
            JobPriority.NORMAL: {"priority": 5},
            JobPriority.HIGH: {"priority": 10},
            JobPriority.URGENT: {"priority": 15}
        }
        
        options = priority_mapping.get(priority, {"priority": 5})
        if delay_seconds > 0:
            options["delay_seconds"] = delay_seconds
        
        try:
            # Enqueue the job
            queue_job_id = await self.queue_provider.enqueue(
                queue_name=f"jobs.{job_type.value}",
                payload=job_data,
                options=options
            )
            
            logger.info(f"Enqueued job {job_id} of type {job_type.value} (queue_job_id: {queue_job_id})")
            
            # Record metrics
            if self.metrics_provider:
                try:
                    await self.metrics_provider.increment_counter(
                        "jobs_enqueued_total",
                        tags={"job_type": job_type.value, "priority": priority.value}
                    )
                except Exception as e:
                    logger.warning(f"Failed to record metrics: {e}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {job_id}: {e}")
            raise
    
    async def start_processing(self):
        """Start processing jobs from all registered queues."""
        if not self.queue_provider:
            raise RuntimeError("Queue provider not available")
        
        logger.info("Starting background job processing")
        
        # Start processing for each registered job type
        for job_type in self._job_handlers.keys():
            try:
                await self.queue_provider.process(
                    queue_name=f"jobs.{job_type}",
                    handler=self._create_job_handler(job_type)
                )
                logger.info(f"Started processing for job type: {job_type}")
            except Exception as e:
                logger.error(f"Failed to start processing for {job_type}: {e}")
    
    def _create_job_handler(self, job_type: str):
        """Create a wrapper handler for the queue provider."""
        async def handler(job_data):
            job_id = job_data.get("job_id", "unknown")
            
            try:
                logger.info(f"Processing job {job_id} of type {job_type}")
                
                # Record job start metrics
                start_time = datetime.utcnow()
                if self.metrics_provider:
                    try:
                        await self.metrics_provider.increment_counter(
                            "jobs_started_total",
                            tags={"job_type": job_type}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record start metrics: {e}")
                
                # Get the registered handler
                handler_func = self._job_handlers.get(job_type)
                if not handler_func:
                    raise ValueError(f"No handler registered for job type: {job_type}")
                
                # Execute the job
                result = await handler_func(job_data)
                
                # Record success metrics
                duration = (datetime.utcnow() - start_time).total_seconds()
                if self.metrics_provider:
                    try:
                        await self.metrics_provider.increment_counter(
                            "jobs_completed_total",
                            tags={"job_type": job_type, "status": "success"}
                        )
                        await self.metrics_provider.record_histogram(
                            "job_duration_seconds",
                            duration,
                            tags={"job_type": job_type}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record completion metrics: {e}")
                
                logger.info(f"Job {job_id} completed successfully in {duration:.2f}s")
                return {"status": "completed", "result": result}
                
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                
                # Record failure metrics
                if self.metrics_provider:
                    try:
                        await self.metrics_provider.increment_counter(
                            "jobs_completed_total",
                            tags={"job_type": job_type, "status": "failed"}
                        )
                    except Exception as metric_error:
                        logger.warning(f"Failed to record failure metrics: {metric_error}")
                
                # Return failure result (queue provider will handle retries)
                return {"status": "failed", "error": str(e)}
        
        return handler
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific job."""
        # This would typically query a job progress table in the database
        # For now, return a placeholder
        return {
            "job_id": job_id,
            "status": "unknown",
            "message": "Job status tracking not yet implemented"
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or running job."""
        # This would typically mark the job as cancelled in the database
        # and remove it from the queue if possible
        logger.warning(f"Job cancellation not yet implemented for job {job_id}")
        return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the job queues."""
        if not self.queue_provider:
            return {"error": "Queue provider not available"}
        
        # This would query queue statistics
        # Implementation depends on the queue provider
        return {
            "total_queued": 0,
            "total_active": 0,
            "total_completed": 0,
            "total_failed": 0,
            "by_type": {}
        }


# Global service instance
_background_job_service = BackgroundJobService()


def get_background_job_service() -> BackgroundJobService:
    """Get the global background job service instance."""
    return _background_job_service


# Job handler examples
async def search_execution_handler(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for search execution jobs."""
    job_id = job_data.get("job_id")
    payload = job_data.get("payload", {})
    
    logger.info(f"Executing search job {job_id} with payload: {payload}")
    
    # TODO: Implement actual search execution logic
    # This would call the search processing services
    
    return {"message": "Search execution completed", "results": {}}


async def export_generation_handler(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for export generation jobs."""
    job_id = job_data.get("job_id")
    payload = job_data.get("payload", {})
    
    logger.info(f"Generating export for job {job_id} with payload: {payload}")
    
    # TODO: Implement actual export generation logic
    # This would call the export services
    
    return {"message": "Export generation completed", "file_path": "exports/sample.csv"}


async def data_ingestion_handler(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for data ingestion jobs."""
    job_id = job_data.get("job_id")
    payload = job_data.get("payload", {})
    
    logger.info(f"Ingesting data for job {job_id} with payload: {payload}")
    
    # TODO: Implement actual data ingestion logic
    # This would call the data ingestion services
    
    return {"message": "Data ingestion completed", "records_processed": 0}


# Register default handlers
def register_default_handlers():
    """Register default job handlers."""
    service = get_background_job_service()
    service.register_handler(JobType.SEARCH_EXECUTION, search_execution_handler)
    service.register_handler(JobType.EXPORT_GENERATION, export_generation_handler)
    service.register_handler(JobType.DATA_INGESTION, data_ingestion_handler)


# Initialize default handlers
register_default_handlers()