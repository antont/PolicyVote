"""Structured voting component using AWS Bedrock tool use for reliable vote distributions.

Uses Bedrock's converse API with tool configuration to get structured JSON output
instead of parsing text like "Support: 45%, Oppose: 40%, Abstain: 15%".
"""

import boto3
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component


# Tool configuration for Bedrock's converse API
VOTE_DISTRIBUTION_TOOL = {
    "toolSpec": {
        "name": "submit_vote_distribution",
        "description": (
            "Submit the vote distribution for this demographic segment. "
            "The percentages must sum to 100."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "support_percent": {
                        "type": "number",
                        "description": "Percentage of this demographic that supports the proposal (0-100)",
                    },
                    "oppose_percent": {
                        "type": "number",
                        "description": "Percentage of this demographic that opposes the proposal (0-100)",
                    },
                    "abstain_percent": {
                        "type": "number",
                        "description": "Percentage of this demographic that abstains (0-100)",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this demographic is divided this way",
                    },
                },
                "required": ["support_percent", "oppose_percent", "abstain_percent", "reasoning"],
            }
        },
    }
}


class StructuredVoteResult:
    """Result from structured voting."""

    def __init__(self, support: float, oppose: float, abstain: float, reasoning: str):
        self.support = support
        self.oppose = oppose
        self.abstain = abstain
        self.reasoning = reasoning

    def to_dict(self) -> dict:
        return {
            'support': self.support,
            'oppose': self.oppose,
            'abstain': self.abstain,
            'reasoning': self.reasoning,
        }

    def __str__(self) -> str:
        return f"Support: {self.support}%, Oppose: {self.oppose}%, Abstain: {self.abstain}%"


def get_structured_vote(
    client: boto3.client,
    model_id: str,
    context: str,
    proposal: str,
    segment_name: str,
) -> StructuredVoteResult:
    """Get structured vote distribution using Bedrock tool use.

    Args:
        client: boto3 bedrock-runtime client
        model_id: Bedrock model ID (e.g. 'anthropic.claude-3-haiku-20240307-v1:0')
        context: The agent's context (demographics, priorities, what they've heard)
        proposal: The proposal being voted on
        segment_name: Name of the voter segment

    Returns:
        StructuredVoteResult with percentages and reasoning
    """
    system_prompt = f"""You are simulating how a demographic segment would vote on a policy proposal.

The segment "{segment_name}" is NOT a single person - it represents many voters with diverse views.
Your job is to estimate what percentage would support, oppose, or abstain.

Consider:
- Internal divisions within this demographic
- How the arguments they've heard might sway different subgroups
- That even like-minded groups rarely vote 100% one way

You MUST use the submit_vote_distribution tool to provide your estimate."""

    user_prompt = f"""Based on the following context about {segment_name}:

{context}

How would this demographic segment vote on:
"{proposal}"

Use the submit_vote_distribution tool to provide the vote distribution as percentages that sum to 100%."""

    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        toolConfig={
            "tools": [VOTE_DISTRIBUTION_TOOL],
            "toolChoice": {"tool": {"name": "submit_vote_distribution"}},
        },
    )

    # Extract tool use from response
    for block in response.get('output', {}).get('message', {}).get('content', []):
        if 'toolUse' in block:
            tool_use = block['toolUse']
            if tool_use.get('name') == 'submit_vote_distribution':
                args = tool_use.get('input', {})
                return StructuredVoteResult(
                    support=args.get('support_percent', 0),
                    oppose=args.get('oppose_percent', 0),
                    abstain=args.get('abstain_percent', 0),
                    reasoning=args.get('reasoning', ''),
                )

    # Fallback if tool use failed
    raise ValueError(f"Failed to get structured vote from model. Response: {response}")


class StructuredVotingActComponent(entity_component.ActingComponent):
    """Act component that uses Bedrock tool use for structured voting output.

    This wraps a standard ConcatActComponent but intercepts voting actions
    to use Bedrock's tool use for reliable vote distributions.

    For non-voting actions (deliberation, etc.), delegates to the wrapped component.
    """

    def __init__(
        self,
        wrapped_act_component: entity_component.ActingComponent,
        model_id: str = 'anthropic.claude-3-haiku-20240307-v1:0',
    ):
        """Initialize the structured voting component.

        Args:
            wrapped_act_component: The original act component (e.g. ConcatActComponent)
            model_id: Bedrock model ID for structured voting
        """
        super().__init__()
        self._wrapped = wrapped_act_component
        self._model_id = model_id
        # AWS credentials come from environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self._client = boto3.client('bedrock-runtime')

    def set_entity(self, entity) -> None:
        """Set entity for both this component and wrapped component."""
        super().set_entity(entity)
        self._wrapped.set_entity(entity)

    def get_state(self) -> dict:
        """Return component state for serialization."""
        return self._wrapped.get_state()

    def set_state(self, state: dict) -> None:
        """Restore component state from serialization."""
        self._wrapped.set_state(state)

    def get_action_attempt(
        self,
        contexts: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        """Generate action using structured voting for vote actions.

        For voting action specs, uses Bedrock tool use to get structured output.
        For other action specs, delegates to wrapped component.
        """
        agent_name = self.get_entity().name

        # Check if this is a voting action
        call_to_action = action_spec.call_to_action.format(name=agent_name)
        is_voting = any(
            keyword in call_to_action.lower()
            for keyword in ['must decide how their demographic votes', 'vote on:', 'votes on:']
        )

        if is_voting and action_spec.output_type == entity_lib.OutputType.FREE:
            # Build context from component contexts
            context = '\n\n'.join(
                f"{key}:\n{value}" for key, value in contexts.items() if value
            )

            # Extract proposal from call to action
            proposal = call_to_action
            if "votes on:" in call_to_action:
                proposal = call_to_action.split("votes on:")[-1].strip()
            elif "vote on:" in call_to_action:
                proposal = call_to_action.split("vote on:")[-1].strip()

            result = get_structured_vote(
                client=self._client,
                model_id=self._model_id,
                context=context,
                proposal=proposal,
                segment_name=agent_name,
            )

            # Return in format that the parser expects
            return f"Support: {result.support}%, Oppose: {result.oppose}%, Abstain: {result.abstain}% ({result.reasoning})"

        # For non-voting actions, delegate to wrapped component
        return self._wrapped.get_action_attempt(contexts, action_spec)
