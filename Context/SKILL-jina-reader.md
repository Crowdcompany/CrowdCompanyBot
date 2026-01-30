# Jina Web Reader Skill

## Purpose
Use Jina Reader API for secure and clean web content fetching instead of direct web scraping.

## Overview
Jina Reader converts any URL into LLM-friendly markdown by:
- Rendering JavaScript-heavy pages properly
- Extracting only main content (no ads, navigation, etc.)
- Converting images to alt-text descriptions
- Bypassing bot-protection mechanisms
- Supporting proxy routing for additional privacy

## Tool: jina_fetch

### Description
Fetch and convert a URL to clean, structured markdown suitable for LLM processing.

### Parameters
- `url` (required): The webpage URL to fetch
- `use_proxy` (optional, default: false): Route through custom proxy
- `with_images` (optional, default: true): Generate alt-text for images
- `timeout` (optional, default: 10): Seconds to wait for page load

### Usage Examples

**Basic fetch:**
```bash
curl "https://r.jina.ai/https://example.com/article"
```

**With authentication (API key):**
```bash
curl "https://r.jina.ai/https://example.com/article" \
  -H "Authorization: Bearer ${JINA_API_KEY}"
```

**With image captions:**
```bash
curl "https://r.jina.ai/https://example.com/article" \
  -H "X-With-Generated-Alt: true"
```

**Through custom proxy:**
```bash
curl "https://r.jina.ai/https://example.com/article" \
  -H "X-Proxy-Url: http://your-proxy:8080"
```

**For slow-loading pages:**
```bash
curl "https://r.jina.ai/https://example.com/article" \
  -H "X-Timeout: 30"
```

## When to Use

### DO use jina_fetch when:
- User asks to read a website or article
- Need to extract content from news sites
- Parsing documentation pages
- Researching topics online
- Converting PDFs to text (via URL)
- Accessing JavaScript-heavy single-page apps

### DON'T use jina_fetch when:
- Content requires authentication/login
- Need real-time updates (use websockets instead)
- Interactive forms or buttons needed
- File downloads required
- Private/internal URLs (not publicly accessible)

## Rate Limits

**Without API Key:**
- 20 requests per minute
- Shared rate limit across all users
- May be throttled during high traffic

**With API Key (JINA_API_KEY):**
- ~10,000 requests per month ($10/mo)
- Priority processing
- Higher cache priority
- Better reliability

## Response Format

Jina returns clean markdown with:

```markdown
Title: [Page Title]

URL Source: [Original URL]

Published Time: [If available]

Markdown Content: [Clean, structured content]

# Main heading
Content paragraphs...

## Subheading
More content...

Image [1]: [Generated caption for image 1]
Image [2]: [Generated caption for image 2]
```

## Error Handling

Common errors and solutions:

**"Rate limit exceeded"**
→ Wait 60 seconds or set JINA_API_KEY

**"Timeout"**
→ Increase X-Timeout header or check if site is accessible

**"403 Forbidden"**
→ Site blocks Jina's crawler; try X-Proxy-Url

**"Empty content"**
→ Page is behind login or CAPTCHA; cannot fetch

## Security Notes

- Jina Reader acts as proxy - your IP is not exposed to target site
- Content is cached on Jina's servers (use X-No-Cache to prevent)
- For sensitive URLs, consider self-hosting Jina Reader
- API keys are transmitted over HTTPS

## Integration with Moltbot

This skill is automatically available in your agent's toolset.

**Example conversation:**

User: "What's the latest news on example.com?"

Agent: [Uses jina_fetch to retrieve https://example.com]
"Here's what I found on example.com: [summarized content from Jina markdown]"

## Implementation

Place this file in: `~/clawd/skills/jina-reader/SKILL.md`

The corresponding tool implementation is built into the agent's bash execution capability:

```bash
# Agent executes internally:
curl "https://r.jina.ai/${URL}" \
  -H "Authorization: Bearer ${JINA_API_KEY}" \
  -H "X-With-Generated-Alt: true"
```
