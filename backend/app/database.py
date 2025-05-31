import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    
mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "auditsmart")
        
        mongodb.client = AsyncIOMotorClient(mongodb_url)
        
        # Test connection
        await mongodb.client.admin.command('ping')
        logger.info("MongoDB connection successful!")

        # Import all models here
        from app.models.user import User
        from app.models.project import Project
        from app.models.analysis import Analysis
        
        # Initialize beanie with the models
        await init_beanie(
            database=mongodb.client[database_name],
            document_models=[User, Project, Analysis]
        )

        logger.info("Beanie initialization successful!")

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("MongoDB connection closed")