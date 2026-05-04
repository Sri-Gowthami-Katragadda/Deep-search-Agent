"""
utils/helpers.py
────────────────
General-purpose utility functions.
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def ensure_dir(path: str) -> Path:
    """Create directory if it doesn't exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    name = re.sub(r'[^\w\s-]', '', name.lower())
    name = re.sub(r'[-\s]+', '_', name)
    return name[:80]


def save_report(content: str, query: str, reports_dir: str) -> str:
    """Save a research report to disk and return the file path."""
    ensure_dir(reports_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{sanitize_filename(query)}_{timestamp}.md"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def safe_json_parse(text: str) -> dict | None:
    """
    Attempt to parse JSON from LLM output.
    Handles: plain JSON, ```json fences, ``` fences, leading prose, trailing prose.
    """
    if not text:
        return None

    # 1. Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # 2. Direct parse attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Find the LARGEST {...} block in the text (handles leading/trailing prose)
    brace_matches = list(re.finditer(r'\{', cleaned))
    for start_match in brace_matches:
        start = start_match.start()
        # Walk forward to find matching closing brace
        depth = 0
        for i, ch in enumerate(cleaned[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break  # try next opening brace

    # 4. Last resort: fix common LLM JSON mistakes
    try:
        # Remove trailing commas before } or ]
        fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


def truncate_text(text: str, max_chars: int = 2000) -> str:
    """Truncate text to max_chars."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def format_currency(value: float, currency: str = "INR") -> str:
    """Format a number as currency string."""
    if currency == "INR":
        if value >= 1e7:
            return f"₹{value/1e7:.2f} Cr"
        elif value >= 1e5:
            return f"₹{value/1e5:.2f} L"
        return f"₹{value:,.0f}"
    else:
        if value >= 1e9:
            return f"${value/1e9:.2f}B"
        elif value >= 1e6:
            return f"${value/1e6:.2f}M"
        return f"${value:,.0f}"


def extract_companies_from_text(text: str, known_companies: list) -> list:
    """Find known company names mentioned in a text block."""
    found = []
    text_lower = text.lower()
    for company in known_companies:
        if company.lower() in text_lower:
            found.append(company)
    return list(set(found))


def build_research_summary(steps: list) -> str:
    """Summarise research steps into a compact string for prompts."""
    lines = []
    for i, step in enumerate(steps, 1):
        lines.append(f"Step {i}: Searched '{step.get('query', '')}' → Found: {step.get('summary', '')[:150]}")
    return "\n".join(lines)