"""Bedrock language model using bearer token authentication."""

import base64
from collections.abc import Collection, Sequence
import json
import os
import urllib.request
import urllib.error

from concordia.language_model import language_model


_MAX_MULTIPLE_CHOICE_ATTEMPTS = 20


class BedrockBearerLanguageModel(language_model.LanguageModel):
    """Language Model that uses Bedrock via bearer token authentication."""

    def __init__(
        self,
        model_name: str = 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        *,
        bearer_token: str | None = None,
        region: str = 'us-east-1',
    ):
        """Initialize the Bedrock language model.

        Args:
            model_name: The Bedrock model ID to use.
            bearer_token: The bearer token. If None, uses AWS_BEARER_TOKEN_BEDROCK env var.
            region: AWS region for the Bedrock endpoint.
        """
        if bearer_token is None:
            bearer_token = os.environ.get('AWS_BEARER_TOKEN_BEDROCK', '')
        if not bearer_token:
            raise ValueError(
                'Bearer token required. Set AWS_BEARER_TOKEN_BEDROCK environment variable.'
            )

        self._model_name = model_name
        self._bearer_token = bearer_token
        self._region = region

        # Use provided region (don't try to parse from token)
        # Common regions: us-east-1, us-west-2, eu-west-1

        # Construct Bedrock endpoint
        self._endpoint = f'https://bedrock-runtime.{self._region}.amazonaws.com'

    def _call_bedrock(self, messages: list, system: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Make a request to Bedrock converse API."""

        url = f'{self._endpoint}/model/{self._model_name}/converse'

        payload = {
            'messages': messages,
            'system': [{'text': system}],
            'inferenceConfig': {
                'maxTokens': max_tokens,
                'temperature': temperature,
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._bearer_token}',
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['output']['message']['content'][0]['text']
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            raise RuntimeError(f'Bedrock API error {e.code}: {error_body}') from e

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
        del terminators, top_p, top_k, seed, timeout  # Not all used

        system_prompt = (
            'You always continue sentences provided by the user. '
            'You never repeat what the user already said. '
            'Respond concisely and directly.'
        )

        messages = [
            {'role': 'user', 'content': [{'text': prompt}]}
        ]

        return self._call_bedrock(messages, system_prompt, max_tokens, temperature)

    def sample_choice(
        self,
        prompt: str,
        responses: Sequence[str],
        *,
        seed: int | None = None,
    ) -> tuple[int, str, dict[str, float]]:
        """Sample a choice from given options."""
        del seed  # Not used

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

        raise language_model.InvalidResponseError(
            f'Could not get valid choice after {_MAX_MULTIPLE_CHOICE_ATTEMPTS} attempts. '
            f'Last answer: {answer}'
        )
