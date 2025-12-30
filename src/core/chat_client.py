"""
Chat client for interacting with OpenAI API.
Supports FlowGPT-style prompts as system messages.
"""
import asyncio
import json
import urllib.parse
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

import httpx

from .config import FlowGPTConfig, OpenAIConfig


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Conversation:
    messages: list[Message] = field(default_factory=list)
    system_prompt: str = ""
    
    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
    
    def to_openai_format(self) -> list[dict]:
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result
    
    def clear(self) -> None:
        self.messages.clear()


class FlowGPTClient:
    """Client for fetching prompts from FlowGPT."""
    
    BASE_URL = "https://flowgpt.com/api/trpc"
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                "Host": "flowgpt.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/json",
                "Accept": "*/*",
            },
            timeout=30.0
        )
    
    async def search_prompts(
        self,
        query: str = "",
        tag: Optional[str] = None,
        sort: Optional[str] = None,
        language: str = "en"
    ) -> list[dict]:
        """Search for prompts on FlowGPT."""
        data = {
            "0": {
                "json": {
                    "tag": tag,
                    "sort": sort,
                    "q": query if query else None,
                    "language": language
                },
                "meta": {
                    "values": {
                        "tag": ["undefined"] if tag is None else [],
                        "sort": ["undefined"] if sort is None else [],
                        "q": ["undefined"] if not query else []
                    }
                }
            }
        }
        
        encoded_data = urllib.parse.quote(json.dumps(data))
        url = f"{self.BASE_URL}/prompt.getPrompts?batch=1&input={encoded_data}"
        
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            result = response.json()
            return result[0].get("result", {}).get("data", {}).get("json", [])
        except Exception as e:
            print(f"Error searching FlowGPT prompts: {e}")
            return []
    
    async def get_prompt_by_id(self, prompt_id: str) -> Optional[dict]:
        """Get a specific prompt by ID."""
        prompts = await self.search_prompts(query=prompt_id)
        for prompt in prompts:
            if prompt.get("id") == prompt_id:
                return prompt
        return None
    
    async def close(self):
        await self.session.aclose()


class ChatClient:
    """Main chat client using OpenAI API with FlowGPT prompt support."""
    
    def __init__(self, openai_config: OpenAIConfig, flowgpt_config: FlowGPTConfig):
        self.openai_config = openai_config
        self.flowgpt_config = flowgpt_config
        self.flowgpt_client = FlowGPTClient()
        self.conversations: dict[str, Conversation] = {}
        
        self.http_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {openai_config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0
        )
    
    def get_or_create_conversation(
        self,
        conversation_id: str,
        system_prompt: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = Conversation(
                system_prompt=system_prompt or self.flowgpt_config.default_system_prompt
            )
        return self.conversations[conversation_id]
    
    def set_system_prompt(self, conversation_id: str, system_prompt: str) -> None:
        """Set the system prompt for a conversation."""
        conv = self.get_or_create_conversation(conversation_id)
        conv.system_prompt = system_prompt
    
    async def chat(
        self,
        conversation_id: str,
        user_message: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Send a message and get a response."""
        conv = self.get_or_create_conversation(conversation_id, system_prompt)
        conv.add_message("user", user_message)
        
        try:
            response = await self.http_client.post(
                "/chat/completions",
                json={
                    "model": self.openai_config.model,
                    "messages": conv.to_openai_format(),
                    "max_tokens": self.openai_config.max_tokens,
                    "temperature": self.openai_config.temperature,
                }
            )
            response.raise_for_status()
            result = response.json()
            
            assistant_message = result["choices"][0]["message"]["content"]
            conv.add_message("assistant", assistant_message)
            
            return assistant_message
        except httpx.HTTPStatusError as e:
            error_msg = f"API error: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg = f"API error: {error_detail.get('error', {}).get('message', str(e))}"
            except Exception:
                pass
            return error_msg
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def chat_stream(
        self,
        conversation_id: str,
        user_message: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream the response."""
        conv = self.get_or_create_conversation(conversation_id, system_prompt)
        conv.add_message("user", user_message)
        
        full_response = ""
        
        try:
            async with self.http_client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": self.openai_config.model,
                    "messages": conv.to_openai_format(),
                    "max_tokens": self.openai_config.max_tokens,
                    "temperature": self.openai_config.temperature,
                    "stream": True,
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                                yield content
                        except json.JSONDecodeError:
                            continue
            
            conv.add_message("assistant", full_response)
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear a conversation's history."""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].clear()
    
    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation entirely."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
    
    async def load_flowgpt_prompt(self, prompt_id: str) -> Optional[str]:
        """Load a prompt from FlowGPT and return its system message."""
        prompt = await self.flowgpt_client.get_prompt_by_id(prompt_id)
        if prompt:
            return prompt.get("initPrompt") or prompt.get("systemMessage")
        return None
    
    async def search_flowgpt_prompts(self, query: str) -> list[dict]:
        """Search for prompts on FlowGPT."""
        return await self.flowgpt_client.search_prompts(query=query)
    
    async def close(self):
        """Close all connections."""
        await self.http_client.aclose()
        await self.flowgpt_client.close()
