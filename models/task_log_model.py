# models/task_log_model.py

import json
from datetime import datetime
from models.base_model import BaseModel

class TaskLogModel(BaseModel):
    """Model for handling scraper task logs in the database"""
    
    async def create_task(self, task_id, task_type, params=None):
        """
        Create a new scraper task in the database
        
        Args:
            task_id (str): Task ID
            task_type (str): Task type
            params (dict, optional): Task parameters
        """
        try:
            query = """
                INSERT INTO scraper_tasks (id, type, status, params)
                VALUES (%s, %s, %s, %s)
            """
            # Convert params to JSON string
            params_json = json.dumps(params or {})
            await self.execute_query(query, (task_id, task_type, 'created', params_json), fetch=False)
        except Exception as e:
            print(f"Error creating task in database: {e}")
    
    async def update_task_status(self, task_id, status, progress=None, error=None, paused_at=None):
        """
        Update a task's status in the database
        
        Args:
            task_id (str): Task ID
            status (str): New status
            progress (float, optional): Task progress (0-100)
            error (str, optional): Error message if any
            paused_at (datetime, optional): When the task was paused
        """
        try:
            # Build the update query dynamically based on provided parameters
            update_parts = ["status = %s", "updated_at = NOW()"]
            params = [status]
            
            if progress is not None:
                update_parts.append("progress = %s")
                params.append(progress)
            
            if error is not None:
                update_parts.append("error = %s")
                params.append(error)
            
            if paused_at is not None:
                update_parts.append("paused_at = %s")
                params.append(paused_at)
            
            query = f"""
                UPDATE scraper_tasks 
                SET {', '.join(update_parts)}
                WHERE id = %s
            """
            params.append(task_id)
            
            await self.execute_query(query, tuple(params), fetch=False)
        except Exception as e:
            print(f"Error updating task status in database: {e}")
    
    async def add_log(self, task_id, message, level="INFO"):
        """
        Add a log message to the database
        
        Args:
            task_id (str): Task ID
            message (str): Log message
            level (str, optional): Log level (INFO, WARNING, ERROR)
        """
        try:
            query = """
                INSERT INTO scraper_logs (task_id, message, level)
                VALUES (%s, %s, %s)
            """
            await self.execute_query(query, (task_id, message, level), fetch=False)
        except Exception as e:
            print(f"Error adding log to database: {e}")
    
    async def get_task(self, task_id):
        """
        Get a task from the database
        
        Args:
            task_id (str): Task ID
            
        Returns:
            dict or None: Task information or None if not found
        """
        try:
            query = """
                SELECT id, type, status, progress, params, error, 
                       created_at, updated_at, paused_at
                FROM scraper_tasks
                WHERE id = %s
            """
            rows = await self.execute_query(query, (task_id,))
            
            if not rows:
                return None
                
            row = rows[0]
            return {
                "id": row[0],
                "type": row[1],
                "status": row[2],
                "progress": row[3],
                "params": json.loads(row[4]) if row[4] else {},
                "error": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "paused_at": row[8]
            }
        except Exception as e:
            print(f"Error getting task from database: {e}")
            return None
    
    async def get_all_tasks(self, limit=100, offset=0):
        """
        Get all tasks from the database
        
        Args:
            limit (int, optional): Maximum number of tasks to return
            offset (int, optional): Offset for pagination
            
        Returns:
            list: List of task dictionaries
        """
        try:
            query = """
                SELECT id, type, status, progress, params, error, 
                       created_at, updated_at, paused_at
                FROM scraper_tasks
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            rows = await self.execute_query(query, (limit, offset))
            
            tasks = []
            for row in rows:
                tasks.append({
                    "id": row[0],
                    "type": row[1],
                    "status": row[2],
                    "progress": row[3],
                    "params": json.loads(row[4]) if row[4] else {},
                    "error": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "paused_at": row[8]
                })
            
            return tasks
        except Exception as e:
            print(f"Error getting all tasks from database: {e}")
            return []
    
    async def get_task_logs(self, task_id, limit=100, offset=0):
        """
        Get logs for a specific task
        
        Args:
            task_id (str): Task ID
            limit (int, optional): Maximum number of logs to return
            offset (int, optional): Offset for pagination
            
        Returns:
            list: List of log dictionaries
        """
        try:
            # Get total count first
            count_query = """
                SELECT COUNT(*) FROM scraper_logs
                WHERE task_id = %s
            """
            count_rows = await self.execute_query(count_query, (task_id,))
            total = count_rows[0][0] if count_rows else 0
            
            # Get the logs
            query = """
                SELECT id, message, timestamp, level
                FROM scraper_logs
                WHERE task_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            rows = await self.execute_query(query, (task_id, limit, offset))
            
            logs = []
            for row in rows:
                logs.append({
                    "id": row[0],
                    "message": row[1],
                    "timestamp": row[2].isoformat(),
                    "level": row[3]
                })
            
            return {
                "logs": logs,
                "total": total
            }
        except Exception as e:
            print(f"Error getting task logs from database: {e}")
            return {"logs": [], "total": 0}