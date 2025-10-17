"""DSPy-based chunk categorizer for KB ingestion with semi-automated review.

This module provides intelligent categorization of knowledge base chunks during ingestion,
with automatic approval for high-confidence categorizations and manual review for uncertain cases.

Architecture:
- Uses DSPy ChainOfThought for transparent reasoning
- Pydantic models for type safety and validation
- Market-agnostic design (works for HK/SG/AU)
- Configurable confidence threshold for auto-approval
- Batch processing support for efficiency

Cost Optimization:
- Target: <$0.05 per chunk
- Supports efficient models (Gemini Flash, GPT-4o-mini)
- Batch processing reduces API overhead
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import dspy
import logging


logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Input/Output
# ============================================================================


class ChunkCategorizationInput(BaseModel):
    """Input data for chunk categorization.

    Attributes:
        chunk_content: The text content to categorize (max 2000 chars for efficiency)
        kb_document_title: Context about the source document
        chunk_index: Position in document (0-based) for contextual understanding
    """

    chunk_content: str = Field(
        ...,
        description="The text content to categorize",
        min_length=10,
        max_length=2000,
    )
    kb_document_title: str = Field(
        ...,
        description="Title of the source document for context",
        min_length=1,
        max_length=500,
    )
    chunk_index: int = Field(
        ...,
        description="Position of this chunk in the document (0-based)",
        ge=0,
    )

    @field_validator("chunk_content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content has meaningful text after stripping."""
        if not v.strip():
            raise ValueError("chunk_content cannot be empty or whitespace only")
        return v


class ChunkCategorizationOutput(BaseModel):
    """Output from chunk categorization.

    Attributes:
        chunk_type: Categorized type of the chunk
        confidence_score: Model confidence in categorization (0.0 to 1.0)
        review_status: Whether auto-approved or needs manual review
        reasoning: Chain-of-thought explanation for the categorization
    """

    chunk_type: str = Field(
        ...,
        description="Type of content: definition|requirement|example|guidance|disclosure|measurement",
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score from 0.0 (lowest) to 1.0 (highest)",
        ge=0.0,
        le=1.0,
    )
    review_status: str = Field(
        ...,
        description="Review status: auto_approved or pending_review",
    )
    reasoning: str = Field(
        ...,
        description="Chain-of-thought explanation for the categorization",
        min_length=20,
    )

    @field_validator("chunk_type")
    @classmethod
    def validate_chunk_type(cls, v: str) -> str:
        """Ensure chunk_type is one of the valid categories."""
        valid_types = {
            "definition",
            "requirement",
            "example",
            "guidance",
            "disclosure",
            "measurement",
        }
        if v.lower() not in valid_types:
            raise ValueError(
                f"chunk_type must be one of {valid_types}, got: {v}"
            )
        return v.lower()

    @field_validator("review_status")
    @classmethod
    def validate_review_status(cls, v: str) -> str:
        """Ensure review_status is valid."""
        valid_statuses = {"auto_approved", "pending_review"}
        if v.lower() not in valid_statuses:
            raise ValueError(
                f"review_status must be one of {valid_statuses}, got: {v}"
            )
        return v.lower()


# ============================================================================
# DSPy Signature
# ============================================================================


class ChunkCategorizationSignature(dspy.Signature):
    """Categorize a knowledge base chunk into one of six types with confidence scoring.

    Chunk Types:
    - definition: Core accounting term definitions (e.g., "Revenue is the gross inflow...")
    - requirement: Mandatory accounting treatment requirements (e.g., "An entity shall...")
    - example: Illustrative examples or scenarios (e.g., "For instance, if a company...")
    - guidance: Implementation guidance and best practices (e.g., "Entities should consider...")
    - disclosure: Required financial statement disclosures (e.g., "The entity shall disclose...")
    - measurement: Measurement and recognition criteria (e.g., "Measure at fair value...")

    Confidence Scoring Guidelines:
    - 0.90-1.00: Very clear indicators, unambiguous categorization
    - 0.85-0.89: Clear categorization with minor ambiguity (auto-approve threshold)
    - 0.70-0.84: Reasonable categorization but needs review
    - 0.00-0.69: Uncertain categorization, requires manual review

    Important Notes:
    - Focus on the PRIMARY purpose of the chunk
    - Use document title for context (e.g., standards vs. guidance documents)
    - Consider chunk position (definitions often appear early)
    - Provide explicit reasoning for your categorization
    """

    chunk_content: str = dspy.InputField(
        desc="The text content to categorize (max 2000 chars)"
    )
    kb_document_title: str = dspy.InputField(
        desc="Title of the source document for context"
    )
    chunk_index: int = dspy.InputField(
        desc="Position of this chunk in the document (0-based)"
    )

    chunk_type: str = dspy.OutputField(
        desc="One of: definition|requirement|example|guidance|disclosure|measurement"
    )
    confidence_score: float = dspy.OutputField(
        desc="Confidence score from 0.0 to 1.0 (≥0.85 for auto-approval)"
    )
    reasoning: str = dspy.OutputField(
        desc="Step-by-step reasoning explaining the categorization decision"
    )


# ============================================================================
# DSPy Module
# ============================================================================


class ChunkCategorizationModule(dspy.Module):
    """DSPy module for chunk categorization using ChainOfThought.

    This module uses ChainOfThought to provide transparent reasoning
    for categorization decisions, enabling better debugging and trust.
    """

    def __init__(self):
        """Initialize the categorization module with ChainOfThought."""
        super().__init__()
        self.categorize_cot = dspy.ChainOfThought(ChunkCategorizationSignature)

    def forward(
        self,
        chunk_content: str,
        kb_document_title: str,
        chunk_index: int,
    ) -> dspy.Prediction:
        """Execute categorization with chain-of-thought reasoning.

        Args:
            chunk_content: The text to categorize
            kb_document_title: Source document title
            chunk_index: Position in document

        Returns:
            DSPy Prediction with chunk_type, confidence_score, reasoning
        """
        return self.categorize_cot(
            chunk_content=chunk_content,
            kb_document_title=kb_document_title,
            chunk_index=chunk_index,
        )


# ============================================================================
# Main ChunkCategorizer Class
# ============================================================================


class ChunkCategorizer:
    """High-level service for categorizing KB chunks with semi-automated review.

    Features:
    - Automatic approval for high-confidence categorizations (≥0.85)
    - Manual review flagging for uncertain cases
    - Batch processing for efficiency
    - Comprehensive error handling and logging
    - Market-agnostic design

    Cost Optimization:
    - Uses efficient models (configurable)
    - Batch processing reduces overhead
    - Target: <$0.05 per chunk

    Example:
        >>> categorizer = ChunkCategorizer(
        ...     lm=dspy.LM('openai/gpt-4o-mini'),
        ...     auto_approve_threshold=0.85
        ... )
        >>> result = categorizer.categorize(
        ...     chunk_content="Revenue is recognised when control is transferred.",
        ...     kb_document_title="HKFRS 15 Revenue Recognition",
        ...     chunk_index=5
        ... )
        >>> print(result.chunk_type)  # 'requirement'
        >>> print(result.review_status)  # 'auto_approved' if confidence ≥ 0.85
    """

    # Class-level constants for chunk types
    CHUNK_TYPES = {
        "definition",
        "requirement",
        "example",
        "guidance",
        "disclosure",
        "measurement",
    }

    DEFAULT_AUTO_APPROVE_THRESHOLD = 0.85

    def __init__(
        self,
        lm: Optional[dspy.LM] = None,
        auto_approve_threshold: float = DEFAULT_AUTO_APPROVE_THRESHOLD,
    ):
        """Initialize the chunk categorizer.

        Args:
            lm: DSPy language model instance. If None, uses the configured default.
            auto_approve_threshold: Minimum confidence score for auto-approval (default: 0.85)

        Raises:
            ValueError: If auto_approve_threshold is not in [0.0, 1.0]
        """
        if not 0.0 <= auto_approve_threshold <= 1.0:
            raise ValueError(
                f"auto_approve_threshold must be in [0.0, 1.0], got: {auto_approve_threshold}"
            )

        self.auto_approve_threshold = auto_approve_threshold

        # Configure DSPy LM if provided
        if lm is not None:
            dspy.configure(lm=lm)

        # Initialize the DSPy module
        self.module = ChunkCategorizationModule()

        logger.info(
            f"ChunkCategorizer initialized with auto-approve threshold: {auto_approve_threshold}"
        )

    def categorize(
        self,
        chunk_content: str,
        kb_document_title: str,
        chunk_index: int,
    ) -> ChunkCategorizationOutput:
        """Categorize a single chunk with confidence scoring.

        Args:
            chunk_content: The text content to categorize (max 2000 chars)
            kb_document_title: Title of the source document
            chunk_index: Position in document (0-based)

        Returns:
            ChunkCategorizationOutput with chunk_type, confidence_score,
            review_status, and reasoning

        Raises:
            ValueError: If input validation fails
            RuntimeError: If DSPy prediction fails

        Example:
            >>> result = categorizer.categorize(
            ...     chunk_content="Revenue is recognised when control is transferred to the customer.",
            ...     kb_document_title="HKFRS 15 Revenue Recognition",
            ...     chunk_index=5
            ... )
            >>> print(f"Type: {result.chunk_type}, Confidence: {result.confidence_score}")
            Type: requirement, Confidence: 0.92
        """
        # Validate input using Pydantic
        try:
            input_data = ChunkCategorizationInput(
                chunk_content=chunk_content,
                kb_document_title=kb_document_title,
                chunk_index=chunk_index,
            )
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            raise ValueError(f"Invalid input: {e}") from e

        # Execute DSPy prediction
        try:
            prediction = self.module.forward(
                chunk_content=input_data.chunk_content,
                kb_document_title=input_data.kb_document_title,
                chunk_index=input_data.chunk_index,
            )
        except Exception as e:
            logger.error(f"DSPy prediction failed: {e}")
            raise RuntimeError(f"Categorization failed: {e}") from e

        # Parse confidence score (handle string or float)
        try:
            confidence_score = float(prediction.confidence_score)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid confidence_score: {prediction.confidence_score}. Defaulting to 0.0"
            )
            confidence_score = 0.0

        # Normalize chunk_type
        chunk_type = prediction.chunk_type.lower().strip()

        # Determine review status based on confidence
        if confidence_score >= self.auto_approve_threshold:
            review_status = "auto_approved"
        else:
            review_status = "pending_review"

        # Validate and construct output
        try:
            output = ChunkCategorizationOutput(
                chunk_type=chunk_type,
                confidence_score=confidence_score,
                review_status=review_status,
                reasoning=prediction.reasoning,
            )
        except Exception as e:
            logger.error(f"Output validation failed: {e}")
            # Fallback to safe defaults
            output = ChunkCategorizationOutput(
                chunk_type="guidance",  # Safe default
                confidence_score=0.0,
                review_status="pending_review",
                reasoning=f"Categorization failed validation: {e}. Manual review required.",
            )

        logger.debug(
            f"Categorized chunk {chunk_index} as '{output.chunk_type}' "
            f"(confidence: {output.confidence_score:.2f}, status: {output.review_status})"
        )

        return output

    def categorize_batch(
        self,
        chunks: List[ChunkCategorizationInput],
        log_progress: bool = True,
    ) -> List[ChunkCategorizationOutput]:
        """Categorize multiple chunks in batch for efficiency.

        Args:
            chunks: List of ChunkCategorizationInput objects
            log_progress: Whether to log progress (default: True)

        Returns:
            List of ChunkCategorizationOutput objects (same order as input)

        Raises:
            ValueError: If chunks list is empty

        Example:
            >>> inputs = [
            ...     ChunkCategorizationInput(
            ...         chunk_content="Revenue is recognised when...",
            ...         kb_document_title="HKFRS 15",
            ...         chunk_index=5
            ...     ),
            ...     ChunkCategorizationInput(
            ...         chunk_content="For example, if a company sells goods...",
            ...         kb_document_title="HKFRS 15",
            ...         chunk_index=6
            ...     ),
            ... ]
            >>> results = categorizer.categorize_batch(inputs)
            >>> print(f"Categorized {len(results)} chunks")
            Categorized 2 chunks
        """
        if not chunks:
            raise ValueError("chunks list cannot be empty")

        if log_progress:
            logger.info(f"Starting batch categorization of {len(chunks)} chunks")

        results = []
        auto_approved_count = 0
        pending_review_count = 0

        for i, chunk_input in enumerate(chunks, start=1):
            try:
                result = self.categorize(
                    chunk_content=chunk_input.chunk_content,
                    kb_document_title=chunk_input.kb_document_title,
                    chunk_index=chunk_input.chunk_index,
                )
                results.append(result)

                # Track approval statistics
                if result.review_status == "auto_approved":
                    auto_approved_count += 1
                else:
                    pending_review_count += 1

                if log_progress and i % 10 == 0:
                    logger.info(f"Processed {i}/{len(chunks)} chunks...")

            except Exception as e:
                logger.error(f"Error categorizing chunk {i}: {e}")
                # Add fallback result for failed chunk
                results.append(
                    ChunkCategorizationOutput(
                        chunk_type="guidance",
                        confidence_score=0.0,
                        review_status="pending_review",
                        reasoning=f"Categorization error: {str(e)}. Manual review required.",
                    )
                )
                pending_review_count += 1

        if log_progress:
            auto_approval_rate = (auto_approved_count / len(chunks)) * 100
            logger.info(
                f"Batch categorization complete: {len(chunks)} chunks processed. "
                f"Auto-approved: {auto_approved_count} ({auto_approval_rate:.1f}%), "
                f"Pending review: {pending_review_count}"
            )

        return results

    def get_statistics(self, results: List[ChunkCategorizationOutput]) -> dict:
        """Calculate statistics for a batch of categorization results.

        Args:
            results: List of ChunkCategorizationOutput objects

        Returns:
            Dictionary with statistics including:
            - total_chunks: Total number of chunks
            - auto_approved: Number of auto-approved chunks
            - pending_review: Number pending manual review
            - auto_approval_rate: Percentage of auto-approved chunks
            - avg_confidence: Average confidence score
            - chunk_type_distribution: Count by chunk type

        Example:
            >>> stats = categorizer.get_statistics(results)
            >>> print(f"Auto-approval rate: {stats['auto_approval_rate']:.1f}%")
            Auto-approval rate: 82.5%
        """
        if not results:
            return {
                "total_chunks": 0,
                "auto_approved": 0,
                "pending_review": 0,
                "auto_approval_rate": 0.0,
                "avg_confidence": 0.0,
                "chunk_type_distribution": {},
            }

        total = len(results)
        auto_approved = sum(1 for r in results if r.review_status == "auto_approved")
        pending_review = total - auto_approved
        avg_confidence = sum(r.confidence_score for r in results) / total

        # Count by chunk type
        type_distribution = {}
        for result in results:
            type_distribution[result.chunk_type] = (
                type_distribution.get(result.chunk_type, 0) + 1
            )

        return {
            "total_chunks": total,
            "auto_approved": auto_approved,
            "pending_review": pending_review,
            "auto_approval_rate": (auto_approved / total) * 100,
            "avg_confidence": avg_confidence,
            "chunk_type_distribution": type_distribution,
        }
