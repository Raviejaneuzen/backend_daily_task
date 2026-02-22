from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import List
from database import notes_collection
from models import NoteCreate, NoteResponse
from routes.users import get_current_user

router = APIRouter(prefix="/notes", tags=["notes"])

@router.post("/", response_model=NoteResponse)
async def create_note(note: NoteCreate, current_user: dict = Depends(get_current_user)):
    note_dict = note.dict()
    note_dict["user_id"] = str(current_user["_id"])
    result = await notes_collection.insert_one(note_dict)
    note_dict["id"] = str(result.inserted_id)
    return note_dict

@router.get("/", response_model=List[NoteResponse])
async def get_notes(current_user: dict = Depends(get_current_user)):
    cursor = notes_collection.find({"user_id": str(current_user["_id"])})
    notes = []
    async for note in cursor:
        note["id"] = str(note["_id"])
        notes.append(note)
    return notes
