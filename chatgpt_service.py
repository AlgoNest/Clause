import json
from openai import OpenAI
from typing import Dict, Any
import time

client = OpenAI(
    base_url="https://api.aimlapi.com/v1",
    api_key="e5b592dcae06475193b733e9dc58fa15",
)

# Structured prompt for legal analysis
LEGAL_ANALYSIS_PROMPT = """
You are a legal expert analyzing contract clauses. For the given clause text, provide a structured JSON response with the following fields:

- clause_type: The type of clause (e.g., Limitation of Liability, Indemnification, Termination, Confidentiality, etc.)
- key_terms: A list of key legal terms or phrases found in the clause
- risk_level: A string indicating the risk level: "Low", "Medium", "High"
- summary: A brief summary of the clause's purpose and implications
- recommendations: A list of recommendations for improving or mitigating risks in the clause

Clause text: {clause_text}

Respond only with valid JSON, no additional text.
"""

def run_model(user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="google/gemma-3-12b-it",
            messages=[{"role": "user", "content": user_message}],
            temperature=0.7,
            top_p=0.7,
            frequency_penalty=1,
            max_tokens=512,
        )
        return response.choices[0].message.content
    except Exception as e:
        print("AI error:", str(e))
        return f"⚠️ Error: {str(e)}"

def analyze_clause_with_chatgpt(clause_text: str) -> Dict[str, Any]:
    """
    Sends clause text to ChatGPT API and returns structured analysis.

    Args:
        clause_text (str): The text of the contract clause to analyze.

    Returns:
        Dict[str, Any]: Dictionary containing clause_type, key_terms, risk_level, summary, recommendations.
    """
    try:
        # Prepare the prompt
        prompt = LEGAL_ANALYSIS_PROMPT.format(clause_text=clause_text)

        # Call OpenAI API with timeout
        response = client.chat.completions.create(
            model="google/gemma-3-12b-it",
            messages=[
                {"role": "system", "content": "You are a legal expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.2,
            timeout=30  # 30 seconds timeout
        )

        # Extract the response content
        content = response.choices[0].message['content'].strip()

        # Parse JSON response
        result = json.loads(content)

        # Validate required fields
        required_fields = ['clause_type', 'key_terms', 'risk_level', 'summary', 'recommendations']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")

        return result

    except Exception as e:
        # Handle unexpected errors
        return {
            "error": f"Unexpected error: {str(e)}",
            "clause_type": "Unknown",
            "key_terms": [],
            "risk_level": "Unknown",
            "summary": "Analysis failed.",
            "recommendations": ["Contact support."]
        }
