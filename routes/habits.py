from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import List
from database import db
from models import HabitCreate, HabitResponse
from routes.users import get_current_user

router = APIRouter(prefix="/habits", tags=["habits"])
habits_collection = db.habits

@router.post("/", response_model=HabitResponse)
async def create_habit(habit: HabitCreate, current_user: dict = Depends(get_current_user)):
    habit_dict = habit.dict()
    habit_dict["user_id"] = str(current_user["_id"])
    result = await habits_collection.insert_one(habit_dict)
    habit_dict["id"] = str(result.inserted_id)
    return habit_dict

@router.get("/", response_model=List[HabitResponse])
async def get_habits(current_user: dict = Depends(get_current_user)):
    cursor = habits_collection.find({"user_id": str(current_user["_id"])})
    habits = []
    async for habit in cursor:
        habit["id"] = str(habit["_id"])
        habits.append(habit)
    return habits

@router.put("/{habit_id}/toggle/{date}")
async def toggle_habit(habit_id: str, date: str, current_user: dict = Depends(get_current_user)):
    habit = await habits_collection.find_one({"_id": ObjectId(habit_id), "user_id": str(current_user["_id"])})
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    
    status = habit.get("status", {})
    status[date] = not status.get(date, False)
    
    await habits_collection.update_one(
        {"_id": ObjectId(habit_id)},
        {"$set": {"status": status}}
    )
    return {"status": status[date]}

@router.delete("/{habit_id}")
async def delete_habit(habit_id: str, current_user: dict = Depends(get_current_user)):
    result = await habits_collection.delete_one({"_id": ObjectId(habit_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Habit not found")
    return {"message": "Habit deleted"}
