"""AWS Bedrock Nova Sonic speech-to-speech adapter.

In MOCK_MODE this returns deterministic simulated responses. In production it
should open a Bedrock bidirectional stream to the Nova Sonic model. The exact
streaming SDK wiring (invoke_model_with_bidirectional_stream) requires valid
AWS credentials and is marked with TODOs below.
"""

from __future__ import annotations

from ..config import settings


class AWSNovaSonicService:
    def __init__(self) -> None:
        self.model_id = settings.aws_bedrock_model_id
        self.region = settings.aws_region
        self.mock = settings.mock_mode
        self._client = None
        self._connected = False

    async def connect(self) -> None:
        """Establish the Bedrock streaming session."""
        if self.mock:
            self._connected = True
            return

        # TODO(production): initialise the Bedrock runtime client and open a
        # bidirectional stream. Requires AWS credentials + the bedrock-runtime
        # async streaming API.
        #
        #   import boto3
        #   self._client = boto3.client(
        #       "bedrock-runtime", region_name=self.region,
        #       aws_access_key_id=settings.aws_access_key_id,
        #       aws_secret_access_key=settings.aws_secret_access_key,
        #   )
        #   self._stream = await self._client.invoke_model_with_bidirectional_stream(
        #       modelId=self.model_id, ...)
        self._connected = True

    async def stream_audio(self, audio_chunk: bytes) -> None:
        """Push a chunk of caller audio into the model stream."""
        if self.mock:
            return
        # TODO(production): send audio frames to the bidirectional stream.
        raise NotImplementedError("Wire Nova Sonic audio streaming for production.")

    async def generate_response(self, user_text: str) -> str:
        """Generate an assistant turn from text (used in text/demo mode)."""
        if self.mock:
            return (
                "Thanks for that — I've noted the details. "
                "(simulated Nova Sonic speech-to-speech response)"
            )
        # TODO(production): collect the model's streamed text/audio output.
        raise NotImplementedError("Wire Nova Sonic response generation.")

    async def close(self) -> None:
        self._connected = False
        if self._client is not None:
            # TODO(production): close the bidirectional stream cleanly.
            self._client = None
