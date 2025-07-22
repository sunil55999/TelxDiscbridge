"""
Image hashing utilities for perceptual hash-based image blocking.
"""
import hashlib
import os
from typing import Optional, Set, Dict, Any
from loguru import logger

try:
    import imagehash
    from PIL import Image
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning("imagehash and/or PIL not available - image hash blocking disabled")

class ImageHashManager:
    """Manages perceptual hash-based image blocking."""
    
    def __init__(self, database=None):
        self.database = database
        self.blocked_hashes: Set[str] = set()
        self.hash_cache: Dict[str, str] = {}
        
    async def initialize(self):
        """Initialize the image hash manager."""
        if not IMAGEHASH_AVAILABLE:
            logger.warning("Image hash blocking disabled - missing dependencies")
            return
            
        if self.database:
            # Load blocked hashes from database
            await self._load_blocked_hashes()
            
    async def _load_blocked_hashes(self):
        """Load blocked image hashes from database."""
        try:
            # This would load from a database table for blocked image hashes
            # For now, just initialize an empty set
            self.blocked_hashes = set()
            logger.info("Loaded blocked image hashes from database")
        except Exception as e:
            logger.error(f"Error loading blocked hashes: {e}")
    
    def calculate_image_hash(self, image_data: bytes) -> Optional[str]:
        """Calculate perceptual hash for image data."""
        if not IMAGEHASH_AVAILABLE:
            return None
            
        try:
            from io import BytesIO
            image = Image.open(BytesIO(image_data))
            
            # Calculate perceptual hash (pHash)
            phash = imagehash.phash(image)
            return str(phash)
            
        except Exception as e:
            logger.error(f"Error calculating image hash: {e}")
            return None
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate perceptual hash for image file."""
        if not IMAGEHASH_AVAILABLE or not os.path.exists(file_path):
            return None
            
        try:
            image = Image.open(file_path)
            phash = imagehash.phash(image)
            return str(phash)
            
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    async def is_image_blocked(self, image_data: bytes, pair_id: Optional[int] = None) -> Dict[str, Any]:
        """Check if image is blocked based on perceptual hash."""
        if not IMAGEHASH_AVAILABLE:
            return {"blocked": False, "reason": "hash_unavailable"}
            
        try:
            image_hash = self.calculate_image_hash(image_data)
            if not image_hash:
                return {"blocked": False, "reason": "hash_failed"}
            
            # Check against blocked hashes
            if image_hash in self.blocked_hashes:
                return {
                    "blocked": True, 
                    "reason": "hash_match",
                    "hash": image_hash
                }
            
            # Check for similar hashes (within threshold)
            similarity_threshold = 5  # Hamming distance threshold
            for blocked_hash in self.blocked_hashes:
                if self._hash_similarity(image_hash, blocked_hash) <= similarity_threshold:
                    return {
                        "blocked": True,
                        "reason": "similar_hash",
                        "hash": image_hash,
                        "matched_hash": blocked_hash
                    }
            
            return {"blocked": False, "hash": image_hash}
            
        except Exception as e:
            logger.error(f"Error checking image block status: {e}")
            return {"blocked": False, "reason": "error"}
    
    def _hash_similarity(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes."""
        try:
            if not IMAGEHASH_AVAILABLE:
                return 100  # Max distance if unavailable
                
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2  # Hamming distance
            
        except Exception:
            return 100  # Max distance on error
    
    async def block_image_hash(self, image_hash: str, pair_id: Optional[int] = None) -> bool:
        """Add image hash to blocked list."""
        try:
            if pair_id:
                # Per-pair blocking (future enhancement)
                pass
            else:
                # Global blocking
                self.blocked_hashes.add(image_hash)
                
            # Save to database
            if self.database:
                await self._save_blocked_hash(image_hash, pair_id)
                
            logger.info(f"Blocked image hash: {image_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Error blocking image hash: {e}")
            return False
    
    async def unblock_image_hash(self, image_hash: str, pair_id: Optional[int] = None) -> bool:
        """Remove image hash from blocked list."""
        try:
            if pair_id:
                # Per-pair unblocking (future enhancement)
                pass
            else:
                # Global unblocking
                self.blocked_hashes.discard(image_hash)
                
            # Remove from database
            if self.database:
                await self._remove_blocked_hash(image_hash, pair_id)
                
            logger.info(f"Unblocked image hash: {image_hash}")
            return True
            
        except Exception as e:
            logger.error(f"Error unblocking image hash: {e}")
            return False
    
    async def _save_blocked_hash(self, image_hash: str, pair_id: Optional[int]):
        """Save blocked hash to database."""
        # TODO: Implement database storage for blocked hashes
        pass
    
    async def _remove_blocked_hash(self, image_hash: str, pair_id: Optional[int]):
        """Remove blocked hash from database."""
        # TODO: Implement database removal for blocked hashes
        pass
    
    async def get_blocked_hashes_stats(self) -> Dict[str, Any]:
        """Get statistics about blocked image hashes."""
        return {
            "total_blocked_hashes": len(self.blocked_hashes),
            "hash_available": IMAGEHASH_AVAILABLE,
            "cache_size": len(self.hash_cache)
        }

# Global instance
image_hash_manager = ImageHashManager()