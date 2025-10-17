"""Test Gemini embedding dimensions."""

import google.generativeai as genai
from genreport.core.utils.config import settings

# Configure Gemini
genai.configure(api_key=settings.google_api_key)

print("Testing Gemini Embedding Dimensions\n" + "=" * 60)

# Test different model names
models_to_test = [
    "models/text-embedding-004",
    "models/embedding-001",
    "gemini-embedding-001",
]

test_text = "Revenue recognition test"

for model_name in models_to_test:
    print(f"\n📝 Testing model: {model_name}")

    try:
        # Test without output_dimensionality (default)
        result_default = genai.embed_content(
            model=model_name,
            content=test_text,
            task_type="RETRIEVAL_DOCUMENT",
        )
        print(f"   Default dimensions: {len(result_default['embedding'])}")

        # Test with 1536 dimensions
        result_1536 = genai.embed_content(
            model=model_name,
            content=test_text,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=1536,
        )
        print(f"   With output_dimensionality=1536: {len(result_1536['embedding'])}")

        # Test with 3072 dimensions
        result_3072 = genai.embed_content(
            model=model_name,
            content=test_text,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=3072,
        )
        print(f"   With output_dimensionality=3072: {len(result_3072['embedding'])}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Checking available models...")

try:
    # List available models
    for model in genai.list_models():
        if 'embed' in model.name.lower():
            print(f"\n📌 {model.name}")
            print(f"   Display name: {model.display_name}")
            print(f"   Description: {model.description}")
            if hasattr(model, 'supported_generation_methods'):
                print(f"   Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
