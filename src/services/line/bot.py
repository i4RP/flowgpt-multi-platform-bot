"""
LINE bot integration for FlowGPT chat.
"""
import asyncio
import logging
from typing import Optional

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    PushMessageRequest,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    UnfollowEvent,
)
from linebot.v3.exceptions import InvalidSignatureError

from ...core.chat_client import ChatClient
from ...core.config import LineConfig

logger = logging.getLogger(__name__)


class LineBot:
    """LINE bot that integrates with FlowGPT/OpenAI chat."""
    
    def __init__(self, config: LineConfig, chat_client: ChatClient):
        self.config = config
        self.chat_client = chat_client
        
        configuration = Configuration(access_token=config.channel_access_token)
        self.api_client = AsyncApiClient(configuration)
        self.messaging_api = AsyncMessagingApi(self.api_client)
        self.handler = WebhookHandler(config.channel_secret)
        
        self._setup_handlers()
    
    def _get_conversation_id(self, user_id: str, source_type: str = "user") -> str:
        """Generate a unique conversation ID."""
        return f"line_{source_type}_{user_id}"
    
    def _setup_handlers(self) -> None:
        """Set up event handlers."""
        
        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_text_message(event):
            asyncio.create_task(self._handle_text_message_async(event))
        
        @self.handler.add(FollowEvent)
        def handle_follow(event):
            asyncio.create_task(self._handle_follow_async(event))
        
        @self.handler.add(UnfollowEvent)
        def handle_unfollow(event):
            asyncio.create_task(self._handle_unfollow_async(event))
    
    async def _handle_text_message_async(self, event: MessageEvent) -> None:
        """Handle incoming text messages."""
        user_id = event.source.user_id
        text = event.message.text.strip()
        reply_token = event.reply_token
        
        source_type = event.source.type
        conversation_id = self._get_conversation_id(user_id, source_type)
        
        if text.startswith("/"):
            await self._handle_command(text, conversation_id, reply_token, user_id)
        else:
            await self._handle_chat(text, conversation_id, reply_token)
    
    async def _handle_command(
        self,
        text: str,
        conversation_id: str,
        reply_token: str,
        user_id: str
    ) -> None:
        """Handle bot commands."""
        parts = text[1:].split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "help":
            response = (
                "FlowGPT Bot Commands:\n\n"
                "/help - Show this help message\n"
                "/clear - Clear conversation history\n"
                "/prompt <text> - Set custom system prompt\n"
                "/search <query> - Search FlowGPT prompts\n"
                "/load <prompt_id> - Load a FlowGPT prompt\n\n"
                "Just send a message to chat with the AI!"
            )
            await self._reply(reply_token, response)
        
        elif command == "clear":
            self.chat_client.clear_conversation(conversation_id)
            await self._reply(reply_token, "Conversation history cleared!")
        
        elif command == "prompt":
            if not args:
                await self._reply(
                    reply_token,
                    "Please provide a system prompt.\nUsage: /prompt <your prompt>"
                )
                return
            
            self.chat_client.set_system_prompt(conversation_id, args)
            self.chat_client.clear_conversation(conversation_id)
            
            preview = args[:100] + "..." if len(args) > 100 else args
            await self._reply(
                reply_token,
                f"System prompt updated!\n\nNew prompt: {preview}"
            )
        
        elif command == "search":
            if not args:
                await self._reply(
                    reply_token,
                    "Please provide a search query.\nUsage: /search <query>"
                )
                return
            
            await self._reply(reply_token, f"Searching for: {args}...")
            
            prompts = await self.chat_client.search_flowgpt_prompts(args)
            
            if not prompts:
                await self._push_message(user_id, "No prompts found.")
                return
            
            response = "Found prompts:\n\n"
            for i, prompt in enumerate(prompts[:5], 1):
                title = prompt.get("title", "Untitled")
                prompt_id = prompt.get("id", "")
                description = prompt.get("description", "")[:80]
                response += f"{i}. {title}\nID: {prompt_id}\n{description}...\n\n"
            
            response += "Use /load <prompt_id> to load a prompt."
            await self._push_message(user_id, response)
        
        elif command == "load":
            if not args:
                await self._reply(
                    reply_token,
                    "Please provide a prompt ID.\nUsage: /load <prompt_id>"
                )
                return
            
            await self._reply(reply_token, f"Loading prompt: {args}...")
            
            system_prompt = await self.chat_client.load_flowgpt_prompt(args)
            
            if system_prompt:
                self.chat_client.set_system_prompt(conversation_id, system_prompt)
                self.chat_client.clear_conversation(conversation_id)
                
                preview = system_prompt[:150] + "..." if len(system_prompt) > 150 else system_prompt
                await self._push_message(
                    user_id,
                    f"Prompt loaded successfully!\n\nPreview: {preview}"
                )
            else:
                await self._push_message(
                    user_id,
                    "Could not load the prompt. Please check the ID and try again."
                )
        
        else:
            await self._reply(
                reply_token,
                f"Unknown command: /{command}\nUse /help for available commands."
            )
    
    async def _handle_chat(
        self,
        text: str,
        conversation_id: str,
        reply_token: str
    ) -> None:
        """Handle regular chat messages."""
        try:
            response = await self.chat_client.chat(conversation_id, text)
            
            if len(response) > 5000:
                response = response[:4997] + "..."
            
            await self._reply(reply_token, response)
        except Exception as e:
            logger.error(f"Error handling chat: {e}")
            await self._reply(
                reply_token,
                "Sorry, I encountered an error. Please try again."
            )
    
    async def _handle_follow_async(self, event: FollowEvent) -> None:
        """Handle when a user follows the bot."""
        user_id = event.source.user_id
        reply_token = event.reply_token
        
        welcome_message = (
            "Welcome to FlowGPT Bot!\n\n"
            "I'm an AI assistant powered by FlowGPT prompts.\n\n"
            "Commands:\n"
            "/help - Show help\n"
            "/clear - Clear history\n"
            "/prompt <text> - Set prompt\n"
            "/search <query> - Search prompts\n"
            "/load <id> - Load prompt\n\n"
            "Just send a message to start chatting!"
        )
        
        await self._reply(reply_token, welcome_message)
    
    async def _handle_unfollow_async(self, event: UnfollowEvent) -> None:
        """Handle when a user unfollows the bot."""
        user_id = event.source.user_id
        conversation_id = self._get_conversation_id(user_id)
        self.chat_client.delete_conversation(conversation_id)
        logger.info(f"User {user_id} unfollowed, conversation deleted")
    
    async def _reply(self, reply_token: str, text: str) -> None:
        """Send a reply message."""
        try:
            await self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)]
                )
            )
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
    
    async def _push_message(self, user_id: str, text: str) -> None:
        """Send a push message to a user."""
        try:
            await self.messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=text)]
                )
            )
        except Exception as e:
            logger.error(f"Error sending push message: {e}")
    
    def handle_webhook(self, body: str, signature: str) -> None:
        """Handle incoming webhook from LINE."""
        try:
            self.handler.handle(body, signature)
        except InvalidSignatureError:
            logger.error("Invalid signature in webhook")
            raise
    
    async def close(self) -> None:
        """Close the API client."""
        await self.api_client.close()


async def create_line_bot(config: LineConfig, chat_client: ChatClient) -> LineBot:
    """Create and configure a LINE bot instance."""
    bot = LineBot(config, chat_client)
    return bot
