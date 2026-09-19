from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.core.database import get_db, hash_password
from datetime import datetime, timezone
import hashlib

router = APIRouter()

class AuthRequest(BaseModel):
    email: str
    password: str

@router.post("/signup")
async def signup(request: AuthRequest):
    conn = get_db()
    c = conn.cursor()
    
    # Check if email exists
    c.execute("SELECT id FROM users WHERE email = ?", (request.email,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
        
    pw_hash, salt = hash_password(request.password)
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        c.execute("""
            INSERT INTO users (email, password_hash, salt, role, created_at)
            VALUES (?, ?, ?, 'citizen', ?)
        """, (request.email, pw_hash, salt, now))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail="Database error")
        
    conn.close()
    return {"message": "User registered successfully", "role": "citizen", "email": request.email}

@router.post("/login")
async def login(request: AuthRequest):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT id, email, password_hash, salt, role FROM users WHERE email = ?", (request.email,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Verify password
    stored_hash = user['password_hash']
    salt = user['salt']
    
    # Hash the provided password with the stored salt
    pw_hash = hashlib.pbkdf2_hmac('sha256', request.password.encode('utf-8'), salt, 100000)
    
    if pw_hash != stored_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    return {
        "message": "Login successful",
        "email": user['email'],
        "role": user['role']
    }

