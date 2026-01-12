"""Anthropic Claude language model for Concordia."""

from collections.abc import Collection, Sequence
import os

import anthropic
from concordia.language_model import language_model


_MAX_MULTIPLE_CHOICE_ATTEMPTS = 20


class AnthropicLanguageModel(language_model.LanguageModel):
    """Language Model that uses Anthropic Claude models."""

    def __init__(
        self,
        model_name: str = 'claude-sonnet-4-20250514',
        *,
        api_key: str | None = None,
    ):
        """Initialize the Anthropic language model.

        Args:
            model_name: The Claude model to use.
            api_key: The API key. If None, uses ANTHROPIC_API_KEY env var.
        """
        if api_key is None:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                'API key required. Set ANTHROPIC_API_KEY environment variable.'
            )
        self._model_name = model_name
        self._client = anthropic.Anthropic(api_key=api_key)

    def sample_text(
        self,
        prompt: str,
        *,
        max_tokens: int = language_model.DEFAULT_MAX_TOKENS,
        terminators: Collection[str] = language_model.DEFAULT_TERMINATORS,
        temperature: float = language_model.DEFAULT_TEMPERATURE,
        top_p: float = language_model.DEFAULT_TOP_P,
        top_k: int = language_model.DEFAULT_TOP_K,
        timeout: float = language_model.DEFAULT_TIMEOUT_SECONDS,
        seed: int | None = None,
    ) -> str:
        """Sample text from Claude given a prompt."""
        del terminators, top_p, top_k, seed  # Not all used for Claude

        system_prompt = (
            'You always continue sentences provided by the user. '
            'You never repeat what the user already said. '
            'Respond concisely and directly.'
        )

        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            timeout=timeout,
        )

        return response.content[0].text

    def sample_choice(
        self,
        prompt: str,
        responses: Sequence[str],
        *,
        seed: int | None = None,
    ) -> tuple[int, str, dict[str, float]]:
        """Sample a choice from given options."""
        del seed  # Not used for Claude

        choice_prompt = (
            prompt
            + '\n\nRespond with EXACTLY one of these options (copy exactly):\n'
            + '\n'.join(f'- {r}' for r in responses)
            + '\n\nYour choice:'
        )

        for attempt in range(_MAX_MULTIPLE_CHOICE_ATTEMPTS):
            answer = self.sample_text(
                choice_prompt,
                max_tokens=100,
                temperature=0.3 if attempt == 0 else 0.7,
            ).strip()

            # Try to find exact match
            for idx, response in enumerate(responses):
                if response.lower() == answer.lower():
                    return idx, response, {}
                if response.lower() in answer.lower():
                    return idx, response, {}

            # If no match, try again with higher temperature

        raise language_model.InvalidResponseError(
            f'Could not get valid choice after {_MAX_MULTIPLE_CHOICE_ATTEMPTS} attempts. '
            f'Last answer: {answer}'
        )
