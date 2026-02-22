from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import List
import os
from database import credentials_collection
from models import CredentialCreate, CredentialResponse
from routes.users import get_current_user
from cryptography.fernet import Fernet

encryption_key = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode()).strip()
fernet = Fernet(encryption_key.encode())


router = APIRouter(prefix="/credentials", tags=["credentials"])

@router.post("/", response_model=CredentialResponse)
async def create_credential(cred: CredentialCreate, current_user: dict = Depends(get_current_user)):
    cred_dict = cred.dict()
    cred_dict["user_id"] = str(current_user["_id"])
    
    # Encrypt password before saving
    if "password" in cred_dict and cred_dict["password"]:
        cred_dict["password"] = fernet.encrypt(cred_dict["password"].encode()).decode()
        
    result = await credentials_collection.insert_one(cred_dict)
    cred_dict["id"] = str(result.inserted_id)
    return cred_dict

@router.get("/", response_model=List[CredentialResponse])
async def get_credentials(current_user: dict = Depends(get_current_user)):
    query = {"user_id": str(current_user["_id"])}
    cursor = credentials_collection.find(query)
    creds = []
    async for cred in cursor:
        cred["id"] = str(cred["_id"])
        
        # Decrypt password if it exists and is encrypted
        if "password" in cred and cred["password"]:
            try:
                cred["password"] = fernet.decrypt(cred["password"].encode()).decode()
            except Exception:
                # If decryption fails, it might be an old plaintext password
                pass
                
        creds.append(cred)
    return creds

@router.put("/{cred_id}", response_model=CredentialResponse)
async def update_credential(cred_id: str, cred: CredentialCreate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in cred.dict().items() if v is not None}
    
    # Encrypt password if it is being updated
    if "password" in update_data and update_data["password"]:
        update_data["password"] = fernet.encrypt(update_data["password"].encode()).decode()

    result = await credentials_collection.update_one(
        {"_id": ObjectId(cred_id), "user_id": str(current_user["_id"])},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Credential not found")
        
    updated = await credentials_collection.find_one({"_id": ObjectId(cred_id)})
    updated["id"] = str(updated["_id"])
    return updated

@router.delete("/{cred_id}")
async def delete_credential(cred_id: str, current_user: dict = Depends(get_current_user)):
    result = await credentials_collection.delete_one({"_id": ObjectId(cred_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"message": "Credential deleted"}
