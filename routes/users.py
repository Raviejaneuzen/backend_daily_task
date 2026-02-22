from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from bson import ObjectId
from datetime import datetime, timedelta
from database import users_collection
from models import UserCreate, UserInDB, Token, ForgotPasswordRequest, ResetPasswordRequest, UpdatePasswordRequest
from auth.utils import get_password_hash, verify_password, create_access_token, decode_access_token
from services.email_service import send_email

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    email = payload.get("sub")
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/register", response_model=UserInDB)
async def register(user: UserCreate):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user.password)
    user_dict["created_at"] = datetime.utcnow()
    
    result = await users_collection.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    return user_dict

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserInDB)
async def me(current_user: dict = Depends(get_current_user)):
    current_user["id"] = str(current_user["_id"])
    return current_user

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    user = await users_collection.find_one({"email": req.email})
    if not user:
        # We don't want to reveal if a user exists, but for this app it's fine or we can just say "Email sent if account exists"
        return {"message": "If an account exists with this email, a reset link has been sent."}
    
    # Create a short-lived token (15 mins)
    reset_token = create_access_token(data={"sub": user["email"], "purpose": "reset"}, expires_delta=timedelta(minutes=15))
    
    # Send email
    # Dynamically determine the origin URL (localhost vs production)
    origin = request.headers.get("origin") or request.headers.get("referer", "https://daily-task-frontend-oumq.onrender.com").rstrip("/")
    reset_link = f"{origin}/reset-password?token={reset_token}"
    email_body = f"""
    Hi {user['name']},
    
    You requested to reset your password for Dhana Durga.
    Click the link below to set a new password. This link will expire in 15 minutes.
    
    {reset_link}
    
    If you didn't request this, please ignore this email.
    """
    
    success = send_email(user["email"], "Reset Your Password - Dhana Durga", email_body)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send reset email")
        
    return {"message": "Reset link sent to your email."}

@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    payload = decode_access_token(req.token)
    if not payload or payload.get("purpose") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    email = payload.get("sub")
    hashed_password = get_password_hash(req.new_password)
    
    result = await users_collection.update_one(
        {"email": email},
        {"$set": {"password": hashed_password}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to reset password")
        
    return {"message": "Password reset successfully. You can now log in."}

@router.post("/update-password")
async def update_password(req: UpdatePasswordRequest, current_user: dict = Depends(get_current_user)):
    if not verify_password(req.old_password, current_user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    hashed_password = get_password_hash(req.new_password)
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"password": hashed_password}}
    )
    
    return {"message": "Password updated successfully."}
