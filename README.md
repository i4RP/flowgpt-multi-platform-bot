# FlowGPT Multi-Platform Bot

A multi-platform chatbot that integrates with FlowGPT prompts, supporting Telegram, Discord, Slack, and LINE messaging platforms.

## Features

- **Multi-Platform Support**: Run bots on Telegram, Discord, Slack, and LINE simultaneously
- **FlowGPT Integration**: Search and load prompts from FlowGPT
- **OpenAI Backend**: Uses OpenAI's GPT models for chat completions
- **Conversation Memory**: Maintains conversation history per user/channel
- **Custom Prompts**: Set custom system prompts for personalized AI behavior
- **Modular Architecture**: Each platform is implemented as a separate service

## Architecture

```
src/
├── core/
│   ├── config.py       # Configuration management
│   └── chat_client.py  # OpenAI/FlowGPT chat client
├── services/
│   ├── telegram/       # Telegram bot implementation
│   ├── discord/        # Discord bot implementation
│   ├── slack/          # Slack bot implementation
│   └── line/           # LINE bot implementation
├── api/
│   └── webhooks.py     # FastAPI webhook endpoints
└── main.py             # Main entry point
```

## Prerequisites

- Python 3.10+
- OpenAI API key
- Bot tokens for the platforms you want to use

## Installation

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/i4RP/flowgpt-multi-platform-bot.git
cd flowgpt-multi-platform-bot

# Install all dependencies
poetry install --all-extras

# Or install specific platforms only
poetry install -E telegram
poetry install -E discord
poetry install -E slack
poetry install -E line
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/i4RP/flowgpt-multi-platform-bot.git
cd flowgpt-multi-platform-bot

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and fill in your credentials:

### Required
- `OPENAI_API_KEY`: Your OpenAI API key

### Platform-Specific

#### Telegram
- `TELEGRAM_BOT_TOKEN`: Get from [@BotFather](https://t.me/botfather)

#### Discord
- `DISCORD_BOT_TOKEN`: Get from [Discord Developer Portal](https://discord.com/developers/applications)
- `DISCORD_APPLICATION_ID`: Your application ID

#### Slack
- `SLACK_BOT_TOKEN`: Bot User OAuth Token (starts with `xoxb-`)
- `SLACK_SIGNING_SECRET`: Signing secret from app settings
- `SLACK_APP_TOKEN`: App-level token for Socket Mode (starts with `xapp-`)

#### LINE
- `LINE_CHANNEL_SECRET`: Channel secret from LINE Developers Console
- `LINE_CHANNEL_ACCESS_TOKEN`: Channel access token

## Usage

### Running All Configured Bots

```bash
# Using Poetry
poetry run flowgpt-bot

# Or directly
python -m src.main
```

The bot will automatically start services for all platforms that have valid credentials configured.

## Bot Commands

### Telegram Commands
- `/start` - Show welcome message
- `/help` - Show help information
- `/clear` - Clear conversation history
- `/prompt <text>` - Set custom system prompt
- `/search <query>` - Search FlowGPT prompts
- `/load <prompt_id>` - Load a FlowGPT prompt

### Discord Commands
- `/chat <message>` - Chat with the AI
- `/clear` - Clear conversation history
- `/prompt <text>` - Set custom system prompt
- `/search <query>` - Search FlowGPT prompts
- `/load <prompt_id>` - Load a FlowGPT prompt
- `/help` - Show help information

You can also:
- Send direct messages to the bot
- Mention the bot in a channel

### Slack Commands
- `/flowgpt chat <message>` - Chat with the AI
- `/flowgpt clear` - Clear conversation history
- `/flowgpt prompt <text>` - Set custom system prompt
- `/flowgpt search <query>` - Search FlowGPT prompts
- `/flowgpt load <prompt_id>` - Load a FlowGPT prompt
- `/flowgpt help` - Show help information

You can also:
- Mention the bot in a channel
- Send direct messages to the bot

### LINE Commands
- `/help` - Show help information
- `/clear` - Clear conversation history
- `/prompt <text>` - Set custom system prompt
- `/search <query>` - Search FlowGPT prompts
- `/load <prompt_id>` - Load a FlowGPT prompt

Or just send a message to chat with the AI.

## Platform Setup Guides

### Telegram Setup
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token to `TELEGRAM_BOT_TOKEN`

### Discord Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to `DISCORD_BOT_TOKEN`
5. Copy the Application ID to `DISCORD_APPLICATION_ID`
6. Enable "Message Content Intent" in the Bot settings
7. Generate an invite URL with `bot` and `applications.commands` scopes
8. Invite the bot to your server

### Slack Setup
1. Go to [Slack API](https://api.slack.com/apps) and create a new app
2. Enable Socket Mode and generate an App-Level Token (`SLACK_APP_TOKEN`)
3. Add Bot Token Scopes: `app_mentions:read`, `chat:write`, `im:history`, `im:read`, `im:write`
4. Install the app to your workspace
5. Copy the Bot User OAuth Token (`SLACK_BOT_TOKEN`)
6. Copy the Signing Secret (`SLACK_SIGNING_SECRET`)
7. Create the `/flowgpt` slash command pointing to your server

### LINE Setup
1. Go to [LINE Developers Console](https://developers.line.biz/console/)
2. Create a new provider and channel (Messaging API)
3. Copy the Channel Secret (`LINE_CHANNEL_SECRET`)
4. Issue and copy the Channel Access Token (`LINE_CHANNEL_ACCESS_TOKEN`)
5. Set the Webhook URL to `https://your-domain.com/webhooks/line`
6. Enable "Use webhook"

## Deployment

### Docker (Coming Soon)

### Fly.io

The bot can be deployed to Fly.io using the FastAPI backend deployment workflow.

### Environment Variables

For production, set environment variables directly instead of using a `.env` file.

## Development

```bash
# Install dev dependencies
poetry install --all-extras

# Run linting
poetry run ruff check src/

# Run type checking
poetry run mypy src/

# Run tests
poetry run pytest
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
