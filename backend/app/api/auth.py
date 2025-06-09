from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse, UserModeUpdate
from app.services.auth_service import AuthService
from app.core.security import verify_token
from app.models.user import User

router = APIRouter()

# Thay đổi từ Header thành HTTPBearer để Swagger UI hiểu
security = HTTPBearer()

async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    try:
        token = credentials.credentials  # Lấy token từ credentials
        
        payload = verify_token(token)
        email = payload.get("sub")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = await AuthService.get_user_by_email(email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last activity (nếu cần)
        # user.last_activity = datetime.utcnow()
        await user.save()
        
        return user
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        user = await AuthService.create_user(user_data)
        return UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            user_mode=user.mode,
            created_at=user.created_at,
            last_login=user.last_login,
            # last_activity=user.last_activity
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login-json", response_model=Token)
async def login_with_json(login_data: UserLogin):
    """Login user with JSON payload - EMAIL VÀ PASSWORD"""
    try:
        user = await AuthService.authenticate_user(login_data)
        
        token = AuthService.create_token(user)
        return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed"
        )

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    """Login user - EMAIL VÀ PASSWORD"""
    try:
        user = await AuthService.authenticate_user(login_data)
        
        token = AuthService.create_token(user)
        return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_user_dependency)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        user_mode=current_user.mode,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        # last_activity=current_user.last_activity
    )

@router.put("/mode", response_model=UserResponse)
async def update_user_mode(
    mode_data: UserModeUpdate,
    current_user: User = Depends(get_current_user_dependency)
):
    """Update user mode (normal/auditor)"""
    try:
        current_user.mode = mode_data.user_mode
        current_user.updated_at = datetime.utcnow()
        
        await current_user.save()
        
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            user_mode=current_user.mode,
            created_at=current_user.created_at,
            last_login=current_user.last_login,
            # last_activity=current_user.last_activity
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update user mode: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user_dependency)):
    """Logout current user"""
    return {"message": "Successfully logged out"}