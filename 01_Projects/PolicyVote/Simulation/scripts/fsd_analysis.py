"""
Finnish Social Science Data Archive (FSD) Analysis Module

Analyzes Finnish survey data to extract voter segment profiles
for use in the PolicyVote election simulation.

Supports:
- FSD4022 Kansalaispulssi (Citizen's Pulse) - issue priorities, trust, attitudes
- FSD3467/FSD3875 FNES (when available) - party vote, political positions

Data source: Finnish Social Science Data Archive (FSD)
Download from: https://services.fsd.tuni.fi/
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
from typing import Optional

# Try to import pandas/numpy for advanced analysis
try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Note: Install pandas for advanced analysis: pip install pandas")


# Variable mappings for Kansalaispulssi (FSD4022)
KANSALAISPULSSI_DEMOGRAPHICS = {
    't1': 'gender',      # 1=Mies, 2=Nainen, 3=Muu
    't2': 'age_group',   # 1-12 (under 20 to 70+)
    't3': 'region',      # 1-18 (maakunnat)
    'T4': 'education',   # 1-5 (peruskoulu to ylempi korkeakoulu)
    'T7': 'economic',    # 1-5 (varakas to pienituloinen)
}

KANSALAISPULSSI_PRIORITIES = {
    'q55_1': 'fiscal_sustainability',   # Kestävä julkinen talous
    'q55_2': 'employment',              # Työllisyyden parantaminen
    'q55_3': 'business_conditions',     # Yritysten toimintaedellytykset
    'q55_4': 'climate_action',          # Ilmastotoimien edistäminen
    'q55_5': 'biodiversity',            # Luontokadon ehkäiseminen
    'q55_6': 'healthcare',              # Toimiva terveydenhuolto
    'q55_7': 'education',               # Laadukas koulutus
    'q55_8': 'poverty_reduction',       # Köyhyyden vähentäminen
    'q55_9': 'exclusion_prevention',    # Syrjäytymisen ehkäiseminen
    'q55_10': 'equality',               # Ihmisten yhdenvertaisuus
    'q55_11': 'daily_security',         # Arjen turvallisuus
    'q55_12': 'defense',                # Sotilaallinen maanpuolustus
}

KANSALAISPULSSI_TRUST = {
    'q11k': 'trust_government',
    'q11l': 'trust_municipal',
    'q11m': 'trust_parliament',
    'q11n': 'trust_courts',
    'q11o': 'trust_parties',
    'q11p': 'trust_police',
    'q11q': 'trust_healthcare',
    'q11r': 'trust_education',
    'q11s': 'trust_admin',
    'q11t': 'trust_media',
    'q11x': 'trust_defense',
    'q11y': 'trust_eu',
    'q11z': 'trust_nato',
    'q11aa': 'trust_us',
}

AGE_GROUP_LABELS = {
    1: 'Under 20',
    2: '20-24',
    3: '25-29',
    4: '30-34',
    5: '35-39',
    6: '40-44',
    7: '45-49',
    8: '50-54',
    9: '55-59',
    10: '60-64',
    11: '65-69',
    12: '70+',
}

EDUCATION_LABELS = {
    1: 'Basic (peruskoulu)',
    2: 'Secondary (lukio/ammatti)',
    3: 'Lower degree (AMK)',
    4: 'Higher degree (yliopisto)',
    5: 'Other',
}


def load_kansalaispulssi_csv(data_path: str) -> list[dict]:
    """Load Kansalaispulssi data from CSV.

    Args:
        data_path: Path to daF4022_fin.csv

    Returns:
        List of respondent dictionaries
    """
    respondents = []
    with open(data_path, 'r', encoding='utf-8-sig') as f:
        # Handle semicolon-separated CSV with comma decimals
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            respondents.append(row)
    return respondents


def parse_value(val: str) -> Optional[int]:
    """Parse a value, handling Finnish decimal format and missing data."""
    if val is None or val.strip() == '':
        return None
    try:
        # Handle comma decimal (e.g., "1,0" -> 1)
        val = val.replace(',', '.')
        return int(float(val))
    except (ValueError, TypeError):
        return None


def analyze_priorities_by_age(respondents: list[dict]) -> dict:
    """Analyze issue priorities by age group.

    Returns:
        Dict mapping age groups to priority percentages
    """
    age_priorities = defaultdict(lambda: defaultdict(int))
    age_counts = defaultdict(int)

    for r in respondents:
        age = parse_value(r.get('t2'))
        if age is None:
            continue

        age_counts[age] += 1

        for var, priority_name in KANSALAISPULSSI_PRIORITIES.items():
            val = parse_value(r.get(var))
            if val == 1:  # 1 = Mainittu (mentioned as top 3 priority)
                age_priorities[age][priority_name] += 1

    # Convert to percentages
    results = {}
    for age, priorities in age_priorities.items():
        age_label = AGE_GROUP_LABELS.get(age, f'Age {age}')
        results[age_label] = {
            'n': age_counts[age],
            'priorities': {
                k: round(100 * v / age_counts[age], 1)
                for k, v in priorities.items()
            }
        }

    return results


def analyze_priorities_by_education(respondents: list[dict]) -> dict:
    """Analyze issue priorities by education level."""
    edu_priorities = defaultdict(lambda: defaultdict(int))
    edu_counts = defaultdict(int)

    for r in respondents:
        edu = parse_value(r.get('T4'))
        if edu is None:
            continue

        edu_counts[edu] += 1

        for var, priority_name in KANSALAISPULSSI_PRIORITIES.items():
            val = parse_value(r.get(var))
            if val == 1:
                edu_priorities[edu][priority_name] += 1

    results = {}
    for edu, priorities in edu_priorities.items():
        edu_label = EDUCATION_LABELS.get(edu, f'Education {edu}')
        results[edu_label] = {
            'n': edu_counts[edu],
            'priorities': {
                k: round(100 * v / edu_counts[edu], 1)
                for k, v in priorities.items()
            }
        }

    return results


def analyze_trust_by_age(respondents: list[dict]) -> dict:
    """Analyze institutional trust by age group.

    Trust is measured 1-10 (1=no trust, 10=full trust).
    """
    age_trust = defaultdict(lambda: defaultdict(list))

    for r in respondents:
        age = parse_value(r.get('t2'))
        if age is None:
            continue

        for var, trust_name in KANSALAISPULSSI_TRUST.items():
            val = parse_value(r.get(var))
            if val is not None and 1 <= val <= 10:
                age_trust[age][trust_name].append(val)

    results = {}
    for age, trusts in age_trust.items():
        age_label = AGE_GROUP_LABELS.get(age, f'Age {age}')
        results[age_label] = {
            trust_name: round(sum(vals) / len(vals), 1) if vals else None
            for trust_name, vals in trusts.items()
        }

    return results


def identify_segments(respondents: list[dict]) -> dict:
    """Identify voter segments based on demographic + attitude clustering.

    Maps respondents to our 8 simulation segments based on:
    - Age (young vs older)
    - Education (degree vs no degree)
    - Economic status
    - Urban vs rural (approximated by region)
    - Issue priorities

    Returns:
        Dict with segment profiles and population estimates
    """
    # Define segment criteria
    segments = {
        'Young Urban Progressives': {
            'age': [1, 2, 3, 4, 5, 6],  # Under 40
            'education': [3, 4],  # Higher education
            'priorities': ['climate_action', 'equality', 'biodiversity'],
            'count': 0,
            'respondents': [],
        },
        'Young Working Class': {
            'age': [1, 2, 3, 4, 5, 6],  # Under 40
            'education': [1, 2],  # No higher education
            'priorities': ['employment', 'daily_security'],
            'count': 0,
            'respondents': [],
        },
        'Urban Professionals': {
            'age': [5, 6, 7, 8, 9],  # 35-59
            'education': [3, 4],  # Higher education
            'priorities': ['healthcare', 'education', 'fiscal_sustainability'],
            'count': 0,
            'respondents': [],
        },
        'Rural/Agricultural': {
            'age': None,  # Any age
            'education': None,  # Any education
            'region': [2, 3, 4, 6, 9, 12, 14],  # Rural regions
            'priorities': ['employment', 'daily_security'],
            'count': 0,
            'respondents': [],
        },
        'Older Middle Class': {
            'age': [9, 10, 11, 12],  # 55+
            'education': None,  # Any
            'economic': [1, 2, 3],  # Not low income
            'priorities': ['healthcare', 'fiscal_sustainability', 'defense'],
            'count': 0,
            'respondents': [],
        },
        'Public Sector': {
            # Note: Kansalaispulssi doesn't have occupation, so we approximate
            # by trust in government institutions
            'age': None,
            'priorities': ['healthcare', 'education', 'poverty_reduction'],
            'count': 0,
            'respondents': [],
        },
        'Business/Entrepreneurs': {
            'priorities': ['business_conditions', 'fiscal_sustainability', 'employment'],
            'count': 0,
            'respondents': [],
        },
        'Tech Workers': {
            # Approximate by age + education + priorities
            'age': [3, 4, 5, 6, 7, 8],  # 25-54
            'education': [3, 4],  # Higher education
            'priorities': ['business_conditions', 'education'],
            'count': 0,
            'respondents': [],
        },
    }

    # Simple heuristic assignment (not ML clustering)
    # Each respondent is assigned to ONE segment based on best match

    for r in respondents:
        age = parse_value(r.get('t2'))
        edu = parse_value(r.get('T4'))
        eco = parse_value(r.get('T7'))
        region = parse_value(r.get('t3'))

        # Get respondent's priorities
        resp_priorities = set()
        for var, priority_name in KANSALAISPULSSI_PRIORITIES.items():
            if parse_value(r.get(var)) == 1:
                resp_priorities.add(priority_name)

        # Score each segment
        best_segment = None
        best_score = -1

        for seg_name, criteria in segments.items():
            score = 0

            # Age match
            if criteria.get('age') and age:
                if age in criteria['age']:
                    score += 2
                else:
                    score -= 1

            # Education match
            if criteria.get('education') and edu:
                if edu in criteria['education']:
                    score += 2
                else:
                    score -= 1

            # Region match (for rural)
            if criteria.get('region') and region:
                if region in criteria['region']:
                    score += 3

            # Economic match
            if criteria.get('economic') and eco:
                if eco in criteria['economic']:
                    score += 1

            # Priority match
            if criteria.get('priorities'):
                matches = len(resp_priorities & set(criteria['priorities']))
                score += matches * 2

            if score > best_score:
                best_score = score
                best_segment = seg_name

        if best_segment:
            segments[best_segment]['count'] += 1
            segments[best_segment]['respondents'].append(r)

    # Calculate segment profiles
    total = sum(s['count'] for s in segments.values())

    profiles = {}
    for seg_name, seg_data in segments.items():
        if seg_data['count'] == 0:
            continue

        # Calculate priority distribution within segment
        seg_priorities = defaultdict(int)
        for r in seg_data['respondents']:
            for var, priority_name in KANSALAISPULSSI_PRIORITIES.items():
                if parse_value(r.get(var)) == 1:
                    seg_priorities[priority_name] += 1

        profiles[seg_name] = {
            'population_pct': round(100 * seg_data['count'] / total, 1) if total > 0 else 0,
            'n': seg_data['count'],
            'top_priorities': sorted(
                seg_priorities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
        }

    return profiles


def estimate_proposal_support(segment_profiles: dict) -> dict:
    """Estimate likely support for UBI and Automation Tax by segment.

    Based on priority profiles:
    - UBI supporters: poverty_reduction, equality, exclusion_prevention
    - UBI opponents: fiscal_sustainability, employment (work focus)
    - Automation Tax supporters: poverty_reduction, equality
    - Automation Tax opponents: business_conditions, fiscal_sustainability
    """

    ubi_positive = {'poverty_reduction', 'equality', 'exclusion_prevention'}
    ubi_negative = {'fiscal_sustainability', 'business_conditions'}

    auto_tax_positive = {'poverty_reduction', 'equality', 'employment'}
    auto_tax_negative = {'business_conditions', 'fiscal_sustainability'}

    estimates = {}

    for seg_name, profile in segment_profiles.items():
        priorities = dict(profile['top_priorities'])
        total_mentions = sum(priorities.values()) or 1

        # Calculate UBI sentiment
        ubi_pos_score = sum(priorities.get(p, 0) for p in ubi_positive)
        ubi_neg_score = sum(priorities.get(p, 0) for p in ubi_negative)
        ubi_net = (ubi_pos_score - ubi_neg_score) / total_mentions

        # Map to support percentage (baseline 40%, range 20-60%)
        ubi_support = min(70, max(20, 40 + ubi_net * 100))

        # Calculate Automation Tax sentiment
        auto_pos_score = sum(priorities.get(p, 0) for p in auto_tax_positive)
        auto_neg_score = sum(priorities.get(p, 0) for p in auto_tax_negative)
        auto_net = (auto_pos_score - auto_neg_score) / total_mentions

        auto_support = min(70, max(20, 40 + auto_net * 100))

        estimates[seg_name] = {
            'ubi_pilot': {
                'support': round(ubi_support),
                'oppose': round(85 - ubi_support),  # Some abstention
                'abstain': round(100 - ubi_support - (85 - ubi_support)),
            },
            'automation_tax': {
                'support': round(auto_support),
                'oppose': round(85 - auto_support),
                'abstain': round(100 - auto_support - (85 - auto_support)),
            },
        }

    return estimates


def export_segment_priors(estimates: dict, output_path: str):
    """Export segment voting priors for simulation use."""
    with open(output_path, 'w') as f:
        json.dump(estimates, f, indent=2)
    print(f"Exported segment priors to {output_path}")


def main(data_dir: str = None):
    """Main analysis pipeline."""
    print("FSD Analysis Module")
    print("=" * 50)

    if data_dir is None:
        # Try default location
        data_dir = Path.home() / "Downloads" / "FSD4022" / "Study" / "Data"
    else:
        data_dir = Path(data_dir)

    csv_path = data_dir / "daF4022_fin.csv"

    if not csv_path.exists():
        print(f"\nData file not found: {csv_path}")
        print("\nTo use this script:")
        print("1. Download FSD4022 from https://services.fsd.tuni.fi/catalogue/FSD4022")
        print("2. Extract to ~/Downloads/FSD4022/")
        print("3. Run this script again")
        return

    print(f"\nLoading data from: {csv_path}")
    respondents = load_kansalaispulssi_csv(csv_path)
    print(f"Loaded {len(respondents)} respondents")

    print("\n--- Priority Analysis by Age ---")
    age_priorities = analyze_priorities_by_age(respondents)
    for age, data in sorted(age_priorities.items(), key=lambda x: x[0]):
        top_3 = sorted(data['priorities'].items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_str = ", ".join(f"{k}({v}%)" for k, v in top_3)
        print(f"  {age} (n={data['n']}): {top_3_str}")

    print("\n--- Priority Analysis by Education ---")
    edu_priorities = analyze_priorities_by_education(respondents)
    for edu, data in edu_priorities.items():
        top_3 = sorted(data['priorities'].items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_str = ", ".join(f"{k}({v}%)" for k, v in top_3)
        print(f"  {edu} (n={data['n']}): {top_3_str}")

    print("\n--- Segment Identification ---")
    segments = identify_segments(respondents)
    for seg_name, profile in segments.items():
        top_priorities = ", ".join(f"{p[0]}" for p in profile['top_priorities'][:3])
        print(f"  {seg_name}: {profile['population_pct']}% (n={profile['n']})")
        print(f"    Top priorities: {top_priorities}")

    print("\n--- Proposal Support Estimates ---")
    estimates = estimate_proposal_support(segments)
    for seg_name, est in estimates.items():
        ubi = est['ubi_pilot']
        auto = est['automation_tax']
        print(f"  {seg_name}:")
        print(f"    UBI: {ubi['support']}% support, {ubi['oppose']}% oppose")
        print(f"    Automation Tax: {auto['support']}% support, {auto['oppose']}% oppose")

    # Export for simulation use
    output_dir = Path(__file__).parent.parent / "src"
    output_path = output_dir / "segment_priors.json"
    export_segment_priors(estimates, str(output_path))

    print("\n" + "=" * 50)
    print("Analysis complete!")


if __name__ == '__main__':
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    main(data_dir)
