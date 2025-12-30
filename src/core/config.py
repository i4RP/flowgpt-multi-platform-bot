"""
Configuration management for the multi-platform bot.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OpenAIConfig:
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("OPENAI_MAX_TOKENS", "2048")))
    temperature: float = field(default_factory=lambda: float(os.getenv("OPENAI_TEMPERATURE", "0.7")))


@dataclass
class FlowGPTConfig:
    default_prompt_id: Optional[str] = field(default_factory=lambda: os.getenv("FLOWGPT_DEFAULT_PROMPT_ID"))
    default_system_prompt: str = field(default_factory=lambda: os.getenv(
        "FLOWGPT_DEFAULT_SYSTEM_PROMPT",
        "You are a helpful AI assistant."
    ))


@dataclass
class TelegramConfig:
    bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_URL"))


@dataclass
class DiscordConfig:
    bot_token: str = field(default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN", ""))
    application_id: str = field(default_factory=lambda: os.getenv("DISCORD_APPLICATION_ID", ""))


@dataclass
class SlackConfig:
    bot_token: str = field(default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    signing_secret: str = field(default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", ""))
    app_token: str = field(default_factory=lambda: os.getenv("SLACK_APP_TOKEN", ""))


@dataclass
class LineConfig:
    channel_secret: str = field(default_factory=lambda: os.getenv("LINE_CHANNEL_SECRET", ""))
    channel_access_token: str = field(default_factory=lambda: os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))


@dataclass
class AppConfig:
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    flowgpt: FlowGPTConfig = field(default_factory=FlowGPTConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    line: LineConfig = field(default_factory=LineConfig)
    
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    return AppConfig()
