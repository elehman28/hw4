"""Campus Customs shop agent: PydanticAI entry point and wiring.

The agent is built once at import time:
  - system prompt: prompts/prompt.md
  - model: CC_CHAT_MODEL (default gpt-5.6-luna) through the Portkey gateway, keyed by PORTKEY_API_KEY
  - tools: tools.SHOP_TOOLS
  - output: models.AgentReply (reply text + product_ids that main.py turns into cards)

Also contains the code-enforced safety checks and the append-only audit trail, so the
whole agent loop lives in this one file.
"""

import asyncio
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import AgentReply, ChatTurn, ProductDetails, ProductNotFound, ProductSearch, StockCheck
from tools import SHOP_TOOLS, ShopDeps, all_prices


# ============================================================================
# Safety rules enforced in code
# Code-enforced safety rules (the prompt states them; these make them hold even if the model slips).
#
# - check_input:   block payment card numbers / SSNs / shared passwords BEFORE anything reaches
#                  the model or the audit log, and answer with a safe canned reply.
# - redact:        mask emails, card-like numbers and SSNs in anything written to the audit trail.
# - foreign_emails: find email addresses in a reply that aren't the current shopper's own
#                  (agent.py rejects such replies with ModelRetry).
# ============================================================================

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PASSWORD_SHARE_RE = re.compile(r"\b(my|the)\s+(password|passcode|pin)\s+(is|=|:)\s*\S+", re.I)

SENSITIVE_REPLY = (
    "For your safety, please don't share card numbers, Social Security numbers, or passwords in chat. "
    "I've ignored that message and didn't save it. I can't take payments here, but I'm happy to help "
    "you find Yale gear, sizes, or stock!"
)


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def _has_card_number(text: str) -> bool:
    for m in CARD_CANDIDATE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return True
    return False


def check_input(message: str) -> str | None:
    """Return the kind of sensitive data found (so the caller can refuse), or None if safe."""
    if _has_card_number(message):
        return "payment_card"
    if SSN_RE.search(message):
        return "ssn"
    if PASSWORD_SHARE_RE.search(message):
        return "password"
    return None


def redact(text: str) -> str:
    text = EMAIL_RE.sub("[email]", text)
    text = SSN_RE.sub("[ssn]", text)
    return CARD_CANDIDATE_RE.sub(lambda m: "[number]" if len(re.sub(r"\D", "", m.group())) >= 13 else m.group(), text)


def foreign_emails(reply: str, own_email: str | None) -> list[str]:
    own = (own_email or "").lower()
    return [e for e in EMAIL_RE.findall(reply) if e.lower() != own]


# ============================================================================
# Audit trail: output/audit_trail.json
# Append-only audit trail of agent loop activity: output/audit_trail.json.
#
# Format: JSON Lines (one JSON object per line). The file is only ever opened in
# append mode, so entries from earlier runs and server restarts are never wiped;
# each line is complete JSON on its own, so a crash mid-run can't corrupt history.
#
# Every chat turn writes:
#   run_start   – who (user id or guest), page, model, the (redacted, truncated) message
#   tool_call   – time, tool name, short args
#   tool_result – time, tool name, short result summary
#   retry       – when a tool/output validator rejected something (e.g. an invented price)
#   run_end     – stop reason, duration, model requests, tokens, product ids returned
#
# Stop reasons: final_result | blocked_sensitive_input | content_filter | request_limit |
#               timeout | output_validation_failed | error
# ============================================================================

AUDIT_FILE = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_FIELD = 160  # keep each entry short and readable
_lock = threading.Lock()


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def audit_short(value: Any, limit: int = MAX_FIELD) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = redact(re.sub(r"\s+", " ", text))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def audit_write(event: str, run_id: str, **fields: Any) -> None:
    entry = {"ts": _now(), "run_id": run_id, "event": event, **fields}
    line = json.dumps(entry, ensure_ascii=False, default=str)
    with _lock:
        AUDIT_FILE.parent.mkdir(exist_ok=True)
        with AUDIT_FILE.open("a", encoding="utf-8") as f:  # append-only, never "w"
            f.audit_write(line + "\n")


def audit_summarize_result(content: Any) -> str:
    """One-line, human-readable summary of a tool's return value."""
    if isinstance(content, ProductSearch):
        top = ", ".join(m.product_id for m in content.matches[:3])
        fixes = f"; fixed {content.corrections}" if content.corrections else ""
        return audit_short(f"{len(content.matches)} matches for '{content.interpreted_as}'{fixes}; top: {top}")
    if isinstance(content, StockCheck):
        return audit_short(f"{content.product_id} {content.size}: qty {content.quantity} ({content.status}), ${content.price:.2f}")
    if isinstance(content, ProductDetails):
        return audit_short(
            f"{content.product_id} ${content.price:.2f}; in stock {','.join(content.sizes_in_stock) or 'none'}; "
            f"sold out {','.join(content.sizes_sold_out) or 'none'}"
        )
    if isinstance(content, ProductNotFound):
        return audit_short(f"not found '{content.query}'; suggestions: {[s.product_id for s in content.suggestions[:3]]}")
    if isinstance(content, BaseModel):
        return audit_short(content.model_dump(exclude_none=True))
    return audit_short(content)


def audit_log_messages(run_id: str, messages: list[ModelMessage]) -> None:
    """Write tool_call / tool_result / retry entries for this run's new messages."""
    for msg in messages:
        ts = getattr(msg, "timestamp", None)
        for part in msg.parts:
            if isinstance(part, ToolCallPart):
                if part.tool_name == "final_result":
                    continue  # the structured answer itself; summarized in run_end
                audit_write("tool_call", run_id, at=ts, tool=part.tool_name, args=audit_short(part.args_as_dict()))
            elif isinstance(part, ToolReturnPart):
                if part.tool_name == "final_result":
                    continue
                audit_write("tool_result", run_id, at=part.timestamp, tool=part.tool_name, result=audit_summarize_result(part.content))
            elif isinstance(part, RetryPromptPart):
                audit_write("retry", run_id, at=part.timestamp, tool=part.tool_name, reason=audit_short(part.model_response()))
        if isinstance(msg, ModelResponse) and msg.model_name and not any(isinstance(p, ToolCallPart) for p in msg.parts):
            audit_write("model_text", run_id, at=ts, note="model replied without a tool call")


# ============================================================================
# Agent: model, prompt, tools, validators, run loop
# ============================================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
# hw4/.env first (see .env.example).
load_dotenv(PROJECT_DIR / ".env")
# Fallback for local course setups: the nearest .env in a parent folder (never overrides values already set).
for parent in PROJECT_DIR.parents:
    if (parent / ".env").is_file():
        load_dotenv(parent / ".env")
        break

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
CHAT_MODEL = os.getenv("CC_CHAT_MODEL", "gpt-5.6-luna")
SYSTEM_PROMPT = (BACKEND_DIR / "prompts" / "prompt.md").read_text()

REQUEST_LIMIT = 8        # max model calls per chat turn (tool loop guard)
RUN_TIMEOUT_SECONDS = 60
MAX_HISTORY_TURNS = 20   # earlier turns (10 exchanges) replayed to the model


def portkey_model(model_name: str) -> OpenAIChatModel:
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is missing: copy .env.example to .env and add your key")
    client = AsyncOpenAI(
        api_key="not-used",
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
    )
    return OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))


# Speed: a shop chat needs quick lookups, not long deliberation. "none" skips hidden reasoning
# tokens (they were ~2/3 of output on some turns); set CC_REASONING_EFFORT=low if quality drops.
# Parallel tool calls let e.g. check_stock for two sizes happen in one round trip.
REASONING_EFFORT = os.getenv("CC_REASONING_EFFORT", "none")
MODEL_SETTINGS = OpenAIChatModelSettings(
    openai_reasoning_effort=REASONING_EFFORT,
    parallel_tool_calls=True,
    max_tokens=600,  # replies are 1-4 sentences; cap runaway generations
)

agent = Agent(
    portkey_model(CHAT_MODEL),
    deps_type=ShopDeps,
    output_type=AgentReply,
    system_prompt=SYSTEM_PROMPT,
    tools=SHOP_TOOLS,
    model_settings=MODEL_SETTINGS,
    retries=2,
)


@agent.system_prompt
def customer_context(ctx: RunContext[ShopDeps]) -> str:
    """Runs on every request: tells the model who is chatting (from ShopDeps.customer)."""
    c = ctx.deps.customer
    if c is None:
        return "## Current shopper\nGuest (not logged in). You don't know their name or email; don't ask for them."
    return (
        "## Current shopper (logged in)\n"
        f"- Name: {c.first_name} {c.last_name}\n"
        f"- Email: {c.email}\n"
        f"- Member since: {c.member_since}\n"
        f"- Saved chat messages: {c.past_messages} (earlier turns of this conversation are included above)"
    )


@agent.system_prompt
def page_context(ctx: RunContext[ShopDeps]) -> str:
    """Runs on every request: tells the model what page the shopper is on (from ShopDeps.page)."""
    page = ctx.deps.page
    lines = [f"## Current page\n- Path: {page.path} ({page.page.replace('_', ' ')})"]
    vp = page.viewed_product
    if vp is not None:
        lines += [
            f"- The shopper is viewing: {vp.name} (product_id: {vp.product_id})",
            f"- Colors: {', '.join(vp.colors)}",
            f"- Price: ${vp.price:.2f}",
            f"- Sizes in stock: {', '.join(vp.sizes_in_stock) or 'none'}; sold out: {', '.join(vp.sizes_sold_out) or 'none'}",
            '- "this", "it", "this one" mean this product unless the shopper names another.',
        ]
    if page.search_title:
        lines.append(f"- The Products page is showing chat search results titled: {page.search_title}")
    return "\n".join(lines)


CATALOGUE_PRICES = all_prices()
_DOLLAR_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
# A dollar amount right after these words is the shopper's budget, not a product price.
_BUDGET_WORDS = re.compile(r"(under|below|less than|over|above|up to|within|budget|max|around|about)\s*$", re.I)


@agent.output_validator
def no_invented_prices(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
    """Reject replies that quote a price that isn't in the catalogue."""
    bad = []
    for m in _DOLLAR_RE.finditer(output.reply):
        if _BUDGET_WORDS.search(output.reply[max(0, m.start() - 15):m.start()]):
            continue
        if float(m.group(1)) not in CATALOGUE_PRICES:
            bad.append(m.group(0))
    if bad:
        raise ModelRetry(
            f"Your reply quotes {', '.join(bad)}, which is not a real Campus Customs price. "
            "Only quote prices exactly as returned by get_product_details, check_stock, or search_products."
        )
    return output


@agent.output_validator
def no_other_peoples_emails(ctx: RunContext[ShopDeps], output: AgentReply) -> AgentReply:
    """Safety rule: the only email the agent may ever write is the logged-in shopper's own."""
    own = ctx.deps.customer.email if ctx.deps.customer else None
    leaked = foreign_emails(output.reply, own)
    if leaked:
        raise ModelRetry(
            "Your reply contains an email address that isn't the current shopper's own. "
            "Never share anyone's contact details; rewrite the reply without it."
        )
    return output


def to_model_history(turns: list[ChatTurn]) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    for t in turns[-MAX_HISTORY_TURNS:]:
        if t.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=t.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=t.content)]))
    return history


async def run_chat(message: str, history: list[ChatTurn], deps: ShopDeps, run_id: str | None = None) -> AgentReply:
    """One chat turn through the agent loop, fully recorded in output/audit_trail.json.

    Raises the underlying exception on failure (main.py turns it into a user-facing reply);
    the audit trail records the stop reason either way.
    """
    run_id = run_id or new_run_id()
    hist = to_model_history(history)
    started = time.perf_counter()
    audit_write(
        "run_start", run_id,
        user=f"user:{deps.customer.user_id}" if deps.customer else "guest",
        page=deps.page.path, model=CHAT_MODEL, reasoning_effort=REASONING_EFFORT,
        history_turns=len(hist), message=audit_short(message),
    )
    stop_reason, output, usage = "error", None, None
    with capture_run_messages() as captured:
        try:
            result = await asyncio.wait_for(
                agent.run(
                    message,
                    deps=deps,
                    message_history=hist,
                    usage_limits=UsageLimits(request_limit=REQUEST_LIMIT),
                ),
                timeout=RUN_TIMEOUT_SECONDS,
            )
            output, usage, stop_reason = result.output, result.usage, "final_result"
            return output
        except UsageLimitExceeded:
            stop_reason = "request_limit"
            raise
        except asyncio.TimeoutError:
            stop_reason = "timeout"
            raise
        except UnexpectedModelBehavior:
            stop_reason = "output_validation_failed"
            raise
        except ModelHTTPError as e:
            stop_reason = "content_filter" if "content_filter" in str(e.body) else "model_http_error"
            raise
        finally:
            audit_log_messages(run_id, captured[len(hist):])
            audit_write(
                "run_end", run_id,
                stop_reason=stop_reason,
                duration_ms=round((time.perf_counter() - started) * 1000),
                requests=usage.requests if usage else None,
                input_tokens=usage.input_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
                result_type=output.result_type if output else None,
                product_ids=output.product_ids[:6] if output else None,
                reply=audit_short(output.reply) if output else None,
            )


if __name__ == "__main__":
    # Quick manual test: python agent.py "do you have navy hoodies?"
    import sys

    reply = asyncio.run(run_chat(" ".join(sys.argv[1:]) or "What hoodies do you have?", [], ShopDeps()))
    print(reply.model_dump_json(indent=2))
