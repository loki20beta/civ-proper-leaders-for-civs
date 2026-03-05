"""OpenRouter API client for Gemini image generation.

Uses OpenRouter's OpenAI-compatible chat completions endpoint with
google/gemini-3.1-flash-image-preview (Nano Banana 2) for multi-image
reference-based image generation.
"""

from __future__ import annotations

import base64
import io
import os
import time
import json
import requests
from PIL import Image

# Load API key from .env file
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3-pro-image-preview"


def _load_api_key() -> str:
    """Load API key from .env file."""
    if os.path.isfile(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1]
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    raise ValueError("No API key found. Set OPENROUTER_API_KEY in ai_generator/.env or environment.")


def _image_to_base64(img: Image.Image) -> str:
    """Convert PIL Image to base64 data URI."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _base64_to_image(data_uri: str) -> Image.Image:
    """Convert base64 data URI to PIL Image."""
    # Handle both raw base64 and data URI format
    if data_uri.startswith("data:"):
        b64 = data_uri.split(",", 1)[1]
    else:
        b64 = data_uri
    img_data = base64.b64decode(b64)
    return Image.open(io.BytesIO(img_data))


class OpenRouterClient:
    """Client for generating images via OpenRouter's Gemini endpoint."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or _load_api_key()
        self.model = model
        self._call_count = 0
        self._total_cost = 0.0

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def total_cost(self) -> float:
        return self._total_cost

    def _make_request(self, messages: list[dict], max_retries: int = 5) -> dict:
        """Make an API request with retry logic.

        Args:
            messages: Chat messages array
            max_retries: Maximum retry attempts on failure

        Returns:
            The full API response dict
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/authentic-leaders-mod",
            "X-Title": "Authentic Leaders Mod"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "modalities": ["image", "text"],
            "image_config": {
                "output_mime_type": "image/png"
            }
        }

        for attempt in range(max_retries):
            try:
                resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)

                if resp.status_code == 429:
                    # Rate limited — exponential backoff
                    wait = min(2 ** attempt * 5, 60)
                    print(f"  Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if resp.status_code == 404:
                    raise RuntimeError(
                        f"Model '{self.model}' not found on OpenRouter (404). "
                        "Check model ID at https://openrouter.ai/models"
                    )

                if resp.status_code == 402:
                    raise RuntimeError(
                        "OpenRouter account has insufficient credits (402 Payment Required). "
                        "Add funds at https://openrouter.ai/settings/credits"
                    )

                if resp.status_code >= 500:
                    # Server error — retry
                    wait = min(2 ** attempt * 3, 30)
                    print(f"  Server error {resp.status_code}. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()

                result = resp.json()
                self._call_count += 1

                # Track cost if available
                usage = result.get("usage", {})
                if "total_cost" in usage:
                    self._total_cost += usage["total_cost"]

                return result

            except requests.exceptions.Timeout:
                wait = min(2 ** attempt * 5, 60)
                print(f"  Timeout. Retrying in {wait}s...")
                time.sleep(wait)
            except requests.exceptions.ConnectionError:
                wait = min(2 ** attempt * 3, 30)
                print(f"  Connection error. Retrying in {wait}s...")
                time.sleep(wait)

        raise RuntimeError(f"Failed after {max_retries} retries")

    def _extract_image(self, response: dict) -> Image.Image | None:
        """Extract generated image from API response.

        Gemini image responses can come in different formats:
        1. choices[0].message.images[].image_url.url (base64)
        2. choices[0].message.content with inline_data
        3. choices[0].message.content as array with image parts
        """
        try:
            message = response["choices"][0]["message"]

            # Format 1: images array
            if "images" in message:
                for img_data in message["images"]:
                    url = img_data.get("image_url", {}).get("url", "")
                    if url:
                        return _base64_to_image(url)

            # Format 2: content as array with image parts
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url:
                            return _base64_to_image(url)
                    elif part.get("type") == "inline_data":
                        data = part.get("data", "")
                        if data:
                            return _base64_to_image(data)

            # Format 3: content as string with embedded base64
            if isinstance(content, str) and "base64" in content:
                # Try to extract base64 data
                import re
                match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', content)
                if match:
                    return _base64_to_image(match.group(0))

        except (KeyError, IndexError) as e:
            print(f"  Warning: Could not extract image from response: {e}")

        # Log what we got instead of an image
        try:
            message = response["choices"][0]["message"]
            content = message.get("content")
            if isinstance(content, str):
                print(f"  Model response text: {content[:200]}")
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        print(f"  Model response text: {part['text'][:200]}")
        except (KeyError, IndexError):
            pass

        return None

    def generate_image(self, prompt: str, ref_images: list[Image.Image] | None = None) -> Image.Image | None:
        """Generate a single image from prompt and optional reference images.

        Args:
            prompt: Text prompt for generation
            ref_images: Optional list of PIL reference images

        Returns:
            Generated PIL Image, or None on failure
        """
        content = []
        content.append({"type": "text", "text": prompt})

        if ref_images:
            for img in ref_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": _image_to_base64(img)}
                })

        messages = [{"role": "user", "content": content}]
        response = self._make_request(messages)
        return self._extract_image(response)

    def create_chat_session(self) -> "ChatSession":
        """Create a multi-turn chat session for consistent generation."""
        return ChatSession(self)


class ChatSession:
    """Multi-turn chat session for generating related images with consistency.

    Used to generate loading screen + 3 icon headshots in a single
    conversation, maintaining visual consistency across all outputs.
    """

    def __init__(self, client: OpenRouterClient):
        self._client = client
        self._messages: list[dict] = []

    def send(self, prompt: str, ref_images: list[Image.Image] | None = None) -> Image.Image | None:
        """Send a message in the chat and get an image response.

        First call includes reference images. Subsequent calls continue
        the conversation for consistent style/identity.
        """
        content = []
        content.append({"type": "text", "text": prompt})

        if ref_images:
            for img in ref_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": _image_to_base64(img)}
                })

        self._messages.append({"role": "user", "content": content})

        response = self._client._make_request(self._messages)

        # Add assistant response to maintain conversation
        if "choices" in response and response["choices"]:
            assistant_msg = response["choices"][0].get("message", {})
            self._messages.append({
                "role": "assistant",
                "content": assistant_msg.get("content", "Image generated.")
            })

        return self._client._extract_image(response)
