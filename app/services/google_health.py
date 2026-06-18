"""
Service for interacting with Google Health API.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Google Health API base URLs
FITNESS_API_BASE = "https://www.googleapis.com/fitness/v1"
HEALTH_API_BASE = "https://health.googleapis.com/v1"


class GoogleHealthService:
    """Service for fetching data from Google Health API."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
    
    async def _make_request(self, url: str, method: str = "GET", json_data: dict = None) -> dict:
        """Make authenticated request to Google Health API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=json_data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Google Health API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise
    
    async def get_profile(self) -> dict:
        """Get user profile information."""
        try:
            # Try Google Health API first
            url = f"{HEALTH_API_BASE}/users/me/profile"
            return await self._make_request(url)
        except Exception:
            # Fallback to Fitness API
            try:
                url = f"{FITNESS_API_BASE}/users/me/profile"
                return await self._make_request(url)
            except Exception as e:
                logger.error(f"Failed to get profile: {e}")
                return {"error": str(e)}
    
    async def get_data_sources(self) -> list[dict]:
        """Get list of available data sources."""
        try:
            url = f"{FITNESS_API_BASE}/users/me/dataSources"
            result = await self._make_request(url)
            return result.get("dataSource", [])
        except Exception as e:
            logger.error(f"Failed to get data sources: {e}")
            return []
    
    async def get_activity_data(self, days: int = 7) -> dict:
        """Get activity data (steps, distance, calories) for the last N days."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            # Convert to nanoseconds (Google Fitness API uses nanoseconds)
            start_nanos = int(start_time.timestamp() * 1_000_000_000)
            end_nanos = int(end_time.timestamp() * 1_000_000_000)
            
            # Aggregate request for steps
            url = f"{FITNESS_API_BASE}/users/me/dataset:aggregate"
            
            payload = {
                "aggregateBy": [
                    {
                        "dataTypeName": "com.google.step_count.delta",
                        "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
                    },
                    {
                        "dataTypeName": "com.google.distance.delta",
                        "dataSourceId": "derived:com.google.distance.delta:com.google.android.gms:merge_distance"
                    },
                    {
                        "dataTypeName": "com.google.calories.expended",
                        "dataSourceId": "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended"
                    }
                ],
                "bucketByTime": {"durationMillis": 86400000},  # 1 day buckets
                "startTimeMillis": int(start_time.timestamp() * 1000),
                "endTimeMillis": int(end_time.timestamp() * 1000)
            }
            
            result = await self._make_request(url, method="POST", json_data=payload)
            return result
        except Exception as e:
            logger.error(f"Failed to get activity data: {e}")
            return {"error": str(e)}
    
    async def get_sleep_data(self, days: int = 7) -> dict:
        """Get sleep data for the last N days."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            url = f"{FITNESS_API_BASE}/users/me/dataset:aggregate"
            
            payload = {
                "aggregateBy": [
                    {
                        "dataTypeName": "com.google.sleep.segment"
                    }
                ],
                "bucketByTime": {"durationMillis": 86400000},
                "startTimeMillis": int(start_time.timestamp() * 1000),
                "endTimeMillis": int(end_time.timestamp() * 1000)
            }
            
            result = await self._make_request(url, method="POST", json_data=payload)
            return result
        except Exception as e:
            logger.error(f"Failed to get sleep data: {e}")
            return {"error": str(e)}
    
    async def get_heart_rate(self, days: int = 7) -> dict:
        """Get heart rate data for the last N days."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            url = f"{FITNESS_API_BASE}/users/me/dataset:aggregate"
            
            payload = {
                "aggregateBy": [
                    {
                        "dataTypeName": "com.google.heart_rate.bpm"
                    }
                ],
                "bucketByTime": {"durationMillis": 3600000},  # 1 hour buckets
                "startTimeMillis": int(start_time.timestamp() * 1000),
                "endTimeMillis": int(end_time.timestamp() * 1000)
            }
            
            result = await self._make_request(url, method="POST", json_data=payload)
            return result
        except Exception as e:
            logger.error(f"Failed to get heart rate data: {e}")
            return {"error": str(e)}
    
    async def get_all_data(self, days: int = 7) -> dict:
        """Get all available health data."""
        import asyncio
        
        # Fetch all data in parallel
        profile, activity, sleep, heart_rate = await asyncio.gather(
            self.get_profile(),
            self.get_activity_data(days),
            self.get_sleep_data(days),
            self.get_heart_rate(days),
            return_exceptions=True
        )
        
        return {
            "profile": profile if not isinstance(profile, Exception) else {"error": str(profile)},
            "activity": activity if not isinstance(activity, Exception) else {"error": str(activity)},
            "sleep": sleep if not isinstance(sleep, Exception) else {"error": str(sleep)},
            "heart_rate": heart_rate if not isinstance(heart_rate, Exception) else {"error": str(heart_rate)},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }