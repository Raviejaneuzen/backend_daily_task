from fastapi import APIRouter, Depends
from services.ai_service import process_user_input
from models import AIChatRequest
from routes.users import get_current_user
from datetime import datetime, timedelta
from database import (
    tasks_collection, work_collection, 
    meeting_collection, routine_collection,
    personal_collection, credentials_collection
)
from services.email_service import send_email
from services.whatsapp_service import send_whatsapp_message
from routes.credentials import fernet
import urllib.parse

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/chat")
async def chat(request: AIChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    past_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    future_date = (datetime.now() + timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    
    all_context_tasks = []
    collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection]
    
    for coll in collections:
        cursor = coll.find({
            "user_id": user_id,
            "date": {"$gte": past_date, "$lte": future_date}
        })
        async for task in cursor:
            task["id"] = str(task["_id"])
            del task["_id"]
            all_context_tasks.append(task)
            
    # Fetch and decrypt credentials for context
    all_context_credentials = []
    cursor_creds = credentials_collection.find({"user_id": user_id})
    async for cred in cursor_creds:
        cred["id"] = str(cred["_id"])
        del cred["_id"]
        # Decrypt password for AI context
        if "password" in cred and cred["password"]:
            try:
                cred["password"] = fernet.decrypt(cred["password"].encode()).decode()
            except Exception:
                pass
        all_context_credentials.append(cred)
            
    result = await process_user_input(request.text, all_context_tasks, all_context_credentials, request.image)
    
    # Process dispatch_schedule if present in actions
    if "actions" in result:
        for action in result["actions"]:
            if action.get("type") == "dispatch_schedule":
                summary = action.get("summary", "Your today's schedule is ready.")
                
                # 1. Send Email
                print(f"DEBUG: Attempting to send schedule email to {current_user['email']}")
                email_success = send_email(current_user["email"], "Today's Schedule Summary - Dhana Durga", summary)
                print(f"DEBUG: Email success status: {email_success}")
                
                # 2. Send Automated WhatsApp (Background)
                print(f"DEBUG: Attempting to send automated WhatsApp message")
                whatsapp_number = "whatsapp:+917013666788" # Direct target as requested
                wa_success = send_whatsapp_message(whatsapp_number, summary)
                print(f"DEBUG: WhatsApp success status: {wa_success}")
                
                # 3. Add a direct WhatsApp link for the frontend to open
                encoded_msg = urllib.parse.quote(summary)
                action["whatsapp_link"] = f"https://wa.me/917013666788?text={encoded_msg}"
                print(f"DEBUG: Generated manual WhatsApp link: {action['whatsapp_link']}")
                
            elif action.get("type") == "dispatch_credentials":
                summary = action.get("summary", "Here are the requested credentials.")
                
                # 1. Send Email
                print(f"DEBUG: Attempting to send credentials email to {current_user['email']}")
                email_success = send_email(current_user["email"], "Your Requested Credentials - Dhana Durga", summary)
                print(f"DEBUG: Credentials Email success status: {email_success}")
                
                # 2. Send Automated WhatsApp (Background)
                print(f"DEBUG: Attempting to send automated credentials WhatsApp message")
                whatsapp_number = "whatsapp:+917013666788" 
                wa_success = send_whatsapp_message(whatsapp_number, summary)
                print(f"DEBUG: Credentials WhatsApp success status: {wa_success}")
                
                # 3. Add a direct WhatsApp link for the frontend
                encoded_msg = urllib.parse.quote(summary)
                action["whatsapp_link"] = f"https://wa.me/917013666788?text={encoded_msg}"
                print(f"DEBUG: Generated credentials manual WhatsApp link: {action['whatsapp_link']}")
                
    return result
