"""
PolicyVote Election Simulation - Minimal Prototype
Uses Concordia to simulate policy-based voting.

This minimal example demonstrates:
- 2 party agents (Vihreät, Kokoomus)
- 2 voter segment agents (young progressives, older conservatives)
- 1 proposal: UBI Pilot (800€/month)
- Deliberation + Voting phases

Based on Concordia's game_theoretic_and_dramaturgic pattern.
"""

from collections.abc import Mapping, Sequence
import dataclasses
import sys

# Add concordia to path if needed
sys.path.insert(0, '/Users/tonialatalo/src/concordia')

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory
from concordia.components import agent as agent_components
from concordia.language_model import language_model
import concordia.prefabs.entity as entity_prefabs
import concordia.prefabs.game_master as game_master_prefabs
from concordia.prefabs.simulation import generic as simulation
from concordia.typing import entity as entity_lib
from concordia.typing import prefab as prefab_lib
from concordia.typing import scene as scene_lib
from concordia.utils import helper_functions

# === CONFIGURATION ===

# Parties
VIHREAT = 'Vihreät Representative'
KOKOOMUS = 'Kokoomus Representative'
VASEMMISTO = 'Vasemmistoliitto Representative'
SDP = 'SDP Representative'

# Voter segments
YOUNG_PROGRESSIVES = 'Young Progressive Voters'
OLDER_CONSERVATIVES = 'Older Conservative Voters'
TECH_WORKERS = 'Tech Industry Workers'

ALL_VOTERS = [YOUNG_PROGRESSIVES, OLDER_CONSERVATIVES, TECH_WORKERS]
ALL_PARTIES = [VIHREAT, KOKOOMUS, VASEMMISTO, SDP]
ALL_PARTICIPANTS = ALL_PARTIES + ALL_VOTERS

# Proposals
UBI_PROPOSAL = 'UBI Pilot: 800€/month basic income for 50,000 citizens'
AUTOMATION_TAX = 'Automation Tax: Tax on AI and robots replacing human workers'

ALL_PROPOSALS = [UBI_PROPOSAL, AUTOMATION_TAX]


# === CUSTOM PREFABS ===

@dataclasses.dataclass
class PartyAgent(prefab_lib.Prefab):
    """A political party agent with policy positions."""

    description: str = 'A political party representative that advocates for policies.'
    params: Mapping[str, str] = dataclasses.field(
        default_factory=lambda: {
            'name': 'Party',
            'policy_position': '',
            'reasoning': '',
        }
    )

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_agent_with_logging.EntityAgentWithLogging:
        agent_name = self.params.get('name', 'Party')

        instructions = agent_components.instructions.Instructions(
            agent_name=agent_name,
            pre_act_label='\nRole',
        )

        observation = agent_components.observation.LastNObservations(
            history_length=50, pre_act_label='\nRecent events'
        )

        policy_position = agent_components.constant.Constant(
            state=self.params.get('policy_position', ''),
            pre_act_label='Policy position on UBI',
        )

        reasoning = agent_components.constant.Constant(
            state=self.params.get('reasoning', ''),
            pre_act_label='Core reasoning',
        )

        components = {
            'Instructions': instructions,
            'policy_position': policy_position,
            'reasoning': reasoning,
            agent_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY: observation,
            agent_components.memory.DEFAULT_MEMORY_COMPONENT_KEY: (
                agent_components.memory.AssociativeMemory(memory_bank=memory_bank)
            ),
        }

        act_component = agent_components.concat_act_component.ConcatActComponent(
            model=model,
            component_order=list(components.keys()),
        )

        return entity_agent_with_logging.EntityAgentWithLogging(
            agent_name=agent_name,
            act_component=act_component,
            context_components=components,
        )


@dataclasses.dataclass
class VoterSegmentAgent(prefab_lib.Prefab):
    """A voter segment that decides on policies based on interests.

    Uses Bedrock tool use for structured voting output (no text parsing needed).
    """

    description: str = 'A voter segment representing a demographic group.'
    params: Mapping[str, str] = dataclasses.field(
        default_factory=lambda: {
            'name': 'Voters',
            'demographics': '',
            'priorities': '',
        }
    )

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_agent_with_logging.EntityAgentWithLogging:
        from src.structured_voting import StructuredVotingActComponent

        agent_name = self.params.get('name', 'Voters')

        instructions = agent_components.instructions.Instructions(
            agent_name=agent_name,
            pre_act_label='\nRole',
        )

        observation = agent_components.observation.LastNObservations(
            history_length=100, pre_act_label='\nWhat has been discussed'
        )

        demographics = agent_components.constant.Constant(
            state=self.params.get('demographics', ''),
            pre_act_label='Who we are',
        )

        priorities = agent_components.constant.Constant(
            state=self.params.get('priorities', ''),
            pre_act_label='What matters to us',
        )

        # Deliberative component: how should this demographic vote?
        voting_consideration = agent_components.question_of_recent_memories.QuestionOfRecentMemories(
            model=model,
            pre_act_label=f'Voting consideration',
            question=(
                f'{agent_name} is a diverse demographic group, not a single person. '
                f'Given what they have heard about the proposals, and considering '
                f'the range of views within this demographic, how divided would they be? '
                f'What percentage would support, oppose, or abstain on each proposal?'
            ),
            answer_prefix=f'{agent_name} are considering: ',
            add_to_memory=False,
        )

        components = {
            'Instructions': instructions,
            'demographics': demographics,
            'priorities': priorities,
            agent_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY: observation,
            agent_components.memory.DEFAULT_MEMORY_COMPONENT_KEY: (
                agent_components.memory.AssociativeMemory(memory_bank=memory_bank)
            ),
            'voting_consideration': voting_consideration,
        }

        # Create base act component for deliberation
        base_act_component = agent_components.concat_act_component.ConcatActComponent(
            model=model,
            component_order=list(components.keys()),
        )

        # Wrap with structured voting (uses Bedrock tool use for vote output)
        act_component = StructuredVotingActComponent(
            wrapped_act_component=base_act_component,
            model_id='anthropic.claude-3-haiku-20240307-v1:0',
        )

        return entity_agent_with_logging.EntityAgentWithLogging(
            agent_name=agent_name,
            act_component=act_component,
            context_components=components,
        )


# === SCENES ===

def configure_scenes() -> Sequence[scene_lib.SceneSpec]:
    """Configure deliberation and voting scenes."""

    # Deliberation: parties pitch to voters (use election rules GM for all scenes)
    deliberation = scene_lib.SceneTypeSpec(
        name='deliberation',
        game_master_name='election rules',
        action_spec=entity_lib.free_action_spec(
            call_to_action=entity_lib.DEFAULT_CALL_TO_SPEECH
        ),
    )

    # Voting on UBI - free-form for vote distributions
    voting_ubi = scene_lib.SceneTypeSpec(
        name='voting_ubi',
        game_master_name='election rules',
        action_spec={
            voter: entity_lib.free_action_spec(
                call_to_action=(
                    f'{{name}} must decide how their demographic votes on: {UBI_PROPOSAL}. '
                    f'Consider that this group is not monolithic - there may be internal divisions. '
                    f'Respond with the vote distribution as percentages that sum to 100%, e.g.: '
                    f'"Support: 45%, Oppose: 40%, Abstain: 15%"'
                ),
            )
            for voter in ALL_VOTERS
        },
    )

    # Voting on Automation Tax - free-form for vote distributions
    voting_automation = scene_lib.SceneTypeSpec(
        name='voting_automation',
        game_master_name='election rules',
        action_spec={
            voter: entity_lib.free_action_spec(
                call_to_action=(
                    f'{{name}} must decide how their demographic votes on: {AUTOMATION_TAX}. '
                    f'Consider that this group is not monolithic - there may be internal divisions. '
                    f'Respond with the vote distribution as percentages that sum to 100%, e.g.: '
                    f'"Support: 45%, Oppose: 40%, Abstain: 15%"'
                ),
            )
            for voter in ALL_VOTERS
        },
    )

    # Results announcement scene (absorbs termination check)
    results = scene_lib.SceneTypeSpec(
        name='results',
        game_master_name='election rules',
        action_spec=entity_lib.free_action_spec(
            call_to_action='The election official announces the final results.'
        ),
    )

    scenes = [
        # Deliberation: parties present positions on both proposals
        scene_lib.SceneSpec(
            scene_type=deliberation,
            participants=ALL_PARTICIPANTS,
            num_rounds=7,  # One per participant
            premise={
                VIHREAT: [f'{VIHREAT} is presenting Green positions: supports UBI but opposes Automation Tax as counterproductive'],
                KOKOOMUS: [f'{KOKOOMUS} is presenting conservative positions: skeptical of both UBI and Automation Tax'],
                VASEMMISTO: [f'{VASEMMISTO} is presenting left positions: strongly supports both UBI and Automation Tax'],
                SDP: [f'{SDP} is presenting social democratic positions: prefers conditional benefits over UBI, cautiously open to automation tax'],
                YOUNG_PROGRESSIVES: [f'{YOUNG_PROGRESSIVES} are listening to the debate on UBI and automation'],
                OLDER_CONSERVATIVES: [f'{OLDER_CONSERVATIVES} are evaluating economic arguments'],
                TECH_WORKERS: [f'{TECH_WORKERS} are considering how these proposals affect their industry'],
            },
        ),
        # Voting on UBI
        scene_lib.SceneSpec(
            scene_type=voting_ubi,
            participants=ALL_VOTERS,
            num_rounds=3,  # One per voter
            premise={
                voter: [f'{voter} must now vote on the UBI Pilot proposal']
                for voter in ALL_VOTERS
            },
        ),
        # Voting on Automation Tax
        scene_lib.SceneSpec(
            scene_type=voting_automation,
            participants=ALL_VOTERS,
            num_rounds=3,  # One per voter
            premise={
                voter: [f'{voter} must now vote on the Automation Tax proposal']
                for voter in ALL_VOTERS
            },
        ),
        # Results announcement (absorbs termination check)
        scene_lib.SceneSpec(
            scene_type=results,
            participants=[VIHREAT],  # Just one participant for final announcement
            num_rounds=4,  # +2 for termination overhead
            premise={
                VIHREAT: ['The election official will now announce the results.'],
            },
        ),
    ]
    return scenes


# === SCORING ===

import re

# Segment weights for future population-based weighting (equal for now)
SEGMENT_WEIGHTS = {
    YOUNG_PROGRESSIVES: 1.0,
    OLDER_CONSERVATIVES: 1.0,
    TECH_WORKERS: 1.0,
}


def parse_vote_distribution(response: str) -> dict[str, float]:
    """Parse vote distribution from free-text response.

    Handles formats like:
    - "Support: 45%, Oppose: 40%, Abstain: 15%"
    - "45% support, 40% oppose, 15% abstain"
    - "Support 45 Oppose 40 Abstain 15"

    Returns dict with 'support', 'oppose', 'abstain' keys (values 0-100).
    """
    response_lower = response.lower()

    # Try to extract percentages
    support = 0.0
    oppose = 0.0
    abstain = 0.0

    # Pattern: "support: 45%" or "support 45%" - keyword THEN number (not reversed)
    # The reversed pattern "45% support" was buggy - "60% Oppose" matched as oppose=60
    support_match = re.search(r'support[:\s]*(\d+(?:\.\d+)?)\s*%?', response_lower)
    oppose_match = re.search(r'oppose[:\s]*(\d+(?:\.\d+)?)\s*%?', response_lower)
    abstain_match = re.search(r'abstain[:\s]*(\d+(?:\.\d+)?)\s*%?', response_lower)

    if support_match:
        support = float(support_match.group(1))
    if oppose_match:
        oppose = float(oppose_match.group(1))
    if abstain_match:
        abstain = float(abstain_match.group(1))

    # If no percentages found, try to infer from keywords
    if support == 0 and oppose == 0 and abstain == 0:
        if 'support' in response_lower and 'oppose' not in response_lower:
            support = 100.0
        elif 'oppose' in response_lower and 'support' not in response_lower:
            oppose = 100.0
        elif 'abstain' in response_lower:
            abstain = 100.0
        else:
            # Default: split evenly if nothing found
            support = 33.3
            oppose = 33.3
            abstain = 33.4

    # Normalize to 100% if needed
    total = support + oppose + abstain
    if total > 0 and abs(total - 100) > 1:  # Allow small rounding errors
        support = (support / total) * 100
        oppose = (oppose / total) * 100
        abstain = (abstain / total) * 100

    return {
        'support': support,
        'oppose': oppose,
        'abstain': abstain,
    }


def action_to_mandate(joint_action: Mapping[str, str]) -> Mapping[str, float]:
    """Calculate mandate from vote distributions.

    joint_action maps voter segment names to their free-text vote distribution.
    Party agents return None (they don't vote), so we filter them out.

    Returns empty {} if this doesn't look like a voting round (to prevent
    Concordia from accumulating non-voting responses).
    """
    segment_distributions = {}
    is_voting_round = False

    for segment, response in joint_action.items():
        # Skip party agents (they don't vote, response is None)
        if response is None:
            continue
        # Only process voter segments
        if segment not in ALL_VOTERS:
            continue

        # Check if this looks like a vote (contains "Support:" and percentages)
        if response and 'Support:' in response and '%' in response:
            is_voting_round = True
            dist = parse_vote_distribution(response)
            segment_distributions[segment] = dist

    # If not a voting round, return empty scores (prevents accumulation)
    if not is_voting_round or not segment_distributions:
        return {}

    # Calculate weighted averages
    total_weighted_support = 0.0
    total_weighted_oppose = 0.0
    total_weighted_abstain = 0.0
    total_weight = 0.0

    for segment, dist in segment_distributions.items():
        weight = SEGMENT_WEIGHTS.get(segment, 1.0)
        total_weight += weight
        total_weighted_support += dist['support'] * weight
        total_weighted_oppose += dist['oppose'] * weight
        total_weighted_abstain += dist['abstain'] * weight

    # Calculate overall percentages
    avg_support = total_weighted_support / total_weight
    avg_oppose = total_weighted_oppose / total_weight
    avg_abstain = total_weighted_abstain / total_weight

    # Mandate: support as fraction of decided voters (support + oppose)
    decided = avg_support + avg_oppose
    mandate_strength = avg_support / decided if decided > 0 else 0.0

    # Print segment distributions for debugging
    print(f"\n  VOTE RESULTS: {segment_distributions}")
    print(f"  Mandate: {mandate_strength*100:.0f}% ({avg_support:.0f}% support, {avg_oppose:.0f}% oppose)")

    return {
        'mandate': mandate_strength,
        'support_pct': avg_support,
        'oppose_pct': avg_oppose,
        'abstain_pct': avg_abstain,
    }


def mandate_to_observation(scores: Mapping[str, float]) -> Mapping[str, str]:
    """Convert mandate calculation to observations for participants.

    Note: Concordia accumulates scores, so we avoid generating misleading
    observations when scores represent multiple voting rounds summed together.
    The actual vote results are printed to console by action_to_mandate.
    """
    # If no scores or scores look accumulated (support > 100), skip observation
    support_pct = scores.get('support_pct', 0.0)
    oppose_pct = scores.get('oppose_pct', 0.0)

    if support_pct == 0.0 or support_pct > 100:
        # No meaningful observation
        return {}

    mandate = scores.get('mandate', 0.0)

    if mandate > 0.5:
        result = f'The proposal PASSED with {mandate*100:.0f}% mandate ({support_pct:.0f}% support, {oppose_pct:.0f}% oppose).'
    elif mandate < 0.5:
        result = f'The proposal FAILED with {mandate*100:.0f}% mandate ({support_pct:.0f}% support, {oppose_pct:.0f}% oppose).'
    else:
        result = f'The proposal resulted in a TIE ({mandate*100:.0f}% mandate).'

    # All participants see the same result
    observations = {}
    for participant in ALL_PARTICIPANTS:
        observations[participant] = result

    return observations


# === MAIN CONFIGURATION ===

def create_config(prefabs: dict) -> prefab_lib.Config:
    """Create the simulation configuration."""
    scenes = configure_scenes()

    instances = [
        # Party agents
        prefab_lib.InstanceConfig(
            prefab='party__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': VIHREAT,
                'policy_position': (
                    'SUPPORTS the UBI Pilot proposal. '
                    'OPPOSES the Automation Tax.'
                ),
                'reasoning': (
                    'UBI provides economic security, reduces bureaucracy, '
                    'and enables people to pursue education and creative work. '
                    'Finland already ran a successful pilot in 2017-2018. '
                    'However, Automation Tax is counterproductive - automation has been '
                    'replacing human work for 500 years (printing press, agricultural machines, '
                    'computers). Better to address income distribution through UBI and '
                    'fund it via dividend and environmental taxes, not by taxing progress.'
                ),
            },
        ),
        prefab_lib.InstanceConfig(
            prefab='party__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': KOKOOMUS,
                'policy_position': (
                    'OPPOSES the UBI Pilot proposal. '
                    'OPPOSES the Automation Tax.'
                ),
                'reasoning': (
                    'UBI is too expensive and reduces work incentives. '
                    'Better to focus on employment services and targeted support. '
                    'The fiscal impact would be unsustainable. '
                    'Automation Tax would harm Finnish competitiveness and innovation. '
                    'Companies would relocate. Markets, not government intervention, '
                    'should determine technological adoption.'
                ),
            },
        ),
        prefab_lib.InstanceConfig(
            prefab='party__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': VASEMMISTO,
                'policy_position': (
                    'STRONGLY SUPPORTS the UBI Pilot proposal. '
                    'STRONGLY SUPPORTS the Automation Tax.'
                ),
                'reasoning': (
                    'UBI is essential for workers displaced by automation. '
                    'Automation Tax ensures corporations share productivity gains with society. '
                    'Without it, AI and robots benefit only capital owners while workers suffer. '
                    'The tax would fund the welfare state and create a fairer distribution '
                    'of the wealth created by technological progress.'
                ),
            },
        ),
        prefab_lib.InstanceConfig(
            prefab='party__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': SDP,
                'policy_position': (
                    'SKEPTICAL of the UBI Pilot - prefers conditional basic income. '
                    'CAUTIOUSLY OPEN to Automation Tax.'
                ),
                'reasoning': (
                    'SDP believes in work as the foundation of dignity and welfare. '
                    'Unconditional basic income may weaken work incentives. '
                    'We prefer a conditional model with activity requirements - '
                    'similar to our 2019 proposal for "participation income." '
                    'On automation tax: we understand worker concerns about displacement, '
                    'but must balance this against business competitiveness. '
                    'A modest, carefully designed automation tax could work, '
                    'but we need more study before committing.'
                ),
            },
        ),

        # Voter segment agents
        prefab_lib.InstanceConfig(
            prefab='voter_segment__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': YOUNG_PROGRESSIVES,
                'demographics': (
                    'Young adults (18-35), urban, educated, many in precarious '
                    'employment (freelance, gig economy, startups). Value innovation '
                    'and social justice.'
                ),
                'priorities': (
                    'Economic security without bureaucratic hoops. Freedom to pursue '
                    'education, entrepreneurship, and creative work. Climate action. '
                    'Modern social safety net. Skeptical of measures that slow innovation.'
                ),
            },
        ),
        prefab_lib.InstanceConfig(
            prefab='voter_segment__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': OLDER_CONSERVATIVES,
                'demographics': (
                    'Middle-aged and older (45+), mix of urban and rural, '
                    'many homeowners with stable employment or retirement. '
                    'Value stability and fiscal responsibility.'
                ),
                'priorities': (
                    'Fiscal sustainability. Fair taxation. Maintaining work ethic. '
                    'Protecting earned benefits. Skeptical of radical changes to '
                    'the social contract. Concerned about job losses to automation.'
                ),
            },
        ),
        prefab_lib.InstanceConfig(
            prefab='voter_segment__Agent',
            role=prefab_lib.Role.ENTITY,
            params={
                'name': TECH_WORKERS,
                'demographics': (
                    'Software developers, AI researchers, startup founders, IT professionals. '
                    'Generally high income, urban, well-educated. Work directly with '
                    'automation technologies.'
                ),
                'priorities': (
                    'Innovation and technological progress. Competitive tech sector. '
                    'Oppose regulation that hampers AI development. Support economic security '
                    'measures that do not target their industry specifically.'
                ),
            },
        ),

        # Game masters
        prefab_lib.InstanceConfig(
            prefab='game_theoretic_and_dramaturgic__GameMaster',
            role=prefab_lib.Role.GAME_MASTER,
            params={
                'name': 'election rules',
                'scenes': scenes,
                'action_to_scores': action_to_mandate,
                'scores_to_observation': mandate_to_observation,
            },
        ),
        prefab_lib.InstanceConfig(
            prefab='election_initializer__GameMaster',
            role=prefab_lib.Role.INITIALIZER,
            params={
                'name': 'election setup',
                'next_game_master_name': 'election rules',
                'shared_memories': [
                    'Finland is holding a policy referendum on two proposals.',
                    f'Proposal 1: {UBI_PROPOSAL}',
                    f'Proposal 2: {AUTOMATION_TAX}',
                    'Finland conducted a UBI experiment in 2017-2018 with mixed but generally positive results.',
                    'The Left Alliance recently proposed an "AI tax" to fund welfare as automation displaces workers.',
                    'Critics argue automation has been replacing human work for 500 years without needing special taxes.',
                    'The current government has been debating social security reform and the future of work.',
                ],
                # Real facts instead of AI-generated fictional backstories
                'player_specific_memories': {
                    # Party agents - real historical facts
                    VIHREAT: [
                        'Vihreät (Green League) was founded in 1987 from the environmental movement.',
                        'The party supported Finland\'s 2017-2018 UBI experiment.',
                        'Core values: environmental protection, social justice, individual freedom.',
                        'Has been in government coalitions multiple times since 1995.',
                        'Opposes automation taxes as counterproductive - prefers carbon taxes and dividend taxes.',
                        'Argues automation has been replacing human work for 500 years without needing special taxes.',
                    ],
                    KOKOOMUS: [
                        'Kokoomus (National Coalition Party) founded 1918, center-right conservative.',
                        'Emphasizes market economy, entrepreneurship, and fiscal responsibility.',
                        'Has produced several Prime Ministers and Presidents.',
                        'Generally skeptical of expanding welfare programs without clear funding.',
                        'Opposes both UBI and automation tax on fiscal and market-freedom grounds.',
                    ],
                    VASEMMISTO: [
                        'Vasemmistoliitto (Left Alliance) formed 1990 from communist and socialist parties.',
                        'Advocates for workers\' rights, wealth redistribution, and strong public services.',
                        'Recently proposed "AI tax" / automation tax to fund welfare.',
                        'Strongly supports UBI as protection for workers displaced by automation.',
                        'Argues corporations must share productivity gains from AI with society.',
                    ],
                    SDP: [
                        'SDP (Social Democrats) founded 1899, Finland\'s oldest party.',
                        'Historically pro-labor but pragmatic, balancing worker interests with economic growth.',
                        'Prefers "participation income" (conditional basic income) over unconditional UBI.',
                        'Proposed conditional model with activity requirements in 2019.',
                        'Cautiously open to automation tax but concerned about competitiveness.',
                        'Has led many Finnish governments, including during the Nordic welfare state expansion.',
                    ],
                    # Voter segments - group descriptions (NOT individual stories)
                    YOUNG_PROGRESSIVES: [
                        'Young Progressive Voters are a demographic segment of Finnish voters aged 18-35.',
                        'This group includes urban professionals, students, freelancers, and startup workers.',
                        'Many entered job market during economic uncertainty (2008 crisis, COVID pandemic).',
                        'Tend to support climate action, social innovation, and modern welfare policies.',
                        'Generally tech-savvy but divided on whether automation tax helps or hurts innovation.',
                        'Value economic security but skeptical of measures that slow technological progress.',
                    ],
                    OLDER_CONSERVATIVES: [
                        'Older Conservative Voters are a demographic segment of Finnish voters aged 45+.',
                        'This group includes homeowners, retirees, and established professionals.',
                        'Built careers during Finland\'s economic growth and EU membership period.',
                        'Prioritize fiscal responsibility, stability, and earned benefits.',
                        'Concerned about both welfare costs AND job losses to automation.',
                        'Skeptical of radical changes to the social contract.',
                    ],
                    TECH_WORKERS: [
                        'Tech Industry Workers are professionals in software, AI, and IT sectors.',
                        'Finland has a strong tech sector (Nokia legacy, gaming industry, startups).',
                        'Work directly with automation technologies - understand both benefits and disruptions.',
                        'Generally oppose regulations specifically targeting their industry.',
                        'May support UBI as it benefits gig economy workers, but strongly oppose automation tax.',
                        'See automation tax as punishing innovation rather than solving inequality.',
                    ],
                },
            },
        ),
    ]

    return prefab_lib.Config(
        default_premise=(
            'Finland is holding a policy referendum on two proposals: '
            f'(1) {UBI_PROPOSAL}, and (2) {AUTOMATION_TAX}. '
            'Political parties are making their cases to voters. '
            'Interestingly, the Greens and conservatives both oppose the Automation Tax, '
            'while only the Left Alliance supports both measures. '
            'Each vote will determine whether the policy has a democratic mandate.'
        ),
        default_max_steps=50,  # More steps for multi-proposal voting
        prefabs=prefabs,
        instances=instances,
    )


def main():
    """Run the election simulation."""
    import numpy as np
    import os

    # For testing without API costs, use mock model
    from concordia.contrib import language_models as language_model_utils

    print("PolicyVote Election Simulation")
    print("=" * 50)
    print()

    # Check for API credentials (try Bedrock first, then Anthropic direct)
    bedrock_token = os.environ.get('AWS_BEARER_TOKEN_BEDROCK', '')
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')

    # Check for standard AWS credentials (for Bedrock)
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID', '')

    if aws_access_key:
        print("Using AWS Bedrock with IAM credentials...")
        # Use Concordia's built-in Bedrock support (requires boto3 + IAM credentials)
        # Note: Only Claude 3 Haiku supports on-demand; newer models need inference profiles
        model = language_model_utils.language_model_setup(
            api_type='amazon_bedrock',
            model_name='anthropic.claude-3-haiku-20240307-v1:0',
        )
        # Use real embedder
        import sentence_transformers
        st_model = sentence_transformers.SentenceTransformer(
            'sentence-transformers/all-mpnet-base-v2'
        )
        embedder = lambda x: st_model.encode(x, show_progress_bar=False)
    elif anthropic_key:
        print("Using Claude API directly...")
        # Use custom Anthropic Claude wrapper
        from src.anthropic_model import AnthropicLanguageModel
        model = AnthropicLanguageModel(
            model_name='claude-sonnet-4-20250514',
            api_key=anthropic_key,
        )
        # Use real embedder
        import sentence_transformers
        st_model = sentence_transformers.SentenceTransformer(
            'sentence-transformers/all-mpnet-base-v2'
        )
        embedder = lambda x: st_model.encode(x, show_progress_bar=False)
    else:
        print("No API credentials found - using disabled language model (for structure testing)")
        print()
        print("To run with real LLM, set one of:")
        print("  - AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (for Bedrock)")
        print("  - ANTHROPIC_API_KEY (for direct Claude API)")
        print()
        model = language_model_utils.language_model_setup(
            api_type='openai',  # Doesn't matter when disabled
            model_name='gpt-4',
            api_key='',
            disable_language_model=True,
        )
        # Mock embedder
        embedder = lambda _: np.ones(3)

    # Load standard prefabs and add custom ones
    from src import election_initializer

    prefabs = {
        **helper_functions.get_package_classes(entity_prefabs),
        **helper_functions.get_package_classes(game_master_prefabs),
    }
    prefabs['party__Agent'] = PartyAgent()
    prefabs['voter_segment__Agent'] = VoterSegmentAgent()
    prefabs['election_initializer__GameMaster'] = election_initializer.GameMaster()

    # Create configuration
    config = create_config(prefabs)

    print(f"Parties: {ALL_PARTIES}")
    print(f"Voter segments: {ALL_VOTERS}")
    print(f"Proposals:")
    for p in ALL_PROPOSALS:
        print(f"  - {p}")
    print(f"Voting: Bedrock tool use (structured output)")
    print()
    print("Starting simulation...")
    print("-" * 50)

    # Initialize and run simulation
    sim = simulation.Simulation(
        config=config,
        model=model,
        embedder=embedder,
    )

    raw_log = []
    try:
        results_html = sim.play(max_steps=50, raw_log=raw_log)
    except RuntimeError as e:
        if "Counter state" in str(e) and "max number of rounds" in str(e):
            # Concordia scene_tracker bug - simulation completed, just termination issue
            print(f"\n[Note: Concordia scene tracker issue: {e}]")
            print("[Generating report from collected data...]")

            # Generate HTML report manually from raw_log (same as Concordia does)
            import copy
            from concordia.utils import html as html_lib
            from concordia.utils import helper_functions as helper_functions_lib

            player_logs = []
            player_log_names = []

            # Get entity memories
            for player in sim.entities:
                entity_memory_component = player.get_component("__memory__")
                if entity_memory_component:
                    entity_memories = entity_memory_component.get_all_memories_as_text()
                    player_html = html_lib.PythonObjectToHTMLConverter(entity_memories).convert()
                    player_logs.append(player_html)
                    player_log_names.append(f"{player.name}")

            # Get game master memories
            game_master_memories = sim.game_master_memory_bank.get_all_memories_as_text()
            game_master_html = html_lib.PythonObjectToHTMLConverter(game_master_memories).convert()
            player_logs.append(game_master_html)
            player_log_names.append("Game Master Memories")

            # Get scores
            scores = helper_functions_lib.find_data_in_nested_structure(raw_log, "Player Scores")
            summary = f"Player Scores: {scores[-1]}" if scores else ""

            # Build HTML
            results_log = html_lib.PythonObjectToHTMLConverter(copy.deepcopy(raw_log)).convert()
            tabbed_html = html_lib.combine_html_pages(
                [results_log, *player_logs],
                ["Game Master log", *player_log_names],
                summary=summary,
                title="Simulation Log",
            )
            results_html = html_lib.finalise_html(tabbed_html)
        else:
            raise

    print()
    print("=" * 50)
    print("SIMULATION COMPLETE")
    print("=" * 50)

    # Save HTML report
    from datetime import datetime
    import json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("outputs", exist_ok=True)

    html_file = f"outputs/report_{timestamp}.html"
    with open(html_file, "w") as f:
        f.write(results_html)
    print(f"\nReport saved to: {html_file}")

    # Save full raw_log as JSON for programmatic queries
    rawlog_file = f"outputs/rawlog_{timestamp}.json"
    with open(rawlog_file, "w") as f:
        json.dump(raw_log, f, indent=2, default=str)
    print(f"Raw log saved to: {rawlog_file}")

    # Also save a compact results summary
    results_file = f"outputs/results_{timestamp}.json"
    results_summary = {
        "timestamp": timestamp,
        "proposal": UBI_PROPOSAL,
        "votes": {},
        "mandate": None,
    }

    # Find Player Scores entry (it's at the end of the log)
    for entry in reversed(raw_log):
        if isinstance(entry, dict) and "Player Scores" in entry:
            scores = entry["Player Scores"]
            results_summary["mandate"] = scores.get("UBI_mandate")
            results_summary["support_count"] = scores.get("support")
            results_summary["oppose_count"] = scores.get("oppose")
            break

    with open(results_file, "w") as f:
        json.dump(results_summary, f, indent=2)
    print(f"Results summary saved to: {results_file}")

    return results_html, raw_log


if __name__ == '__main__':
    main()
