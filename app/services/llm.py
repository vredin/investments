"""OpenRouter LLM adapter. All AI calls go through this module.
Never instantiate OpenAI() directly in routers or other services.

Models used:
  - Fast tasks (rationale bullets, sentiment): google/gemini-flash-1.5
  - Monthly reports (long narrative): anthropic/claude-sonnet-4-5 via OpenRouter
"""

from openai import OpenAI

from app.config import get_settings

DISCLAIMER = "Not investment advice. For informational purposes only."

# Fast model for short tasks (cheaper)
MODEL_FAST = "google/gemini-flash-1.5"
# Capable model for monthly reports
MODEL_REPORT = "anthropic/claude-sonnet-4-5"


def _client() -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=get_settings().OPENROUTER_API_KEY,
    )


def chat(prompt: str, model: str = MODEL_FAST, system: str | None = None) -> str:
    """Send a single prompt, return text response. Appends disclaimer."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = _client().chat.completions.create(model=model, messages=messages)
    text = response.choices[0].message.content or ""
    return f"{text}\n\n{DISCLAIMER}"


def generate_rationale(prompt: str) -> str:
    """Generate buy rationale for a ticker. Phase 02."""
    raise NotImplementedError("Buy rationale generation — Phase 02")


def ask_rag_question(_question: str, _context_chunks: list[str]) -> str:
    """Answer a question using retrieved course chunks. Phase 02."""
    raise NotImplementedError("RAG Q&A over course corpus — Phase 02")


def generate_monthly_report_narrative(_report_data: dict) -> str:
    """Generate narrative for monthly report. Phase 03."""
    raise NotImplementedError("Monthly report narrative — Phase 03")
