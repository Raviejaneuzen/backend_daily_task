import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URL:
    raise ValueError("MONGO_URL is not set")
if not DB_NAME:
    raise ValueError("DB_NAME is not set")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def get_db():
    return db

# Collections
users_collection = db.users
tasks_collection = db.tasks 
personal_collection = db.personal # For 'Personal Space'
work_collection = db.work
meeting_collection = db.meetings
routine_collection = db.routines
notes_collection = db.notes
alerts_log_collection = db.alerts_log
credentials_collection = db.credentials
plans_collection = db.plans
