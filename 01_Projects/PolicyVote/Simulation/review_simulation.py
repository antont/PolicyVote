#!/usr/bin/env python3
"""Review a PolicyVote simulation run - extract and display the process step by step."""

import json
import sys
import textwrap
from pathlib import Path


def review_simulation(rawlog_path: str):
    """Parse and display simulation process from a raw log file."""

    with open(rawlog_path) as f:
        data = json.load(f)

    print("=" * 70)
    print("POLICYVOTE SIMULATION REVIEW")
    print(f"Source: {rawlog_path}")
    print(f"Total entries: {len(data)}")
    print("=" * 70)

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        step = item.get('Step', '?')

        # Find the event key (it's in the dict keys)
        for key in item.keys():
            if '---' not in key or 'Event:' not in key:
                continue

            # Extract entity and event
            parts = key.split('---')
            if len(parts) < 2:
                continue

            event = parts[1].strip()

            # Determine phase
            if 'deliberation rules' in key:
                phase = "DELIBERATION"
            elif 'election rules' in key:
                phase = "VOTING"
            else:
                phase = "OTHER"

            # Extract entity name
            entity = "Unknown"
            for k in item.keys():
                if k.startswith('Entity ['):
                    entity = k.replace('Entity [', '').replace(']', '')
                    break

            print(f"\n{'=' * 70}")
            print(f"STEP {step} | {phase} | {entity}")
            print("-" * 70)

            # Clean up the event text
            event_text = event.replace('Event: ', '').replace('Putative event to resolve: ', '')

            # Wrap text nicely
            wrapped = textwrap.fill(event_text, width=70)
            print(wrapped)

    print(f"\n{'=' * 70}")
    print("END OF SIMULATION REVIEW")
    print("=" * 70)


def find_latest_rawlog():
    """Find the most recent rawlog file in outputs/."""
    outputs = Path('outputs')
    if not outputs.exists():
        return None

    rawlogs = sorted(outputs.glob('rawlog_*.json'), reverse=True)
    return str(rawlogs[0]) if rawlogs else None


if __name__ == '__main__':
    if len(sys.argv) > 1:
        rawlog_path = sys.argv[1]
    else:
        rawlog_path = find_latest_rawlog()
        if not rawlog_path:
            print("No rawlog files found in outputs/")
            print("Usage: python review_simulation.py [path/to/rawlog.json]")
            sys.exit(1)

    review_simulation(rawlog_path)
