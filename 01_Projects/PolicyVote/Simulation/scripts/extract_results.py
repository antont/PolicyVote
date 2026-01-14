"""
PolicyVote Simulation Results Extractor

Extracts vote distributions and generates a summary report from simulation output.
Describes the simulation methodology and calculates weighted mandate results.

Usage:
    python scripts/extract_results.py [output_file.txt]
    python scripts/extract_results.py  # uses /tmp/sim_output.txt by default
"""

import re
import json
from pathlib import Path
from datetime import datetime

# Segment weights (population proportions)
SEGMENT_WEIGHTS = {
    'Young Urban Progressives': 0.15,
    'Young Working Class': 0.10,
    'Urban Professionals': 0.15,
    'Rural and Agricultural Voters': 0.10,
    'Older Middle Class': 0.18,
    'Public Sector Workers': 0.12,
    'Business and Entrepreneurs': 0.08,
    'Tech Industry Workers': 0.07,
}

# Alternative segment name mappings
SEGMENT_ALIASES = {
    'Rural/Agricultural': 'Rural and Agricultural Voters',
    'Business/Entrepreneurs': 'Business and Entrepreneurs',
    'Tech Workers': 'Tech Industry Workers',
}


def parse_vote_line(line: str) -> dict | None:
    """Parse a vote distribution line from simulation output.

    Expected format:
    Entity <Segment> chose action: Support: X%, Oppose: Y%, Abstain: Z% (reasoning...)
    """
    # Match pattern like "Support: 62%, Oppose: 23%, Abstain: 15%"
    match = re.search(
        r'Entity ([^:]+?) chose action: Support: (\d+)%, Oppose: (\d+)%, Abstain: (\d+)%',
        line
    )
    if match:
        segment = match.group(1).strip()
        # Normalize segment name
        segment = SEGMENT_ALIASES.get(segment, segment)
        return {
            'segment': segment,
            'support': int(match.group(2)),
            'oppose': int(match.group(3)),
            'abstain': int(match.group(4)),
        }
    return None


def extract_votes_from_output(output_path: str) -> dict:
    """Extract all vote distributions from simulation output.

    Returns:
        Dict with 'ubi_pilot' and 'automation_tax' vote distributions
    """
    votes = {
        'ubi_pilot': {},
        'automation_tax': {},
    }

    current_proposal = 'ubi_pilot'
    seen_segments_ubi = set()

    with open(output_path, 'r') as f:
        for line in f:
            # Detect when we switch to automation tax voting
            if 'Automation Tax' in line and 'votes on:' in line.lower():
                current_proposal = 'automation_tax'

            vote = parse_vote_line(line)
            if vote:
                segment = vote['segment']

                # Determine which proposal this vote is for
                # If we've already seen this segment for UBI, it's automation tax
                if segment in seen_segments_ubi and current_proposal == 'ubi_pilot':
                    current_proposal = 'automation_tax'

                if current_proposal == 'ubi_pilot':
                    seen_segments_ubi.add(segment)

                # Store the vote (later votes for same segment overwrite)
                if segment in SEGMENT_WEIGHTS or any(
                    alias == segment for alias in SEGMENT_ALIASES.values()
                ):
                    votes[current_proposal][segment] = {
                        'support': vote['support'],
                        'oppose': vote['oppose'],
                        'abstain': vote['abstain'],
                    }

    return votes


def calculate_weighted_mandate(votes: dict) -> dict:
    """Calculate weighted mandate from segment votes.

    Returns:
        Dict with weighted support, oppose, abstain percentages and pass/fail
    """
    total_weight = 0
    weighted_support = 0
    weighted_oppose = 0
    weighted_abstain = 0

    for segment, weight in SEGMENT_WEIGHTS.items():
        if segment in votes:
            v = votes[segment]
            weighted_support += weight * v['support']
            weighted_oppose += weight * v['oppose']
            weighted_abstain += weight * v['abstain']
            total_weight += weight

    if total_weight == 0:
        return {'error': 'No votes found'}

    # Normalize
    support_pct = weighted_support / total_weight
    oppose_pct = weighted_oppose / total_weight
    abstain_pct = weighted_abstain / total_weight

    # Calculate mandate (support as fraction of support + oppose)
    if support_pct + oppose_pct > 0:
        mandate = support_pct / (support_pct + oppose_pct)
    else:
        mandate = 0.5

    return {
        'support_pct': round(support_pct, 1),
        'oppose_pct': round(oppose_pct, 1),
        'abstain_pct': round(abstain_pct, 1),
        'mandate': round(mandate * 100, 1),
        'passed': support_pct > oppose_pct,
        'segments_counted': len(votes),
    }


def generate_report(votes: dict, output_path: str = None) -> str:
    """Generate a markdown report describing the simulation and results."""

    report = []
    report.append("# PolicyVote Election Simulation Results")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    # Methodology section
    report.append("## Methodology")
    report.append("")
    report.append("### Simulation Framework")
    report.append("- **Framework:** Google DeepMind's Concordia (agent-based simulation)")
    report.append("- **LLM Backend:** Claude Haiku 4.5 via AWS Bedrock")
    report.append("- **Structured Output:** Bedrock tool use for reliable vote distributions")
    report.append("")

    report.append("### Agents")
    report.append("**Political Parties (8):** Simulate party positions and deliberation")
    report.append("- Vihreät (Green League)")
    report.append("- Kokoomus (National Coalition)")
    report.append("- Vasemmistoliitto (Left Alliance)")
    report.append("- SDP (Social Democrats)")
    report.append("- Keskusta (Centre Party)")
    report.append("- Perussuomalaiset (Finns Party)")
    report.append("- RKP (Swedish People's Party)")
    report.append("- KD (Christian Democrats)")
    report.append("")

    report.append("**Voter Segments (8):** Represent demographic groups with weighted populations")
    report.append("")
    report.append("| Segment | Population Weight |")
    report.append("|---------|-------------------|")
    for segment, weight in SEGMENT_WEIGHTS.items():
        report.append(f"| {segment} | {weight*100:.0f}% |")
    report.append("")

    report.append("### Simulation Process")
    report.append("1. **Deliberation Phase:** Parties present positions, voter segments observe")
    report.append("2. **Information Exchange:** Agents share concerns and arguments")
    report.append("3. **Voting Phase:** Each voter segment provides vote distribution (Support/Oppose/Abstain %)")
    report.append("4. **Aggregation:** Weighted average across segments determines mandate")
    report.append("")

    report.append("### Data-Driven Priors")
    report.append("Voter segments receive baseline priors from Finnish survey data (FSD4022 Kansalaispulssi):")
    report.append("- Issue priorities by demographic group")
    report.append("- Trust in institutions")
    report.append("- Regional and educational variations")
    report.append("")

    # Results section
    report.append("## Results")
    report.append("")

    for proposal_key, proposal_name in [
        ('ubi_pilot', 'UBI Pilot (800€/month for 50,000 citizens)'),
        ('automation_tax', 'Automation Tax (tax on AI/robots replacing workers)'),
    ]:
        report.append(f"### {proposal_name}")
        report.append("")

        if proposal_key in votes and votes[proposal_key]:
            prop_votes = votes[proposal_key]
            result = calculate_weighted_mandate(prop_votes)

            # Vote table
            report.append("| Segment | Support | Oppose | Abstain |")
            report.append("|---------|---------|--------|---------|")
            for segment in SEGMENT_WEIGHTS.keys():
                if segment in prop_votes:
                    v = prop_votes[segment]
                    report.append(f"| {segment} | {v['support']}% | {v['oppose']}% | {v['abstain']}% |")
            report.append("")

            # Summary
            status = "**PASSED**" if result['passed'] else "**FAILED**"
            report.append(f"**Weighted Result:** {result['support_pct']}% support, {result['oppose_pct']}% oppose")
            report.append(f"**Mandate:** {result['mandate']}% → {status}")
            report.append("")
        else:
            report.append("*No votes recorded for this proposal*")
            report.append("")

    # Observations section
    report.append("## Key Observations")
    report.append("")

    if 'ubi_pilot' in votes and 'automation_tax' in votes:
        ubi = votes['ubi_pilot']
        auto = votes['automation_tax']

        # Find most/least supportive segments
        if ubi:
            most_ubi = max(ubi.items(), key=lambda x: x[1]['support'])
            least_ubi = min(ubi.items(), key=lambda x: x[1]['support'])
            report.append(f"- **Strongest UBI support:** {most_ubi[0]} ({most_ubi[1]['support']}%)")
            report.append(f"- **Weakest UBI support:** {least_ubi[0]} ({least_ubi[1]['support']}%)")

        if auto:
            most_auto = max(auto.items(), key=lambda x: x[1]['support'])
            least_auto = min(auto.items(), key=lambda x: x[1]['support'])
            report.append(f"- **Strongest Automation Tax support:** {most_auto[0]} ({most_auto[1]['support']}%)")
            report.append(f"- **Weakest Automation Tax support:** {least_auto[0]} ({least_auto[1]['support']}%)")

    report.append("")
    report.append("---")
    report.append("*Generated by PolicyVote Simulation using Concordia framework*")

    return "\n".join(report)


def main(output_file: str = None):
    """Main extraction pipeline."""
    if output_file is None:
        # Try default locations
        candidates = [
            '/tmp/sim_output.txt',
            Path(__file__).parent.parent / 'simulation_output.txt',
        ]
        for c in candidates:
            if Path(c).exists():
                output_file = str(c)
                break

    if output_file is None or not Path(output_file).exists():
        print("Error: No simulation output file found")
        print("Usage: python extract_results.py <output_file.txt>")
        return

    print(f"Extracting results from: {output_file}")
    print("=" * 50)

    # Extract votes
    votes = extract_votes_from_output(output_file)

    print(f"\nFound votes for {len(votes['ubi_pilot'])} segments (UBI)")
    print(f"Found votes for {len(votes['automation_tax'])} segments (Automation Tax)")

    # Calculate mandates
    print("\n--- UBI Pilot Results ---")
    if votes['ubi_pilot']:
        ubi_result = calculate_weighted_mandate(votes['ubi_pilot'])
        print(f"Support: {ubi_result['support_pct']}%")
        print(f"Oppose: {ubi_result['oppose_pct']}%")
        print(f"Mandate: {ubi_result['mandate']}%")
        print(f"Result: {'PASSED' if ubi_result['passed'] else 'FAILED'}")

    print("\n--- Automation Tax Results ---")
    if votes['automation_tax']:
        auto_result = calculate_weighted_mandate(votes['automation_tax'])
        print(f"Support: {auto_result['support_pct']}%")
        print(f"Oppose: {auto_result['oppose_pct']}%")
        print(f"Mandate: {auto_result['mandate']}%")
        print(f"Result: {'PASSED' if auto_result['passed'] else 'FAILED'}")

    # Generate report
    report = generate_report(votes, output_file)

    # Save report
    report_path = Path(__file__).parent.parent / 'outputs' / 'simulation_report.md'
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")

    # Also save JSON results
    json_path = Path(__file__).parent.parent / 'outputs' / 'extracted_results.json'
    with open(json_path, 'w') as f:
        json.dump({
            'votes': votes,
            'ubi_pilot_result': calculate_weighted_mandate(votes['ubi_pilot']) if votes['ubi_pilot'] else None,
            'automation_tax_result': calculate_weighted_mandate(votes['automation_tax']) if votes['automation_tax'] else None,
        }, f, indent=2)
    print(f"JSON results saved to: {json_path}")


if __name__ == '__main__':
    import sys
    output_file = sys.argv[1] if len(sys.argv) > 1 else None
    main(output_file)
