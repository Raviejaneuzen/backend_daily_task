import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv

load_dotenv()

# Setup Twilio Client
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER") # e.g. "whatsapp:+14155238886"

client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except Exception as e:
        print(f"Failed to initialize Twilio client: {e}")

def send_whatsapp_message(to_number: str, text: str) -> bool:
    """
    Sends a WhatsApp message using Twilio.
    to_number should be formatted like: 'whatsapp:+917013666788'
    """
    if not client:
        print("Twilio Client is not configured. Could not send WhatsApp message.")
        return False
        
    try:
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
            
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=text,
            to=to_number
        )
        print(f"WhatsApp message sent successfully. SID: {message.sid}")
        return True
    except TwilioRestException as e:
        print(f"Twilio API Error while sending WhatsApp message: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error while sending WhatsApp message: {e}")
        return False
