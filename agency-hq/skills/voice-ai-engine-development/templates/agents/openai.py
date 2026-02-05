from typing import Dict, Any, List, AsyncGenerator, Optional
import logging
from openai import AsyncOpenAI
from ..interfaces import LLMProvider

logger = logging.getLogger(__name__)

class OpenAIAgent(LLMProvider):
    """OpenAI agent implementation"""

    def __init__(self, api_key: str, model: str = "gpt-4", system_prompt: str = "You are a helpful assistant."):
        """
        Initialize OpenAI agent

        Args:
            api_key: OpenAI API key
            model: Model identifier (e.g., "gpt-4", "gpt-3.5-turbo")
            system_prompt: System prompt to define agent behavior
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        logger.info(f"Initialized OpenAI agent with model: {model}")

    async def generate_response(self, messages: List[Dict[str, str]], stream: bool = True) -> AsyncGenerator[str, None]:
        """
        Generate response from messages

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response

        Yields:
            Chunks of the generated response
        """
        # Prepend system prompt
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                stream=stream
            )

            if stream:
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            else:
                yield response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {e}", exc_info=True)
            raise
