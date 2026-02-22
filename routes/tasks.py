from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timedelta
from database import (
    tasks_collection, work_collection, 
    meeting_collection, routine_collection,
    personal_collection, plans_collection
)
from models import TaskCreate, TaskResponse, TaskUpdate
from routes.users import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

def get_collection_for_category(category: str):
    """Router for segmented collections - Case Insensitive"""
    if not category:
        return tasks_collection

    cat_lower = category.lower()
    mapping = {
        "work": work_collection,
        "meeting": meeting_collection,
        "routine": routine_collection,
        "task": tasks_collection,
        "personal": personal_collection,
        "personal space": personal_collection,
        "plan": plans_collection
    }
    return mapping.get(cat_lower, tasks_collection)

@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    try:
        task_dict = task.dict()
        task_dict["user_id"] = str(current_user["_id"])
        
        # Determine target collection
        coll = get_collection_for_category(task.category)
        
        result = await coll.insert_one(task_dict)
        task_dict["id"] = str(result.inserted_id)
        return task_dict
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    category: Optional[str] = None,
    date: Optional[str] = None, 
    status: Optional[str] = None, 
    period: Optional[str] = None, # 'today', 'weekly'
    current_user: dict = Depends(get_current_user)
):
    user_query = {"user_id": str(current_user["_id"])}
    
    # Filter by date/period
    date_query = {}
    if period == "today":
        date_query["date"] = datetime.now().strftime("%Y-%m-%d")
    elif period == "weekly":
        today = datetime.now()
        next_week = today + timedelta(days=7)
        date_query["date"] = {
            "$gte": today.strftime("%Y-%m-%d"),
            "$lte": next_week.strftime("%Y-%m-%d")
        }
    elif date:
        date_query["date"] = date
        
    status_query = {"status": status} if status else {}
    
    final_query = {**user_query, **date_query, **status_query}

    # If a specific category is requested, just search that collection
    if category:
        coll = get_collection_for_category(category)
        cursor = coll.find(final_query)
        tasks = []
        async for task in cursor:
            task["id"] = str(task["_id"])
            tasks.append(task)
        return tasks
    
    # Otherwise, aggregate from all (for "All Activities" view)
    all_tasks = []
    collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection, plans_collection]
    for coll in collections:
        cursor = coll.find(final_query)
        async for task in cursor:
            task["id"] = str(task["_id"])
            all_tasks.append(task)
    
    return all_tasks

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_update: TaskUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in task_update.dict().items() if v is not None}
    
    # Since we split collections, we need to know where it is. 
    # Try the most likely one (category in update) or check all.
    target_coll = None
    if task_update.category:
        target_coll = get_collection_for_category(task_update.category)
        result = await target_coll.update_one(
            {"_id": ObjectId(task_id), "user_id": str(current_user["_id"])},
            {"$set": update_data}
        )
        if result.matched_count > 0:
            updated_task = await target_coll.find_one({"_id": ObjectId(task_id)})
            updated_task["id"] = str(updated_task["_id"])
            return updated_task

    # Fallback: Search all collections if category wasn't provided or not found in target
    collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection, plans_collection]
    for coll in collections:
        result = await coll.update_one(
            {"_id": ObjectId(task_id), "user_id": str(current_user["_id"])},
            {"$set": update_data}
        )
        if result.matched_count > 0:
            updated_task = await coll.find_one({"_id": ObjectId(task_id)})
            updated_task["id"] = str(updated_task["_id"])
            return updated_task
            
    raise HTTPException(status_code=404, detail="Task not found")

@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    # Check all collections
    collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection, plans_collection]
    for coll in collections:
        result = await coll.delete_one({"_id": ObjectId(task_id), "user_id": str(current_user["_id"])})
        if result.deleted_count > 0:
            return {"message": "Task deleted"}
            
    raise HTTPException(status_code=404, detail="Task not found")
