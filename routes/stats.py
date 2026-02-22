from fastapi import APIRouter, Depends
from database import tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection, plans_collection
from routes.users import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/")
async def get_stats(category: str = None, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Collection mapping
    mapping = {
        "work": [work_collection],
        "meeting": [meeting_collection],
        "routine": [routine_collection],
        "task": [tasks_collection],
        "personal": [personal_collection],
        "personal space": [personal_collection],
        "plan": [plans_collection]
    }
    
    # Determine which collections to query
    if category and category.lower() in mapping:
        active_collections = mapping[category.lower()]
    elif category and category.lower() in ["personal", "personal space", "task"]:
        # If frontend sends 'task', it might mean 'personal space'
        active_collections = [personal_collection, tasks_collection]
    else:
        active_collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection]
    
    total_tasks = 0
    completed_tasks = 0
    today_total = 0
    today_completed = 0
    
    for coll in active_collections:
        total_tasks += await coll.count_documents({"user_id": user_id})
        completed_tasks += await coll.count_documents({"user_id": user_id, "status": "Completed"})
        today_total += await coll.count_documents({"user_id": user_id, "date": today_str})
        today_completed += await coll.count_documents({"user_id": user_id, "date": today_str, "status": "Completed"})
    
    completion_percentage = (today_completed / today_total * 100) if today_total > 0 else 0
    
    # Routine-specific stats (stays in routine_collection)
    routine_total_week = await routine_collection.count_documents({
        "user_id": user_id, 
        "date": {"$gte": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")}
    })
    routine_completed_week = await routine_collection.count_documents({
        "user_id": user_id, 
        "status": "Completed",
        "date": {"$gte": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")}
    })
    weekly_consistency = (routine_completed_week / routine_total_week * 100) if routine_total_week > 0 else 0

    # Calculate Streak
    streak = 0
    for i in range(30):
        check_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_completed = await routine_collection.count_documents({
            "user_id": user_id,
            "status": "Completed",
            "date": check_date
        })
        if day_completed > 0:
            streak += 1
        else:
            if i > 0: break
    
    # Monthly Target
    first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    monthly_completed = await routine_collection.count_documents({
        "user_id": user_id,
        "status": "Completed",
        "date": {"$gte": first_of_month}
    })
    monthly_total = await routine_collection.count_documents({
        "user_id": user_id,
        "date": {"$gte": first_of_month}
    })

    # Plan/Trip specific stats
    plans_total = await plans_collection.count_documents({"user_id": user_id})
    plans_completed = await plans_collection.count_documents({"user_id": user_id, "status": "Completed"})
    plans_upcoming = await plans_collection.count_documents({"user_id": user_id, "date": {"$gte": today_str}, "status": {"$ne": "Completed"}})

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "today": {
            "total": today_total,
            "completed": today_completed,
            "percentage": round(completion_percentage, 2)
        },
        "routine": {
            "weekly_consistency": round(weekly_consistency, 0),
            "streak": streak,
            "monthly_completed": monthly_completed,
            "monthly_total": monthly_total
        },
        "plan": {
            "total": plans_total,
            "completed": plans_completed,
            "upcoming": plans_upcoming
        },
        "status": "Success"
    }

@router.get("/weekly")
async def get_weekly_stats(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    today = datetime.now()
    
    collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection]
    weekly_data = []
    
    for i in range(7):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        total = 0
        completed = 0
        
        for coll in collections:
            total += await coll.count_documents({"user_id": user_id, "date": date})
            completed += await coll.count_documents({"user_id": user_id, "date": date, "status": "Completed"})
            
        weekly_data.append({
            "date": date,
            "total": total,
            "completed": completed
        })
        
    return weekly_data
