import json
import re

# Keywords for clause type detection
CLAUSE_KEYWORDS = {
    "Limitation of Liability": ["liability", "limit", "damages"],
    "Indemnification": ["indemnify", "hold harmless", "defend"],
    "Termination": ["terminate", "expire", "end"]
}

# High-risk terms
HIGH_RISK_TERMS = ["unlimited", "capless", "no limit", "full liability", "gross negligence", "willful misconduct"]

# One-sided language indicators
ONE_SIDED_INDICATORS = ["shall", "must", "will", "agrees to", "obligated to"]

# Protective language
PROTECTIVE_LANGUAGE = ["mutual", "reasonable", "fair", "reciprocal", "limited to"]

def detect_clause_type(clause_text):
    clause_lower = clause_text.lower()
    for clause_type, keywords in CLAUSE_KEYWORDS.items():
        if any(keyword in clause_lower for keyword in keywords):
            return clause_type
    return "Unknown"

def calculate_risk_score(clause_text):
    score = 0
    clause_lower = clause_text.lower()

    # Presence of high-risk terms
    for term in HIGH_RISK_TERMS:
        if term in clause_lower:
            score += 2

    # One-sided language detection
    one_sided_count = sum(1 for indicator in ONE_SIDED_INDICATORS if indicator in clause_lower)
    if one_sided_count > 2:
        score += 3

    # Missing protective language
    protective_count = sum(1 for protect in PROTECTIVE_LANGUAGE if protect in clause_lower)
    if protective_count == 0:
        score += 2

    # Cap the score at 10
    return min(score, 10)

def generate_flags(clause_text):
    flags = []
    clause_lower = clause_text.lower()

    if any(term in clause_lower for term in HIGH_RISK_TERMS):
        flags.append("Contains high-risk terms")

    one_sided_count = sum(1 for indicator in ONE_SIDED_INDICATORS if indicator in clause_lower)
    if one_sided_count > 2:
        flags.append("One-sided language detected")

    protective_count = sum(1 for protect in PROTECTIVE_LANGUAGE if protect in clause_lower)
    if protective_count == 0:
        flags.append("Missing protective language")

    return flags

def generate_summary(clause_type, risk_score, flags):
    summary = f"Clause type: {clause_type}. Risk score: {risk_score}/10."
    if flags:
        summary += f" Flags: {', '.join(flags)}."
    else:
        summary += " No flags raised."
    return summary

def analyze_clause_rules(clause_text):
    clause_type = detect_clause_type(clause_text)
    risk_score = calculate_risk_score(clause_text)
    flags = generate_flags(clause_text)
    summary = generate_summary(clause_type, risk_score, flags)

    result = {
        "clause_type": clause_type,
        "risk_score": risk_score,
        "flags": flags,
        "summary": summary
    }

    return json.dumps(result)
