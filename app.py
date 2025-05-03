# app.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
import asyncio
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import logging
import json
from datetime import datetime

# Import task manager and models
from task_manager import TaskManager, Task, TaskStatus
from api_models import (
    ScraperType, 
    TaskCreate,
    TaskResponse,
    CategoryRequest,
    ProductCountRequest,
    CategoryProductLinkRequest,
    ProductDetailRequest,
    SellerRequest,
    ProductUpdateRequest,
    StaleProductUpdateRequest
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ibay Scraper API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize task manager
task_manager = TaskManager()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

# Dependency to get task by ID
async def get_task_by_id(task_id: str) -> Task:
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        # Send initial task status upon connection
        task = await task_manager.get_task(task_id)
        if task:
            await websocket.send_json({
                "type": "status",
                "status": task.status.value,
                "progress": task.progress,
                "message": f"Connected to task {task_id}"
            })
            
            try:
                # Get logs from database and send them
                log_data = await task_manager.task_log_model.get_task_logs(task_id, limit=100)
                for log in log_data["logs"]:
                    await websocket.send_json({
                        "type": "log",
                        "message": log["message"],
                        "timestamp": log["timestamp"],
                        "level": log.get("level", "INFO")
                    })
            except Exception as e:
                logger.error(f"Error sending logs via WebSocket: {e}")
                # Fallback to in-memory logs
                if task.logs:
                    for log in task.logs:
                        await websocket.send_json({
                            "type": "log",
                            "message": log["message"],
                            "timestamp": log["timestamp"],
                            "level": log.get("level", "INFO")
                        })
        
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            
            # Client can send commands through websocket
            if data == "stop":
                await task_manager.stop_task(task_id)
                await websocket.send_json({
                    "type": "status",
                    "status": "STOPPING",
                    "message": "Stopping task..."
                })
            elif data == "pause":
                await task_manager.pause_task(task_id)
                await websocket.send_json({
                    "type": "status",
                    "status": "PAUSED",
                    "message": "Pausing task..."
                })
            elif data == "resume":
                await task_manager.resume_task(task_id)
                await websocket.send_json({
                    "type": "status",
                    "status": "RESUMING",
                    "message": "Resuming task..."
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, task_id)

# Endpoints for listing available scrapers
@app.get("/api/scrapers", response_model=List[str])
async def list_scrapers():
    """List all available scrapers"""
    return [scraper.value for scraper in ScraperType]

# Endpoints for task management
@app.get("/api/tasks", response_model=List[TaskResponse])
async def list_tasks(limit: int = 100, offset: int = 0):
    """List all tasks with their status"""
    try:
        tasks = await task_manager.get_all_tasks(limit, offset)
        return [TaskResponse(
            id=task["id"],
            type=task["type"],
            status=task["status"],
            progress=task["progress"],
            created_at=task["created_at"],
            updated_at=task["updated_at"],
            params=task["params"]
        ) for task in tasks]
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        # Fallback to in-memory tasks if database query fails
        return [TaskResponse(
            id=task_id,
            type=task.type.value,
            status=task.status.value,
            progress=task.progress,
            created_at=task.created_at,
            updated_at=task.updated_at,
            params=task.params
        ) for task_id, task in task_manager.tasks.items()][offset:offset+limit]

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task: Task = Depends(get_task_by_id)):
    """Get details of a specific task"""
    return TaskResponse(
        id=task.id,
        type=task.type.value,
        status=task.status.value,
        progress=task.progress,
        created_at=task.created_at,
        updated_at=task.updated_at,
        params=task.params
    )

@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task: Task = Depends(get_task_by_id)):
    """Stop a running task"""
    if task.status not in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Task must be running or paused to stop it")
    
    await task_manager.stop_task(task.id)
    return {"message": f"Task {task.id} is being stopped"}

@app.post("/api/tasks/{task_id}/pause")
async def pause_task(task: Task = Depends(get_task_by_id)):
    """Pause a running task"""
    if task.status != TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task is not running")
    
    success = await task_manager.pause_task(task.id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not pause task")
        
    return {"message": f"Task {task.id} is being paused"}

@app.post("/api/tasks/{task_id}/resume")
async def resume_task(task: Task = Depends(get_task_by_id)):
    """Resume a paused task"""
    if task.status != TaskStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Task is not paused")
    
    success = await task_manager.resume_task(task.id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not resume task")
        
    return {"message": f"Task {task.id} is being resumed"}

@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, limit: int = 100, offset: int = 0):
    """Get logs for a specific task"""
    # Verify the task exists
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
    # Get logs from database
    log_data = await task_manager.task_log_model.get_task_logs(task_id, limit, offset)
    return log_data

# Endpoints for each scraper type
@app.post("/api/scrapers/category", response_model=TaskResponse)
async def start_category_scraper(background_tasks: BackgroundTasks):
    """Start the category scraper"""
    task_id = str(uuid.uuid4())
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.CATEGORY,
        params={},
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.CATEGORY.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params={}
    )

@app.post("/api/scrapers/product-count", response_model=TaskResponse)
async def start_product_count_scraper(background_tasks: BackgroundTasks):
    """Start the product count scraper"""
    task_id = str(uuid.uuid4())
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.PRODUCT_COUNT,
        params={},
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.PRODUCT_COUNT.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params={}
    )

@app.post("/api/scrapers/category-product-link", response_model=TaskResponse)
async def start_category_product_link_scraper(background_tasks: BackgroundTasks):
    """Start the category product link scraper"""
    task_id = str(uuid.uuid4())
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.CATEGORY_PRODUCT_LINK,
        params={},
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.CATEGORY_PRODUCT_LINK.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params={}
    )

@app.post("/api/scrapers/product-detail", response_model=TaskResponse)
async def start_product_detail_scraper(background_tasks: BackgroundTasks):
    """Start the product detail scraper"""
    task_id = str(uuid.uuid4())
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.PRODUCT_DETAIL,
        params={},
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.PRODUCT_DETAIL.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params={}
    )

@app.post("/api/scrapers/seller", response_model=TaskResponse)
async def start_seller_scraper(background_tasks: BackgroundTasks):
    """Start the seller scraper"""
    task_id = str(uuid.uuid4())
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.SELLER,
        params={},
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.SELLER.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params={}
    )

@app.post("/api/scrapers/product-updater", response_model=TaskResponse)
async def start_product_updater(request: ProductUpdateRequest, background_tasks: BackgroundTasks):
    """Start the product updater with specified parameters"""
    task_id = str(uuid.uuid4())
    params = {
        "days": request.days,
        "category_id": request.category_id
    }
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.PRODUCT_UPDATER,
        params=params,
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.PRODUCT_UPDATER.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params=params
    )

@app.post("/api/scrapers/stale-product-updater", response_model=TaskResponse)
async def start_stale_product_updater(request: StaleProductUpdateRequest, background_tasks: BackgroundTasks):
    """Start the stale product updater with specified parameters"""
    task_id = str(uuid.uuid4())
    params = {
        "days": request.days,
        "category_id": request.category_id,
        "status": request.status,
        "limit": request.limit
    }
    await task_manager.create_task(
        task_id=task_id,
        scraper_type=ScraperType.STALE_PRODUCT_UPDATER,
        params=params,
        background_tasks=background_tasks,
        websocket_manager=manager
    )
    return TaskResponse(
        id=task_id,
        type=ScraperType.STALE_PRODUCT_UPDATER.value,
        status=TaskStatus.CREATED.value,
        progress=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        params=params
    )

# Home page
@app.get("/")
async def root():
    return {"message": "Welcome to Ibay Scraper API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)