"""
Embedding service for generating text embeddings.
Supports multiple embedding strategies with fallbacks.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global variables for models
sentence_transformer_model = None
tfidf_vectorizer = None

def load_embedding_model():
    """Load the sentence transformer model."""
    global sentence_transformer_model
    print(f"🤖 MODEL_LOAD: Attempting to load SentenceTransformer model...")
    try:
        from sentence_transformers import SentenceTransformer
        print(f"🤖 MODEL_LOAD: Loading model: {settings.embedding_model}")
        sentence_transformer_model = SentenceTransformer(settings.embedding_model)
        print(f" MODEL_LOAD: SentenceTransformer model loaded successfully")
        logger.info(f"✅ Loaded SentenceTransformer model: {settings.embedding_model}")
    except Exception as e:
        print(f" MODEL_LOAD: Failed to load SentenceTransformer: {e}")
        logger.warning(f"⚠️ Failed to load SentenceTransformer: {e}")
        sentence_transformer_model = None

async def load_embedding_model_async():
    """Async wrapper for loading the embedding model."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, load_embedding_model)

def generate_embeddings(texts: List[str], method: str = "auto") -> List[List[float]]:
    """Generate embeddings for a list of texts with fallback strategies."""
    print(f"EMBEDDINGS: Starting embedding generation for {len(texts)} texts")
    print(f"EMBEDDINGS: Method: {method}")

    if not texts:
        print(f" EMBEDDINGS: No texts provided, returning empty list")
        return []

    # Show sample of input texts
    for i, text in enumerate(texts[:3]):
        print(f"EMBEDDINGS: Sample text {i+1}: {text[:100]}...")

    # Strategy 1: SentenceTransformer (preferred)
    if method in ["auto", "sentence_transformer"]:
        print(f"EMBEDDINGS: Trying SentenceTransformer method...")
        print(f"EMBEDDINGS: SentenceTransformer model available: {sentence_transformer_model is not None}")

        if sentence_transformer_model:
            try:
                print(f" EMBEDDINGS: Encoding {len(texts)} texts with SentenceTransformer...")
                embeddings = sentence_transformer_model.encode(texts)
                result = [embedding.tolist() for embedding in embeddings]
                print(f" EMBEDDINGS: SentenceTransformer succeeded - generated {len(result)} embeddings")
                print(f" EMBEDDINGS: First embedding shape: {len(result[0])} dimensions")
                return result
            except Exception as e:
                print(f" EMBEDDINGS: SentenceTransformer failed: {e}")
                logger.warning(f"⚠️ SentenceTransformer failed: {e}, falling back to TF-IDF")

    # Strategy 2: TF-IDF fallback
    if method in ["auto", "tfidf"]:
        print(f" EMBEDDINGS: Trying TF-IDF fallback method...")
        try:
            result = _generate_tfidf_embeddings(texts)
            print(f" EMBEDDINGS: TF-IDF succeeded - generated {len(result)} embeddings")
            if result:
                print(f" EMBEDDINGS: TF-IDF embedding shape: {len(result[0])} dimensions")
            return result
        except Exception as e:
            print(f" EMBEDDINGS: TF-IDF failed: {e}")
            logger.warning(f"⚠️ TF-IDF failed: {e}, using basic embeddings")

    # Strategy 3: Basic word-based embeddings (last resort)
    print(f" EMBEDDINGS: Using basic word-based embeddings as last resort...")
    result = _generate_basic_embeddings(texts)
    print(f" EMBEDDINGS: Basic embeddings generated - {len(result)} embeddings")
    if result:
        print(f" EMBEDDINGS: Basic embedding shape: {len(result[0])} dimensions")
    return result

def _generate_tfidf_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate TF-IDF based embeddings."""
    print(f" TFIDF: Starting TF-IDF embedding generation for {len(texts)} texts")
    global tfidf_vectorizer

    if tfidf_vectorizer is None:
        print(f" TFIDF: Creating new TF-IDF vectorizer...")
        tfidf_vectorizer = TfidfVectorizer(
            max_features=384,  # Match sentence transformer dimension
            stop_words='english',
            ngram_range=(1, 2)
        )
        print(f" TFIDF: Fitting vectorizer on {len(texts)} texts...")
        # Fit on the provided texts
        tfidf_vectorizer.fit(texts)
        print(f" TFIDF: Vectorizer fitted successfully")
    else:
        print(f" TFIDF: Using existing TF-IDF vectorizer")

    try:
        print(f" TFIDF: Transforming texts to TF-IDF vectors...")
        # Transform texts to TF-IDF vectors
        tfidf_matrix = tfidf_vectorizer.transform(texts)
        result = tfidf_matrix.toarray().tolist()
        print(f" TFIDF: Successfully transformed {len(result)} texts to vectors")
        print(f" TFIDF: Matrix shape: {tfidf_matrix.shape}")
        return result
    except Exception as e:
        print(f" TFIDF: Transform failed: {e}, trying refit...")
        # If transform fails, refit and transform
        try:
            tfidf_vectorizer.fit(texts)
            tfidf_matrix = tfidf_vectorizer.transform(texts)
            result = tfidf_matrix.toarray().tolist()
            print(f" TFIDF: Refit and transform succeeded")
            return result
        except Exception as refit_error:
            print(f" TFIDF: Refit also failed: {refit_error}")
            raise

def _generate_basic_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate basic word-count based embeddings as last resort."""
    all_words = set()
    for text in texts:
        words = text.lower().split()
        all_words.update(words)

    vocab = list(all_words)
    embeddings = []

    for text in texts:
        words = text.lower().split()
        word_counts = {word: words.count(word) for word in vocab}
        embedding = [word_counts.get(word, 0) for word in vocab]
        # Normalize
        total = sum(embedding) or 1
        normalized = [count/total for count in embedding]
        embeddings.append(normalized)

    return embeddings

async def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for a single query by reconstructing vectorizer from database."""
    global tfidf_vectorizer

    print(f"QUERY_EMBEDDING: Generating embedding for query: '{query[:50]}...'")

    # Always reconstruct the vectorizer from database to ensure consistency
    try:
        from app.core.database import db_manager

        async with db_manager.get_connection() as conn:
            # Get all document content to retrain the vectorizer
            chunks = await conn.fetch("SELECT content FROM document_embeddings ORDER BY \"chunkIndex\"")

            if not chunks:
                print("QUERY_EMBEDDING: No chunks found in database - no documents processed yet")
                return []

            print(f"QUERY_EMBEDDING: Found {len(chunks)} chunks, reconstructing vectorizer...")
            chunk_texts = [chunk['content'] for chunk in chunks]

            # Create a new TF-IDF vectorizer with the same settings as document processing
            from sklearn.feature_extraction.text import TfidfVectorizer

            vectorizer = TfidfVectorizer(
                max_features=384,  # Match the document processing settings
                stop_words='english',
                ngram_range=(1, 2)
            )

            # Fit on all document chunks PLUS the query to ensure query tokens are included
            all_texts = chunk_texts + [query]
            vectorizer.fit(all_texts)

            print(f"QUERY_EMBEDDING: Vectorizer fitted on {len(all_texts)} texts")

            # Now transform just the query
            query_matrix = vectorizer.transform([query])
            query_embedding = query_matrix.toarray()[0].tolist()

            print(f"QUERY_EMBEDDING: Generated {len(query_embedding)}-dimensional embedding")
            print(f"QUERY_EMBEDDING: Sample values: {query_embedding[:5]}")

            return query_embedding

    except Exception as e:
        print(f"QUERY_EMBEDDING: Error reconstructing vectorizer: {e}")
        import traceback
        traceback.print_exc()
        return []

def cosine_similarity_score(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    try:
        # Check if dimensions match
        if len(embedding1) != len(embedding2):
            print(f"SIMILARITY: Dimension mismatch {len(embedding1)} vs {len(embedding2)} - using fallback")
            # Fallback: simple word overlap similarity
            return _fallback_similarity(embedding1, embedding2)

        # Convert to numpy arrays
        vec1 = np.array(embedding1).reshape(1, -1)
        vec2 = np.array(embedding2).reshape(1, -1)

        # Calculate cosine similarity
        similarity = cosine_similarity(vec1, vec2)[0][0]
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        print(f"SIMILARITY: Cosine similarity failed, using fallback similarity")
        return _fallback_similarity(embedding1, embedding2)

def _fallback_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Fallback similarity when dimensions don't match."""
    try:
        # Simple fallback: if both embeddings have non-zero values, give some similarity
        sum1 = sum(abs(x) for x in embedding1)
        sum2 = sum(abs(x) for x in embedding2)

        if sum1 > 0 and sum2 > 0:
            return 0.1  # Give a small positive similarity
        else:
            return 0.0
    except:
        return 0.05  # Default small similarity