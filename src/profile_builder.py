"""Profile builder for FinanceIQ Pro mode.

Constructs a demographic profile dict based on toggled-on factors.
IRONCLAD RULE: if a parameter is None, it is never used as input to any
other calculation and is never inferred or assumed.
"""

import json
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOGRAPHICS_PATH = os.path.join(BASE_DIR, "config", "demographics.json")


def _load_demographics():
    with open(DEMOGRAPHICS_PATH, "r") as f:
        return json.load(f)


def _age_to_bucket(age):
    """Convert a numeric age to the bucket string used in demographics.json."""
    if age < 25:
        return "18-24"
    elif age < 30:
        return "25-29"
    elif age < 35:
        return "30-34"
    elif age < 40:
        return "35-39"
    elif age < 45:
        return "40-44"
    elif age < 55:
        return "45-54"
    else:
        return "55+"


def _sample_age(state_code, demo):
    """Sample a random age from the state's age distribution."""
    dist = demo["age_distribution"].get(state_code)
    if not dist:
        return random.randint(25, 55)
    buckets = []
    weights = []
    for bucket, weight in dist.items():
        if bucket.startswith("_"):
            continue
        buckets.append(bucket)
        weights.append(weight)
    chosen = random.choices(buckets, weights=weights, k=1)[0]
    # Sample a uniform age within the chosen bucket
    bucket_ranges = {
        "18-24": (18, 24), "25-29": (25, 29), "30-34": (30, 34),
        "35-39": (35, 39), "40-44": (40, 44), "45-54": (45, 54),
        "55+": (55, 70),
    }
    low, high = bucket_ranges.get(chosen, (25, 55))
    return random.randint(low, high)


def _sample_marriage(state_code, age, demo):
    """Sample marriage status. age may be None."""
    rates = demo["marriage_rate_by_age"].get(state_code, {})
    if age is not None:
        bucket = _age_to_bucket(age)
        rate = rates.get(bucket, 0.45)
    else:
        # Average across all buckets for the state
        vals = [v for k, v in rates.items() if not k.startswith("_")]
        rate = sum(vals) / len(vals) if vals else 0.45
    return random.random() < rate


def _sample_num_children(state_code, age, is_married, demo):
    """Sample number of children using CDC fertility data.

    Handles every combination of None explicitly:
      age known + married known -> age-and-status-specific rate
      age known + married None  -> age-specific all-statuses-combined rate
      age None  + married known -> all-ages rate for that marital status
      age None  + married None  -> pure state-wide baseline rate
    """
    fertility = demo["fertility_by_age_and_status"].get(state_code, {})

    if age is not None and is_married is not None:
        # Both known: age-and-status-specific rate
        bucket = _age_to_bucket(age)
        status_key = "married" if is_married else "single"
        rate = fertility.get(status_key, {}).get(bucket, 1.0)
    elif age is not None and is_married is None:
        # Age known, marriage unknown: all-statuses-combined rate
        bucket = _age_to_bucket(age)
        rate = fertility.get("all", {}).get(bucket, 1.0)
    elif age is None and is_married is not None:
        # Marriage known, age unknown: average across all age buckets for status
        status_key = "married" if is_married else "single"
        status_data = fertility.get(status_key, {})
        vals = [v for k, v in status_data.items() if not k.startswith("_")]
        rate = sum(vals) / len(vals) if vals else 1.0
    else:
        # Both unknown: state-wide baseline
        rate = fertility.get("baseline", 1.6)

    # Poisson sampling from the rate
    return int(random.expovariate(1.0 / max(rate, 0.1))) if rate > 0 else 0


def _sample_social(state_code, demo):
    """Sample race, ethnicity, and gender from state demographics."""
    state_demo = demo["state_demographics"].get(state_code, {})
    race_dist = state_demo.get("race", {"white": 1.0})
    gender_dist = state_demo.get("gender", {"male": 0.5, "female": 0.5})

    race = random.choices(list(race_dist.keys()), weights=list(race_dist.values()), k=1)[0]
    gender = random.choices(list(gender_dist.keys()), weights=list(gender_dist.values()), k=1)[0]

    # Map race to ethnicity label
    ethnicity = "hispanic" if race == "hispanic" else "non-hispanic"

    return race, ethnicity, gender


def _get_wage_multiplier(race, gender, demo):
    """Look up BLS wage multiplier for a race/gender combination."""
    multipliers = demo.get("wage_multipliers", {})
    key = f"{race}_{gender}"
    return multipliers.get(key, 0.85)


def build_profile(state, age=None, marriage=None, kids=None, social=None):
    """Build a demographic profile dict for data generation.

    Parameters:
        state: 2-letter state code (required)
        age: int or None (None = toggle OFF)
        marriage: dict with keys 'is_married' (bool/None), 'dual_income' (bool/None)
                  or None (None = toggle OFF)
        kids: dict with keys 'num_children' (int/None), 'child_ages' (list/None)
              or None (None = toggle OFF)
        social: dict with keys 'race' (str/None), 'ethnicity' (str/None),
                'gender' (str/None) or None (None = toggle OFF)

    Returns a profile dict.
    """
    demo = _load_demographics()
    state_code = state.upper()

    # --- Age ---
    if age is not None:
        resolved_age = age
    else:
        resolved_age = None

    # --- Marriage ---
    if marriage is not None:
        user_married = marriage.get("is_married")
        if user_married is None:
            # User toggled marriage ON but wants random
            resolved_married = _sample_marriage(state_code, resolved_age, demo)
        else:
            resolved_married = user_married

        user_dual = marriage.get("dual_income")
        if user_dual is None and resolved_married:
            resolved_dual = random.choice([True, False])
        elif resolved_married:
            resolved_dual = user_dual
        else:
            resolved_dual = None
    else:
        resolved_married = None
        resolved_dual = None

    # --- Kids ---
    if kids is not None:
        user_num = kids.get("num_children")
        user_ages = kids.get("child_ages")

        if user_num is not None:
            resolved_num_children = user_num
        else:
            resolved_num_children = _sample_num_children(
                state_code, resolved_age, resolved_married, demo
            )

        if user_ages is not None:
            resolved_child_ages = list(user_ages)
        else:
            resolved_child_ages = [random.randint(1, 18) for _ in range(resolved_num_children)]
    else:
        resolved_num_children = None
        resolved_child_ages = None

    # --- Social factors ---
    if social is not None:
        user_race = social.get("race")
        user_ethnicity = social.get("ethnicity")
        user_gender = social.get("gender")

        if user_race is None or user_gender is None:
            sampled_race, sampled_ethnicity, sampled_gender = _sample_social(state_code, demo)
            resolved_race = user_race if user_race is not None else sampled_race
            resolved_gender = user_gender if user_gender is not None else sampled_gender
            resolved_ethnicity = user_ethnicity if user_ethnicity is not None else sampled_ethnicity
        else:
            resolved_race = user_race
            resolved_gender = user_gender
            resolved_ethnicity = user_ethnicity if user_ethnicity is not None else (
                "hispanic" if resolved_race == "hispanic" else "non-hispanic"
            )

        income_weight = _get_wage_multiplier(resolved_race, resolved_gender, demo)
    else:
        resolved_race = None
        resolved_ethnicity = None
        resolved_gender = None
        income_weight = 1.0

    # --- Expense adjustments (rule-based) ---
    expense_adjustments = {}
    if resolved_child_ages is not None:
        childcare_cost = sum(1800 for a in resolved_child_ages if a < 5)
        education_cost = sum(400 for a in resolved_child_ages if 5 <= a <= 17)
        if childcare_cost > 0:
            expense_adjustments["childcare"] = childcare_cost
        if education_cost > 0:
            expense_adjustments["education"] = education_cost

    if resolved_dual is True:
        expense_adjustments["transportation_multiplier"] = 1.15

    return {
        "age": resolved_age,
        "is_married": resolved_married,
        "dual_income": resolved_dual,
        "num_children": resolved_num_children,
        "child_ages": resolved_child_ages,
        "race": resolved_race,
        "ethnicity": resolved_ethnicity,
        "gender": resolved_gender,
        "income_weight": income_weight,
        "expense_adjustments": expense_adjustments,
    }
