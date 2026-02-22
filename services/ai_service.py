import os
import json
import re
import google.generativeai as genai
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

client = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        client = genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        print(f"Warning: Failed to initialize Gemini Client: {e}")

# Robust Configuration
generate_config = genai.types.GenerationConfig(
    temperature=0.1,
    top_p=0.95,
    top_k=0,
    max_output_tokens=8192,
)

if "1.5" in GEMINI_MODEL or "2.0" in GEMINI_MODEL or "flash" in GEMINI_MODEL:
    generate_config.response_mime_type = "application/json"

SYSTEM_PROMPT = """
You are Dhana, an advanced agentic productivity assistant.
Your job is to manage a high-fidelity workspace. 

**Core Capabilities**:
1. **Dynamic Schema**: You can add/update any field. Use the `metadata` dictionary for custom data (e.g., "cost", "location", "destination", "file_link").
2. **Rich Data Extraction**: Always look for `description`, `notes`, `remarks`, `path` (links/files), and `end_date` (for multi-day events).
3. **Agentic Actions**:
   - `add_task`: Use for Tasks, Work, Meetings, Routine, or Plan (Trips/Itineraries).
   - `update_task`: Modify existing items by `target_title`.
   - `delete_task`: Remove items.
   - `set_timer`: Control focus session.
   - `manage_credential`: Store or manage user credentials/logins (add/update/delete).
   - `dispatch_schedule`: Send the today/tomorrow schedule summary to the user's email and WhatsApp.
   - `dispatch_credentials`: Send requested credentials (passwords, logins, etc.) to the user's email and WhatsApp.

**Handling Schedule Queries & Conflicts**:
1. **Overlap Prevention**: Before adding a task, check if the requested time slot (Start Time to End Time) is already occupied by another task on that date. 
2. **Strict Rule**: If a slot is taken, DO NOT issue an `add_task` action. Instead:
   - State clearly in the `reply`: "This slot is already fixed for [Existing Task Title]. I cannot double-book you."
   - Explicitly list the available time gaps for **Today** based on the provided schedule.
   - If tomorrow's schedule is also provided, suggest available slots for **Tomorrow** as well.
3. **Mandatory Dispatch**: Whenever the user asks for their schedule, available time, or if you are reporting a conflict, YOU MUST ALWAYS include a `dispatch_schedule` action in your JSON response. This provides the user with a "link type" (button) to send their data via WhatsApp and triggers the automatic email dispatch.
4. **Data Accuracy**: Ensure the `summary` field in the `dispatch_schedule` action contains a beautifully formatted, exhaustive list of the schedule you are discussing (today or tomorrow). Use clear headers like "📅 Schedule" and "✨ Available Slots". Keep it professional and scannable.
5. **Calculating Gaps**: Assume a standard working day is 09:00 to 21:00 unless otherwise visible. Calculate availability by finding the empty spaces between existing tasks.

**Handling Trip & Plan Conflict Detection (CRITICAL)**:
1. When a user asks to plan a trip, itinerary, or industry visit (which belongs in the `Plan` category), you MUST FIRST meticulously check their schedule for the requested dates.
2. If there are existing `Task`, `Work`, or `Meeting` items on those dates, this is a **SEVERE CONFLICT**.
3. **DO NOT** create the `add_task` action for the trip yet.
4. Instead, reply to the user listing the exact conflicts. Example: "You have a meeting with HR and a work shift scheduled tomorrow. Are you sure you want to schedule your Goa trip? Should I cancel or reschedule those existing tasks first?"
5. Only proceed with creating the trip plan once the user confirms how to handle the conflicts.

**Handling Vision (Images)**:
1. **Scenario**: The user might upload an image of a handwritten note, a physical schedule, a business card, or a screenshot.
2. **Action**: Scan the image for any dates, times, tasks, or login details.
3. **Intelligence**: Suggest the most appropriate category (e.g., a "Sign-in" note becomes a `Routine`, a business card might be a `Credential`, a meeting photo is a `Meeting`).
4. **Mandatory Action**: If you find actionable items in the image, you MUST include the corresponding `add_task` or `manage_credential` actions in your JSON response.

**Bulk Operations (Multiple Items at Once)**:
1. If the user provides multiple passwords, logins, tasks, or routines in a single message, you MUST create a separate action object in the `actions` array for EACH item.
2. For example, if a user pastes 5 passwords, generate 5 distinct `manage_credential` actions in your JSON response.

**Retrieving Credentials**:
1. When a user asks for a credential generally (e.g., "provide my GreyHR credentials"), you MUST include ALL information (service name, username/email, and the password) beautifully formatted in the `reply` string.
2. If the user specifically asks ONLY for the password (e.g., "what is my GreyHR password?"), then provide just the password in the `reply` string.
3. Do not just say "Here it is" without actually printing the requested text directly in the `reply` field.

**Output Format (Strict JSON)**:
{
  "reply": "Conversational message (e.g., 'I see you have a meeting at 2 PM from this photo, I've added it to your schedule!').",
  "actions": [
    { 
      "type": "add_task", 
      "data": { "title": "...", "date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "category": "Task/Work/Meeting/Routine" } 
    },
    { "type": "dispatch_schedule", "summary": "..." },
    { "type": "dispatch_credentials", "summary": "Beautifully formatted plaintext list of the specific requested credentials." },
    { "type": "manage_credential", "action": "add/update/delete", "data": { "service_name": "...", "identifier_type": "...", "identifier_value": "...", "password": "..." } }
  ]
}

**Professional Routines**:
When a user mentions a professional routine like "Sign-in" or "Sign-out", or if you see it in an image, categorize it as `Routine`. If the user specifies "every Monday to Friday", you must create multiple `add_task` actions for the current week specifically for those days.
"""

def clean_json_response(text):
    """Helper to extract JSON if the model includes markdown backticks or extra text."""
    try:
        # Try to find JSON block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(text)
    except:
        return None

async def process_user_input(text: str, context_tasks: list = None, context_credentials: list = None, image_b64: str = None):
    if not client:
        return {"reply": "AI Service is offline: GEMINI_API_KEY is missing from the environment variables.", "actions": []}

    try:
        if context_tasks is None:
            context_tasks = []
        if context_credentials is None:
            context_credentials = []
            
        # Get current date and tomorrow for context
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        tomorrow_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Sort and format tasks for context
        today_context = ""
        tomorrow_context = ""
        
        today_list = [t for t in context_tasks if t.get("date") == today_date]
        tomorrow_list = [t for t in context_tasks if t.get("date") == tomorrow_date]
        
        if today_list:
            today_context = "\n\nUser's Schedule for TODAY (" + today_date + "):\n"
            for task in sorted(today_list, key=lambda x: x.get("start_time", "23:59")):
                today_context += f"- {task.get('start_time', '')} to {task.get('end_time', '')}: {task.get('title', '')} ({task.get('category', '')})\n"
        else:
            today_context = "\n\nThe user has no tasks scheduled for today."

        if tomorrow_list:
            tomorrow_context = "\n\nUser's Schedule for TOMORROW (" + tomorrow_date + "):\n"
            for task in sorted(tomorrow_list, key=lambda x: x.get("start_time", "23:59")):
                tomorrow_context += f"- {task.get('start_time', '')} to {task.get('end_time', '')}: {task.get('title', '')} ({task.get('category', '')})\n"
        else:
            tomorrow_context = "\n\nThe user has no tasks scheduled for tomorrow yet."
        
        schedule_context = today_context + tomorrow_context
        
        credentials_context = "\n\nCREDENTIAL VAULT CONTEXT:\n"
        if context_credentials:
            for cred in context_credentials:
                credentials_context += f"- Service: {cred.get('service_name', 'Unknown')}, Type: {cred.get('identifier_type', '')}, ID: {cred.get('identifier_value', '')}, Password: {cred.get('password', '')}\n"
        else:
            credentials_context += "The user's credential vault is empty.\n"
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nIMPORTANT: Today's date is {today_date}.{schedule_context}{credentials_context}\n\nUser Input: {text}"
        
        # Prepare contents (multimodal)
        contents = [full_prompt]
        if image_b64:
            # Handle base64 image (remove prefix if present)
            if "," in image_b64:
                image_b64 = image_b64.split(",")[1]
            
            import base64
            contents.append({
                "mime_type": "image/jpeg",
                "data": base64.b64decode(image_b64)
            })

        response = client.generate_content(
            contents=contents,
            generation_config=generate_config
        )
        
        if not response.text:
            return {"reply": "I'm sorry, I couldn't generate a response.", "tasks": []}

        data = clean_json_response(response.text)
        if data:
            return data
            
        return {"reply": "Sorry, I had trouble formatting the response correctly.", "tasks": []}
        
    except Exception as e:
        print(f"AI Error: {e}")
        return {"reply": f"AI Error: {str(e)}", "tasks": []}
