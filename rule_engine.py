import json
import re

# Rental Agreement Clause Keywords
CLAUSE_KEYWORDS = {
    "Rent Payment": ["rent", "monthly payment", "due date", "late fee", "grace period"],
    "Security Deposit": ["security deposit", "damage deposit", "refundable", "deduct"],
    "Maintenance and Repairs": ["maintenance", "repairs", "upkeep", "fix", "property damage"],
    "Utilities and Services": ["utilities", "water", "electricity", "gas", "internet", "garbage"],
    "Termination": ["terminate", "end of lease", "notice", "vacate"],
    "Renewal": ["renew", "extension", "automatic renewal", "renewal term"],
    "Subletting": ["sublet", "assign", "transfer lease"],
    "Right of Entry": ["entry", "inspect", "landlord access", "visit"],
    "Pet Policy": ["pet", "animal", "dog", "cat", "pet fee", "deposit"],
    "Guest Policy": ["guest", "visitor", "overnight stay"],
    "Property Condition": ["condition", "move-in", "inspection", "damage report"],
    "Liability and Insurance": ["liability", "insurance", "coverage"],
    "Default": ["default", "breach", "non-payment", "failure to comply"]
}

# High-risk / tenant-unfriendly terms
HIGH_RISK_TERMS = [
    "unlimited", "no notice", "immediate eviction", "non-refundable",
    "forfeit", "arbitrary", "sole discretion", "without cause", "no liability",
    "penalty", "waive rights", "irrevocable", "final and binding"
]

# One-sided landlord language
ONE_SIDED_INDICATORS = [
    "tenant shall", "tenant must", "tenant agrees to", "landlord may", "at landlord’s discretion"
]

# Protective / balanced language
PROTECTIVE_LANGUAGE = [
    "reasonable", "mutual", "both parties", "written notice", "as required by law",
    "fair", "reciprocal", "limited to", "subject to"
]

def detect_clause_type(clause_text):
    clause_lower = clause_text.lower()
    for clause_type, keywords in CLAUSE_KEYWORDS.items():
        if any(keyword in clause_lower for keyword in keywords):
            return clause_type
    return "Unknown"

def calculate_risk_score(clause_text):
    score = 0
    clause_lower = clause_text.lower()

    # High-risk terms
    for term in HIGH_RISK_TERMS:
        if term in clause_lower:
            score += 2

    # One-sided language
    one_sided_count = sum(1 for indicator in ONE_SIDED_INDICATORS if indicator in clause_lower)
    if one_sided_count > 1:
        score += 3

    # Missing protective terms
    protective_count = sum(1 for word in PROTECTIVE_LANGUAGE if word in clause_lower)
    if protective_count == 0:
        score += 2

    # Adjust for unknown clauses
    if detect_clause_type(clause_text) == "Unknown":
        score += 1

    return min(score, 10)

def generate_flags(clause_text):
    flags = []
    clause_lower = clause_text.lower()

    if any(term in clause_lower for term in HIGH_RISK_TERMS):
        flags.append("Contains high-risk or tenant-unfriendly language")

    one_sided_count = sum(1 for indicator in ONE_SIDED_INDICATORS if indicator in clause_lower)
    if one_sided_count > 1:
        flags.append("Clause appears one-sided in favor of the landlord")

    protective_count = sum(1 for word in PROTECTIVE_LANGUAGE if word in clause_lower)
    if protective_count == 0:
        flags.append("No protective or mutual language found")

    # Rental-specific red flags
    if "automatic renewal" in clause_lower:
        flags.append("Automatic renewal clause detected — verify tenant consent")
    if "no notice" in clause_lower:
        flags.append("Missing or unfair notice period")
    if "non-refundable" in clause_lower:
        flags.append("Non-refundable deposit may be unfair to tenant")

    return flags

def generate_summary(clause_type, risk_score, flags):
    summary = f"This clause relates to {clause_type.lower() if clause_type != 'Unknown' else 'an unspecified section of the rental agreement'}. "
    if risk_score <= 3:
        summary += "It poses low risk to the tenant."
    elif risk_score <= 6:
        summary += "It poses medium risk and should be reviewed for fairness."
    else:
        summary += "It poses high risk to the tenant and likely favors the landlord."

    if flags:
        summary += " Key concerns: " + "; ".join(flags) + "."
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

    return result

