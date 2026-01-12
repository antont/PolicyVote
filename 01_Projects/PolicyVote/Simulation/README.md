# PolicyVote Election Simulation

A Concordia-based simulation to validate PolicyVote voting mechanics and explore emergent dynamics.

## Setup

1. **Clone Concordia** (if not already done):
   ```bash
   git clone https://github.com/google-deepmind/concordia.git ~/src/concordia
   ```

2. **Create virtual environment**:
   ```bash
   cd /path/to/PolicyVote/Simulation
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ~/src/concordia
   pip install -r requirements.txt
   ```

4. **Set API credentials** (one of these):
   ```bash
   # Option A: AWS Bedrock (requires IAM credentials)
   export AWS_ACCESS_KEY_ID='your-key'
   export AWS_SECRET_ACCESS_KEY='your-secret'
   export AWS_DEFAULT_REGION='us-east-1'

   # Option B: Anthropic API directly
   export ANTHROPIC_API_KEY='your-api-key'
   ```

## Running the Simulation

### Structure test (no API needed)

Without API credentials - tests the simulation structure:
```bash
python election_minimal.py
```

### Full simulation (requires API credentials)

With Bedrock:
```bash
AWS_ACCESS_KEY_ID='xxx' AWS_SECRET_ACCESS_KEY='yyy' python election_minimal.py
```

With Anthropic API:
```bash
ANTHROPIC_API_KEY='your-key' python election_minimal.py
```

**Note**: Claude Code's internal Bedrock bearer token (`AWS_BEARER_TOKEN_BEDROCK`) cannot be used for direct API calls - it's for internal Claude Code use only.

## Architecture

Uses Concordia's multi-agent framework:

| Agent Type | Description |
|------------|-------------|
| **Party agents** | Represent political parties (Vihreät, Kokoomus) with policy positions |
| **Voter segment agents** | Represent demographic groups with priorities and concerns |
| **Game Master** | Orchestrates deliberation and voting phases |

### Phases

1. **Initialization**: Sets up shared context (Finland's UBI debate background)
2. **Deliberation**: Parties present arguments, voters listen
3. **Voting**: Voter segments choose Support/Oppose/Abstain
4. **Results**: Mandate calculated and reported

## Files

- `election_minimal.py` - Minimal 2-party, 2-segment prototype
- `src/anthropic_model.py` - Claude language model wrapper for Concordia
- `requirements.txt` - Python dependencies
