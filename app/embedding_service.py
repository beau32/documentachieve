"""Vector embeddings service for semantic search."""

import logging
from typing import Optional, List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing document embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model to use
                       Lightweight options: all-MiniLM-L6-v2, all-MiniLM-L12-v2
                       More accurate: all-mpnet-base-v2
        """
        self.model_name = model_name
        self.model = None
        self.enabled = EMBEDDINGS_AVAILABLE
        
        if self.enabled:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Embedding model '{model_name}' loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {str(e)}")
                self.enabled = False
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list, or None if embedding service is unavailable
        """
        if not self.enabled or not self.model:
            return None
        
        try:
            if not text or not text.strip():
                return None
            
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Convert to list for JSON serialization
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (or None for each failed)
        """
        if not self.enabled or not self.model:
            return [None] * len(texts)
        
        try:
            # Filter non-empty texts
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                return [None] * len(texts)
            
            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts, convert_to_numpy=True)
            
            # Map back to original list
            result = []
            valid_idx = 0
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[valid_idx].tolist())
                    valid_idx += 1
                else:
                    result.append(None)
            
            return result
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return [None] * len(texts)
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            if not vec1 or not vec2:
                return 0.0
            
            # Convert to numpy arrays
            v1 = np.array(vec1).reshape(1, -1)
            v2 = np.array(vec2).reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(v1, v2)[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    @staticmethod
    def batch_cosine_similarity(
        query_vec: List[float],
        vectors: List[List[float]]
    ) -> List[float]:
        """
        Calculate cosine similarity between query and multiple vectors.
        
        Args:
            query_vec: Query embedding vector
            vectors: List of embedding vectors to compare
            
        Returns:
            List of similarity scores (0-1)
        """
        try:
            if not query_vec or not vectors:
                return []
            
            # Convert to numpy arrays
            q = np.array(query_vec).reshape(1, -1)
            vecs = np.array(vectors)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(q, vecs)[0]
            return [float(s) for s in similarities]
        except Exception as e:
            logger.error(f"Error calculating batch similarities: {str(e)}")
            return [0.0] * len(vectors)


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service singleton instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
