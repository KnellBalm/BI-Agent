# Explore Feature User Guide

**Version**: 1.0
**Last Updated**: 2026-02-09
**Language**: English (한국어 버전은 별도 문서 참고)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Mode Comparison](#mode-comparison)
3. [Setup Instructions](#setup-instructions)
4. [Usage Examples](#usage-examples)
5. [Keyboard Shortcuts](#keyboard-shortcuts)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Quick Start

### Command Structure

The `/explore` command supports multiple modes for different situations:

```bash
/explore              # Use default mode (configured in settings)
/explore:local        # Force Local AI mode (Ollama)
/explore:api          # Force Cloud API mode (auto-selects Gemini/Claude/OpenAI)
/explore:api:gemini   # Explicitly use Gemini
/explore:api:claude   # Explicitly use Claude
/explore:api:openai   # Explicitly use OpenAI
```

### Basic Workflow

1. **Launch explore**: Type `/explore` or `/explore:local` in the console
2. **Enter your question**: Write your question in natural language (English or Korean)
3. **Review the SQL**: The AI generates SQL with helpful comments
4. **Execute**: Press `Ctrl+R` to run the query
5. **View results**: Results display in the data grid below

---

## Mode Comparison

Choose the mode that best fits your situation:

| Feature | Local Mode | API Mode |
|---------|-----------|----------|
| **Speed** | ⚡ Very fast (1-3 sec) | 🐌 Slower (3-10 sec) |
| **Cost** | 💰 Free | 💸 Requires API credits |
| **Accuracy** | ⭐⭐⭐ 80-85% | ⭐⭐⭐⭐⭐ 95%+ |
| **Offline capable** | ✅ Yes | ❌ No (requires internet) |
| **Complex queries** | ⚠️ Limited | ✅ Strong |
| **Hardware needed** | 8GB+ RAM, CPU/GPU | Not needed |
| **Recommended for** | Quick prototyping, simple SELECT | Production, complex JOIN/CTE |

### Recommended Workflows

**Daily Analysis (Local Mode)**:
- Quick data verification
- Simple aggregate queries
- Rapid prototyping
- Offline work

**Important Reports (API Mode)**:
- Monthly/quarterly reports
- Complex business logic
- Production queries
- Highest accuracy needed

**Hybrid Approach (Mode Switching)**:
- Start with Local for speed
- Switch to API when needed for accuracy
- Use `Alt+M` to toggle between modes

---

## Setup Instructions

### Local Mode (Ollama)

Local mode uses Ollama, a free, open-source tool that runs AI models on your computer.

#### Step 1: Install Ollama

**macOS/Linux**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows**:
- Visit https://ollama.com/download
- Download and run the installer

**Docker**:
```bash
docker pull ollama/ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 ollama/ollama
```

#### Step 2: Download the Model

After installing Ollama, download the Qwen-2.5-Coder model (about 4.7GB, one-time only):

```bash
ollama pull qwen2.5-coder:7b
```

Alternative models (choose based on your hardware):
- `qwen2.5-coder:7b` (recommended, smaller)
- `qwen2.5-coder:14b` (more accurate, requires more RAM)
- `deepseek-r1:7b` (alternative)

#### Step 3: Start Ollama Server

Open a terminal and keep it running:

```bash
ollama serve
```

You should see output like:
```
2026-02-09 10:30:00.000 [INFO] Listening on 127.0.0.1:11434
```

#### Step 4: Verify Installation

In another terminal, test the connection:

```bash
curl http://localhost:11434/api/tags
```

You should see your downloaded models listed in the response.

#### Hardware Requirements

- **Minimum**: 8GB RAM total system memory
- **Recommended**: 16GB+ RAM, GPU acceleration (NVIDIA/AMD)
- **CPU**: 4+ cores recommended

#### Performance Optimization

If responses are slow, try these optimizations:

```bash
# Use GPU acceleration (NVIDIA)
OLLAMA_NUM_GPU=1 ollama serve

# Adjust CPU threads (default: all cores)
OLLAMA_NUM_THREADS=4 ollama serve

# Increase context window for larger schemas
OLLAMA_NUM_CTX=4096 ollama serve
```

### API Mode (Cloud Models)

API mode uses cloud-hosted models for maximum accuracy.

#### Step 1: Set Up API Keys

Use the `/login` command to configure your API keys:

```bash
/login
```

Follow the prompts to enter your API keys for:
- **Gemini**: Get free credits at https://ai.google.dev
- **Claude**: Get API key at https://console.anthropic.com
- **OpenAI**: Get API key at https://platform.openai.com/api-keys

#### Step 2: Configure Default Provider

Edit the config file or set via `/login`:

```yaml
# backend/config/explorer_config.yaml (optional)
text2sql:
  default_mode: "api"
  default_api_provider: "gemini"  # or "claude", "openai"
```

#### Step 3: Verify Connection

Try a simple query:
```bash
/explore:api:gemini
```

If it works, you're ready to use API mode.

---

## Usage Examples

### Example 1: Simple Query (Local Mode)

**Situation**: You want a quick answer during daily work

```
Command: /explore:local
Input:   "Show me new user signups this week"
Output:  (1-3 seconds)
         SELECT COUNT(*) as new_users
         FROM users
         WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)

         -- Notes:
         -- 1. Ensure created_at is a TIMESTAMP type
         -- 2. If performance is slow, add an index: CREATE INDEX idx_created_at ON users(created_at)
```

### Example 2: Complex Analysis (API Mode)

**Situation**: Creating a production monthly report with complex calculations

```
Command: /explore:api:claude
Input:   "Calculate month-over-month revenue growth by product category
          for the last 3 months with year-over-year comparison"

Output:  (5-8 seconds, more detailed and accurate)
         WITH current_period AS (
           SELECT
             DATE_TRUNC('month', sale_date) as month,
             category,
             SUM(amount) as revenue
           FROM sales
           WHERE sale_date >= CURRENT_DATE - INTERVAL '3 months'
           GROUP BY month, category
         ),
         previous_period AS (
           SELECT
             DATE_TRUNC('month', sale_date) + INTERVAL '12 months' as month,
             category,
             SUM(amount) as previous_revenue
           FROM sales
           WHERE sale_date >= CURRENT_DATE - INTERVAL '15 months'
             AND sale_date < CURRENT_DATE - INTERVAL '12 months'
           GROUP BY month, category
         )
         SELECT
           c.month,
           c.category,
           c.revenue as current_revenue,
           p.previous_revenue,
           ROUND(((c.revenue - p.previous_revenue) / p.previous_revenue * 100), 2) as growth_pct
         FROM current_period c
         LEFT JOIN previous_period p
           ON c.month = p.month AND c.category = p.category
         ORDER BY c.month DESC, c.category;

         -- Performance tips:
         -- 1. Add index: CREATE INDEX idx_sale_date_category ON sales(sale_date, category)
         -- 2. For 1M+ rows, consider table partitioning
```

### Example 3: Mode Switching During Work

**Situation**: Starting with local mode, then switching when analysis becomes complex

```
Step 1: /explore:local
        "Top 5 products by revenue this month"
        → Gets results in 2 seconds ✓

Step 2: Query execution works well, but you need something more complex
        Press Alt+M to switch to API mode

Step 3: "Show correlation between product price and sales volume"
        → Generates more accurate CTE-based query (5 seconds)

Step 4: After complex query is saved, press Alt+M again
        → Back to Local mode for quick daily checks
```

### Example 4: Natural Language in English

```
Command: /explore:api
Input:   "What are the top 10 customers by total purchase amount
          in the last year?"

Output:  SELECT
           customer_id,
           customer_name,
           SUM(amount) as total_purchases,
           COUNT(*) as transaction_count
         FROM orders
         WHERE order_date >= CURRENT_DATE - INTERVAL '1 year'
         GROUP BY customer_id, customer_name
         ORDER BY total_purchases DESC
         LIMIT 10;
```

### Example 5: Natural Language in Korean

```
Command: /explore
Input:   "지난 분기 카테고리별 매출 현황을 보여줘"
         (Show last quarter's revenue by category)

Output:  SELECT
           category,
           SUM(amount) as total_revenue,
           COUNT(*) as num_transactions,
           AVG(amount) as avg_transaction
         FROM sales
         WHERE sale_date >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '1 quarter')
           AND sale_date < DATE_TRUNC('quarter', CURRENT_DATE)
         GROUP BY category
         ORDER BY total_revenue DESC;
```

---

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `Alt+M` | Toggle between Local ⟷ API mode |
| `Alt+N` | Switch to Natural Language input mode |
| `Tab` | Auto-complete commands and table names |
| `Esc` | Close modal or return to main screen |

### Editing

| Key | Action |
|-----|--------|
| `Ctrl+R` | Run current query |
| `Ctrl+A` | AI Assistant - explain/optimize current query |
| `Ctrl+Z` | Undo last change |
| `Ctrl+Y` | Redo |

### Query Management (Phase 2)

| Key | Action |
|-----|--------|
| `F4` | Toggle Query History panel |
| `Ctrl+B` | Bookmark current query |
| `/` | Command palette (search commands) |

---

## Troubleshooting

### Issue 1: "Ollama server not responding"

**Symptom**: You see an error like `ConnectionError: Failed to connect to localhost:11434`

**Solution**:
```bash
# 1. Check if Ollama is running
curl http://localhost:11434/api/tags

# 2. If not running, start it
ollama serve

# 3. Check which models are installed
ollama list

# 4. If qwen2.5-coder:7b is missing, download it
ollama pull qwen2.5-coder:7b
```

### Issue 2: "API Key Invalid"

**Symptom**: Error when using `/explore:api`

**Solution**:
```bash
# 1. Re-enter your API key
/login

# 2. Verify the key is correct:
#    - Gemini: https://ai.google.dev/
#    - Claude: https://console.anthropic.com/
#    - OpenAI: https://platform.openai.com/api-keys

# 3. Try a simple query to test
/explore:api:gemini
```

### Issue 3: Generated SQL Has Wrong Syntax

**Symptom**: SQL has errors or doesn't match your database dialect

**Solution**:
1. Manually edit the SQL before executing
2. Try switching modes (`Alt+M`) to use a different AI model
3. Include the database type in your question: "For PostgreSQL, show..."
4. Report the issue if it persists

### Issue 4: Slow Responses in Local Mode

**Symptom**: Queries take >10 seconds to generate

**Solutions**:
1. **Reduce schema size**: Local models struggle with large schemas. Simplify your schema info.
2. **Use API mode instead**: `Alt+M` to switch to API mode
3. **Reduce context window**:
   ```bash
   OLLAMA_NUM_CTX=2048 ollama serve  # Smaller context
   ```
4. **Check system resources**:
   - Close other applications
   - Check CPU/memory usage
   - Increase `OLLAMA_NUM_THREADS` if CPU usage is low

### Issue 5: Korean Text Shows as Garbage Characters

**Symptom**: Korean comments appear as `?` or mojibake

**Solution**:
```bash
# Ensure UTF-8 encoding is used
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Then restart Ollama
ollama serve
```

### Issue 6: Out of Memory (OOM) Error

**Symptom**: System crashes or freezes when using Local mode

**Solution**:
1. **Reduce model size**:
   ```bash
   ollama pull qwen2.5-coder:7b  # Smaller than 14b
   ```
2. **Reduce context window**:
   ```bash
   OLLAMA_NUM_CTX=2048 ollama serve
   ```
3. **Allocate more GPU memory** (if available):
   ```bash
   OLLAMA_NUM_GPU=1 ollama serve
   ```
4. **Switch to API mode** (`Alt+M`)

---

## FAQ

### General

**Q: Should I use Local or API mode?**

A:
- **Local (Ollama)** if you need speed and don't want to spend money
- **API** if you need high accuracy and complex queries
- **Both** by switching with `Alt+M` based on your current task

**Q: Can I use explore offline?**

A: Yes, Local mode (Ollama) works completely offline. API mode requires internet.

**Q: Does my data leave my computer?**

A:
- **Local mode**: No, stays on your computer
- **API mode**: Query schema goes to the cloud API, but not your actual data

**Q: How much does API mode cost?**

A: Depends on the provider:
- **Gemini**: Free tier available, then pay per token
- **Claude**: Fixed pricing, check https://www.anthropic.com/pricing
- **OpenAI**: Pay per token, check https://openai.com/pricing

**Q: Can I bookmark/save favorite queries?**

A: Yes, this is coming in Phase 2. For now, copy-paste queries into a text file.

### Local Mode

**Q: How much storage does the model take?**

A:
- `qwen2.5-coder:7b`: ~4.7GB
- `qwen2.5-coder:14b`: ~8.5GB
- Total with Ollama: ~5-10GB

**Q: Can I use a different model?**

A: Yes, try:
```bash
ollama pull deepseek-r1:7b      # Alternative
ollama pull neural-chat:7b       # Another option
```

**Q: How accurate is Qwen-2.5-Coder?**

A: About 80-85% for standard queries. For complex SQL, use API mode (95%+).

**Q: Can I use GPU acceleration?**

A: Yes, if you have an NVIDIA or AMD GPU:
```bash
OLLAMA_NUM_GPU=1 ollama serve
```

### API Mode

**Q: Which API provider should I choose?**

A:
- **Gemini**: Best free tier, very good accuracy
- **Claude**: Excellent accuracy, good for complex analysis
- **OpenAI**: Industry standard, but can be expensive

**Q: Can I use multiple API providers?**

A: Yes, set multiple API keys via `/login` and switch between them:
```bash
/explore:api:gemini   # Use Gemini
Alt+M                 # Stay in API mode but change provider
/explore:api:claude   # Use Claude next time
```

**Q: How do I monitor API usage/costs?**

A: Check your provider's dashboard:
- Gemini: https://ai.google.dev/
- Claude: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/account/billing/overview

**Q: What if I run out of API credits?**

A: Switch to Local mode (`Alt+M`) to continue working for free.

### Mode Switching

**Q: Does switching modes (`Alt+M`) lose my current query?**

A: No, your input is preserved when you switch.

**Q: Can I set a default mode?**

A: Yes, configure it:
```bash
# Edit config file or set via /login
default_mode: "local"  # or "api"
```

**Q: How often can I switch modes?**

A: As often as you want. It's instant with `Alt+M`.

### Performance

**Q: Why is my query taking 30+ seconds?**

A: Possible causes:
- Large schema (>100 tables) - try filtering by schema
- Slow LLM model - switch to API mode
- Network latency (API mode) - try Local mode
- System resource constraints - close other apps

**Q: Can I cache results?**

A: Not yet, but this is planned for Phase 2.

**Q: How large can my dataset be?**

A: The explore feature works with any database size. Query generation time depends on schema size, not data size.

---

## Advanced Tips

### Tip 1: Better Query Results

Include context in your natural language input:

**Bad**: "Top products"
**Good**: "Top 10 products by revenue in the last 30 days"

**Better**: "Top 10 products by revenue in the last 30 days, grouped by category, excluding discontinued products"

### Tip 2: Switching Modes Strategically

```
Morning routine: Use Local mode for quick checks (fast + free)
    ↓
Complex analysis needed: Switch to API mode with Alt+M
    ↓
Production query created: Bookmark it
    ↓
Reuse bookmarked query: Works in both modes
```

### Tip 3: Debugging Bad SQL

If generated SQL is wrong:

1. **Check the schema**: Does the AI have the right table/column names?
2. **Simplify your request**: Break complex asks into smaller pieces
3. **Specify the database**: "For PostgreSQL, give me..."
4. **Manually edit**: Edit the SQL before running
5. **Switch providers**: Try a different AI model

### Tip 4: Optimize Large Schemas

If you have 100+ tables and queries are slow:

1. Use the schema filter to show only relevant tables
2. Switch to API mode for better handling
3. Specify which tables to focus on: "Using the 'sales' and 'products' tables only, show..."

---

## Related Documentation

- [User Guide](./USER_GUIDE.md) - Overall BI-Agent usage
- [Setup Guide](./SETUP_GUIDE.md) - Initial installation
- [GCP Setup](./GCP_SETUP_GUIDE.md) - Google Cloud Platform integration

---

## Getting Help

**Having issues?**

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the [FAQ](#faq)
3. Check error messages - they include helpful suggestions
4. Refer to provider docs:
   - Ollama: https://ollama.ai
   - Gemini: https://ai.google.dev
   - Claude: https://www.anthropic.com
   - OpenAI: https://openai.com

**Found a bug?**

Report it with:
- Your mode (Local/API)
- The query you tried
- The error message
- Your database type (PostgreSQL/MySQL/SQLite)

---

**Last Updated**: February 9, 2026
**Author**: BI-Agent Documentation Team

Copyright © 2026 BI-Agent. All rights reserved.
