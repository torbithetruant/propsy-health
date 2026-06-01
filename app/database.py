"""MongoDB database connection and management using Motor."""
import logging
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongodb() -> None:
    """Establish connection to MongoDB."""
    global _client, _db
    
    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        # Ping to verify connection
        await _client.admin.command("ping")
        
        _db = _client[settings.mongodb_db_name]
        
        # Create indexes for oauth_tokens collection
        await _db.oauth_tokens.create_index("legacy_id", unique=True)
        await _db.oauth_tokens.create_index("health_id", unique=True, sparse=True)
        await _db.oauth_tokens.create_index("client_id")
        
        logger.info(f"✅ Connected to MongoDB: {settings.mongodb_db_name}")
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def close_mongodb() -> None:
    """Close MongoDB connection."""
    global _client
    
    if _client:
        _client.close()
        _client = None
        logger.info("✅ MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance for dependency injection."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongodb() first.")
    return _db


async def health_check() -> dict[str, str]:
    """Check database connectivity."""
    try:
        await _db.command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "database": "disconnected"}


@asynccontextmanager
async def get_db_session():
    """Context manager for database operations."""
    db = get_database()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise