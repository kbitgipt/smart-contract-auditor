from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.user import User, UserMode
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from beanie import PydanticObjectId
from typing import Optional

class AuthService:
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = await User.find_one(User.email == user_data.email)
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password, 
            mode=user_data.user_mode,
            created_at=datetime.now(datetime.timezone.utc)(),
            updated_at=datetime.now(datetime.timezone.utc)(),
            # is_active=True
        )
        
        await db_user.insert()
        return db_user
    
    @staticmethod
    async def authenticate_user(login_data: UserLogin) -> User:
        """Authenticate user credentials"""
        user = await User.find_one(User.email == login_data.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # if not user.is_active:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="User account is disabled",
        #         headers={"WWW-Authenticate": "Bearer"},
        #     )
        
        # Cập nhật last_login
        user.last_login = datetime.now(datetime.timezone.utc)()
        # user.last_activity = datetime.now(datetime.timezone.utc)()
        await user.save()
        
        return user
    
    @staticmethod
    def create_token(user: User) -> Token:
        """Create access token for user"""
        access_token = create_access_token(data={"sub": user.email})
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                user_mode=user.mode,
                created_at=user.created_at,
                last_login=user.last_login,
                # last_activity=user.last_activity
            )
        )
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email"""
        return await User.find_one(User.email == email)

