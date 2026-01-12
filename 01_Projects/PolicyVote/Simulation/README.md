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

Uses Concordia's **Entity-Component** architectural pattern, as described in:

> Vezhnevets et al. (2025) "Multi-Actor Generative Artificial Intelligence as a Game Engine"
> [arXiv:2507.08892](https://arxiv.org/abs/2507.08892)

The paper identifies three user motivations for multi-actor generative AI:
- **Evaluationist**: Benchmark and compare AI capabilities
- **Dramatist**: Generate compelling narratives
- **Simulationist**: Model real-world social dynamics with fidelity

**This simulation is Simulationist** - we model Finnish voting dynamics to explore PolicyVote mechanics.

### Entities

| Agent Type | Description |
|------------|-------------|
| **Party agents** | Represent political parties (Vihreät, Kokoomus, Vasemmisto, SDP) with policy positions |
| **Voter segment agents** | Represent demographic groups with priorities and concerns |
| **Game Master** | Orchestrates deliberation and voting phases |

### Components

Following Concordia's Entity-Component pattern, entities are containers whose behavior emerges from attached components:

**Party Agent Components:**
| Component | Type | Purpose |
|-----------|------|---------|
| `Instructions` | Context | Defines agent's role |
| `LastNObservations` | Context | Recent events (50 lines) |
| `Constant` | Context | Policy position on proposals |
| `Constant` | Context | Core reasoning/values |
| `AssociativeMemory` | Memory | RAG-based memory bank |
| `ConcatActComponent` | Acting | Aggregates context → action |

**Voter Segment Agent Components:**
| Component | Type | Purpose |
|-----------|------|---------|
| `Instructions` | Context | Defines segment's role |
| `LastNObservations` | Context | What has been discussed (100 lines) |
| `Constant` | Context | Demographics |
| `Constant` | Context | Priorities/values |
| `AssociativeMemory` | Memory | RAG-based memory bank |
| `QuestionOfRecentMemories` | Context | "How divided would this group be?" |
| `ConcatActComponent` | Acting | Base deliberation |
| `StructuredVotingActComponent` | Acting | **Custom** - Bedrock tool use for vote distributions |

**Custom Components (in `src/`):**
- `StructuredVotingActComponent` - Uses AWS Bedrock tool use for structured vote output (avoids text parsing)
- `election_initializer` - Seeds memories with real Finnish political facts (not AI-generated fiction)

### Design Philosophy

The Entity-Component architecture separates **engineer** and **designer** concerns:
- **Engineer**: Creates reusable, testable components (e.g., memory models, voting algorithms)
- **Designer**: Composes scenarios from components without writing new code

This allows rapid iteration on election scenarios by mixing and matching components.

### Phases

1. **Initialization**: Sets up shared context (Finland's UBI debate background, real party histories)
2. **Deliberation**: Parties present arguments, voters listen
3. **Voting**: Voter segments output vote distributions (Support/Oppose/Abstain percentages)
4. **Results**: Mandate calculated and reported

## Files

- `election_minimal.py` - Main simulation (4 parties, 3 voter segments, 2 proposals)
- `src/anthropic_model.py` - Claude language model wrapper for Concordia
- `src/election_initializer.py` - Custom initializer using real facts
- `src/structured_voting.py` - Bedrock tool use for structured vote output
- `requirements.txt` - Python dependencies
- `outputs/` - Generated HTML reports and JSON logs

## References

- [Concordia GitHub](https://github.com/google-deepmind/concordia)
- [Vezhnevets et al. 2025 - Multi-Actor Generative AI as a Game Engine](https://arxiv.org/abs/2507.08892)
- [PolicyVote Project](../README.md)
