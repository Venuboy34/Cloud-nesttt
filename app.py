"""
CloudNest - Universal Application Hosting Platform
A Koyeb-like backend for deploying any type of application
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import uvicorn
import motor.motor_asyncio
from datetime import datetime, timedelta
from passlib.hash import bcrypt
import jwt
import os
import secrets
import asyncio
import docker
import git
import shutil
import subprocess
import json
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "cloudnest-secret-key-change-in-production")
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DOMAIN = os.getenv("DOMAIN", "cloudnest.app")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BASE_DEPLOY_PATH = os.getenv("BASE_DEPLOY_PATH", "/var/cloudnest/apps")

# FastAPI app
app = FastAPI(title="CloudNest", description="Deploy Anything. Instantly.", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client.cloudnest

# Docker client
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.warning(f"Docker client not available: {e}")
    docker_client = None

# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class AppCreate(BaseModel):
    name: str
    git_url: str
    branch: Optional[str] = "main"
    env_vars: Optional[dict] = {}
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace('-', '').isalnum():
            raise ValueError('App name must be alphanumeric (hyphens allowed)')
        return v.lower()

class AppAction(BaseModel):
    app_id: str

# Helper functions
def create_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    
    user = await db.users.find_one({"email": payload.get("email")})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("verified"):
        raise HTTPException(status_code=403, detail="Email not verified")
    
    return user

async def send_email(to_email: str, subject: str, body: str):
    """Generic email sending function"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Email not sent.")
        logger.info(f"Email would be sent to {to_email}: {subject}")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

async def send_verification_email(email: str, token: str):
    """Send verification email"""
    verification_link = f"{FRONTEND_URL}/auth/verify/{token}"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Welcome to CloudNest! 🚀</h2>
                <p>Thank you for signing up. Please verify your email address by clicking the link below:</p>
                <p style="margin: 30px 0;">
                    <a href="{verification_link}" 
                       style="background-color: #4F46E5; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verify Email Address
                    </a>
                </p>
                <p>Or copy this link to your browser:</p>
                <p style="background-color: #f3f4f6; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {verification_link}
                </p>
                <p style="color: #666; font-size: 14px;">This link will expire in 24 hours.</p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    If you didn't create this account, please ignore this email.
                </p>
            </div>
        </body>
    </html>
    """
    
    await send_email(email, "Verify your CloudNest account", body)

async def send_password_reset_email(email: str, token: str):
    """Send password reset email"""
    reset_link = f"{FRONTEND_URL}/auth/reset-password/{token}"
    
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Reset Your Password 🔐</h2>
                <p>We received a request to reset your CloudNest account password.</p>
                <p>Click the button below to reset your password:</p>
                <p style="margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #4F46E5; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </p>
                <p>Or copy this link to your browser:</p>
                <p style="background-color: #f3f4f6; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {reset_link}
                </p>
                <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
                </p>
            </div>
        </body>
    </html>
    """
    
    await send_email(email, "Reset your CloudNest password", body)

async def send_password_changed_email(email: str):
    """Send password changed confirmation email"""
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #10B981;">Password Changed Successfully ✓</h2>
                <p>Your CloudNest account password has been changed successfully.</p>
                <p>If you didn't make this change, please contact support immediately.</p>
                <p style="margin-top: 30px;">
                    <a href="{FRONTEND_URL}/login" 
                       style="background-color: #4F46E5; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Login to Your Account
                    </a>
                </p>
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    CloudNest - Deploy Anything. Instantly.
                </p>
            </div>
        </body>
    </html>
    """
    
    await send_email(email, "Password Changed - CloudNest", body)

def detect_app_type(repo_path: str):
    """Detect application type from repository contents"""
    path = Path(repo_path)
    
    if (path / "Dockerfile").exists():
        return "docker"
    elif (path / "package.json").exists():
        return "nodejs"
    elif (path / "requirements.txt").exists() or (path / "app.py").exists():
        if (path / "bot.py").exists():
            return "telegram-bot"
        return "python"
    elif (path / "index.html").exists():
        return "static"
    else:
        return "unknown"

async def build_and_deploy_app(app_id: str, user_id: str):
    """Build and deploy application"""
    try:
        app = await db.apps.find_one({"_id": app_id, "user_id": user_id})
        if not app:
            raise Exception("App not found")
        
        # Update status
        await db.apps.update_one(
            {"_id": app_id},
            {"$set": {"status": "building", "updated_at": datetime.utcnow()}}
        )
        
        # Clone repository
        repo_path = f"{BASE_DEPLOY_PATH}/{user_id}/{app['name']}"
        Path(repo_path).parent.mkdir(parents=True, exist_ok=True)
        
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
        
        logger.info(f"Cloning repository: {app['git_url']}")
        git.Repo.clone_from(app['git_url'], repo_path, branch=app.get('branch', 'main'))
        
        # Detect app type
        app_type = detect_app_type(repo_path)
        
        await db.apps.update_one(
            {"_id": app_id},
            {"$set": {"app_type": app_type}}
        )
        
        # Build based on app type
        if app_type == "docker" and docker_client:
            # Build Docker image
            image_tag = f"cloudnest/{app['name']}:latest"
            logger.info(f"Building Docker image: {image_tag}")
            
            docker_client.images.build(
                path=repo_path,
                tag=image_tag,
                rm=True
            )
            
            # Run container
            container = docker_client.containers.run(
                image_tag,
                name=f"cloudnest-{app['name']}-{app_id[:8]}",
                detach=True,
                environment=app.get('env_vars', {}),
                restart_policy={"Name": "unless-stopped"}
            )
            
            container_info = {
                "id": container.id,
                "name": container.name,
                "image": image_tag
            }
            
            await db.apps.update_one(
                {"_id": app_id},
                {
                    "$set": {
                        "status": "running",
                        "container": container_info,
                        "deployed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
        elif app_type in ["python", "telegram-bot"]:
            # For Python apps, create a simple process
            logger.info(f"Deploying Python app: {app['name']}")
            
            # Install requirements
            if os.path.exists(f"{repo_path}/requirements.txt"):
                subprocess.run(
                    ["pip", "install", "-r", "requirements.txt"],
                    cwd=repo_path,
                    check=True
                )
            
            await db.apps.update_one(
                {"_id": app_id},
                {
                    "$set": {
                        "status": "deployed",
                        "deployed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
        else:
            await db.apps.update_one(
                {"_id": app_id},
                {
                    "$set": {
                        "status": "unknown-type",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        logger.info(f"App deployed successfully: {app['name']}")
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        await db.apps.update_one(
            {"_id": app_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )

# API Routes

@app.get("/")
async def root():
    return {
        "name": "CloudNest",
        "tagline": "Deploy Anything. Instantly.",
        "version": "1.0.0",
        "status": "running"
    }

# ============= AUTH ROUTES =============

@app.post("/auth/register")
async def register(user: UserRegister, background_tasks: BackgroundTasks):
    """Register new user and send verification email"""
    
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"email": user.email}, {"username": user.username}]})
    if existing_user:
        if existing_user.get("email") == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create verification token
    verification_token = secrets.token_urlsafe(32)
    
    # Hash password
    hashed_password = bcrypt.hash(user.password)
    
    # Create user
    user_data = {
        "email": user.email,
        "username": user.username,
        "password": hashed_password,
        "verified": False,
        "verification_token": verification_token,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_data)
    
    # Send verification email in background
    background_tasks.add_task(send_verification_email, user.email, verification_token)
    
    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "email": user.email
    }

@app.get("/auth/verify/{token}")
async def verify_email(token: str):
    """Verify user email"""
    
    user = await db.users.find_one({"verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    if user.get("verified"):
        return {"message": "Email already verified", "verified": True}
    
    # Update user as verified
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"verified": True, "updated_at": datetime.utcnow()},
            "$unset": {"verification_token": ""}
        }
    )
    
    return {
        "message": "Email verified successfully! You can now login.",
        "verified": True
    }

@app.post("/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not bcrypt.verify(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if email is verified
    if not user.get("verified"):
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")
    
    # Create JWT token
    token = create_token({"email": user["email"], "username": user["username"]})
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "email": user["email"],
            "username": user["username"]
        }
    }

@app.post("/auth/forgot-password")
async def forgot_password(data: ForgotPassword, background_tasks: BackgroundTasks):
    """Send password reset email"""
    
    user = await db.users.find_one({"email": data.email})
    
    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate reset token (expires in 1 hour)
    reset_token = secrets.token_urlsafe(32)
    reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Save reset token
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "reset_token": reset_token,
                "reset_token_expires": reset_token_expires,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Send reset email in background
    background_tasks.add_task(send_password_reset_email, data.email, reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent"}

@app.post("/auth/reset-password")
async def reset_password(data: ResetPassword, background_tasks: BackgroundTasks):
    """Reset password with token"""
    
    user = await db.users.find_one({"reset_token": data.token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if token is expired
    if user.get("reset_token_expires") and user["reset_token_expires"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Hash new password
    hashed_password = bcrypt.hash(data.new_password)
    
    # Update password and remove reset token
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password": hashed_password,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expires": ""
            }
        }
    )
    
    # Send confirmation email in background
    background_tasks.add_task(send_password_changed_email, user["email"])
    
    return {"message": "Password reset successful. You can now login with your new password."}

@app.get("/auth/me")
async def get_current_user_info(user = Depends(get_current_user)):
    """Get current user information"""
    return {
        "email": user["email"],
        "username": user["username"],
        "verified": user.get("verified", False),
        "created_at": user.get("created_at")
    }

# ============= APP ROUTES =============

@app.post("/apps/create")
async def create_app(app_data: AppCreate, background_tasks: BackgroundTasks, user = Depends(get_current_user)):
    """Create and deploy new application"""
    
    # Check if app name already exists for this user
    existing_app = await db.apps.find_one({"name": app_data.name, "user_id": str(user["_id"])})
    if existing_app:
        raise HTTPException(status_code=400, detail="App with this name already exists")
    
    # Create app document
    app_id = secrets.token_urlsafe(16)
    subdomain = f"{app_data.name}-{user['username']}.{DOMAIN}"
    
    app_doc = {
        "_id": app_id,
        "name": app_data.name,
        "user_id": str(user["_id"]),
        "git_url": app_data.git_url,
        "branch": app_data.branch,
        "env_vars": app_data.env_vars,
        "subdomain": subdomain,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await db.apps.insert_one(app_doc)
    
    # Start deployment in background
    background_tasks.add_task(build_and_deploy_app, app_id, str(user["_id"]))
    
    return {
        "message": "App created successfully. Deployment started.",
        "app_id": app_id,
        "name": app_data.name,
        "subdomain": subdomain,
        "status": "pending"
    }

@app.post("/apps/deploy")
async def deploy_app(action: AppAction, background_tasks: BackgroundTasks, user = Depends(get_current_user)):
    """Deploy or redeploy an application"""
    
    app = await db.apps.find_one({"_id": action.app_id, "user_id": str(user["_id"])})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Start deployment in background
    background_tasks.add_task(build_and_deploy_app, action.app_id, str(user["_id"]))
    
    return {"message": "Deployment started", "app_id": action.app_id}

@app.post("/apps/stop")
async def stop_app(action: AppAction, user = Depends(get_current_user)):
    """Stop running application"""
    
    app = await db.apps.find_one({"_id": action.app_id, "user_id": str(user["_id"])})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    if app.get("container") and docker_client:
        try:
            container = docker_client.containers.get(app["container"]["id"])
            container.stop()
            
            await db.apps.update_one(
                {"_id": action.app_id},
                {"$set": {"status": "stopped", "updated_at": datetime.utcnow()}}
            )
            
            return {"message": "App stopped successfully", "app_id": action.app_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to stop app: {str(e)}")
    
    return {"message": "No running container found"}

@app.post("/apps/start")
async def start_app(action: AppAction, user = Depends(get_current_user)):
    """Start stopped application"""
    
    app = await db.apps.find_one({"_id": action.app_id, "user_id": str(user["_id"])})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    if app.get("container") and docker_client:
        try:
            container = docker_client.containers.get(app["container"]["id"])
            container.start()
            
            await db.apps.update_one(
                {"_id": action.app_id},
                {"$set": {"status": "running", "updated_at": datetime.utcnow()}}
            )
            
            return {"message": "App started successfully", "app_id": action.app_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start app: {str(e)}")
    
    return {"message": "No container found"}

@app.get("/apps/list")
async def list_apps(user = Depends(get_current_user)):
    """List all user applications"""
    
    apps = await db.apps.find({"user_id": str(user["_id"])}).to_list(100)
    
    return {
        "apps": [
            {
                "app_id": app["_id"],
                "name": app["name"],
                "subdomain": app.get("subdomain"),
                "status": app.get("status"),
                "app_type": app.get("app_type"),
                "created_at": app.get("created_at"),
                "deployed_at": app.get("deployed_at")
            }
            for app in apps
        ]
    }

@app.get("/apps/{app_id}/status")
async def get_app_status(app_id: str, user = Depends(get_current_user)):
    """Get application status"""
    
    app = await db.apps.find_one({"_id": app_id, "user_id": str(user["_id"])})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    return {
        "app_id": app["_id"],
        "name": app["name"],
        "status": app.get("status"),
        "subdomain": app.get("subdomain"),
        "app_type": app.get("app_type"),
        "container": app.get("container"),
        "error": app.get("error")
    }

@app.get("/apps/{app_id}/logs")
async def get_app_logs(app_id: str, user = Depends(get_current_user)):
    """Get application logs"""
    
    app = await db.apps.find_one({"_id": app_id, "user_id": str(user["_id"])})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    logs = []
    
    if app.get("container") and docker_client:
        try:
            container = docker_client.containers.get(app["container"]["id"])
            logs = container.logs(tail=100).decode('utf-8').split('\n')
        except Exception as e:
            logs = [f"Error fetching logs: {str(e)}"]
    
    return {
        "app_id": app_id,
        "logs": logs
    }

@app.delete("/apps/{app_id}")
async def delete_app(app_id: str, user = Depends(get_current_user)):
    """Delete application"""
    
    app = await db.apps.find_one({"_id": app_id, "user_id": str(user["_id"])})
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Stop and remove container if exists
    if app.get("container") and docker_client:
        try:
            container = docker_client.containers.get(app["container"]["id"])
            container.stop()
            container.remove()
        except Exception as e:
            logger.error(f"Error removing container: {e}")
    
    # Delete app files
    repo_path = f"{BASE_DEPLOY_PATH}/{user['_id']}/{app['name']}"
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    
    # Delete from database
    await db.apps.delete_one({"_id": app_id})
    
    return {"message": "App deleted successfully", "app_id": app_id}

# ============= HEALTH CHECK =============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "mongodb": "connected" if client else "disconnected",
            "docker": "available" if docker_client else "unavailable"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
