"""
Firebase configuration and client management.
CRITICAL: Environment variable GOOGLE_APPLICATION_CREDENTIALS must point to service account key.
"""
import os
import logging
from typing import Optional
from firebase_admin import credentials, firestore, initialize_app, App

logger = logging.getLogger(__name__)


class FirebaseClient:
    """Singleton Firebase client with automatic initialization."""
    
    _instance: Optional['FirebaseClient'] = None
    _app: Optional[App] = None
    _db: Optional[firestore.Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._db is None:
            self._initialize_firebase()
    
    def _initialize_firebase(self) -> None:
        """Initialize Firebase with proper error handling."""
        try:
            # Method 1: Use environment variable
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                self._app = initialize_app(cred)
                logger.info(f"Firebase initialized with service account: {cred_path}")
            else:
                # Method 2: Use default credentials (for Google Cloud environments)
                self._app = initialize_app()
                logger.info("Firebase initialized with default credentials")
            
            self._db = firestore.client(self._app)
            logger.info("Firestore client initialized successfully")
            
        except FileNotFoundError as e:
            logger.error(f"Service account file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid Firebase configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    @property
    def db(self) -> firestore.Client:
        """Get Firestore database client."""
        if self._db is None:
            raise RuntimeError("Firebase not initialized. Call initialize() first.")
        return self._db
    
    @property
    def app(self) -> App:
        """Get Firebase app instance."""
        if self._app is None:
            raise RuntimeError("Firebase not initialized. Call initialize() first.")
        return self._app
    
    def close(self) -> None:
        """Cleanup resources (Firebase doesn't have explicit close)."""
        logger.info("Firebase client cleanup completed")


# Global instance
firebase_client = FirebaseClient()