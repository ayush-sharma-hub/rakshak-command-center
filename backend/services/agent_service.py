"""
================================================================================
          RAKSHAK SEOC BACKEND  --  agent_service.py
  Autonomous Disaster Risk Assessment & Dispatch Coordination Service
================================================================================

Integrates the smolagents-powered Rakshak Autonomous Agent into the FastAPI
backend, executing non-blocking intelligence retrieval and Gemini reasoning.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import textwrap
import time
import traceback
import contextvars
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ── Force UTF-8 on Windows Console to prevent encoding crashes ────────────────
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── LiteLLM Local Mode: Skip slow remote model-cost download ──────────────────
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

# ── Load Environment Variables ────────────────────────────────────────────────
from dotenv import load_dotenv

load_dotenv()

# ── Dedicated Service Logger ──────────────────────────────────────────────────
logger = logging.getLogger("rakshak.agent")

# ── ContextVar for Streaming Thought Logs to WebSockets ──────────────────────
_current_thought_callback: contextvars.ContextVar[Optional[Callable[[str, str], None]]] = contextvars.ContextVar(
    "thought_callback", default=None
)

def emit_thought(log_text: str, level: str = "info") -> None:
    """Dispatches a thought log line to the active WebSocket or callback."""
    cb = _current_thought_callback.get()
    if cb:
        try:
            cb(log_text, level)
        except Exception as e:
            logger.debug("Error in thought callback: %s", e)

# ── LiteLLM Configuration ─────────────────────────────────────────────────────
try:
    import litellm
    litellm.suppress_debug_info = True
except Exception:
    pass

# ── smolagents Imports ────────────────────────────────────────────────────────
from smolagents import LiteLLMModel, ToolCallingAgent, LogLevel, tool

# ── DuckDuckGo Search (supports new ddgs package & legacy duckduckgo_search) ──
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS  # type: ignore

# ── Tenacity Retry Engine ─────────────────────────────────────────────────────
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & STORAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Local logs directory (resolves relative to application root or current working dir)
LOG_DIR = Path("./local_logs")
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning("Could not initialize local_logs directory: %s", e)

# Default to latest active Flash model; can be overridden via environment variable
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-flash-latest")

MAX_SEARCH_RESULTS = 6
RISK_LEVELS = ("Normal", "Elevated", "Severe")

THREAT_LABELS = {"Normal": "[NORMAL]", "Elevated": "[ELEVATED]", "Severe": "[SEVERE]"}

# ─────────────────────────────────────────────────────────────────────────────
# RESILIENT SEARCH TOOL
# ─────────────────────────────────────────────────────────────────────────────

def _run_single_search(query: str, max_results: int) -> list[dict]:
    """Execute a single DuckDuckGo text search."""
    with DDGS() as ddgs:
        results = ddgs.text(
            query,
            region="in-en",
            safesearch="off",
            max_results=max_results,
        )
        return list(results) if results else []


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1.0, max=5.0),
    reraise=False,
)
def _resilient_search(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    """Search DuckDuckGo with exponential backoff on transient network drops."""
    return _run_single_search(query, max_results)


@tool
def environmental_search_tool(location: str) -> str:
    """
    Searches DuckDuckGo for live weather forecasts, rainfall observations,
    flood warnings, landslide advisories, and emergency response reports for a specific location.

    Args:
        location: Target geographic area (e.g. "Roorkee, Uttarakhand").

    Returns:
        Formatted intelligence brief of deduplicated live reports.
    """
    emit_thought(f"[TOOL EXEC] environmental_search_tool scanning target sector '{location}'", "warning")

    queries = [
        f"{location} current weather forecast rainfall IMD alerts today",
        f"{location} flood landslide disaster emergency warning 2025",
        f"{location} NDRF SDRF rescue relief operations news",
    ]

    seen_texts: set[str] = set()
    snippets: list[str] = []
    errors: list[str] = []

    for idx, query in enumerate(queries, 1):
        emit_thought(f"[INTEL QUERY {idx}/3] Interrogating live telemetry for: '{query}'...", "info")
        try:
            results = _resilient_search(query, MAX_SEARCH_RESULTS)
            count = 0
            for item in results or []:
                title = (item.get("title") or "").strip()
                body = (item.get("body") or "").strip()
                if not body or body in seen_texts:
                    continue
                seen_texts.add(body)
                snippet = f"[{title}] {body}" if title else body
                snippets.append(snippet)
                count += 1
            emit_thought(f"[INTEL RX {idx}/3] Harvested {count} real-time reports.", "info")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{query}: {type(exc).__name__}")
            logger.warning("Search query failed for '%s': %s", query, exc)
            emit_thought(f"[SEARCH FALLBACK] Query {idx} notice: {type(exc).__name__}", "warning")

    if not snippets:
        emit_thought(f"[INTEL GAP] No live web reports retrieved for '{location}'. Engaging precautionary elevated mode.", "warning")
        return (
            f"[WARNING] No live web results retrieved for '{location}'. "
            "Assume precautionary ELEVATED risk status until field data is verified."
        )

    emit_thought(f"[INTEL COMPLETE] Synthesized {len(snippets)} verified reports across meteorology & disaster feeds.", "info")
    header = (
        f"=== LIVE INTELLIGENCE BRIEF FOR: {location} ===\n"
        f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Verified Reports: {len(snippets)}\n\n"
    )
    return header + "\n\n".join(f"* {s}" for s in snippets)


# ─────────────────────────────────────────────────────────────────────────────
# LLM MODEL FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def _build_model() -> LiteLLMModel:
    """Instantiate and return the LiteLLM-backed Gemini model instance with retries & fallbacks."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in environment or .env file.")

    os.environ["GEMINI_API_KEY"] = api_key

    return LiteLLMModel(
        model_id=GEMINI_MODEL,
        api_key=api_key,
        max_tokens=2048,
        timeout=60,
        num_retries=3,
        fallbacks=["gemini/gemini-3.5-flash", "gemini/gemini-3.7-flash"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM INSTRUCTIONS
# ─────────────────────────────────────────────────────────────────────────────

AGENT_INSTRUCTIONS = textwrap.dedent("""
    You are RAKSHAK, a senior autonomous AI analyst for the National Disaster Response
    Framework (NDRF / NDMA / SEOC), India.

    MISSION WORKFLOW:
    1. Call the `environmental_search_tool` for the specified location to obtain live ground truth.
    2. Analyze the search results for active weather anomalies, rainfall, IMD warnings,
       landslides, floods, and civil emergencies.
    3. Return ONLY a single valid JSON object adhering strictly to the schema below.
       DO NOT include markdown fences, preambles, or postscripts.

    OUTPUT JSON SCHEMA:
    {
        "location": "<Target location string>",
        "threat_level": "<Normal | Elevated | Severe>",
        "confidence": "<High | Medium | Low>",
        "active_hazards": ["<Hazard 1>", "<Hazard 2>"],
        "summary": "<2-4 sentence concise situational analysis>",
        "action_plan": [
            "<Action item 1>",
            "<Action item 2>",
            "<Action item 3>"
        ],
        "resources_needed": {
            "ndrf_teams": <number>,
            "helicopters": <number>,
            "medical_units": <number>,
            "relief_camps": <number>
        },
        "contact_agencies": ["<Agency 1>", "<Agency 2>"]
    }

    THREAT CRITERIA:
    - Normal  : Fair weather, routine seasonal patterns, standard preparedness.
    - Elevated: Heavy rainfall warning (Yellow/Orange alert), high river levels, localized waterlogging, alert standby.
    - Severe  : Active flood inundation, major landslides, cyclone warning (Red alert), structural damage, immediate dispatch.
""").strip()


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE PARSER & SAFE FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def _safe_fallback(location: str, reason: str = "Precautionary Fallback") -> Dict[str, Any]:
    """Fail-safe structured assessment when LLM synthesis or connectivity fails."""
    return {
        "location": location,
        "threat_level": "Elevated",
        "confidence": "Low",
        "active_hazards": ["Data retrieval gap / Verification in progress"],
        "summary": (
            f"Autonomous risk engine encountered an unparseable response ({reason}). "
            "A precautionary ELEVATED status has been assigned. "
            "Duty officers must independently confirm ground conditions via IMD/SEOC channels."
        ),
        "action_plan": [
            "Alert district disaster management officer and local emergency centers.",
            "Pre-position NDRF/SDRF swift-water or hill rescue teams on standby.",
            "Continuously track IMD Doppler radar and automated weather stations.",
            "Verify emergency telecommunications and satellite channels."
        ],
        "resources_needed": {
            "ndrf_teams": 1,
            "helicopters": 0,
            "medical_units": 1,
            "relief_camps": 0
        },
        "contact_agencies": ["NDMA", "USDMA", "IMD", "District Magistrate Office"]
    }


def _parse_agent_response(raw: Any, location: str) -> Dict[str, Any]:
    """Safely extract and validate the JSON payload from the agent's output."""
    if isinstance(raw, dict):
        data = raw
    else:
        text = str(getattr(raw, "content", raw)).strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE).strip()

        json_match = re.search(r"\{[\s\S]*\}", text)
        if not json_match:
            logger.error("No JSON block located in agent output: %s", text[:200])
            return _safe_fallback(location, "No JSON found")

        try:
            data = json.loads(json_match.group())
        except Exception as exc:
            logger.error("JSON decoding failed: %s", exc)
            return _safe_fallback(location, "JSON Decode Error")

    # Validate required baseline keys
    for key in ("threat_level", "summary", "action_plan"):
        if key not in data:
            return _safe_fallback(location, f"Missing required key '{key}'")

    tl = str(data.get("threat_level", "")).strip().title()
    data["threat_level"] = tl if tl in RISK_LEVELS else "Elevated"
    data["location"] = location

    ap = data.get("action_plan", [])
    if isinstance(ap, str):
        ap = [ap]
    data["action_plan"] = [str(x).strip() for x in ap if str(x).strip()]

    conf = str(data.get("confidence", "Medium")).strip().title()
    data["confidence"] = conf if conf in ("High", "Medium", "Low") else "Medium"

    hazards = data.get("active_hazards", [])
    if isinstance(hazards, str):
        hazards = [hazards]
    data["active_hazards"] = [str(h).strip() for h in hazards if str(h).strip()]

    rn = data.get("resources_needed", {})
    if not isinstance(rn, dict):
        rn = {}
    for sub in ("ndrf_teams", "helicopters", "medical_units", "relief_camps"):
        if sub not in rn or not isinstance(rn[sub], (int, float)):
            rn[sub] = 0
        else:
            rn[sub] = int(rn[sub])
    data["resources_needed"] = rn

    ca = data.get("contact_agencies", [])
    if isinstance(ca, str):
        ca = [ca]
    data["contact_agencies"] = [str(c).strip() for c in ca if str(c).strip()] or ["NDMA", "IMD"]

    return data


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING & AUDIT TRAIL
# ─────────────────────────────────────────────────────────────────────────────

def _save_log(result: Dict[str, Any], elapsed_secs: float = 0.0) -> Path | None:
    """Persists a Markdown audit report into ./local_logs/."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_loc = re.sub(r"[^\w\-]", "_", result["location"]).strip("_")
        filename = f"{timestamp}_{safe_loc}.md"
        filepath = LOG_DIR / filename

        tl = result["threat_level"]
        tag = THREAT_LABELS.get(tl, f"[{tl.upper()}]")
        rn = result.get("resources_needed", {})
        hazards = ", ".join(result.get("active_hazards", [])) or "None identified"
        agencies = ", ".join(result.get("contact_agencies", [])) or "NDMA, IMD"

        action_list = "\n".join(
            f"{idx+1}. {item}" for idx, item in enumerate(result.get("action_plan", []))
        )

        report_content = (
            f"# RAKSHAK AUTONOMOUS DISPATCH REPORT\n\n"
            f"**Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Location**: {result['location']}\n"
            f"**Execution Time**: {elapsed_secs:.2f} seconds\n"
            f"**Model**: {GEMINI_MODEL}\n\n"
            f"---\n\n"
            f"## Threat Assessment\n"
            f"* **Status**: {tag}\n"
            f"* **Confidence**: {result.get('confidence', 'Medium')}\n"
            f"* **Active Hazards**: {hazards}\n\n"
            f"## Situational Overview\n"
            f"{result['summary']}\n\n"
            f"## Priority Action & Dispatch Directives\n"
            f"{action_list}\n\n"
            f"## Emergency Resource Allocation\n"
            f"* **NDRF Teams**: {rn.get('ndrf_teams', 0)}\n"
            f"* **Rescue Helicopters**: {rn.get('helicopters', 0)}\n"
            f"* **Mobile Medical Units**: {rn.get('medical_units', 0)}\n"
            f"* **Relief / Evacuation Camps**: {rn.get('relief_camps', 0)}\n\n"
            f"## Coordinating Agencies\n"
            f"{agencies}\n\n"
            f"---\n"
            f"*Report compiled automatically by Rakshak Autonomous Dispatch Agent.*\n"
        )

        filepath.write_text(report_content, encoding="utf-8")
        logger.info("Audit report saved to: %s", filepath)
        return filepath
    except Exception as exc:
        logger.warning("Could not persist local markdown report: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CORE ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run_disaster_analysis(
    location: str,
    verbose: bool = False,
    on_thought: Optional[Callable[[str, str], None]] = None
) -> Dict[str, Any]:
    """
    Executes a disaster risk intelligence assessment cycle.

    Synchronous blocking function: Designed to be called inside a worker
    thread (e.g. via `starlette.concurrency.run_in_threadpool` or `asyncio.to_thread`).

    Args:
        location: Target geographic place name (e.g. "Roorkee, Uttarakhand").
        verbose: Set to True to stream tool execution steps to stdout.
        on_thought: Optional callback (msg, level) to stream intermediate thoughts.

    Returns:
        Structured dictionary matching the required dispatch analysis schema.
    """
    t0 = time.monotonic()
    token = _current_thought_callback.set(on_thought)
    try:
        emit_thought(f"[SYS INIT] C4ISR Autonomous Assessment activated for target: '{location}'", "info")
        emit_thought(f"[SYS MODEL] Deploying LiteLLM bridge with model: {GEMINI_MODEL}", "info")
        logger.info("Autonomous disaster analysis initiated for location: '%s'", location)

        model = _build_model()

        def step_callback(step_log):
            try:
                step_num = getattr(step_log, "step_number", 1)
                tool_calls = getattr(step_log, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        name = getattr(tc, "name", str(tc))
                        args = getattr(tc, "arguments", "")
                        emit_thought(f"[AGENT TOOL INVOCATION · STEP {step_num}] {name}({args})", "warning")

                obs = getattr(step_log, "observations", None)
                if obs:
                    obs_str = str(obs).strip().replace("\n", " ")[:110]
                    emit_thought(f"[OBSERVATION · STEP {step_num}] {obs_str}...", "info")

                out = getattr(step_log, "model_output", None)
                if out:
                    emit_thought(f"[REASONING · STEP {step_num}] Gemini analyzing multi-spectral risk matrix...", "info")
            except Exception as e:
                logger.debug("Step callback error: %s", e)

        agent = ToolCallingAgent(
            tools=[environmental_search_tool],
            model=model,
            instructions=AGENT_INSTRUCTIONS,
            max_steps=8,
            verbosity_level=LogLevel.INFO if verbose else LogLevel.ERROR,
            step_callbacks=[step_callback],
        )

        task = (
            f"Perform an urgent environmental and disaster risk analysis for: '{location}'.\n"
            f"1. Call `environmental_search_tool` for '{location}' to fetch live weather and alert data.\n"
            f"2. Synthesize the findings and output the final JSON risk assessment."
        )

        emit_thought(f"[MISSION DISPATCH] Analyzing hazards for '{location}' under NDMA/SEOC criteria...", "info")

        raw_response: Any = None
        try:
            raw_response = agent.run(task)
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent execution failed for '%s': %s\n%s", location, exc, traceback.format_exc())
            emit_thought(f"[AGENT WARNING] Agent execution interrupted: {exc}. Activating safe fallback.", "warning")
            raw_response = None

        elapsed = time.monotonic() - t0
        emit_thought("[PARSING] Ingesting and verifying schema consistency...", "info")
        result = _parse_agent_response(raw_response, location)

        _save_log(result, elapsed)

        tl = result.get("threat_level", "Normal")
        lvl = "critical" if tl == "Severe" else ("warning" if tl == "Elevated" else "info")
        emit_thought(f"[ASSESSMENT COMPLETE] Threat Level: {tl.upper()} (Confidence: {result.get('confidence', 'Medium')})", lvl)
        hazards = ", ".join(result.get("active_hazards", [])) or "None identified"
        emit_thought(f"[ACTIVE HAZARDS] {hazards}", lvl)
        emit_thought(f"[SITUATIONAL SUMMARY] {result.get('summary', '')[:130]}...", "info")
        if result.get("action_plan"):
            emit_thought(f"[TACTICAL DIRECTIVE 1] {result['action_plan'][0]}", "warning")
        rn = result.get("resources_needed", {})
        emit_thought(f"[DISPATCH ASSETS] NDRF: {rn.get('ndrf_teams', 0)} teams | Helis: {rn.get('helicopters', 0)} | Med Units: {rn.get('medical_units', 0)} | Camps: {rn.get('relief_camps', 0)}", "info")

        logger.info(
            "Analysis finished for '%s' in %.2fs (Threat: %s, Confidence: %s)",
            location, elapsed, result.get("threat_level"), result.get("confidence")
        )

        return result
    finally:
        _current_thought_callback.reset(token)
