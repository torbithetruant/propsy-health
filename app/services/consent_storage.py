"""MongoDB storage service for user informed consent records."""
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

# Import encryption utilities
from app.core.encryption import encrypt, decrypt

logger = logging.getLogger(__name__)


class ConsentStorageService:
    """
    Manages informed consent records for health research participants.
    
    Uses an upsert strategy to ensure only ONE consent record exists per user.
    Sensitive audit fields (IP address, User-Agent) are encrypted at rest.
    """
    
    COLLECTION_NAME = "user_consents"
    CURRENT_CONSENT_VERSION = "1.0"  # Increment when policy changes
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
    
    # =========================================================================
    # ENCRYPTION HELPERS
    # =========================================================================
    
    def _decrypt_audit_fields(self, doc: dict | None) -> dict | None:
        """
        Decrypts sensitive audit fields (IP and User-Agent) in a consent document.
        Returns the document with plaintext audit fields.
        """
        if not doc:
            return None
        
        # Decrypt IP address
        if doc.get("ip_address") and isinstance(doc["ip_address"], str):
            try:
                # Fernet encrypted strings always start with 'gAAAA'
                if doc["ip_address"].startswith("gAAAA"):
                    doc["ip_address"] = decrypt(doc["ip_address"])
            except Exception as e:
                logger.warning(f"Failed to decrypt ip_address for {doc.get('legacy_id')}: {e}")
                
        # Decrypt User-Agent
        if doc.get("user_agent") and isinstance(doc["user_agent"], str):
            try:
                if doc["user_agent"].startswith("gAAAA"):
                    doc["user_agent"] = decrypt(doc["user_agent"])
            except Exception as e:
                logger.warning(f"Failed to decrypt user_agent for {doc.get('legacy_id')}: {e}")
                
        return doc

    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    
    async def has_active_consent(self, legacy_id: str) -> bool:
        """Check if user has an active (non-withdrawn) consent."""
        doc = await self.collection.find_one({
            "legacy_id": legacy_id,
            "status": "active"
        })
        return doc is not None
    
    async def get_consent(self, legacy_id: str) -> dict | None:
        """
        Get the most recent consent record for a user.
        Automatically decrypts IP and User-Agent before returning.
        """
        doc = await self.collection.find_one(
            {"legacy_id": legacy_id},
            sort=[("consented_at", -1)]
        )
        return self._decrypt_audit_fields(doc)
    
    async def record_consent(
        self,
        legacy_id: str,
        health_id: str,
        ip_address: str,
        user_agent: str,
        consent_read: bool,
        consent_voluntary: bool,
        consent_data: bool,
        consent_version: str = None
    ) -> str:
        """
        Record or update a consent acceptance.
        
        Encrypts IP address and User-Agent before saving to MongoDB.
        Uses MongoDB's upsert feature to ensure only one record per user.
        
        :return: The consent_id (MongoDB _id as string)
        """
        consent_version = consent_version or self.CURRENT_CONSENT_VERSION
        
        # Encrypt sensitive audit fields
        encrypted_ip = encrypt(ip_address) if ip_address else None
        encrypted_ua = encrypt(user_agent) if user_agent else None
        
        # Fields to update (or set if inserting)
        update_fields = {
            "health_id": health_id,
            "consent_version": consent_version,
            "consented_at": datetime.now(timezone.utc).isoformat(),
            "ip_address": encrypted_ip,       # ← ENCRYPTED
            "user_agent": encrypted_ua,       # ← ENCRYPTED
            "status": "active",
            "withdrawn_at": None,
            "withdrawal_reason": None,
            "consent_read": consent_read,
            "consent_voluntary": consent_voluntary,
            "consent_data": consent_data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Fields to set ONLY if the document is being created for the first time
        insert_fields = {
            "legacy_id": legacy_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Perform the upsert
        result = await self.collection.update_one(
            {"legacy_id": legacy_id},
            {
                "$set": update_fields,
                "$setOnInsert": insert_fields
            },
            upsert=True
        )
        
        # Retrieve the MongoDB _id
        if result.upserted_id:
            consent_id = str(result.upserted_id)
        else:
            doc = await self.collection.find_one({"legacy_id": legacy_id}, {"_id": 1})
            consent_id = str(doc["_id"]) if doc else "unknown"
            
        action = "Updated" if result.matched_count > 0 else "Recorded"
        logger.info(f"Consent {action} for {legacy_id} (v{consent_version}) [Audit fields encrypted]")
        
        return consent_id
    
    async def withdraw_consent(
        self,
        legacy_id: str,
        reason: str = None,
        delete_data: bool = True
    ) -> bool:
        """Withdraw consent for a user."""
        result = await self.collection.update_one(
            {"legacy_id": legacy_id, "status": "active"},
            {"$set": {
                "status": "withdrawn",
                "withdrawn_at": datetime.now(timezone.utc).isoformat(),
                "withdrawal_reason": reason,
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Consent withdrawn for {legacy_id}")
            return True
        return False
    
    async def get_all_consents(self, limit: int = 100) -> list[dict]:
        """
        Get all consent records (for admin/audit purposes).
        Automatically decrypts IP and User-Agent for all records.
        """
        cursor = self.collection.find().sort("consented_at", -1).limit(limit)
        docs = [doc async for doc in cursor]
        return [self._decrypt_audit_fields(doc) for doc in docs]