import json
import time
from typing import Dict, Any
from openai import OpenAI

# Primary and fallback API keys
API_KEYS = [
    "8c485bc0789e4e998bc3ea2acf02b69c",
    "d7ad2c18bb7349b49644b89bc93713bd",
    "afa9af47c92b4f75a26643a5e26013dd",
    "a375c0a161094aff8708070cb95d3da3",
    "68ced62eac3c48eca9e451a63a45d2ac",
    "e58ed952cfac4686a297e94e1174c4e7"
]

BASE_URL = "https://api.aimlapi.com/v1"
MODEL_NAME = "google/gemma-3-12b-it"


def get_client(api_key: str) -> OpenAI:
    """Initialize and return an OpenAI client with the given API key."""
    return OpenAI(base_url=BASE_URL, api_key=api_key)


def run_model(user_message: str) -> Dict[str, Any]:
    """
    Sends a legal clause text to the ChatGPT-like API for analysis.
    Returns a structured JSON with fields:
    clause_type, key_terms, risk_level, summary, recommendations.
    """

    # Notice: no 'f' before triple quotes to prevent {} errors
    prompt = """
You are a senior legal expert specializing in **rental home agreements** between landlords and tenants.  
Your job is to review and analyze the given clause text in the context of **real estate rental contracts** — focusing on fairness, legal clarity, and risk for both parties.

Respond **only** with valid JSON (not a string or text). Do **not** include explanations, comments, markdown, or any text outside the JSON.  
The JSON must be well-formed and contain the following exact fields:

{
  "clause_type": "string - The category of the clause (e.g., Rent Payment, Security Deposit, Maintenance, Termination, Renewal, Subletting, Rules, Right of Entry, Pet Policy, etc.)",
  "key_terms": ["list of important legal or financial terms found in the clause"],
  "risk_level": "string - One of ['Low', 'Medium', 'High'], based on risk to the tenant",
  "confidence": "number between 0 and 1, representing how confident you are in your interpretation",
  "summary": "string - A concise, plain-language explanation of what the clause means and its impact on the tenant",
  "recommendations": ["list of suggestions to improve fairness, transparency, and compliance with tenant protection laws"],
  "negotiation_script": {
    "vendor": "What the tenant should say or ask the landlord/property manager when negotiating this clause",
    "contract_additions": ["list of clauses or phrases to request adding for tenant protection"],
    "contract_removals": ["list of clauses or phrases to request removing or revising that may harm the tenant"]
  }
}

When analyzing, evaluate the clause considering the **core rental agreement principles** below:

**Key Components to Keep in Mind**
- **Parties Involved:** Are landlord and tenant clearly identified?
- **Property Description:** Is the property properly described (address, unit)?
- **Term of Lease:** Are start and end dates, and renewal conditions, clearly stated?
- **Rent Details:** Are rent amount, due date, payment method, and late fee terms transparent?
- **Security Deposit:** Are amount, use, and return conditions fair and lawful?
- **Utilities and Services:** Is responsibility for utilities clearly divided?
- **Rules and Regulations:** Are restrictions on pets, smoking, guests, and alterations reasonable?
- **Maintenance and Repairs:** Are landlord and tenant responsibilities well defined?
- **Termination and Renewal:** Are notice periods and exit terms fair?
- **Signatures:** Does the clause relate to acknowledgment or consent by both parties?

**What to Watch Out For**
- Automatic renewals without tenant notice
- Unclear or unlimited rent increase terms
- Vague maintenance responsibility
- Subletting restrictions
- Excessive fees or penalties
- Unreasonable right of entry without notice
- Overly strict pet or guest policies
- Lack of property condition documentation
- Non-compliance with local laws or tenant rights

Keep your tone **neutral and professional**, and focus on protecting tenant interests while maintaining fairness.
"""

    # Now safely append the variable
    prompt += f'\n\nClause text to analyze:\n"""{user_message}"""\n'

    for key in API_KEYS:
        try:
            client = get_client(key)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                top_p=0.8,
                max_tokens=600,
                timeout=20,
            )

            content = response.choices[0].message.content.strip()

            try:
                clean_text = content.replace("```json", "").replace("```", "").strip()
                print(clean_text)
                return json.loads(clean_text)
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format", "raw": content}

        except Exception as e:
            print(f"Error using key {key[:5]}...: {e}")
            continue  # Try next key

    return {"error": "All API calls failed or rate limited."}
