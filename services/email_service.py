import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

def wrap_in_template(content: str, subject: str):
    """Wraps plain text content in a premium HTML template."""
    # Convert newlines to <br> for HTML
    html_content = content.replace("\n", "<br>")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f7ff; }}
            .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #e1e8f5; }}
            .header {{ background: linear-gradient(135deg, #5c67f2 0%, #8b5cf6 100%); padding: 30px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px; }}
            .header p {{ margin: 5px 0 0; opacity: 0.9; font-size: 14px; }}
            .content {{ padding: 30px; background-color: #ffffff; }}
            .schedule-box {{ background: #f9faff; border-left: 4px solid #5c67f2; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .footer {{ background: #f1f3f9; padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }}
            .btn {{ display: inline-block; padding: 12px 24px; background-color: #5c67f2; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Dhana Durga</h1>
                <p>Personal Productivity Assistant</p>
            </div>
            <div class="content">
                <h2 style="color: #1f2937; margin-top: 0;">{subject}</h2>
                <div class="schedule-box">
                    {html_content}
                </div>
                <p style="color: #4b5563; font-size: 14px;">This summary was prepared by Dhana, your AI agent, based on your current workspace activities.</p>
                <div style="text-align: center;">
                    <a href="#" class="btn">View Dashboard</a>
                </div>
            </div>
            <div class="footer">
                <p>&copy; 2026 Dhana Durga. All rights reserved.</p>
                <p>Focused. Productive. Empowered.</p>
            </div>
        </div>
    </body>
    </html>
    """

def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"SMTP not configured. Email to {to_email} skipped.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = f"Dhana Durga <{SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Determine content type
        content = body
        if is_html:
            msg.attach(MIMEText(content, "html"))
        else:
            # If not explicitly HTML, we wrap the plain text in our template
            html_version = wrap_in_template(body, subject)
            msg.attach(MIMEText(html_version, "html"))
            # Optional: attach plain text version too for reliability
            msg.attach(MIMEText(body, "plain"))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False
