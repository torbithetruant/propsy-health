"""Token storage service with encryption-ready architecture."""
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)


class TokenStorageService:
    """
    Service for managing OAuth tokens in MongoDB.
    
    Architecture designed for future encryption:
    - All token access goes through this service
    - Encryption/decryption can be added without modifying API routes
    - Currently stores tokens in plaintext as requested
    """
    
    COLLECTION_NAME = "oauth_tokens"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
    
    # ========================================================================
    # ENCRYPTION HOOKS - Implement these when encryption is required
    # ========================================================================
    
    def _encrypt_token_data(self, token_data: dict) -> dict:
        """
        Hook for token encryption.
        
        Currently returns data as-is. Implement encryption logic here
        when security requirements change.
        """
        # TODO: Implement encryption using cryptography library
        # Example: return encrypt(token_data, settings.ENCRYPTION_KEY)
        return token_data
    
    def _decrypt_token_data(self, token_data: dict) -> dict:
        """
        Hook for token decryption.
        
        Currently returns data as-is. Implement decryption logic here
        when security requirements change.
        """
        # TODO: Implement decryption using cryptography library
        # Example: return decrypt(token_data, settings.ENCRYPTION_KEY)
        return token_data
    
    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    async def create_token(self, token_document: dict) -> ObjectId:
        """
        Store a new token document in MongoDB.
        
        Args:
            token_document: Dict containing token data
            
        Returns:
            ObjectId of created document
        """
        # Apply encryption hook (currently passthrough)
        encrypted_doc = self._encrypt_token_data(token_document.copy())
        
        # Add timestamps
        now = datetime.now(timezone.utc).isoformat()
        encrypted_doc["created_at"] = now
        encrypted_doc["updated_at"] = now
        encrypted_doc.setdefault("status", "active")
        
        result = await self.collection.insert_one(encrypted_doc)
        logger.info(f"✅ Token stored for legacy_id: {token_document.get('legacy_id')}")
        return result.inserted_id
    
    async def get_token_by_legacy_id(self, legacy_id: str) -> dict | None:
        """
        Retrieve token document by legacy_id.
        
        Args:
            legacy_id: The platform's primary user identifier
            
        Returns:
            Decrypted token document or None if not found
        """
        doc = await self.collection.find_one({"legacy_id": legacy_id})
        
        if doc is None:
            return None
        
        # Apply decryption hook (currently passthrough)
        return self._decrypt_token_data(doc)
    
    async def get_token_by_health_id(self, health_id: str) -> dict | None:
        """
        Retrieve token document by Google Health ID.
        
        Args:
            health_id: Google's user identifier
            
        Returns:
            Decrypted token document or None if not found
        """
        doc = await self.collection.find_one({"health_id": health_id})
        
        if doc is None:
            return None
        
        return self._decrypt_token_data(doc)
    
    async def get_all_tokens(self, limit: int = 100) -> list[dict]:
        """
        Retrieve all active token documents.
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            List of decrypted token documents
        """
        cursor = self.collection.find(
            {"status": "active"}, 
            {"token.access_token": 0, "token.refresh_token": 0}  # Exclude sensitive fields
        ).limit(limit)
        
        tokens = []
        async for doc in cursor:
            tokens.append(self._decrypt_token_data(doc))
        
        return tokens
    
    async def update_token(self, legacy_id: str, updates: dict) -> bool:
        """
        Update an existing token document.
        
        Args:
            legacy_id: The platform's primary user identifier
            updates: Fields to update
            
        Returns:
            True if update succeeded, False otherwise
        """
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Apply encryption to token field if present
        if "token" in updates:
            updates["token"] = self._encrypt_token_data(updates["token"])
        
        result = await self.collection.update_one(
            {"legacy_id": legacy_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def delete_token(self, legacy_id: str) -> bool:
        """
        Soft-delete a token document by setting status to revoked.
        
        Args:
            legacy_id: The platform's primary user identifier
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        result = await self.collection.update_one(
            {"legacy_id": legacy_id},
            {"$set": {
                "status": "revoked",
                "revoked_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        logger.info(f"✅ Token revoked for legacy_id: {legacy_id}")
        return result.modified_count > 0
    
    async def hard_delete_token(self, legacy_id: str) -> bool:
        """
        Permanently delete a token document.
        
        ⚠️ Use with caution - this cannot be undone.
        
        Args:
            legacy_id: The platform's primary user identifier
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        result = await self.collection.delete_one({"legacy_id": legacy_id})
        logger.warning(f"⚠️ Token permanently deleted for legacy_id: {legacy_id}")
        return result.deleted_count > 0