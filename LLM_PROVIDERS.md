# LLM Provider Configuration

The MI Superintendent Updater supports multiple LLM providers for flexible deployment options. You can easily switch between providers using environment variables.

## Supported Providers

### 1. Groq (Default)
Fast, cloud-based LLM API service.

**Pros:**
- Fast inference speed
- Reliable cloud service
- Easy to set up (just API key)

**Cons:**
- Requires API key
- Requires internet connection
- Usage costs (though generous free tier)

### 2. Ollama
Self-hosted LLM inference server.

**Pros:**
- Complete data privacy (runs on your infrastructure)
- No API costs
- Can use custom/local models
- No internet required (after model download)

**Cons:**
- Requires self-hosted Ollama server
- Slower inference (depends on hardware)
- Requires GPU for reasonable performance

## Configuration

All LLM configuration is managed through environment variables in the `.env` file.

### Groq Configuration

```bash
# Set provider to Groq
LLM_PROVIDER=groq

# Groq API settings
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.3
```

**Getting a Groq API Key:**
1. Visit https://console.groq.com
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

### Ollama Configuration

```bash
# Set provider to Ollama
LLM_PROVIDER=ollama

# Ollama server settings
OLLAMA_URL=http://privatechat.setseg.org:11434/api/generate
OLLAMA_MODEL=gpt-oss:120b
OLLAMA_TEMPERATURE=0.3
```

**Setting up Ollama Server:**
1. Install Ollama: https://ollama.ai
2. Pull your desired model: `ollama pull gpt-oss:120b`
3. Start the Ollama server (usually runs on port 11434)
4. Update `OLLAMA_URL` in `.env` to point to your server
5. Set `OLLAMA_MODEL` to the model you pulled

## Switching Providers

To switch between providers, simply change the `LLM_PROVIDER` variable in your `.env` file:

```bash
# Use Groq
LLM_PROVIDER=groq

# Or use Ollama
LLM_PROVIDER=ollama
```

No code changes required - the system automatically routes to the correct provider.

## Testing Your Configuration

Use the included test script to verify your LLM provider is working:

```bash
python test_llm_providers.py
```

This will:
- Show which provider is active
- Test the LLM with sample data
- Confirm the provider is working correctly

Example output:
```
============================================================
LLM Provider Test
============================================================
Active Provider: groq
Groq Model: llama-3.3-70b-versatile

Testing URL filtering with sample data...
------------------------------------------------------------

Success! LLM returned 3 URLs
Selected URLs: ['https://example.com/administration', ...]
Reasoning: The selected URLs are most likely to contain...

============================================================
SUCCESS: GROQ provider is working correctly!
============================================================
```

## Model Selection

### Recommended Groq Models
- `llama-3.3-70b-versatile` (default) - Best balance of speed and quality
- `llama-3.1-70b-versatile` - Alternative if 3.3 is unavailable
- `mixtral-8x7b-32768` - Good for longer contexts

### Recommended Ollama Models
- `llama3.1:70b` - High quality, requires ~40GB RAM
- `llama3.1:8b` - Faster, requires ~8GB RAM
- `gpt-oss:120b` - Very high quality (if available), requires significant resources
- `mistral` - Good balance of speed and quality

## Temperature Settings

The `TEMPERATURE` parameter controls randomness:
- `0.0` - Deterministic (same input = same output)
- `0.3` (default) - Low randomness, consistent results
- `0.7` - Moderate creativity
- `1.0` - High creativity, more variation

For data extraction tasks, we recommend keeping temperature low (0.1-0.3) for consistency.

## Architecture Notes

### Implementation Details

The LLM abstraction layer is implemented in `utils/llm_client.py`:

- **Single Client Interface**: All code uses `get_client().call()` regardless of provider
- **Template System**: Prompts are stored in `prompts/*.txt` files (provider-agnostic)
- **Pydantic Validation**: All LLM responses are validated against Pydantic models
- **Automatic Retry**: Built-in retry logic with exponential backoff
- **Provider Routing**: `LLMClient` automatically routes to the correct provider based on `LLM_PROVIDER`

### Adding New Providers

To add support for a new LLM provider:

1. Add configuration to `config.py`:
   ```python
   NEW_PROVIDER_URL = os.getenv('NEW_PROVIDER_URL')
   NEW_PROVIDER_MODEL = os.getenv('NEW_PROVIDER_MODEL')
   ```

2. Add a `_call_new_provider()` method to `utils/llm_client.py`:
   ```python
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
   def _call_new_provider(self, system_prompt: str, user_prompt: str) -> dict:
       # Implementation here
       pass
   ```

3. Update `__init__()` to initialize the new provider

4. Update `_call_api()` to route to the new provider

5. Update `.env.example` with new configuration options

## Troubleshooting

### Groq Issues

**"GROQ_API_KEY not set"**
- Ensure your `.env` file has `GROQ_API_KEY=your_key_here`
- Verify the file is in the project root directory

**"Rate limit exceeded"**
- You've hit Groq's rate limits
- Wait a few minutes and try again
- Consider upgrading your Groq plan

### Ollama Issues

**"Connection refused"**
- Ensure Ollama server is running: `ollama serve`
- Verify the URL in `OLLAMA_URL` is correct
- Check firewall settings if using remote server

**"Model not found"**
- Pull the model: `ollama pull gpt-oss:120b`
- Verify model name matches exactly in `OLLAMA_MODEL`

**Slow performance**
- Ollama requires significant compute resources
- Use a smaller model (e.g., `llama3.1:8b`)
- Ensure you have a GPU for faster inference

### General Issues

**"Unsupported LLM provider"**
- Check `LLM_PROVIDER` is set to either `groq` or `ollama`
- Verify no typos in the provider name

**Validation errors**
- The LLM returned unexpected JSON structure
- Try a different model or adjust temperature
- Check prompt templates in `prompts/*.txt`

## Performance Comparison

Based on typical usage:

| Provider | Speed | Cost | Privacy | Setup Difficulty |
|----------|-------|------|---------|------------------|
| Groq     | ⚡⚡⚡  | 💰   | ⚠️      | Easy            |
| Ollama   | ⚡     | Free | ✅      | Moderate        |

**Recommendations:**
- **Development**: Use Groq for fast iteration
- **Production (privacy-sensitive)**: Use Ollama on your infrastructure
- **Production (cost-conscious)**: Use Groq with rate limiting
- **High-volume**: Use Ollama to avoid API costs
