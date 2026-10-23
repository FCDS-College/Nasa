"""Typed request/response contracts for every AI capability. Stdlib only."""

from ai.providers.contracts.base import Capability, HealthStatus, Locality, Provider, ProviderInfo
from ai.providers.contracts.chat import ChatMessage, ChatProvider, ChatRequest, ChatResponse, Passage
from ai.providers.contracts.embeddings import EmbeddingProvider, EmbeddingRequest, EmbeddingResponse
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.metadata import ExecutionMetadata
from ai.providers.contracts.reranking import RerankProvider, RerankRequest, RerankResponse
from ai.providers.contracts.structured import StructuredProvider, StructuredRequest, StructuredResponse
from ai.providers.contracts.transcription import TranscriptionProvider, TranscriptionRequest, TranscriptionResponse
from ai.providers.contracts.video import VideoAnalysisRequest, VideoAnalysisResponse, VideoProvider
from ai.providers.contracts.vision import ImageAnalysisRequest, ImageAnalysisResponse, VisionProvider

__all__ = [
    "Capability", "ChatMessage", "ChatProvider", "ChatRequest", "ChatResponse", "EmbeddingProvider",
    "EmbeddingRequest", "EmbeddingResponse", "ExecutionMetadata", "HealthStatus", "ImageAnalysisRequest",
    "ImageAnalysisResponse", "Locality", "Passage", "Provider", "ProviderError", "ProviderErrorCode",
    "ProviderInfo", "RerankProvider", "RerankRequest", "RerankResponse", "StructuredProvider",
    "StructuredRequest", "StructuredResponse", "TranscriptionProvider", "TranscriptionRequest",
    "TranscriptionResponse", "VideoAnalysisRequest", "VideoAnalysisResponse", "VideoProvider", "VisionProvider",
]
