"""
Main entry point for the FlowGPT Multi-Platform Bot.
"""
import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from .core.config import load_config, AppConfig
from .core.chat_client import ChatClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BotManager:
    """Manages all bot instances."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.chat_client = ChatClient(config.openai, config.flowgpt)
        self.telegram_bot = None
        self.discord_bot = None
        self.slack_bot = None
        self.line_bot = None
        self.tasks: list[asyncio.Task] = []
    
    async def start_telegram(self) -> None:
        """Start the Telegram bot."""
        if not self.config.telegram.bot_token:
            logger.warning("Telegram bot token not configured, skipping...")
            return
        
        try:
            from .services.telegram.bot import create_telegram_bot
            self.telegram_bot = await create_telegram_bot(
                self.config.telegram,
                self.chat_client
            )
            
            if self.config.telegram.webhook_url:
                task = asyncio.create_task(
                    self.telegram_bot.run_webhook(self.config.telegram.webhook_url)
                )
            else:
                task = asyncio.create_task(self.telegram_bot.run_polling())
            
            self.tasks.append(task)
            logger.info("Telegram bot started")
        except ImportError as e:
            logger.error(f"Failed to import Telegram dependencies: {e}")
            logger.info("Install with: pip install python-telegram-bot")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    
    async def start_discord(self) -> None:
        """Start the Discord bot."""
        if not self.config.discord.bot_token:
            logger.warning("Discord bot token not configured, skipping...")
            return
        
        try:
            from .services.discord.bot import create_discord_bot, run_discord_bot
            self.discord_bot = await create_discord_bot(
                self.config.discord,
                self.chat_client
            )
            
            task = asyncio.create_task(
                run_discord_bot(self.discord_bot, self.config.discord.bot_token)
            )
            self.tasks.append(task)
            logger.info("Discord bot started")
        except ImportError as e:
            logger.error(f"Failed to import Discord dependencies: {e}")
            logger.info("Install with: pip install discord.py")
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
    
    async def start_slack(self) -> None:
        """Start the Slack bot."""
        if not self.config.slack.bot_token or not self.config.slack.app_token:
            logger.warning("Slack bot tokens not configured, skipping...")
            return
        
        try:
            from .services.slack.bot import create_slack_bot, run_slack_bot
            self.slack_bot = await create_slack_bot(
                self.config.slack,
                self.chat_client
            )
            
            task = asyncio.create_task(run_slack_bot(self.slack_bot))
            self.tasks.append(task)
            logger.info("Slack bot started")
        except ImportError as e:
            logger.error(f"Failed to import Slack dependencies: {e}")
            logger.info("Install with: pip install slack-bolt")
        except Exception as e:
            logger.error(f"Failed to start Slack bot: {e}")
    
    async def start_line(self) -> None:
        """Start the LINE bot (requires FastAPI server)."""
        if not self.config.line.channel_access_token or not self.config.line.channel_secret:
            logger.warning("LINE bot credentials not configured, skipping...")
            return
        
        try:
            from .services.line.bot import create_line_bot
            from .api.webhooks import set_line_bot
            
            self.line_bot = await create_line_bot(
                self.config.line,
                self.chat_client
            )
            set_line_bot(self.line_bot)
            logger.info("LINE bot initialized (webhook ready)")
        except ImportError as e:
            logger.error(f"Failed to import LINE dependencies: {e}")
            logger.info("Install with: pip install line-bot-sdk")
        except Exception as e:
            logger.error(f"Failed to initialize LINE bot: {e}")
    
    async def start_api_server(self) -> None:
        """Start the FastAPI server for webhooks."""
        try:
            import uvicorn
            from fastapi import FastAPI
            from .api.webhooks import router as webhooks_router
            
            app = FastAPI(
                title="FlowGPT Multi-Platform Bot",
                description="API endpoints for bot webhooks",
                version="1.0.0"
            )
            app.include_router(webhooks_router)
            
            config = uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            task = asyncio.create_task(server.serve())
            self.tasks.append(task)
            logger.info(f"API server started on {self.config.host}:{self.config.port}")
        except ImportError as e:
            logger.error(f"Failed to import FastAPI/uvicorn: {e}")
            logger.info("Install with: pip install fastapi uvicorn")
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
    
    async def start_all(self) -> None:
        """Start all configured bots."""
        logger.info("Starting FlowGPT Multi-Platform Bot...")
        
        await self.start_telegram()
        await self.start_discord()
        await self.start_slack()
        await self.start_line()
        
        if self.line_bot:
            await self.start_api_server()
        
        if not self.tasks:
            logger.error("No bots were started. Please configure at least one bot.")
            return
        
        logger.info(f"Started {len(self.tasks)} service(s)")
    
    async def stop_all(self) -> None:
        """Stop all running bots."""
        logger.info("Stopping all bots...")
        
        for task in self.tasks:
            task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        await self.chat_client.close()
        
        if self.line_bot:
            await self.line_bot.close()
        
        logger.info("All bots stopped")
    
    async def run(self) -> None:
        """Run all bots until interrupted."""
        await self.start_all()
        
        if not self.tasks:
            return
        
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop_all()


async def main() -> None:
    """Main entry point."""
    config = load_config()
    manager = BotManager(config)
    
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        for task in manager.tasks:
            task.cancel()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    await manager.run()


def run() -> None:
    """Entry point for the application."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
