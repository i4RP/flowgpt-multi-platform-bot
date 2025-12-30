"""
Telegram bot integration for FlowGPT chat.
"""
import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ...core.chat_client import ChatClient
from ...core.config import TelegramConfig

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that integrates with FlowGPT/OpenAI chat."""
    
    def __init__(self, config: TelegramConfig, chat_client: ChatClient):
        self.config = config
        self.chat_client = chat_client
        self.application: Optional[Application] = None
    
    def _get_conversation_id(self, update: Update) -> str:
        """Generate a unique conversation ID for the chat."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else 0
        return f"telegram_{chat_id}_{user_id}"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        welcome_message = (
            "Welcome to FlowGPT Bot!\n\n"
            "I'm an AI assistant powered by FlowGPT prompts.\n\n"
            "Commands:\n"
            "/start - Show this welcome message\n"
            "/help - Show help information\n"
            "/clear - Clear conversation history\n"
            "/prompt <text> - Set a custom system prompt\n"
            "/search <query> - Search FlowGPT prompts\n"
            "/load <prompt_id> - Load a FlowGPT prompt\n\n"
            "Just send me a message to start chatting!"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = (
            "FlowGPT Bot Help\n\n"
            "Available Commands:\n"
            "/start - Show welcome message\n"
            "/help - Show this help message\n"
            "/clear - Clear your conversation history\n"
            "/prompt <text> - Set a custom system prompt for the AI\n"
            "/search <query> - Search for prompts on FlowGPT\n"
            "/load <prompt_id> - Load a specific FlowGPT prompt\n\n"
            "Tips:\n"
            "- Just type your message to chat with the AI\n"
            "- Use /clear to start a fresh conversation\n"
            "- Use /prompt to customize the AI's behavior"
        )
        await update.message.reply_text(help_message)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /clear command."""
        conversation_id = self._get_conversation_id(update)
        self.chat_client.clear_conversation(conversation_id)
        await update.message.reply_text("Conversation history cleared!")
    
    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /prompt command to set custom system prompt."""
        if not context.args:
            await update.message.reply_text(
                "Please provide a system prompt.\n"
                "Usage: /prompt <your system prompt>"
            )
            return
        
        system_prompt = " ".join(context.args)
        conversation_id = self._get_conversation_id(update)
        self.chat_client.set_system_prompt(conversation_id, system_prompt)
        self.chat_client.clear_conversation(conversation_id)
        
        await update.message.reply_text(
            f"System prompt updated!\n\n"
            f"New prompt: {system_prompt[:100]}{'...' if len(system_prompt) > 100 else ''}"
        )
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search command to search FlowGPT prompts."""
        if not context.args:
            await update.message.reply_text(
                "Please provide a search query.\n"
                "Usage: /search <query>"
            )
            return
        
        query = " ".join(context.args)
        await update.message.reply_text(f"Searching for: {query}...")
        
        prompts = await self.chat_client.search_flowgpt_prompts(query)
        
        if not prompts:
            await update.message.reply_text("No prompts found.")
            return
        
        response = "Found prompts:\n\n"
        for i, prompt in enumerate(prompts[:5], 1):
            title = prompt.get("title", "Untitled")
            prompt_id = prompt.get("id", "")
            description = prompt.get("description", "")[:100]
            response += f"{i}. {title}\n   ID: {prompt_id}\n   {description}...\n\n"
        
        response += "Use /load <prompt_id> to load a prompt."
        await update.message.reply_text(response)
    
    async def load_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /load command to load a FlowGPT prompt."""
        if not context.args:
            await update.message.reply_text(
                "Please provide a prompt ID.\n"
                "Usage: /load <prompt_id>"
            )
            return
        
        prompt_id = context.args[0]
        await update.message.reply_text(f"Loading prompt: {prompt_id}...")
        
        system_prompt = await self.chat_client.load_flowgpt_prompt(prompt_id)
        
        if system_prompt:
            conversation_id = self._get_conversation_id(update)
            self.chat_client.set_system_prompt(conversation_id, system_prompt)
            self.chat_client.clear_conversation(conversation_id)
            await update.message.reply_text(
                f"Prompt loaded successfully!\n\n"
                f"Preview: {system_prompt[:200]}{'...' if len(system_prompt) > 200 else ''}"
            )
        else:
            await update.message.reply_text(
                "Could not load the prompt. Please check the ID and try again."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular text messages."""
        user_message = update.message.text
        conversation_id = self._get_conversation_id(update)
        
        await update.message.chat.send_action("typing")
        
        try:
            response = await self.chat_client.chat(conversation_id, user_message)
            
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.message.reply_text(response[i:i+4096])
            else:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your message. Please try again."
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Update {update} caused error {context.error}")
    
    def setup(self) -> Application:
        """Set up the Telegram bot application."""
        self.application = Application.builder().token(self.config.bot_token).build()
        
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("prompt", self.prompt_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("load", self.load_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        self.application.add_error_handler(self.error_handler)
        
        return self.application
    
    async def run_polling(self) -> None:
        """Run the bot using polling."""
        if not self.application:
            self.setup()
        
        logger.info("Starting Telegram bot with polling...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
    
    async def run_webhook(self, webhook_url: str, port: int = 8443) -> None:
        """Run the bot using webhooks."""
        if not self.application:
            self.setup()
        
        logger.info(f"Starting Telegram bot with webhook at {webhook_url}...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=self.config.bot_token,
            webhook_url=f"{webhook_url}/{self.config.bot_token}",
            drop_pending_updates=True,
        )
        
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


async def create_telegram_bot(config: TelegramConfig, chat_client: ChatClient) -> TelegramBot:
    """Create and configure a Telegram bot instance."""
    bot = TelegramBot(config, chat_client)
    bot.setup()
    return bot
