"""LLM-powered expense realism adjuster for FinanceIQ Pro mode.

Calls the Anthropic Claude API to generate realistic expense adjustments
based on the user's demographic profile and state of residence.
Falls back to rule-based adjustments if the API call fails.
"""

import json
import os


def get_expense_adjustments(profile, state):
    """Get LLM-generated expense adjustments based on the demographic profile.

    Parameters:
        profile: dict from build_profile() — only non-None fields are described
        state: 2-letter state code

    Returns:
        dict with 'category_multipliers' and 'reasoning' keys,
        or the rule-based expense_adjustments from the profile on failure.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [LLM] No ANTHROPIC_API_KEY found — using rule-based adjustments.")
        return profile.get("expense_adjustments", {})

    # Build a plain-English description using ONLY non-None fields
    description_parts = []
    description_parts.append(f"State of residence: {state}")

    if profile.get("age") is not None:
        description_parts.append(f"Age: {profile['age']}")

    if profile.get("is_married") is not None:
        status = "married" if profile["is_married"] else "single"
        description_parts.append(f"Marital status: {status}")

    if profile.get("dual_income") is not None:
        dual = "yes" if profile["dual_income"] else "no"
        description_parts.append(f"Dual-income household: {dual}")

    if profile.get("num_children") is not None:
        description_parts.append(f"Number of children: {profile['num_children']}")

    if profile.get("child_ages") is not None:
        ages_str = ", ".join(str(a) for a in profile["child_ages"])
        description_parts.append(f"Children's ages: {ages_str}")

    if profile.get("race") is not None:
        description_parts.append(f"Race: {profile['race']}")

    if profile.get("ethnicity") is not None:
        description_parts.append(f"Ethnicity: {profile['ethnicity']}")

    if profile.get("gender") is not None:
        description_parts.append(f"Gender: {profile['gender']}")

    person_description = "\n".join(f"- {p}" for p in description_parts)

    prompt = f"""You are a financial data modeling assistant. Given the following demographic profile, produce realistic expense adjustment factors for a synthetic personal finance simulator.

Profile:
{person_description}

The system already has a middle-class baseline for {state} with cost-of-living scaling applied. Your multipliers adjust categories RELATIVE to that existing baseline (1.0 = no change).

For purely additive line items that don't exist in the baseline (like childcare or education), provide absolute monthly dollar amounts instead of multipliers.

Respond with ONLY valid JSON, no markdown fences, no preamble, no explanation outside the JSON:
{{
  "category_multipliers": {{
    "groceries": <float multiplier>,
    "dining_out": <float multiplier>,
    "transportation": <float multiplier>,
    "entertainment": <float multiplier>,
    "shopping": <float multiplier>,
    "utilities": <float multiplier>,
    "healthcare": <float multiplier>,
    "childcare": <float absolute monthly $ or 0>,
    "education": <float absolute monthly $ or 0>
  }},
  "reasoning": "<one sentence explaining the key adjustments>"
}}"""

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        print("  [LLM] Sending profile to Claude API for expense adjustment...")
        print(f"\n  --- Prompt sent to API ---\n{prompt}\n  --- End prompt ---\n")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text
        print(f"  --- Raw API response ---\n{raw_text}\n  --- End response ---\n")

        result = json.loads(raw_text)

        if "category_multipliers" not in result:
            raise ValueError("Missing 'category_multipliers' in response")

        return result

    except Exception as e:
        print(f"  [LLM] WARNING: API call failed ({e}) — falling back to rule-based adjustments.")
        return profile.get("expense_adjustments", {})
