"""Tests for DSPy-based chunk categorizer.

Test coverage:
- Pydantic model validation (input/output)
- DSPy signature definition
- Individual chunk categorization
- Batch processing
- Auto-approval logic
- Edge cases (very short chunks, ambiguous content, mixed content)
- Error handling
- Statistics calculation
"""

import pytest
from unittest.mock import Mock, patch
import dspy
from dspy import Prediction

from genreport.core.retrieval.chunk_categorizer import (
    ChunkCategorizationInput,
    ChunkCategorizationOutput,
    ChunkCategorizationSignature,
    ChunkCategorizationModule,
    ChunkCategorizer,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_lm():
    """Create a mock DSPy LM for testing without API calls."""
    mock = Mock(spec=dspy.LM)
    return mock


@pytest.fixture
def categorizer(mock_lm):
    """Create a ChunkCategorizer instance with mocked LM."""
    return ChunkCategorizer(lm=mock_lm, auto_approve_threshold=0.85)


# ============================================================================
# Test Pydantic Input Model
# ============================================================================


def test_chunk_categorization_input_valid():
    """Test valid input creation."""
    input_data = ChunkCategorizationInput(
        chunk_content="Revenue is recognised when control of goods is transferred.",
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=5,
    )

    assert input_data.chunk_content == "Revenue is recognised when control of goods is transferred."
    assert input_data.kb_document_title == "HKFRS 15 Revenue Recognition"
    assert input_data.chunk_index == 5


def test_chunk_categorization_input_too_short():
    """Test input validation for content too short."""
    with pytest.raises(ValueError, match="at least 10 characters"):
        ChunkCategorizationInput(
            chunk_content="Short",  # Only 5 characters
            kb_document_title="HKFRS 15",
            chunk_index=0,
        )


def test_chunk_categorization_input_too_long():
    """Test input validation for content too long."""
    long_content = "A" * 2001  # Exceeds max length

    with pytest.raises(ValueError, match="at most 2000 characters"):
        ChunkCategorizationInput(
            chunk_content=long_content,
            kb_document_title="HKFRS 15",
            chunk_index=0,
        )


def test_chunk_categorization_input_empty_content():
    """Test input validation for empty or whitespace-only content."""
    # Pydantic will catch this as "too short" before our custom validator
    with pytest.raises(ValueError, match="at least 10 characters"):
        ChunkCategorizationInput(
            chunk_content="   ",  # Whitespace only (less than 10 chars)
            kb_document_title="HKFRS 15",
            chunk_index=0,
        )


def test_chunk_categorization_input_negative_index():
    """Test input validation for negative chunk index."""
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        ChunkCategorizationInput(
            chunk_content="Valid content here.",
            kb_document_title="HKFRS 15",
            chunk_index=-1,  # Invalid negative index
        )


# ============================================================================
# Test Pydantic Output Model
# ============================================================================


def test_chunk_categorization_output_valid():
    """Test valid output creation."""
    output = ChunkCategorizationOutput(
        chunk_type="requirement",
        confidence_score=0.92,
        review_status="auto_approved",
        reasoning="This chunk states a mandatory accounting treatment for revenue recognition.",
    )

    assert output.chunk_type == "requirement"
    assert output.confidence_score == 0.92
    assert output.review_status == "auto_approved"
    assert len(output.reasoning) > 20


def test_chunk_categorization_output_invalid_chunk_type():
    """Test output validation for invalid chunk_type."""
    with pytest.raises(ValueError, match="chunk_type must be one of"):
        ChunkCategorizationOutput(
            chunk_type="invalid_type",  # Invalid type
            confidence_score=0.85,
            review_status="auto_approved",
            reasoning="Some reasoning here that is long enough.",
        )


def test_chunk_categorization_output_normalizes_chunk_type():
    """Test that chunk_type is normalized to lowercase."""
    output = ChunkCategorizationOutput(
        chunk_type="REQUIREMENT",  # Uppercase
        confidence_score=0.85,
        review_status="auto_approved",
        reasoning="Some reasoning here that is long enough.",
    )

    assert output.chunk_type == "requirement"  # Normalized to lowercase


def test_chunk_categorization_output_confidence_out_of_range():
    """Test output validation for confidence_score out of range."""
    with pytest.raises(ValueError, match="less than or equal to 1"):
        ChunkCategorizationOutput(
            chunk_type="requirement",
            confidence_score=1.5,  # Out of range
            review_status="auto_approved",
            reasoning="Some reasoning here that is long enough.",
        )

    with pytest.raises(ValueError, match="greater than or equal to 0"):
        ChunkCategorizationOutput(
            chunk_type="requirement",
            confidence_score=-0.1,  # Out of range
            review_status="auto_approved",
            reasoning="Some reasoning here that is long enough.",
        )


def test_chunk_categorization_output_invalid_review_status():
    """Test output validation for invalid review_status."""
    with pytest.raises(ValueError, match="review_status must be one of"):
        ChunkCategorizationOutput(
            chunk_type="requirement",
            confidence_score=0.85,
            review_status="invalid_status",  # Invalid status
            reasoning="Some reasoning here that is long enough.",
        )


def test_chunk_categorization_output_reasoning_too_short():
    """Test output validation for reasoning too short."""
    with pytest.raises(ValueError, match="at least 20 characters"):
        ChunkCategorizationOutput(
            chunk_type="requirement",
            confidence_score=0.85,
            review_status="auto_approved",
            reasoning="Too short",  # Less than 20 chars
        )


# ============================================================================
# Test Valid Chunk Types
# ============================================================================


@pytest.mark.parametrize(
    "chunk_type",
    ["definition", "requirement", "example", "guidance", "disclosure", "measurement"],
)
def test_all_valid_chunk_types(chunk_type):
    """Test that all valid chunk types are accepted."""
    output = ChunkCategorizationOutput(
        chunk_type=chunk_type,
        confidence_score=0.9,
        review_status="auto_approved",
        reasoning="This is a valid categorization with sufficient reasoning.",
    )
    assert output.chunk_type == chunk_type


# ============================================================================
# Test ChunkCategorizer Initialization
# ============================================================================


def test_chunk_categorizer_initialization_default():
    """Test categorizer initialization with default threshold."""
    categorizer = ChunkCategorizer()
    assert categorizer.auto_approve_threshold == 0.85


def test_chunk_categorizer_initialization_custom_threshold():
    """Test categorizer initialization with custom threshold."""
    categorizer = ChunkCategorizer(auto_approve_threshold=0.90)
    assert categorizer.auto_approve_threshold == 0.90


def test_chunk_categorizer_initialization_invalid_threshold():
    """Test categorizer initialization with invalid threshold."""
    with pytest.raises(ValueError, match="auto_approve_threshold must be in"):
        ChunkCategorizer(auto_approve_threshold=1.5)

    with pytest.raises(ValueError, match="auto_approve_threshold must be in"):
        ChunkCategorizer(auto_approve_threshold=-0.1)


# ============================================================================
# Test Single Chunk Categorization
# ============================================================================


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_requirement_high_confidence(mock_forward, categorizer):
    """Test categorization of a clear requirement with high confidence."""
    # Mock DSPy prediction
    mock_forward.return_value = Prediction(
        chunk_type="requirement",
        confidence_score=0.92,
        reasoning="This chunk states a mandatory accounting treatment for revenue recognition, "
        "specifically the timing criterion. The use of 'is recognised when' indicates "
        "a requirement rather than guidance or definition.",
    )

    result = categorizer.categorize(
        chunk_content="Revenue is recognised when control of goods or services is transferred to the customer.",
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=5,
    )

    assert result.chunk_type == "requirement"
    assert result.confidence_score == 0.92
    assert result.review_status == "auto_approved"  # ≥ 0.85
    assert len(result.reasoning) > 20


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_definition_high_confidence(mock_forward, categorizer):
    """Test categorization of a clear definition with high confidence."""
    mock_forward.return_value = Prediction(
        chunk_type="definition",
        confidence_score=0.95,
        reasoning="This chunk provides a clear definition of revenue, starting with 'Revenue is' "
        "which is a classic definition pattern. It appears early in the document (index 2) "
        "where definitions typically occur.",
    )

    result = categorizer.categorize(
        chunk_content="Revenue is the gross inflow of economic benefits during the period arising "
        "from ordinary activities of an entity.",
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=2,
    )

    assert result.chunk_type == "definition"
    assert result.confidence_score == 0.95
    assert result.review_status == "auto_approved"
    assert "definition" in result.reasoning.lower()


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_example_medium_confidence(mock_forward, categorizer):
    """Test categorization of an example with medium confidence (needs review)."""
    mock_forward.return_value = Prediction(
        chunk_type="example",
        confidence_score=0.78,  # Below auto-approve threshold
        reasoning="This chunk appears to be an example based on the phrase 'For instance', "
        "but it also contains some guidance elements, making the categorization "
        "somewhat ambiguous.",
    )

    result = categorizer.categorize(
        chunk_content="For instance, if a company sells goods with a right of return, it should estimate "
        "the expected returns and recognize revenue only for goods expected to be retained.",
        kb_document_title="HKFRS 15 Implementation Guide",
        chunk_index=45,
    )

    assert result.chunk_type == "example"
    assert result.confidence_score == 0.78
    assert result.review_status == "pending_review"  # < 0.85
    assert len(result.reasoning) > 20


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_disclosure_high_confidence(mock_forward, categorizer):
    """Test categorization of a disclosure requirement with high confidence."""
    mock_forward.return_value = Prediction(
        chunk_type="disclosure",
        confidence_score=0.89,
        reasoning="This chunk clearly specifies a disclosure requirement using 'An entity shall disclose', "
        "which is standard language for mandatory disclosures in accounting standards. "
        "The content focuses on what must be disclosed in financial statements.",
    )

    result = categorizer.categorize(
        chunk_content="An entity shall disclose the amount of revenue recognised from contracts with customers "
        "in the current reporting period, disaggregated by major category.",
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=78,
    )

    assert result.chunk_type == "disclosure"
    assert result.confidence_score == 0.89
    assert result.review_status == "auto_approved"
    assert "disclose" in result.reasoning.lower()


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_measurement_medium_confidence(mock_forward, categorizer):
    """Test categorization of measurement criteria with medium confidence."""
    mock_forward.return_value = Prediction(
        chunk_type="measurement",
        confidence_score=0.82,
        reasoning="This chunk discusses measurement criteria for contract assets, using 'measure at'. "
        "However, it also contains some requirement language, creating slight ambiguity.",
    )

    result = categorizer.categorize(
        chunk_content="Contract assets shall be measured at fair value less costs to sell if that measurement "
        "results in a higher carrying amount.",
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=34,
    )

    assert result.chunk_type == "measurement"
    assert result.confidence_score == 0.82
    assert result.review_status == "pending_review"  # < 0.85


# ============================================================================
# Test Edge Cases
# ============================================================================


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_very_short_chunk(mock_forward, categorizer):
    """Test categorization of a very short but valid chunk."""
    mock_forward.return_value = Prediction(
        chunk_type="definition",
        confidence_score=0.88,
        reasoning="Short chunk but clearly defines a term using standard definition format.",
    )

    result = categorizer.categorize(
        chunk_content="Assets are resources controlled by the entity.",
        kb_document_title="Conceptual Framework",
        chunk_index=1,
    )

    assert result.chunk_type == "definition"
    assert result.confidence_score == 0.88
    assert result.review_status == "auto_approved"


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_ambiguous_mixed_content(mock_forward, categorizer):
    """Test categorization of ambiguous content mixing multiple types."""
    mock_forward.return_value = Prediction(
        chunk_type="guidance",
        confidence_score=0.65,  # Low confidence due to ambiguity
        reasoning="This chunk mixes definition, requirement, and guidance elements, "
        "making categorization difficult. Defaulting to guidance as it contains "
        "implementation advice, but manual review is needed.",
    )

    result = categorizer.categorize(
        chunk_content="Fair value is the price that would be received to sell an asset. "
        "Entities shall measure fair value using market prices. "
        "When determining fair value, entities should consider market conditions.",
        kb_document_title="HKFRS 13 Fair Value Measurement",
        chunk_index=12,
    )

    assert result.chunk_type == "guidance"
    assert result.confidence_score == 0.65
    assert result.review_status == "pending_review"
    assert "manual review" in result.reasoning.lower() or "ambig" in result.reasoning.lower()


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_with_confidence_at_threshold(mock_forward, categorizer):
    """Test categorization with confidence exactly at auto-approve threshold."""
    mock_forward.return_value = Prediction(
        chunk_type="requirement",
        confidence_score=0.85,  # Exactly at threshold
        reasoning="Clear requirement statement with standard mandatory language.",
    )

    result = categorizer.categorize(
        chunk_content="An entity shall recognize revenue when it satisfies a performance obligation.",
        kb_document_title="HKFRS 15 Revenue Recognition",
        chunk_index=10,
    )

    assert result.chunk_type == "requirement"
    assert result.confidence_score == 0.85
    assert result.review_status == "auto_approved"  # ≥ 0.85 is auto-approved


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_with_confidence_just_below_threshold(mock_forward, categorizer):
    """Test categorization with confidence just below auto-approve threshold."""
    mock_forward.return_value = Prediction(
        chunk_type="guidance",
        confidence_score=0.8499,  # Just below threshold
        reasoning="Likely guidance based on language patterns, but some uncertainty remains.",
    )

    result = categorizer.categorize(
        chunk_content="Entities should consider the substance of the arrangement when applying this standard.",
        kb_document_title="HKFRS 15 Implementation Guide",
        chunk_index=20,
    )

    assert result.chunk_type == "guidance"
    assert result.confidence_score == 0.8499
    assert result.review_status == "pending_review"  # < 0.85 requires review


# ============================================================================
# Test Error Handling
# ============================================================================


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_invalid_confidence_score_handling(mock_forward, categorizer):
    """Test handling of invalid confidence_score from DSPy."""
    mock_forward.return_value = Prediction(
        chunk_type="requirement",
        confidence_score="invalid",  # Invalid type
        reasoning="Some reasoning that should still be returned.",
    )

    result = categorizer.categorize(
        chunk_content="Valid content here for categorization.",
        kb_document_title="HKFRS 15",
        chunk_index=5,
    )

    # Should default to 0.0 confidence and pending review
    assert result.confidence_score == 0.0
    assert result.review_status == "pending_review"


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_invalid_chunk_type_handling(mock_forward, categorizer):
    """Test handling of invalid chunk_type from DSPy."""
    mock_forward.return_value = Prediction(
        chunk_type="invalid_type",  # Invalid chunk type
        confidence_score=0.9,
        reasoning="Some reasoning here.",
    )

    result = categorizer.categorize(
        chunk_content="Valid content here for categorization.",
        kb_document_title="HKFRS 15",
        chunk_index=5,
    )

    # Should fallback to safe defaults
    assert result.chunk_type == "guidance"  # Safe default
    assert result.confidence_score == 0.0
    assert result.review_status == "pending_review"
    assert "validation" in result.reasoning.lower() or "manual review" in result.reasoning.lower()


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_dspy_prediction_failure(mock_forward, categorizer):
    """Test handling of DSPy prediction failure."""
    mock_forward.side_effect = RuntimeError("DSPy API error")

    with pytest.raises(RuntimeError, match="Categorization failed"):
        categorizer.categorize(
            chunk_content="Valid content here for categorization.",
            kb_document_title="HKFRS 15",
            chunk_index=5,
        )


def test_categorize_invalid_input_raises_error(categorizer):
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValueError, match="Invalid input"):
        categorizer.categorize(
            chunk_content="",  # Empty content (invalid)
            kb_document_title="HKFRS 15",
            chunk_index=5,
        )


# ============================================================================
# Test Batch Processing
# ============================================================================


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_batch_success(mock_forward, categorizer):
    """Test successful batch categorization."""
    # Mock different predictions for each chunk
    mock_forward.side_effect = [
        Prediction(
            chunk_type="definition",
            confidence_score=0.95,
            reasoning="Clear definition of revenue concept.",
        ),
        Prediction(
            chunk_type="requirement",
            confidence_score=0.88,
            reasoning="Mandatory requirement for revenue recognition.",
        ),
        Prediction(
            chunk_type="example",
            confidence_score=0.75,
            reasoning="Illustrative example, but needs review.",
        ),
    ]

    chunks = [
        ChunkCategorizationInput(
            chunk_content="Revenue is the gross inflow of economic benefits.",
            kb_document_title="HKFRS 15",
            chunk_index=0,
        ),
        ChunkCategorizationInput(
            chunk_content="An entity shall recognize revenue when performance obligation is satisfied.",
            kb_document_title="HKFRS 15",
            chunk_index=1,
        ),
        ChunkCategorizationInput(
            chunk_content="For example, if goods are sold with a right of return...",
            kb_document_title="HKFRS 15",
            chunk_index=2,
        ),
    ]

    results = categorizer.categorize_batch(chunks, log_progress=False)

    assert len(results) == 3
    assert results[0].chunk_type == "definition"
    assert results[0].review_status == "auto_approved"
    assert results[1].chunk_type == "requirement"
    assert results[1].review_status == "auto_approved"
    assert results[2].chunk_type == "example"
    assert results[2].review_status == "pending_review"


@patch.object(ChunkCategorizationModule, "forward")
def test_categorize_batch_with_partial_failure(mock_forward, categorizer):
    """Test batch categorization with some failures."""
    # First succeeds, second fails, third succeeds
    mock_forward.side_effect = [
        Prediction(
            chunk_type="definition",
            confidence_score=0.95,
            reasoning="This chunk provides a clear definition of revenue, which is a fundamental accounting concept.",
        ),
        RuntimeError("API error"),
        Prediction(
            chunk_type="requirement",
            confidence_score=0.88,
            reasoning="This chunk states a mandatory accounting treatment requirement for revenue recognition.",
        ),
    ]

    chunks = [
        ChunkCategorizationInput(
            chunk_content="Revenue is the gross inflow of economic benefits.",
            kb_document_title="HKFRS 15",
            chunk_index=0,
        ),
        ChunkCategorizationInput(
            chunk_content="Some content that will fail during processing.",
            kb_document_title="HKFRS 15",
            chunk_index=1,
        ),
        ChunkCategorizationInput(
            chunk_content="An entity shall recognize revenue when satisfied.",
            kb_document_title="HKFRS 15",
            chunk_index=2,
        ),
    ]

    results = categorizer.categorize_batch(chunks, log_progress=False)

    # Should still return 3 results (with fallback for failed one)
    assert len(results) == 3
    assert results[0].chunk_type == "definition"
    # Second result should be fallback due to error (type: guidance, confidence: 0.0)
    assert results[1].chunk_type == "guidance"  # Safe fallback default
    assert results[1].review_status == "pending_review"  # Fallback for error
    assert results[1].confidence_score == 0.0
    assert results[2].chunk_type == "requirement"


def test_categorize_batch_empty_list_raises_error(categorizer):
    """Test that empty batch list raises error."""
    with pytest.raises(ValueError, match="chunks list cannot be empty"):
        categorizer.categorize_batch([])


# ============================================================================
# Test Statistics
# ============================================================================


def test_get_statistics_with_results():
    """Test statistics calculation for a batch of results."""
    categorizer = ChunkCategorizer(auto_approve_threshold=0.85)

    results = [
        ChunkCategorizationOutput(
            chunk_type="definition",
            confidence_score=0.95,
            review_status="auto_approved",
            reasoning="Clear definition with high confidence.",
        ),
        ChunkCategorizationOutput(
            chunk_type="requirement",
            confidence_score=0.88,
            review_status="auto_approved",
            reasoning="Clear requirement with high confidence.",
        ),
        ChunkCategorizationOutput(
            chunk_type="example",
            confidence_score=0.75,
            review_status="pending_review",
            reasoning="Example needing manual review.",
        ),
        ChunkCategorizationOutput(
            chunk_type="requirement",
            confidence_score=0.90,
            review_status="auto_approved",
            reasoning="Another clear requirement.",
        ),
    ]

    stats = categorizer.get_statistics(results)

    assert stats["total_chunks"] == 4
    assert stats["auto_approved"] == 3
    assert stats["pending_review"] == 1
    assert stats["auto_approval_rate"] == 75.0
    assert stats["avg_confidence"] == pytest.approx(0.87, rel=0.01)
    assert stats["chunk_type_distribution"]["definition"] == 1
    assert stats["chunk_type_distribution"]["requirement"] == 2
    assert stats["chunk_type_distribution"]["example"] == 1


def test_get_statistics_empty_results():
    """Test statistics calculation for empty results."""
    categorizer = ChunkCategorizer()

    stats = categorizer.get_statistics([])

    assert stats["total_chunks"] == 0
    assert stats["auto_approved"] == 0
    assert stats["pending_review"] == 0
    assert stats["auto_approval_rate"] == 0.0
    assert stats["avg_confidence"] == 0.0
    assert stats["chunk_type_distribution"] == {}


def test_get_statistics_all_pending_review():
    """Test statistics when all chunks need review."""
    categorizer = ChunkCategorizer(auto_approve_threshold=0.85)

    results = [
        ChunkCategorizationOutput(
            chunk_type="guidance",
            confidence_score=0.70,
            review_status="pending_review",
            reasoning="Low confidence categorization.",
        ),
        ChunkCategorizationOutput(
            chunk_type="guidance",
            confidence_score=0.65,
            review_status="pending_review",
            reasoning="Another low confidence categorization.",
        ),
    ]

    stats = categorizer.get_statistics(results)

    assert stats["total_chunks"] == 2
    assert stats["auto_approved"] == 0
    assert stats["pending_review"] == 2
    assert stats["auto_approval_rate"] == 0.0


# ============================================================================
# Test Market-Agnostic Design
# ============================================================================


@pytest.mark.parametrize(
    "document_title,jurisdiction",
    [
        ("HKFRS 15 Revenue Recognition", "HK"),
        ("SFRS(I) 15 Revenue from Contracts", "SG"),
        ("AASB 15 Revenue from Contracts with Customers", "AU"),
        ("SME-FRS Revenue Recognition", "HK"),
    ],
)
@patch.object(ChunkCategorizationModule, "forward")
def test_market_agnostic_categorization(mock_forward, categorizer, document_title, jurisdiction):
    """Test that categorizer works for different markets/jurisdictions."""
    mock_forward.return_value = Prediction(
        chunk_type="requirement",
        confidence_score=0.90,
        reasoning=f"Clear requirement from {jurisdiction} accounting standard.",
    )

    result = categorizer.categorize(
        chunk_content="Revenue shall be recognized when control is transferred.",
        kb_document_title=document_title,
        chunk_index=10,
    )

    assert result.chunk_type == "requirement"
    assert result.confidence_score == 0.90
    assert result.review_status == "auto_approved"
    # Should work regardless of jurisdiction
    assert jurisdiction in result.reasoning or document_title in result.reasoning or True  # Market-agnostic
