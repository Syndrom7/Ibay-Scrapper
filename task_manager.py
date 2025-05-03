# task_manager.py
import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import traceback
import logging

from fastapi import BackgroundTasks
from pydantic import BaseModel

from api_models import ScraperType
from scrapper_adapters import get_scraper_by_type
from models.task_log_model import TaskLogModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESUMING = "resuming"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"

class Task:
    def __init__(self, id: str, type: ScraperType, params: Dict = None):
        self.id = id
        self.type = type
        self.status = TaskStatus.CREATED
        self.progress = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.params = params or {}
        self.logs: List[Dict] = []
        self.error: Optional[str] = None
        self.stop_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.resume_event = asyncio.Event()
        self.resume_event.set()  # Initially not paused, so resume is set
        self.task_instance = None
        self.paused_at = None
    
    def add_log(self, message: str):
        """Add a log message with timestamp"""
        log_entry = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "level": "INFO"  # Default level
        }
        self.logs.append(log_entry)
        self.updated_at = datetime.now()
        return log_entry
    
    def update_progress(self, progress: float):
        """Update task progress (0-100)"""
        self.progress = min(max(progress, 0), 100)
        self.updated_at = datetime.now()

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.task_log_model = TaskLogModel()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
        
    async def get_all_tasks(self, limit=100, offset=0):
        """Get all tasks with pagination"""
        # Try to get tasks from database first
        try:
            return await self.task_log_model.get_all_tasks(limit, offset)
        except Exception as e:
            logger.error(f"Error getting tasks from database: {e}")
            # Fall back to in-memory tasks if database query fails
            tasks_list = []
            for task_id, task in list(self.tasks.items())[offset:offset+limit]:
                tasks_list.append({
                    "id": task.id,
                    "type": task.type.value,
                    "status": task.status.value,
                    "progress": task.progress,
                    "params": task.params,
                    "error": task.error,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at,
                    "paused_at": task.paused_at
                })
            return tasks_list
    
    async def create_task(
        self, 
        task_id: str, 
        scraper_type: ScraperType, 
        params: Dict = None,
        background_tasks: BackgroundTasks = None,
        websocket_manager = None
    ):
        """Create a new task and optionally start it in the background"""
        task = Task(id=task_id, type=scraper_type, params=params or {})
        self.tasks[task_id] = task
        
        # Create task in database
        await self.task_log_model.create_task(
            task_id=task_id,
            task_type=scraper_type.value,
            params=params or {}
        )
        
        # Add initial log
        await self.task_log_model.add_log(
            task_id=task_id,
            message=f"Task created with type {scraper_type.value} and parameters: {params}"
        )
        
        if background_tasks:
            background_tasks.add_task(
                self.run_task,
                task_id=task_id,
                websocket_manager=websocket_manager
            )
            
        return task
    
    async def run_task(self, task_id: str, websocket_manager = None):
        """Run a task and update its status"""
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # Custom logger to capture logs
        class TaskLogger:
            def __init__(self, task_manager, task, websocket_manager):
                self.task_manager = task_manager
                self.task = task
                self.websocket_manager = websocket_manager
            
            async def log(self, message, level="INFO"):
                # Add to in-memory logs
                log_entry = self.task.add_log(message)
                
                # Add to database
                await self.task_manager.task_log_model.add_log(task_id=self.task.id, message=message, level=level)
                
                if self.websocket_manager:
                    await self.websocket_manager.broadcast(
                        self.task.id,
                        {
                            "type": "log",
                            "message": message,
                            "timestamp": log_entry["timestamp"],
                            "level": level
                        }
                    )
                logger.info(f"[Task {self.task.id}] {message}")
            
            async def update_progress(self, progress, message=None):
                self.task.update_progress(progress)
                
                # Update progress in database
                await self.task_manager.task_log_model.update_task_status(
                    self.task.id, 
                    self.task.status.value,
                    progress
                )
                
                if self.websocket_manager:
                    data = {
                        "type": "progress",
                        "progress": progress
                    }
                    if message:
                        data["message"] = message
                        await self.log(message)
                    await self.websocket_manager.broadcast(self.task.id, data)
            
            async def update_status(self, status):
                self.task.status = status
                self.task.updated_at = datetime.now()
                
                # Update status in database
                await self.task_manager.task_log_model.update_task_status(
                    self.task.id, 
                    status.value
                )
                
                if self.websocket_manager:
                    await self.websocket_manager.broadcast(
                        self.task.id,
                        {
                            "type": "status",
                            "status": status.value
                        }
                    )
                    
            async def check_pause(self):
                """Check if the task should be paused and wait for resume if needed"""
                if self.task.pause_event.is_set():
                    await self.log(f"Task paused at progress {self.task.progress}%")
                    
                    # Wait for resume event
                    await self.task.resume_event.wait()
                    
                    # If stop was requested while paused, return True to indicate stop
                    if self.task.stop_event.is_set():
                        return True
                        
                    # If resumed, update status
                    if self.task.status == TaskStatus.PAUSED:
                        self.task.status = TaskStatus.RUNNING
                        await self.task_manager.task_log_model.update_task_status(
                            self.task.id, 
                            TaskStatus.RUNNING.value
                        )
                        
                        await self.log("Task resumed")
                        if self.websocket_manager:
                            await self.websocket_manager.broadcast(
                                self.task.id,
                                {
                                    "type": "status",
                                    "status": TaskStatus.RUNNING.value,
                                    "message": "Task resumed"
                                }
                            )
                
                # Return False to indicate not stopped
                return False
        
        # Create task logger
        task_logger = TaskLogger(self, task, websocket_manager)
        
        try:
            # Update status to running
            task.status = TaskStatus.RUNNING
            if websocket_manager:
                await websocket_manager.broadcast(
                    task_id,
                    {
                        "type": "status",
                        "status": TaskStatus.RUNNING.value,
                        "message": f"Task {task_id} started"
                    }
                )
            
            # Get the appropriate scraper
            scraper = get_scraper_by_type(
                task.type, 
                task_logger=task_logger,
                stop_event=task.stop_event,
                pause_event=task.pause_event,
                resume_event=task.resume_event
            )
            
            if not scraper:
                raise ValueError(f"Scraper for type {task.type} not found")
            
            # Store reference to the scraper instance
            task.task_instance = scraper
            
            # Run the scraper with parameters
            await task_logger.log(f"Starting {task.type.value} with parameters: {task.params}")
            
            result = await scraper.run(**task.params)
            
            # Check if stopped
            if task.stop_event.is_set():
                task.status = TaskStatus.STOPPED
                await task_logger.log("Task was stopped")
                if websocket_manager:
                    await websocket_manager.broadcast(
                        task_id,
                        {
                            "type": "status",
                            "status": TaskStatus.STOPPED.value,
                            "message": "Task stopped"
                        }
                    )
            else:
                # Mark as completed
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                await task_logger.log("Task completed successfully")
                if websocket_manager:
                    await websocket_manager.broadcast(
                        task_id,
                        {
                            "type": "status",
                            "status": TaskStatus.COMPLETED.value,
                            "message": "Task completed",
                            "result": result
                        }
                    )
        
        except Exception as e:
            # Handle exception
            error_details = traceback.format_exc()
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await task_logger.log(f"Task failed: {str(e)}")
            await task_logger.log(f"Error details: {error_details}")
            
            if websocket_manager:
                await websocket_manager.broadcast(
                    task_id,
                    {
                        "type": "status",
                        "status": TaskStatus.FAILED.value,
                        "message": f"Task failed: {str(e)}"
                    }
                )
            
            logger.error(f"Error in task {task_id}: {str(e)}\n{error_details}")
    
    async def stop_task(self, task_id: str):
        """Stop a running task"""
        task = self.get_task(task_id)
        if task and (task.status == TaskStatus.RUNNING or task.status == TaskStatus.PAUSED):
            # Set the stop event to signal the task to stop
            task.stop_event.set()
            task.status = TaskStatus.STOPPING
            task.updated_at = datetime.now()
            
            # If task was paused, also set resume event to allow it to process the stop
            if task.status == TaskStatus.PAUSED:
                task.resume_event.set()
            
            # If the task has a reference to the running instance, try to close it
            if task.task_instance and hasattr(task.task_instance, 'close'):
                try:
                    await task.task_instance.close()
                except Exception as e:
                    logger.error(f"Error closing task instance: {e}")
            
            # Update status in database
            await self.task_log_model.update_task_status(
                task_id, 
                TaskStatus.STOPPING.value
            )
            
            return True
        return False
        
    async def pause_task(self, task_id: str):
        """Pause a running task"""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            # Set the pause event to signal the task to pause
            task.pause_event.set()
            task.resume_event.clear()
            task.status = TaskStatus.PAUSED
            task.paused_at = datetime.now()
            task.updated_at = datetime.now()
            
            # Update status in database
            await self.task_log_model.update_task_status(
                task_id, 
                TaskStatus.PAUSED.value,
                paused_at=task.paused_at
            )
            
            return True
        return False
    
    async def resume_task(self, task_id: str):
        """Resume a paused task"""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PAUSED:
            # Clear the pause event and set the resume event
            task.pause_event.clear()
            task.resume_event.set()
            task.status = TaskStatus.RESUMING
            task.updated_at = datetime.now()
            
            # Update status in database
            await self.task_log_model.update_task_status(
                task_id, 
                TaskStatus.RESUMING.value
            )
            
            # Add a log about resuming
            if task.paused_at:
                pause_duration = (datetime.now() - task.paused_at).total_seconds()
                await self.task_log_model.add_log(
                    task_id, 
                    f"Task resumed after being paused for {pause_duration:.2f} seconds"
                )
            else:
                await self.task_log_model.add_log(task_id, "Task resumed")
            
            return True
        return False