# Explore Commands Reference

**Version**: 1.0
**Last Updated**: 2026-02-09

Quick reference for all `/explore` command variants and their usage.

---

## Overview

The explore feature provides natural language to SQL generation with two execution modes:

- **Local Mode**: Uses Ollama (free, fast, offline-capable)
- **API Mode**: Uses cloud providers (Gemini/Claude/OpenAI) for higher accuracy

---

## Command Structure

All explore commands follow this pattern:

```
/explore[:mode][:provider]
```

### Basic Syntax

| Command | Mode | Provider | Auto-select |
|---------|------|----------|-------------|
| `/explore` | Default (config) | Default (config) | Yes |
| `/explore:local` | Local | N/A | Uses Ollama |
| `/explore:api` | API | Auto (Gemini→Claude→OpenAI) | Yes |
| `/explore:api:gemini` | API | Gemini | Explicit |
| `/explore:api:claude` | API | Claude | Explicit |
| `/explore:api:openai` | API | OpenAI | Explicit |

---

## Commands

### `/explore`

Use the default mode configured in settings.

#### Syntax
```bash
/explore
```

#### Behavior
- Reads `default_mode` from configuration
- Reads `default_api_provider` if in API mode
- Launches the database explorer screen
- Maintains current mode and provider

#### Example
```bash
# If config has: default_mode: "local"
/explore
→ Launches with Local mode (Ollama)

# If config has: default_mode: "api"
/explore
→ Launches with API mode (Gemini)
```

#### Configuration
```yaml
# backend/config/explorer_config.yaml
text2sql:
  default_mode: "local"        # or "api"
  default_api_provider: "gemini"  # or "claude", "openai"
```

#### Related
- Modify default: Run `/login` to reconfigure
- Switch mode: Use `Alt+M` after launching

---

### `/explore:local`

Force Local mode with Ollama (free, offline-capable).

#### Syntax
```bash
/explore:local
```

#### Requirements
1. Ollama installed (https://ollama.com)
2. Model downloaded: `ollama pull qwen2.5-coder:7b`
3. Server running: `ollama serve` in another terminal

#### Behavior
- Launches database explorer with Local mode
- Ignores default provider setting
- Uses `qwen2.5-coder:7b` by default (configurable)
- Generates SQL in 1-3 seconds

#### Example
```bash
# Terminal 1: Start Ollama server
ollama serve

# Terminal 2: Start BI-Agent
bi-agent
/explore:local
```

#### Performance Tips
- Response time: 1-3 seconds (typical)
- RAM needed: 8GB minimum, 16GB recommended
- GPU acceleration: Set `OLLAMA_NUM_GPU=1` for faster responses
- Large schemas: Reduce schema info to relevant tables only

#### Related
- Setup: See [Setup Guide - Local Mode](./EXPLORE_FEATURE_GUIDE.md#local-mode-ollama)
- Troubleshooting: [Local mode issues](./EXPLORE_FEATURE_GUIDE.md#issue-1-ollama-server-not-responding)

---

### `/explore:api`

Use API mode with automatic provider selection.

#### Syntax
```bash
/explore:api
```

#### Automatic Selection Order
1. **Gemini** - If API key configured
2. **Claude** - If Gemini not available
3. **OpenAI** - If Claude not available
4. **Fallback** - If none configured, shows error with setup instructions

#### Behavior
- Launches database explorer with API mode
- Queries cloud providers for higher accuracy (95%+)
- Requires internet connection
- Response time: 3-10 seconds

#### Prerequisites
Configure at least one API key via `/login`:

```bash
/login
→ Follow prompts to enter:
  - Gemini API key
  - Claude API key
  - OpenAI API key
```

#### Cost
- **Gemini**: Free tier available, then $0.075-0.15 per 1M input tokens
- **Claude**: $3-15 per 1M input tokens (varies by model)
- **OpenAI**: $0.03-0.15 per 1K input tokens

#### Example
```bash
/explore:api
→ Detects available keys
→ Uses Gemini (highest priority)
→ If Gemini key missing, tries Claude
→ If both missing, tries OpenAI
```

#### Related
- Setup: See [Setup Guide - API Mode](./EXPLORE_FEATURE_GUIDE.md#api-mode-cloud-models)
- Troubleshooting: [API key issues](./EXPLORE_FEATURE_GUIDE.md#issue-2-api-key-invalid)

---

### `/explore:api:gemini`

Explicitly use Google Gemini API.

#### Syntax
```bash
/explore:api:gemini
```

#### Requirements
- Gemini API key configured (via `/login`)
- Internet connection
- Optional: Free tier account at https://ai.google.dev

#### Model Used
- Default: `gemini-2.0-flash-exp`
- Temperature: 0.3
- Max tokens: 2048

#### Strengths
- Fast responses (3-5 seconds)
- Free tier with good quota
- Excellent for balanced accuracy/cost
- Handles complex SQL well

#### Cost
- **Free tier**: 60 requests per minute
- **Paid**: $0.075 per 1M input tokens, $0.3 per 1M output tokens

#### Example
```bash
# Setup once
/login
→ Enter Gemini API key

# Use anytime
/explore:api:gemini
→ Natural language input
→ Generates SQL with Gemini
```

#### Related
- Get API key: https://ai.google.dev
- Pricing: https://ai.google.dev/pricing
- Troubleshooting: [API key invalid](./EXPLORE_FEATURE_GUIDE.md#issue-2-api-key-invalid)

---

### `/explore:api:claude`

Explicitly use Anthropic Claude API.

#### Syntax
```bash
/explore:api:claude
```

#### Requirements
- Claude API key configured (via `/login`)
- Internet connection
- Account at https://console.anthropic.com

#### Model Used
- Default: `claude-3-5-sonnet-20241022`
- Temperature: 0.3
- Max tokens: 2048

#### Strengths
- Highest accuracy (95-98%)
- Excellent reasoning for complex queries
- Best for production SQL generation
- Superior handling of CTE and window functions

#### Cost
- **Input**: $3 per 1M tokens
- **Output**: $15 per 1M tokens

#### Example
```bash
# Setup once
/login
→ Enter Claude API key

# Use for critical queries
/explore:api:claude
→ Complex natural language input
→ Generates highly accurate SQL
```

#### Related
- Get API key: https://console.anthropic.com/api/keys
- Pricing: https://www.anthropic.com/pricing
- Models: https://docs.anthropic.com/en/docs/about/models/latest

---

### `/explore:api:openai`

Explicitly use OpenAI GPT API.

#### Syntax
```bash
/explore:api:openai
```

#### Requirements
- OpenAI API key configured (via `/login`)
- Internet connection with active API credits
- Account at https://platform.openai.com

#### Model Used
- Default: `gpt-4o`
- Temperature: 0.3
- Max tokens: 2048

#### Strengths
- Industry standard model
- Very good accuracy (90-95%)
- Reliable and well-tested
- Good documentation and community

#### Cost
- **Input**: $0.03 per 1K tokens
- **Output**: $0.15 per 1K tokens
- Note: Can be expensive for large schemas

#### Example
```bash
# Setup once
/login
→ Enter OpenAI API key

# Use when others unavailable
/explore:api:openai
→ Natural language input
→ Generates SQL with GPT-4o
```

#### Related
- Get API key: https://platform.openai.com/api-keys
- Pricing: https://openai.com/pricing
- Models: https://platform.openai.com/docs/models

---

## Mode Switching at Runtime

### Alt+M: Toggle Mode

While using the explore feature, press `Alt+M` to switch between Local and API modes instantly.

#### Before
```
[Mode: 🏠 Local (Qwen-7B)]  Press Alt+M to toggle
```

#### After (pressing Alt+M)
```
[Mode: ☁️ API (Gemini)]  Press Alt+M to toggle
```

#### Behavior
- Current input is preserved
- Query results are cleared
- Mode indicator updates
- Notification shows new mode

#### Example Workflow
```
1. /explore:local
   → Running fast local queries

2. Alt+M
   → Switched to API mode (Gemini)

3. Complex query needs higher accuracy
   → Generates with Gemini

4. Alt+M
   → Back to Local mode for quick checks
```

---

## Command Parsing

### How Commands are Parsed

The command parser follows this logic:

```
Input: /explore[:mode][:provider]
       ↓
Parse mode part
  ├─ if "local" → mode = "local"
  ├─ if "api" → mode = "api"
  └─ if empty → mode = config.default_mode
       ↓
Parse provider part (only if mode = "api")
  ├─ if "gemini" → provider = "gemini"
  ├─ if "claude" → provider = "claude"
  ├─ if "openai" → provider = "openai"
  └─ if empty → provider = config.default_api_provider or auto-select
```

### Examples

| Input | Parsed Mode | Parsed Provider | Result |
|-------|------------|-----------------|--------|
| `/explore` | config default | config default | Uses config |
| `/explore:local` | local | N/A | Ollama |
| `/explore:api` | api | auto-select | Gemini (if key exists) |
| `/explore:api:gemini` | api | gemini | Gemini |
| `/explore:api:claude` | api | claude | Claude |
| `/explore:api:openai` | api | openai | OpenAI |

---

## Configuration

### Default Configuration File

```yaml
# backend/config/explorer_config.yaml
text2sql:
  default_mode: "local"              # Default command mode
  default_api_provider: "gemini"     # Default API provider

  local:
    ollama_host: "http://localhost:11434"
    model: "qwen2.5-coder:7b"
    timeout: 30
    temperature: 0.1
    num_ctx: 4096

  api:
    gemini:
      model: "gemini-2.0-flash-exp"
      temperature: 0.3
      max_tokens: 2048
    claude:
      model: "claude-3-5-sonnet-20241022"
      temperature: 0.3
      max_tokens: 2048
    openai:
      model: "gpt-4o"
      temperature: 0.3
      max_tokens: 2048
```

### Modify Defaults

Use `/login` to update API keys and preferences:

```bash
/login
→ Select: Update API keys
→ Enter Gemini key, Claude key, OpenAI key
→ Set default mode: local or api
→ Set default provider: gemini, claude, or openai
```

---

## Keyboard Shortcuts

### While Using Explore

| Key | Action |
|-----|--------|
| `Alt+M` | Toggle between Local ⟷ API mode |
| `Ctrl+R` | Run current SQL query |
| `Ctrl+A` | AI Assistant - explain/optimize query |
| `Tab` | Auto-complete table/column names |
| `Escape` | Close modal or exit explore |

---

## Error Messages

### Common Errors and Solutions

#### "Ollama server not responding"
```
Command: /explore:local
Error: ConnectionError: Failed to connect to localhost:11434
Solution:
1. Check Ollama is running: curl http://localhost:11434/api/tags
2. If not, start it: ollama serve
3. Verify model: ollama list
```

#### "API Key Invalid"
```
Command: /explore:api:gemini
Error: APIError: Invalid API key
Solution:
1. Reconfigure: /login
2. Verify key at https://ai.google.dev
3. Ensure key starts with "AIza..." (Gemini format)
```

#### "Model not found"
```
Command: /explore:local
Error: ResponseError: model not found
Solution:
1. Download model: ollama pull qwen2.5-coder:7b
2. Verify: ollama list
3. Restart: ollama serve
```

#### "API rate limit exceeded"
```
Command: /explore:api:openai
Error: RateLimitError: Too many requests
Solution:
1. Wait 60 seconds before retrying
2. Switch to Gemini: /explore:api:gemini
3. Check billing at https://platform.openai.com/account/billing
```

---

## FAQ

**Q: What's the difference between modes?**
A: Local mode is free and offline, but less accurate. API mode is cloud-based and more accurate but costs money and requires internet.

**Q: Can I use both modes?**
A: Yes! Use `/explore:local` for quick checks and `/explore:api` for complex analysis. Switch with `Alt+M`.

**Q: How do I change the default mode?**
A: Run `/login` and select your preferences, or edit `backend/config/explorer_config.yaml`.

**Q: Which API provider should I choose?**
A: Gemini is best for free tier, Claude for accuracy, OpenAI for reliability.

**Q: Does my data leave my computer?**
A: In Local mode: No. In API mode: Only the schema, not your actual data.

---

## Related Documentation

- [Full User Guide](./EXPLORE_FEATURE_GUIDE.md)
- [Setup Instructions](./EXPLORE_FEATURE_GUIDE.md#setup-instructions)
- [Troubleshooting](./EXPLORE_FEATURE_GUIDE.md#troubleshooting)
- [FAQ](./EXPLORE_FEATURE_GUIDE.md#faq)

---

**Last Updated**: February 9, 2026
**Author**: BI-Agent Documentation Team

Copyright © 2026 BI-Agent. All rights reserved.
