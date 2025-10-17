# LLM Configuration Guide
**Date**: 2025-10-17
**Topic**: Configuring LLM Providers (Gemini & OpenAI)

---

## Overview

GenReport supports multiple LLM providers with **Google Gemini 2.5 Flash** as the default provider. The system is designed to support provider switching and fallback strategies.

---

## Default Configuration

### Google Gemini (Default)

Gemini 2.5 Flash is the default LLM provider for GenReport:

**Benefits**:
- Fast inference speed (optimized for latency)
- Large context window (up to 1M tokens)
- Cost-effective for production workloads
- Strong performance on RAG tasks
- Native multimodal support

**Configuration** (`.env`):
```bash
DEFAULT_LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_TOKENS=8192
GEMINI_TEMPERATURE=0.1
```

**Get API Key**:
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy to `GOOGLE_API_KEY` in `.env`

### OpenAI (Optional Alternative)

OpenAI models are supported as an alternative provider:

**Configuration** (`.env`):
```bash
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4096
OPENAI_TEMPERATURE=0.1
```

---

## Provider Selection

### Using Settings Object

The `Settings` class provides convenient properties for accessing the current provider's configuration:

```python
from genreport.core.utils.config import settings

# Get configuration for default provider
api_key = settings.llm_api_key          # Returns google_api_key or openai_api_key
model = settings.llm_model              # Returns gemini_model or openai_model
max_tokens = settings.llm_max_tokens    # Returns provider-specific max tokens
temperature = settings.llm_temperature  # Returns provider-specific temperature

# Or access provider-specific settings directly
google_key = settings.google_api_key
gemini_model = settings.gemini_model

openai_key = settings.openai_api_key
openai_model = settings.openai_model
```

### Switching Providers

To switch between providers, update `DEFAULT_LLM_PROVIDER` in `.env`:

```bash
# Use Gemini
DEFAULT_LLM_PROVIDER=gemini

# Use OpenAI
DEFAULT_LLM_PROVIDER=openai
```

---

## LLM Client Implementation (Sprint 2)

### Basic Client Structure

```python
# genreport/core/llm/client.py
from genreport.core.utils.config import settings
from typing import Optional

class LLMClient:
    """Base LLM client with provider abstraction."""

    def __init__(self, provider: Optional[str] = None):
        """Initialize LLM client.

        Args:
            provider: Provider name ('gemini' or 'openai').
                     Defaults to settings.default_llm_provider.
        """
        self.provider = provider or settings.default_llm_provider

        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "openai":
            self._init_openai()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_gemini(self):
        """Initialize Gemini client."""
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        self.client = genai.GenerativeModel(settings.gemini_model)
        self.max_tokens = settings.gemini_max_tokens
        self.temperature = settings.gemini_temperature

    def _init_openai(self):
        """Initialize OpenAI client."""
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate completion from prompt.

        Args:
            prompt: Input prompt
            **kwargs: Provider-specific parameters

        Returns:
            Generated text
        """
        if self.provider == "gemini":
            return self._generate_gemini(prompt, **kwargs)
        elif self.provider == "openai":
            return self._generate_openai(prompt, **kwargs)

    def _generate_gemini(self, prompt: str, **kwargs) -> str:
        """Generate using Gemini."""
        response = self.client.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }
        )
        return response.text

    def _generate_openai(self, prompt: str, **kwargs) -> str:
        """Generate using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
        )
        return response.choices[0].message.content
```

### Usage Example

```python
from genreport.core.llm.client import LLMClient

# Use default provider (Gemini)
client = LLMClient()
response = client.generate("Analyze this financial statement...")

# Explicitly use OpenAI
openai_client = LLMClient(provider="openai")
response = openai_client.generate("Analyze this financial statement...")
```

---

## Model Comparison

### Gemini 2.5 Flash vs GPT-4o Mini

| Feature | Gemini 2.5 Flash | GPT-4o Mini |
|---------|-----------------|-------------|
| **Context Window** | 1M tokens | 128K tokens |
| **Speed** | Very Fast | Fast |
| **Cost** | Low | Medium |
| **Best For** | RAG, long documents | General purpose |
| **Multimodal** | Yes (native) | Yes |
| **Structured Output** | Yes | Yes |

### When to Use Each

**Use Gemini 2.5 Flash for**:
- Processing large documents (trial balances, financial statements)
- RAG with extensive context
- Cost-sensitive production workloads
- Fast inference requirements

**Use GPT-4o Mini for**:
- Tasks requiring OpenAI ecosystem tools
- When Gemini quota is exhausted
- Specific model features not available in Gemini

---

## Rate Limits & Quotas

### Google Gemini

- **Free Tier**: 15 requests/minute, 1M tokens/day
- **Paid Tier**: 360 requests/minute, higher token limits
- See [pricing](https://ai.google.dev/pricing)

### OpenAI

- **Tier 1**: 500 RPM, 200K TPM
- **Tier 2-5**: Higher limits based on usage
- See [rate limits](https://platform.openai.com/docs/guides/rate-limits)

---

## Cost Optimization

### Token Usage

Monitor token usage with Langfuse:

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
)

# Track generation
trace = langfuse.trace(name="audit_report_generation")
generation = trace.generation(
    name="analyze_trial_balance",
    model=settings.llm_model,
    input=prompt,
    output=response,
)
```

### Best Practices

1. **Use appropriate max_tokens**
   - Gemini: 8192 tokens (default)
   - OpenAI: 4096 tokens (default)
   - Adjust based on use case

2. **Lower temperature for deterministic tasks**
   - Financial analysis: 0.1
   - Creative writing: 0.7-0.9

3. **Implement caching** (Sprint 3)
   - Cache similar prompts
   - Use Redis for response caching
   - Avoid redundant API calls

4. **Batch processing** (Sprint 4)
   - Group similar requests
   - Process in parallel where possible

---

## Security Considerations

### API Key Management

1. **Never commit keys to version control**
   ```bash
   # Add to .gitignore
   .env
   .env.local
   ```

2. **Use different keys per environment**
   - Development: Test keys with lower rate limits
   - Staging: Separate keys for testing
   - Production: Production keys in AWS Secrets Manager

3. **Rotate keys regularly**
   - Production: Every 90 days
   - Development: As needed

### Audit Logging

All LLM API calls should be logged:

```python
AuditLogger.log_event(
    db=db,
    event_type="LLM_API_CALL",
    action="GENERATE",
    user_id=user.id,
    tenant_id=tenant_id,
    details={
        "provider": settings.default_llm_provider,
        "model": settings.llm_model,
        "prompt_tokens": len(prompt.split()),
        "completion_tokens": len(response.split()),
    },
)
```

---

## Troubleshooting

### Common Issues

**1. "Invalid API Key"**
- Check key is correctly set in `.env`
- Verify key has not expired
- Ensure no extra spaces or quotes

**2. "Rate Limit Exceeded"**
- Implement exponential backoff
- Use Redis-based rate limiting
- Consider upgrading tier

**3. "Context Length Exceeded"**
- Reduce prompt size
- Implement chunking strategy
- Use summarization for long documents

### Debug Mode

Enable debug logging:

```bash
# .env
LOG_LEVEL=DEBUG
```

View LLM API calls:

```python
import logging

logging.getLogger("genreport.core.llm").setLevel(logging.DEBUG)
```

---

## Next Steps

1. **Sprint 2**: Implement `LLMClient` base class
2. **Sprint 3**: Add Langfuse integration for observability
3. **Sprint 4**: Implement DSPy agents with LLM client
4. **Sprint 5**: Add caching and cost optimization

---

**References**:
- [Google Gemini API Docs](https://ai.google.dev/docs)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Langfuse Docs](https://langfuse.com/docs)
