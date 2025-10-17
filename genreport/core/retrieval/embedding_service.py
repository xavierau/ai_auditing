"""Enhanced embedding service supporting Google Gemini and OpenAI.

Provides flexible embedding generation with support for multiple providers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from enum import Enum

import openai
import google.generativeai as genai

from genreport.core.utils.config import settings


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    GEMINI = "gemini"
    OPENAI = "openai"


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def generate_embedding(self, text: str, task_type: Optional[str] = None) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            task_type: Optional task type hint (provider-specific)

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    def generate_embeddings_batch(
        self, texts: List[str], task_type: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            task_type: Optional task type hint (provider-specific)

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Get the embedding dimensions for this provider."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name for this provider."""
        pass


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embedding provider.

    Reference: https://ai.google.dev/gemini-api/docs/embeddings
    """

    def __init__(
        self,
        api_key: str,
        model: str = "models/text-embedding-004",
        dimensions: int = 768,
    ):
        """Initialize Gemini embedding provider.

        Args:
            api_key: Google API key
            model: Gemini embedding model name
            dimensions: Output embedding dimensions (768 default)
        """
        self.model = model
        self.dimensions = dimensions

        # Configure Gemini
        genai.configure(api_key=api_key)

    def generate_embedding(
        self, text: str, task_type: Optional[str] = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        """Generate embedding for a single text using Gemini.

        Args:
            text: Text to embed
            task_type: Task type - one of:
                - RETRIEVAL_QUERY: Query in search/retrieval
                - RETRIEVAL_DOCUMENT: Document in search/retrieval (default)
                - SEMANTIC_SIMILARITY: Semantic similarity
                - CLASSIFICATION: Text classification
                - CLUSTERING: Text clustering

        Returns:
            Embedding vector (Python floats, not numpy)
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Cannot generate embedding for empty text")

        # Truncate if too long (Gemini has ~20K token limit)
        if len(text) > 80000:  # Rough estimate: 4 chars per token
            text = text[:80000]

        result = genai.embed_content(
            model=self.model,
            content=text,
            task_type=task_type,
            output_dimensionality=self.dimensions,
        )

        # Convert numpy.float32 to Python float for JSON serialization
        embedding = result["embedding"]
        return [float(x) for x in embedding]

    def generate_embeddings_batch(
        self, texts: List[str], task_type: Optional[str] = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts using Gemini.

        Args:
            texts: List of texts to embed
            task_type: Task type for all texts

        Returns:
            List of embedding vectors (Python floats, not numpy)
        """
        if not texts:
            return []

        # Filter out empty texts and truncate long ones
        processed_texts = []
        for text in texts:
            if text and len(text.strip()) > 0:
                if len(text) > 80000:
                    text = text[:80000]
                processed_texts.append(text)

        if not processed_texts:
            return []

        # Gemini batch embedding
        result = genai.embed_content(
            model=self.model,
            content=processed_texts,
            task_type=task_type,
            output_dimensionality=self.dimensions,
        )

        # Convert numpy.float32 to Python float for JSON serialization
        embeddings = result["embedding"]
        return [[float(x) for x in emb] for emb in embeddings]

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self.dimensions

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-ada-002",
        dimensions: int = 1536,
    ):
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            model: OpenAI embedding model name
            dimensions: Output embedding dimensions
        """
        self.model = model
        self.dimensions = dimensions
        self.client = openai.OpenAI(api_key=api_key)

    def generate_embedding(self, text: str, task_type: Optional[str] = None) -> List[float]:
        """Generate embedding for a single text using OpenAI.

        Args:
            text: Text to embed
            task_type: Not used for OpenAI (kept for interface compatibility)

        Returns:
            Embedding vector
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Cannot generate embedding for empty text")

        # Truncate if too long (max 8191 tokens for ada-002)
        if len(text) > 32000:  # Rough estimate: 4 chars per token
            text = text[:32000]

        response = self.client.embeddings.create(model=self.model, input=text)

        return response.data[0].embedding

    def generate_embeddings_batch(
        self, texts: List[str], task_type: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts using OpenAI.

        Args:
            texts: List of texts to embed
            task_type: Not used for OpenAI (kept for interface compatibility)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter out empty texts and truncate long ones
        processed_texts = []
        for text in texts:
            if text and len(text.strip()) > 0:
                if len(text) > 32000:
                    text = text[:32000]
                processed_texts.append(text)

        if not processed_texts:
            return []

        response = self.client.embeddings.create(model=self.model, input=processed_texts)

        return [item.embedding for item in response.data]

    def get_dimensions(self) -> int:
        """Get embedding dimensions."""
        return self.dimensions

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model


class EmbeddingService:
    """Unified embedding service supporting multiple providers.

    Automatically selects provider based on settings with Redis caching.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        use_cache: bool = True,
    ):
        """Initialize embedding service.

        Args:
            provider: Provider name (gemini or openai). Uses settings.embedding_provider if None.
            api_key: API key. Uses settings.embedding_api_key if None.
            model: Model name. Uses settings.embedding_model if None.
            dimensions: Embedding dimensions. Uses settings.embedding_dimensions if None.
            use_cache: Whether to use Redis cache (default: True)
        """
        # Use settings as defaults
        self.provider_name = provider or settings.embedding_provider
        self.api_key = api_key or settings.embedding_api_key
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions
        self.use_cache = use_cache

        # Validate API key
        if not self.api_key:
            raise ValueError(
                f"API key not configured for {self.provider_name}. "
                f"Set GOOGLE_API_KEY or OPENAI_API_KEY in .env"
            )

        # Initialize provider
        self.provider = self._create_provider()

        # Initialize cache if enabled
        if self.use_cache:
            from genreport.core.retrieval.embedding_cache import EmbeddingCache
            self.cache = EmbeddingCache(
                provider=self.provider_name,
                model=self.model,
                dimensions=self.dimensions,
            )
        else:
            self.cache = None

    def _create_provider(self) -> BaseEmbeddingProvider:
        """Create the appropriate embedding provider."""
        if self.provider_name == EmbeddingProvider.GEMINI:
            return GeminiEmbeddingProvider(
                api_key=self.api_key,
                model=self.model,
                dimensions=self.dimensions,
            )
        elif self.provider_name == EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingProvider(
                api_key=self.api_key,
                model=self.model,
                dimensions=self.dimensions,
            )
        else:
            raise ValueError(
                f"Unsupported embedding provider: {self.provider_name}. "
                f"Use 'gemini' or 'openai'."
            )

    def generate_embedding(
        self, text: str, task_type: Optional[str] = "RETRIEVAL_DOCUMENT"
    ) -> List[float]:
        """Generate embedding for a single text with caching.

        Args:
            text: Text to embed
            task_type: Task type hint for Gemini (ignored for OpenAI)
                - RETRIEVAL_QUERY: For search queries
                - RETRIEVAL_DOCUMENT: For documents (default)
                - SEMANTIC_SIMILARITY: For similarity tasks
                - CLASSIFICATION: For classification
                - CLUSTERING: For clustering

        Returns:
            Embedding vector
        """
        # Try cache first if enabled
        if self.cache:
            cached_embedding = self.cache.get_cached_embedding(text)
            if cached_embedding is not None:
                return cached_embedding

        # Generate new embedding
        embedding = self.provider.generate_embedding(text, task_type)

        # Cache if enabled
        if self.cache:
            self.cache.cache_embedding(text, embedding)

        return embedding

    def generate_embeddings_batch(
        self, texts: List[str], task_type: Optional[str] = "RETRIEVAL_DOCUMENT"
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            task_type: Task type hint for Gemini (ignored for OpenAI)

        Returns:
            List of embedding vectors
        """
        return self.provider.generate_embeddings_batch(texts, task_type)

    def get_dimensions(self) -> int:
        """Get the embedding dimensions."""
        return self.provider.get_dimensions()

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.provider.get_model_name()

    def get_provider_name(self) -> str:
        """Get the provider name."""
        return self.provider_name
