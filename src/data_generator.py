"""Synthetic financial data generation using Faker."""

import json
import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Base amount ranges calibrated to California cost of living (COL index 142.3)
# Other states are scaled relative to CA using their COL index
AMOUNT_RANGES = {
    "Rent": (2200, 3200),
    "Mortgage": (2800, 4200),
    "Property Tax": (400, 800),
    "Home Insurance": (150, 300),
    "HOA Fees": (250, 550),
    "Gasoline": (120, 200),
    "Car Payment": (400, 700),
    "Auto Insurance": (155, 250),
    "Public Transit": (75, 150),
    "Parking": (15, 50),
    "Groceries": (80, 200),
    "Restaurants": (30, 100),
    "Coffee Shops": (5, 10),
    "Fast Food": (10, 22),
    "Electric": (120, 200),
    "Water": (60, 100),
    "Natural Gas": (45, 90),
    "Internet": (60, 100),
    "Phone": (50, 110),
    "Health Insurance": (350, 600),
    "Prescriptions": (15, 100),
    "Doctor Visits": (75, 350),
    "Dental": (100, 300),
    "Streaming Services": (12, 25),
    "Movies": (18, 40),
    "Concerts": (60, 200),
    "Hobbies": (20, 100),
    "Clothing": (30, 180),
    "Electronics": (40, 600),
    "Home Goods": (20, 120),
    "Personal Care": (15, 60),
    "Credit Card Payment": (150, 500),
    "Loan Payment": (250, 700),
    "Investment Contribution": (200, 1200),
    "Bonus": (2000, 8000),
    "Freelance": (300, 2500),
    "Interest": (5, 60),
    "Dividends": (50, 400),
    "Rental Income": (1500, 3000),
}

CA_COL_INDEX = 142.3  # AMOUNT_RANGES are calibrated to this baseline


def load_state_config(config_path, state_code):
    """Load state-specific configuration from states.json."""
    with open(config_path, "r") as f:
        all_states = json.load(f)
    state_code = state_code.upper()
    if state_code not in all_states:
        available = ", ".join(sorted(all_states.keys()))
        raise ValueError(f"State '{state_code}' not found. Available: {available}")
    return all_states[state_code]


def _get_col_factor(state_config):
    """Get cost-of-living scaling factor relative to the CA baseline."""
    return state_config["cost_of_living_index"] / CA_COL_INDEX


def _scale_range(low, high, col_factor):
    """Scale an amount range by a cost-of-living factor."""
    return (low * col_factor, high * col_factor)

# Categories that recur monthly
RECURRING_SUBCATEGORIES = {
    "Rent", "Mortgage", "Property Tax", "Home Insurance", "HOA Fees",
    "Car Payment", "Auto Insurance", "Health Insurance",
    "Electric", "Water", "Natural Gas", "Internet", "Phone",
    "Streaming Services",
    "Credit Card Payment", "Loan Payment", "Investment Contribution",
    "Salary",
}

# Merchant name templates by subcategory
MERCHANT_TEMPLATES = {
    "Rent": ["Property Management Co", "Apartment Living LLC"],
    "Mortgage": ["National Mortgage Corp", "HomeFirst Lending"],
    "Property Tax": ["County Tax Office"],
    "Home Insurance": ["State Farm", "Allstate Home"],
    "HOA Fees": ["Community HOA"],
    "Gasoline": ["Shell", "Chevron", "BP", "ExxonMobil"],
    "Car Payment": ["Toyota Financial", "Honda Financial", "Ford Credit"],
    "Auto Insurance": ["GEICO", "Progressive", "State Farm Auto"],
    "Public Transit": ["Metro Transit", "City Bus Authority"],
    "Parking": ["ParkMobile", "SpotHero"],
    "Groceries": ["Kroger", "Whole Foods", "Trader Joe's", "Walmart", "Safeway", "Aldi"],
    "Restaurants": None,  # will use Faker
    "Coffee Shops": ["Starbucks", "Dunkin'", "Peet's Coffee", "Local Brew"],
    "Fast Food": ["McDonald's", "Chick-fil-A", "Chipotle", "Subway", "Wendy's"],
    "Electric": ["City Electric Utility", "Power & Light Co"],
    "Water": ["Municipal Water", "City Water Dept"],
    "Natural Gas": ["City Gas Company", "National Gas Utility"],
    "Internet": ["Comcast Xfinity", "AT&T Internet", "Spectrum"],
    "Phone": ["Verizon Wireless", "T-Mobile", "AT&T Wireless"],
    "Health Insurance": ["Blue Cross Blue Shield", "UnitedHealthcare", "Aetna"],
    "Prescriptions": ["CVS Pharmacy", "Walgreens", "Rite Aid"],
    "Doctor Visits": ["Primary Care Associates", "City Medical Group"],
    "Dental": ["Bright Smile Dental", "Family Dentistry"],
    "Streaming Services": ["Netflix", "Spotify", "Hulu", "Disney+", "HBO Max"],
    "Movies": ["AMC Theatres", "Regal Cinemas"],
    "Concerts": ["Ticketmaster", "Live Nation", "StubHub"],
    "Hobbies": None,
    "Clothing": ["Target", "H&M", "Nordstrom", "Old Navy", "Nike"],
    "Electronics": ["Best Buy", "Amazon", "Apple Store"],
    "Home Goods": ["Target Home", "IKEA", "Bed Bath & Beyond", "HomeDepot"],
    "Personal Care": ["Ulta Beauty", "Bath & Body Works", "Target Beauty"],
    "Credit Card Payment": ["Visa Payment", "Mastercard Payment", "Amex Payment"],
    "Loan Payment": ["Student Loan Corp", "LendingClub"],
    "Investment Contribution": ["Vanguard", "Fidelity", "Charles Schwab"],
    "Salary": ["Employer Direct Deposit"],
    "Bonus": ["Employer Bonus"],
    "Freelance": None,
    "Interest": ["Bank Interest"],
    "Dividends": ["Investment Dividends"],
    "Rental Income": ["Tenant Payment"],
}


def generate_users(num_users=3, state_config=None):
    """Generate realistic user profiles with income based on state middle class range."""
    income_min, income_max = 63000, 191000  # fallback
    if state_config:
        income_min, income_max = state_config["middle_class_income"]
    users = []
    for i in range(1, num_users + 1):
        users.append({
            "user_id": i,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "date_joined": fake.date_between(start_date="-3y", end_date="-1y").isoformat(),
            "annual_income": round(random.uniform(income_min, income_max), 2),
        })
    return pd.DataFrame(users)


def generate_categories(config_path):
    """Load categories from config and build category records with parent-child relationships."""
    with open(config_path, "r") as f:
        config = json.load(f)

    categories = []
    cat_id = 1

    for parent, subcats in config["expense_categories"].items():
        for sub in subcats:
            categories.append({
                "category_id": cat_id,
                "category_name": sub,
                "parent_category": parent,
                "category_type": "expense",
            })
            cat_id += 1

    for parent, subcats in config["income_categories"].items():
        for sub in subcats:
            categories.append({
                "category_id": cat_id,
                "category_name": sub,
                "parent_category": parent,
                "category_type": "income",
            })
            cat_id += 1

    return pd.DataFrame(categories)


def generate_merchants(categories_df, num_merchants=100):
    """Create merchants assigned to appropriate categories."""
    merchants = []
    merchant_id = 1

    for _, cat in categories_df.iterrows():
        sub = cat["category_name"]
        templates = MERCHANT_TEMPLATES.get(sub)
        is_recurring = sub in RECURRING_SUBCATEGORIES

        if templates is None:
            # Generate random merchant names
            count = random.randint(2, 4)
            for _ in range(count):
                merchants.append({
                    "merchant_id": merchant_id,
                    "merchant_name": fake.company(),
                    "category_id": cat["category_id"],
                    "is_recurring": is_recurring,
                })
                merchant_id += 1
        else:
            for name in templates:
                merchants.append({
                    "merchant_id": merchant_id,
                    "merchant_name": name,
                    "category_id": cat["category_id"],
                    "is_recurring": is_recurring,
                })
                merchant_id += 1

    return pd.DataFrame(merchants)


def generate_accounts(users_df):
    """Create 2-4 bank/credit accounts per user."""
    accounts = []
    account_id = 1

    account_templates = [
        ("checking", "Primary Checking", 1500, 8000),
        ("savings", "Savings Account", 2000, 25000),
        ("credit_card", "Rewards Credit Card", -3000, 0),
        ("checking", "Secondary Checking", 500, 3000),
    ]

    bank_names = ["Chase", "Bank of America", "Wells Fargo", "Capital One", "Citi"]

    for _, user in users_df.iterrows():
        num_accounts = random.randint(2, 4)
        selected = random.sample(account_templates, num_accounts)
        for acct_type, acct_name, bal_low, bal_high in selected:
            accounts.append({
                "account_id": account_id,
                "user_id": user["user_id"],
                "account_type": acct_type,
                "account_name": acct_name,
                "bank_name": random.choice(bank_names),
                "current_balance": round(random.uniform(bal_low, bal_high), 2),
                "created_date": user["date_joined"],
            })
            account_id += 1

    return pd.DataFrame(accounts)


def _estimate_monthly_takehome(annual_income, state_config):
    """Estimate monthly take-home pay using federal + state tax brackets."""
    # Approximate effective federal tax rate by income bracket
    if annual_income <= 44725:
        federal_rate = 0.12
    elif annual_income <= 95375:
        federal_rate = 0.17
    elif annual_income <= 182100:
        federal_rate = 0.22
    else:
        federal_rate = 0.26

    # State tax rate from brackets (use highest bracket the income falls into)
    state_rate = 0.0
    for bracket in state_config["state_tax_brackets"]:
        if annual_income >= bracket["min_income"]:
            state_rate = bracket["rate"]

    # FICA (Social Security 6.2% + Medicare 1.45%)
    fica_rate = 0.0765

    total_tax_rate = federal_rate + state_rate + fica_rate
    annual_takehome = annual_income * (1 - total_tax_rate)
    return round(annual_takehome / 12, 2)


def generate_transactions(accounts_df, merchants_df, categories_df, users_df,
                          state_config=None, months=12):
    """Generate 12 months of realistic transactions with recurring, weekly, and random patterns."""
    transactions = []
    txn_id = 1
    today = datetime.now().date()
    start_date = today.replace(day=1) - timedelta(days=months * 30)

    # Cost-of-living scaling relative to CA baseline
    col_factor = _get_col_factor(state_config) if state_config else 1.0
    income_min, income_max = (state_config["middle_class_income"]
                              if state_config else [63000, 191000])

    # Build lookups
    expense_cats = categories_df[categories_df["category_type"] == "expense"]
    income_cats = categories_df[categories_df["category_type"] == "income"]

    for _, account in accounts_df.iterrows():
        user_accounts = accounts_df[accounts_df["user_id"] == account["user_id"]]
        # Only generate from one account per user to avoid duplication
        if account["account_id"] != user_accounts.iloc[0]["account_id"]:
            continue

        # Derive salary and spending scale from the user's actual annual income
        user_id = account["user_id"]
        annual_income = users_df[users_df["user_id"] == user_id].iloc[0]["annual_income"]
        user_salary = _estimate_monthly_takehome(annual_income, state_config or {
            "state_tax_brackets": []})

        # Income factor scales expenses relative to income position (0.6x to 1.4x)
        income_pct = (annual_income - income_min) / (income_max - income_min)
        income_factor = 0.6 + income_pct * 0.8  # range: 0.6 to 1.4

        # Assign housing profile: renters get Rent only, homeowners get Mortgage + extras
        # Higher earners are more likely to own
        is_homeowner = random.random() < (0.3 + income_pct * 0.5)
        if is_homeowner:
            skip_housing = {"Rent"}
        else:
            skip_housing = {"Mortgage", "Property Tax", "Home Insurance", "HOA Fees"}

        for month_offset in range(months):
            month_start = start_date + timedelta(days=month_offset * 30)
            month_num = month_start.month

            # Seasonal multipliers by category type
            # Holiday shopping surge in Nov-Dec, summer entertainment bump,
            # winter utility costs, post-holiday dip in January
            def get_season_mult(cat_name, parent_cat):
                # Shopping categories: Black Friday (Nov) + holiday gifts (Dec)
                if parent_cat == "Shopping":
                    if month_num == 11:
                        return random.uniform(1.5, 2.0)  # Black Friday
                    elif month_num == 12:
                        return random.uniform(1.8, 2.5)  # Holiday gifts
                    elif month_num == 1:
                        return random.uniform(0.6, 0.8)  # Post-holiday pullback
                    return 1.0

                # Food: more dining out during holidays and summer
                if parent_cat == "Food":
                    if month_num in (11, 12):
                        return random.uniform(1.2, 1.5)  # Holiday meals/parties
                    elif month_num in (6, 7, 8):
                        return random.uniform(1.1, 1.3)  # Summer socializing
                    return 1.0

                # Entertainment: summer + holiday bumps
                if parent_cat == "Entertainment":
                    if month_num in (6, 7, 8):
                        return random.uniform(1.3, 1.6)  # Summer activities
                    elif month_num == 12:
                        return random.uniform(1.2, 1.5)  # Holiday events
                    elif month_num in (1, 2):
                        return random.uniform(0.7, 0.9)  # Winter slowdown
                    return 1.0

                # Utilities: higher electric in summer (AC), higher gas in winter
                if cat_name == "Electric":
                    if month_num in (7, 8):
                        return random.uniform(1.4, 1.8)  # AC costs
                    elif month_num in (3, 4, 10):
                        return random.uniform(0.8, 0.9)  # Mild weather
                    return 1.0
                if cat_name == "Natural Gas":
                    if month_num in (12, 1, 2):
                        return random.uniform(1.5, 2.0)  # Heating costs
                    elif month_num in (6, 7, 8):
                        return random.uniform(0.4, 0.6)  # Minimal heating
                    return 1.0

                # Transportation: summer road trips
                if cat_name == "Gasoline":
                    if month_num in (6, 7, 8):
                        return random.uniform(1.2, 1.4)  # Summer driving
                    return 1.0

                return 1.0

            # --- Recurring monthly expenses ---
            for _, cat in expense_cats.iterrows():
                if cat["category_name"] in RECURRING_SUBCATEGORIES:
                    # Skip housing categories that don't match this user's profile
                    if cat["category_name"] in skip_housing:
                        continue
                    cat_merchants = merchants_df[merchants_df["category_id"] == cat["category_id"]]
                    if cat_merchants.empty:
                        continue
                    merchant = cat_merchants.iloc[0]
                    low, high = AMOUNT_RANGES.get(cat["category_name"], (50, 200))
                    mult = get_season_mult(cat["category_name"], cat["parent_category"])
                    amount = -round(random.uniform(low, high) * mult * income_factor * col_factor, 2)
                    txn_date = month_start + timedelta(days=random.randint(0, 5))
                    if txn_date > today:
                        continue
                    transactions.append({
                        "transaction_id": txn_id,
                        "account_id": account["account_id"],
                        "merchant_id": merchant["merchant_id"],
                        "category_id": cat["category_id"],
                        "transaction_date": txn_date.isoformat(),
                        "amount": amount,
                        "description": f"{merchant['merchant_name']} - {cat['category_name']}",
                        "is_recurring": True,
                    })
                    txn_id += 1

            # --- Weekly expenses (groceries, coffee, gas) ---
            weekly_cats = ["Groceries", "Coffee Shops", "Gasoline"]
            for cat_name in weekly_cats:
                cat_row = expense_cats[expense_cats["category_name"] == cat_name]
                if cat_row.empty:
                    continue
                cat_row = cat_row.iloc[0]
                cat_merchants = merchants_df[merchants_df["category_id"] == cat_row["category_id"]]
                if cat_merchants.empty:
                    continue
                low, high = AMOUNT_RANGES.get(cat_name, (10, 50))
                mult = get_season_mult(cat_name, cat_row["parent_category"])
                for week in range(4):
                    txn_date = month_start + timedelta(days=week * 7 + random.randint(0, 2))
                    if txn_date > today:
                        continue
                    merchant = cat_merchants.sample(1).iloc[0]
                    amount = -round(random.uniform(low, high) * mult * income_factor * col_factor, 2)
                    transactions.append({
                        "transaction_id": txn_id,
                        "account_id": account["account_id"],
                        "merchant_id": merchant["merchant_id"],
                        "category_id": cat_row["category_id"],
                        "transaction_date": txn_date.isoformat(),
                        "amount": amount,
                        "description": f"{merchant['merchant_name']}",
                        "is_recurring": False,
                    })
                    txn_id += 1

            # --- Random purchases (restaurants, shopping, entertainment) ---
            random_cats = ["Restaurants", "Fast Food", "Clothing", "Electronics",
                           "Home Goods", "Personal Care", "Movies", "Concerts", "Hobbies"]
            # More random purchases during holiday months, fewer in Jan
            if month_num in (11, 12):
                num_random = random.randint(10, 20)
            elif month_num == 1:
                num_random = random.randint(3, 8)
            else:
                num_random = random.randint(5, 15)
            for _ in range(num_random):
                cat_name = random.choice(random_cats)
                cat_row = expense_cats[expense_cats["category_name"] == cat_name]
                if cat_row.empty:
                    continue
                cat_row = cat_row.iloc[0]
                cat_merchants = merchants_df[merchants_df["category_id"] == cat_row["category_id"]]
                if cat_merchants.empty:
                    continue
                merchant = cat_merchants.sample(1).iloc[0]
                low, high = AMOUNT_RANGES.get(cat_name, (10, 100))
                mult = get_season_mult(cat_name, cat_row["parent_category"])
                amount = -round(random.uniform(low, high) * mult * income_factor * col_factor, 2)
                txn_date = month_start + timedelta(days=random.randint(0, 29))
                if txn_date > today:
                    continue
                transactions.append({
                    "transaction_id": txn_id,
                    "account_id": account["account_id"],
                    "merchant_id": merchant["merchant_id"],
                    "category_id": cat_row["category_id"],
                    "transaction_date": txn_date.isoformat(),
                    "amount": amount,
                    "description": f"{merchant['merchant_name']}",
                    "is_recurring": False,
                })
                txn_id += 1

            # --- Income: biweekly salary (consistent per user) ---
            salary_cat = income_cats[income_cats["category_name"] == "Salary"]
            if not salary_cat.empty:
                salary_cat = salary_cat.iloc[0]
                salary_merchants = merchants_df[merchants_df["category_id"] == salary_cat["category_id"]]
                if not salary_merchants.empty:
                    merchant = salary_merchants.iloc[0]
                    for pay_day in [15, 30]:
                        txn_date = month_start + timedelta(days=min(pay_day, 28))
                        if txn_date > today:
                            continue
                        transactions.append({
                            "transaction_id": txn_id,
                            "account_id": account["account_id"],
                            "merchant_id": merchant["merchant_id"],
                            "category_id": salary_cat["category_id"],
                            "transaction_date": txn_date.isoformat(),
                            "amount": user_salary,
                            "description": "Direct Deposit - Salary",
                            "is_recurring": True,
                        })
                        txn_id += 1

            # --- Year-end bonus in December ---
            if month_num == 12:
                bonus_cat = income_cats[income_cats["category_name"] == "Bonus"]
                if not bonus_cat.empty:
                    bonus_cat = bonus_cat.iloc[0]
                    bonus_merchants = merchants_df[merchants_df["category_id"] == bonus_cat["category_id"]]
                    if not bonus_merchants.empty:
                        merchant = bonus_merchants.iloc[0]
                        bonus_amt = round(user_salary * random.uniform(0.5, 1.5), 2)
                        txn_date = month_start + timedelta(days=random.randint(10, 20))
                        if txn_date <= today:
                            transactions.append({
                                "transaction_id": txn_id,
                                "account_id": account["account_id"],
                                "merchant_id": merchant["merchant_id"],
                                "category_id": bonus_cat["category_id"],
                                "transaction_date": txn_date.isoformat(),
                                "amount": bonus_amt,
                                "description": "Year-End Bonus",
                                "is_recurring": False,
                            })
                            txn_id += 1

    return pd.DataFrame(transactions)


def generate_budgets(users_df, categories_df, state_config=None, months=6):
    """Create monthly budgets for the last 6 months for expense categories."""
    budgets = []
    budget_id = 1
    today = datetime.now().date()
    col_factor = _get_col_factor(state_config) if state_config else 1.0
    income_min, income_max = (state_config["middle_class_income"]
                              if state_config else [63000, 191000])

    expense_parents = categories_df[
        (categories_df["category_type"] == "expense") &
        (categories_df["parent_category"].isin(["Housing", "Food", "Transportation",
                                                  "Utilities", "Entertainment", "Shopping"]))
    ]

    # Pick a subset of categories to budget for
    budget_cats = expense_parents.drop_duplicates("parent_category")

    for _, user in users_df.iterrows():
        income_pct = (user["annual_income"] - income_min) / (income_max - income_min)
        user_income_factor = 0.6 + income_pct * 0.8
        for month_offset in range(months):
            month_date = today.replace(day=1) - timedelta(days=month_offset * 30)
            month_year = month_date.strftime("%Y-%m")
            for _, cat in budget_cats.iterrows():
                low, high = AMOUNT_RANGES.get(cat["category_name"], (100, 500))
                budget_amount = round(random.uniform(low, high) * 1.1 * user_income_factor * col_factor, 2)
                budgets.append({
                    "budget_id": budget_id,
                    "user_id": user["user_id"],
                    "category_id": cat["category_id"],
                    "month_year": month_year,
                    "budget_amount": budget_amount,
                    "notes": None,
                })
                budget_id += 1

    return pd.DataFrame(budgets)


def generate_financial_goals(users_df):
    """Generate 2-3 financial goals per user."""
    goals = []
    goal_id = 1
    today = datetime.now().date()

    goal_templates = [
        ("Emergency Fund", "savings", 10000, 25000),
        ("Vacation Fund", "savings", 2000, 5000),
        ("Pay Off Student Loans", "debt_payoff", 10000, 40000),
        ("Pay Off Credit Card", "debt_payoff", 2000, 8000),
        ("Retirement Savings", "investment", 50000, 200000),
        ("Investment Portfolio", "investment", 10000, 50000),
    ]

    for _, user in users_df.iterrows():
        num_goals = random.randint(2, 3)
        selected = random.sample(goal_templates, num_goals)
        for name, category, target_low, target_high in selected:
            target = round(random.uniform(target_low, target_high), 2)
            current = round(random.uniform(0, target * 0.6), 2)
            target_date = today + timedelta(days=random.randint(180, 1095))
            goals.append({
                "goal_id": goal_id,
                "user_id": user["user_id"],
                "goal_name": name,
                "target_amount": target,
                "current_amount": current,
                "target_date": target_date.isoformat(),
                "category": category,
            })
            goal_id += 1

    return pd.DataFrame(goals)


def save_synthetic_data(data_dict, output_path):
    """Save all DataFrames to CSV for review before database insert."""
    os.makedirs(output_path, exist_ok=True)
    for name, df in data_dict.items():
        filepath = os.path.join(output_path, f"{name}.csv")
        df.to_csv(filepath, index=False)
        print(f"  Saved {name}: {len(df)} rows -> {filepath}")
