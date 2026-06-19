"""MongoDB storage service for daily health records."""
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class HealthDataStorage:
    COLLECTION_NAME = "health_records"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
        
    async def get_record(self, legacy_id: str, date: str) -> dict | None:
        """Retrieve a specific day's health record from the database."""
        return await self.collection.find_one({
            "legacy_id": legacy_id, 
            "date_of_datas": date
        })
        
    async def save_record(self, legacy_id: str, health_id: str, date: str, data: dict):
        """Save or update a health record in the database."""
        record = {
            "legacy_id": legacy_id,
            "health_id": health_id,
            "date_of_datas": date,
            "created_at": datetime.utcnow().isoformat(),
            **data
        }
        
        # Upsert: Insert if doesn't exist, update if it does
        await self.collection.update_one(
            {"legacy_id": legacy_id, "date_of_datas": date},
            {"$set": record},
            upsert=True
        )
        logger.info(f"💾 Saved health record for {legacy_id} on {date}")

    async def delete_all_records(self, legacy_id: str) -> int:
        """
        Delete all health records for a specific user from the database.
        
        :param legacy_id: The user's legacy_id
        :return: The number of deleted records
        """
        result = await self.collection.delete_many({"legacy_id": legacy_id})
        logger.info(f"🗑️ Deleted {result.deleted_count} health records for {legacy_id}")
        return result.deleted_count