"""
Slack bot integration for FlowGPT chat.
"""
import asyncio
import logging
import re
from typing import Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.web.async_client import AsyncWebClient

from ...core.chat_client import ChatClient
from ...core.config import SlackConfig

logger = logging.getLogger(__name__)


class SlackBot:
    """Slack bot that integrates with FlowGPT/OpenAI chat."""
    
    def __init__(self, config: SlackConfig, chat_client: ChatClient):
        self.config = config
        self.chat_client = chat_client
        self.app = AsyncApp(
            token=config.bot_token,
            signing_secret=config.signing_secret
        )
        self.bot_user_id: Optional[str] = None
        self._setup_handlers()
    
    def _get_conversation_id(self, channel: str, user: str) -> str:
        """Generate a unique conversation ID."""
        return f"slack_{channel}_{user}"
    
    def _setup_handlers(self) -> None:
        """Set up event handlers and commands."""
        
        @self.app.command("/flowgpt")
        async def handle_flowgpt_command(ack, command, client):
            """Handle /flowgpt slash command."""
            await ack()
            
            text = command.get("text", "").strip()
            channel = command["channel_id"]
            user = command["user_id"]
            
            if not text:
                await client.chat_postMessage(
                    channel=channel,
                    text=(
                        "*FlowGPT Bot Commands*\n\n"
                        "`/flowgpt chat <message>` - Chat with the AI\n"
                        "`/flowgpt clear` - Clear conversation history\n"
                        "`/flowgpt prompt <text>` - Set custom system prompt\n"
                        "`/flowgpt search <query>` - Search FlowGPT prompts\n"
                        "`/flowgpt load <prompt_id>` - Load a FlowGPT prompt\n"
                        "`/flowgpt help` - Show this help message"
                    )
                )
                return
            
            parts = text.split(maxsplit=1)
            subcommand = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            conversation_id = self._get_conversation_id(channel, user)
            
            if subcommand == "chat":
                if not args:
                    await client.chat_postMessage(
                        channel=channel,
                        text="Please provide a message. Usage: `/flowgpt chat <message>`"
                    )
                    return
                
                await client.chat_postMessage(
                    channel=channel,
                    text=":hourglass: Thinking..."
                )
                
                try:
                    response = await self.chat_client.chat(conversation_id, args)
                    await client.chat_postMessage(
                        channel=channel,
                        text=response
                    )
                except Exception as e:
                    logger.error(f"Error in chat: {e}")
                    await client.chat_postMessage(
                        channel=channel,
                        text="Sorry, I encountered an error. Please try again."
                    )
            
            elif subcommand == "clear":
                self.chat_client.clear_conversation(conversation_id)
                await client.chat_postMessage(
                    channel=channel,
                    text=":white_check_mark: Conversation history cleared!"
                )
            
            elif subcommand == "prompt":
                if not args:
                    await client.chat_postMessage(
                        channel=channel,
                        text="Please provide a system prompt. Usage: `/flowgpt prompt <text>`"
                    )
                    return
                
                self.chat_client.set_system_prompt(conversation_id, args)
                self.chat_client.clear_conversation(conversation_id)
                
                preview = args[:100] + "..." if len(args) > 100 else args
                await client.chat_postMessage(
                    channel=channel,
                    text=f":white_check_mark: System prompt updated!\n\n*New prompt:* {preview}"
                )
            
            elif subcommand == "search":
                if not args:
                    await client.chat_postMessage(
                        channel=channel,
                        text="Please provide a search query. Usage: `/flowgpt search <query>`"
                    )
                    return
                
                await client.chat_postMessage(
                    channel=channel,
                    text=f":mag: Searching for: {args}..."
                )
                
                prompts = await self.chat_client.search_flowgpt_prompts(args)
                
                if not prompts:
                    await client.chat_postMessage(
                        channel=channel,
                        text="No prompts found."
                    )
                    return
                
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"FlowGPT Prompts: {args}"
                        }
                    }
                ]
                
                for i, prompt in enumerate(prompts[:5], 1):
                    title = prompt.get("title", "Untitled")
                    prompt_id = prompt.get("id", "")
                    description = prompt.get("description", "")[:100]
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{i}. {title}*\nID: `{prompt_id}`\n{description}..."
                        }
                    })
                
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Use `/flowgpt load <prompt_id>` to load a prompt"
                        }
                    ]
                })
                
                await client.chat_postMessage(
                    channel=channel,
                    blocks=blocks,
                    text=f"Found {len(prompts[:5])} prompts"
                )
            
            elif subcommand == "load":
                if not args:
                    await client.chat_postMessage(
                        channel=channel,
                        text="Please provide a prompt ID. Usage: `/flowgpt load <prompt_id>`"
                    )
                    return
                
                await client.chat_postMessage(
                    channel=channel,
                    text=f":hourglass: Loading prompt: {args}..."
                )
                
                system_prompt = await self.chat_client.load_flowgpt_prompt(args)
                
                if system_prompt:
                    self.chat_client.set_system_prompt(conversation_id, system_prompt)
                    self.chat_client.clear_conversation(conversation_id)
                    
                    preview = system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt
                    await client.chat_postMessage(
                        channel=channel,
                        text=f":white_check_mark: Prompt loaded successfully!\n\n*Preview:* {preview}"
                    )
                else:
                    await client.chat_postMessage(
                        channel=channel,
                        text="Could not load the prompt. Please check the ID and try again."
                    )
            
            elif subcommand == "help":
                await client.chat_postMessage(
                    channel=channel,
                    text=(
                        "*FlowGPT Bot Help*\n\n"
                        "`/flowgpt chat <message>` - Chat with the AI assistant\n"
                        "`/flowgpt clear` - Clear your conversation history\n"
                        "`/flowgpt prompt <text>` - Set a custom system prompt\n"
                        "`/flowgpt search <query>` - Search for FlowGPT prompts\n"
                        "`/flowgpt load <prompt_id>` - Load a specific FlowGPT prompt\n"
                        "`/flowgpt help` - Show this help message\n\n"
                        "*Tips:*\n"
                        "- Mention the bot in a channel to chat directly\n"
                        "- Use `/flowgpt clear` to start a fresh conversation\n"
                        "- Use `/flowgpt prompt` to customize the AI's behavior"
                    )
                )
            
            else:
                await client.chat_postMessage(
                    channel=channel,
                    text=f"Unknown command: `{subcommand}`. Use `/flowgpt help` for available commands."
                )
        
        @self.app.event("app_mention")
        async def handle_mention(event, client, say):
            """Handle when the bot is mentioned."""
            text = event.get("text", "")
            channel = event["channel"]
            user = event["user"]
            thread_ts = event.get("thread_ts") or event["ts"]
            
            if self.bot_user_id:
                text = re.sub(f"<@{self.bot_user_id}>", "", text).strip()
            else:
                text = re.sub(r"<@\w+>", "", text).strip()
            
            if not text:
                await say(
                    text="Hello! Mention me with a message to chat, or use `/flowgpt help` for commands.",
                    thread_ts=thread_ts
                )
                return
            
            conversation_id = self._get_conversation_id(channel, user)
            
            try:
                response = await self.chat_client.chat(conversation_id, text)
                await say(text=response, thread_ts=thread_ts)
            except Exception as e:
                logger.error(f"Error handling mention: {e}")
                await say(
                    text="Sorry, I encountered an error. Please try again.",
                    thread_ts=thread_ts
                )
        
        @self.app.event("message")
        async def handle_direct_message(event, client, say):
            """Handle direct messages."""
            if event.get("channel_type") != "im":
                return
            
            if event.get("bot_id"):
                return
            
            text = event.get("text", "").strip()
            channel = event["channel"]
            user = event["user"]
            
            if not text:
                return
            
            conversation_id = self._get_conversation_id(channel, user)
            
            try:
                response = await self.chat_client.chat(conversation_id, text)
                await say(text=response)
            except Exception as e:
                logger.error(f"Error handling DM: {e}")
                await say(text="Sorry, I encountered an error. Please try again.")
    
    async def start(self) -> None:
        """Start the Slack bot using Socket Mode."""
        logger.info("Starting Slack bot with Socket Mode...")
        
        auth_response = await self.app.client.auth_test()
        self.bot_user_id = auth_response["user_id"]
        logger.info(f"Bot user ID: {self.bot_user_id}")
        
        handler = AsyncSocketModeHandler(self.app, self.config.app_token)
        await handler.start_async()


async def create_slack_bot(config: SlackConfig, chat_client: ChatClient) -> SlackBot:
    """Create and configure a Slack bot instance."""
    bot = SlackBot(config, chat_client)
    return bot


async def run_slack_bot(bot: SlackBot) -> None:
    """Run the Slack bot."""
    await bot.start()
