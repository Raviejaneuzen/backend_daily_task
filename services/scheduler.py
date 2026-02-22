from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
from database import (
    tasks_collection, work_collection, 
    meeting_collection, routine_collection,
    personal_collection,
    users_collection, alerts_log_collection
)
from services.email_service import send_email
from services.whatsapp_service import send_whatsapp_message
from bson import ObjectId

scheduler = AsyncIOScheduler()
activity_collections = [tasks_collection, work_collection, meeting_collection, routine_collection, personal_collection]

async def check_reminders():
    # Check for items starting in the next 10 minutes that haven't been alerted
    now = datetime.now()
    ten_mins_later = now + timedelta(minutes=10)
    
    now_str = now.strftime("%H:%M")
    ten_mins_later_str = ten_mins_later.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")
    
    for coll in activity_collections:
        cursor = coll.find({
            "date": today_str,
            "status": "Pending",
            "start_time": {"$gte": now_str, "$lte": ten_mins_later_str}
        })
        
        async for task in cursor:
            task_id = str(task["_id"])
            user_id = task["user_id"]
            
            # Check if alert already sent
            already_sent = await alerts_log_collection.find_one({
                "task_id": task_id,
                "user_id": user_id,
                "method": "email"
            })
            
            if not already_sent:
                user = await users_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    subject = f"Reminder: {task['title']}"
                    body = f"Your {task['category']} '{task['title']}' starts at {task['start_time']}."
                    success = send_email(user["email"], subject, body)
                    
                    if success:
                        await alerts_log_collection.insert_one({
                            "user_id": user_id,
                            "task_id": task_id,
                            "alert_sent_at": datetime.utcnow(),
                            "method": "email"
                        })

async def check_whatsapp_reminders():
    # Check for items starting in exactly 20 minutes that haven't been alerted via WhatsApp
    now = datetime.now()
    twenty_mins_later = now + timedelta(minutes=20)
    
    twenty_mins_later_str = twenty_mins_later.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")
    
    for coll in activity_collections:
        cursor = coll.find({
            "date": today_str,
            "status": "Pending",
            "start_time": twenty_mins_later_str
        })
        
        async for task in cursor:
            task_id = str(task["_id"])
            user_id = task["user_id"]
            
            # Check if alert already sent for WhatsApp exactly
            already_sent = await alerts_log_collection.find_one({
                "task_id": task_id,
                "user_id": user_id,
                "method": "whatsapp"
            })
            
            if not already_sent:
                # Format the WhatsApp message
                body = f"*Reminder*\nYour {task['category']} '{task['title']}' starts in 20 minutes at {task['start_time']}."
                
                # Target WhatsApp number
                whatsapp_number = "whatsapp:+917013666788"
                
                success = send_whatsapp_message(whatsapp_number, body)
                
                if success:
                    await alerts_log_collection.insert_one({
                        "user_id": user_id,
                        "task_id": task_id,
                        "alert_sent_at": datetime.utcnow(),
                        "method": "whatsapp"
                    })

async def send_daily_summaries():
    # Send a summary of today's work at the end of the day
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    cursor = users_collection.find()
    async for user in cursor:
        user_id = str(user["_id"])
        
        # Aggregate from all collections
        all_activities = []
        for coll in activity_collections:
            act_cursor = coll.find({"user_id": user_id, "date": today_str})
            async for act in act_cursor:
                all_activities.append(act)
            
        completed = [a for a in all_activities if a["status"] == "Completed"]
        pending = [a for a in all_activities if a["status"] == "Pending"]
        
        if all_activities:
            subject = f"Your Daily Summary for {today_str}"
            body = f"Hello {user['name']},\n\nHere is your productivity report for today:\n\n"
            body += f"✅ Completed: {len(completed)}\n"
            body += f"⏳ Pending: {len(pending)}\n\n"
            
            whatsapp_body = f"*Daily Summary for {today_str}*\n\n✅ Completed: {len(completed)}\n⏳ Pending: {len(pending)}\n\n"
            
            if completed:
                items_text = "\n".join([f"- {a['title']} ({a['category']})" for a in completed])
                body += "Completed Items:\n" + items_text + "\n\n"
                whatsapp_body += "*Completed Items:*\n" + items_text + "\n\n"
            if pending:
                items_text = "\n".join([f"- {a['title']} ({a.get('start_time', 'No time')})" for a in pending])
                body += "Still Pending:\n" + items_text + "\n\n"
                whatsapp_body += "*Still Pending:*\n" + items_text + "\n\n"
            
            body += "Keep up the great work!"
            whatsapp_body += "Keep up the great work!"
            
            send_email(user["email"], subject, body)
            send_whatsapp_message("whatsapp:+917013666788", whatsapp_body)

def start_scheduler():
    # misfire_grace_time allows the job to run even if missed by up to 60 seconds (useful for restarts)
    scheduler.add_job(check_reminders, "interval", minutes=1, misfire_grace_time=60)
    scheduler.add_job(check_whatsapp_reminders, "interval", minutes=1, misfire_grace_time=60)
    # Run daily summary at 9 PM
    scheduler.add_job(send_daily_summaries, "cron", hour=21, minute=0, misfire_grace_time=3600)
    if not scheduler.running:
        scheduler.start()
