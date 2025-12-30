"""
Discord bot integration for FlowGPT chat.
"""
import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ...core.chat_client import ChatClient
from ...core.config import DiscordConfig

logger = logging.getLogger(__name__)


class DiscordBot(commands.Bot):
    """Discord bot that integrates with FlowGPT/OpenAI chat."""
    
    def __init__(self, config: DiscordConfig, chat_client: ChatClient):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.chat_client = chat_client
        self.synced = False
    
    def _get_conversation_id(self, interaction_or_message) -> str:
        """Generate a unique conversation ID."""
        if isinstance(interaction_or_message, discord.Interaction):
            channel_id = interaction_or_message.channel_id
            user_id = interaction_or_message.user.id
        else:
            channel_id = interaction_or_message.channel.id
            user_id = interaction_or_message.author.id
        return f"discord_{channel_id}_{user_id}"
    
    async def setup_hook(self) -> None:
        """Set up slash commands."""
        self.tree.add_command(self.chat_command)
        self.tree.add_command(self.clear_command)
        self.tree.add_command(self.prompt_command)
        self.tree.add_command(self.search_command)
        self.tree.add_command(self.load_command)
        self.tree.add_command(self.help_command)
    
    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Discord bot logged in as {self.user}")
        
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            logger.info("Slash commands synced")
    
    @app_commands.command(name="chat", description="Chat with the AI assistant")
    @app_commands.describe(message="Your message to the AI")
    async def chat_command(self, interaction: discord.Interaction, message: str) -> None:
        """Handle /chat command."""
        await interaction.response.defer(thinking=True)
        
        conversation_id = self._get_conversation_id(interaction)
        
        try:
            response = await self.chat_client.chat(conversation_id, message)
            
            if len(response) > 2000:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.channel.send(chunk)
            else:
                await interaction.followup.send(response)
        except Exception as e:
            logger.error(f"Error in chat command: {e}")
            await interaction.followup.send(
                "Sorry, I encountered an error. Please try again."
            )
    
    @app_commands.command(name="clear", description="Clear your conversation history")
    async def clear_command(self, interaction: discord.Interaction) -> None:
        """Handle /clear command."""
        conversation_id = self._get_conversation_id(interaction)
        self.chat_client.clear_conversation(conversation_id)
        await interaction.response.send_message(
            "Conversation history cleared!",
            ephemeral=True
        )
    
    @app_commands.command(name="prompt", description="Set a custom system prompt")
    @app_commands.describe(prompt="The system prompt to use")
    async def prompt_command(self, interaction: discord.Interaction, prompt: str) -> None:
        """Handle /prompt command."""
        conversation_id = self._get_conversation_id(interaction)
        self.chat_client.set_system_prompt(conversation_id, prompt)
        self.chat_client.clear_conversation(conversation_id)
        
        preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        await interaction.response.send_message(
            f"System prompt updated!\n\nNew prompt: {preview}",
            ephemeral=True
        )
    
    @app_commands.command(name="search", description="Search for FlowGPT prompts")
    @app_commands.describe(query="Search query for prompts")
    async def search_command(self, interaction: discord.Interaction, query: str) -> None:
        """Handle /search command."""
        await interaction.response.defer(thinking=True)
        
        prompts = await self.chat_client.search_flowgpt_prompts(query)
        
        if not prompts:
            await interaction.followup.send("No prompts found.")
            return
        
        embed = discord.Embed(
            title=f"FlowGPT Prompts: {query}",
            color=discord.Color.blue()
        )
        
        for i, prompt in enumerate(prompts[:5], 1):
            title = prompt.get("title", "Untitled")
            prompt_id = prompt.get("id", "")
            description = prompt.get("description", "")[:100]
            embed.add_field(
                name=f"{i}. {title}",
                value=f"ID: `{prompt_id}`\n{description}...",
                inline=False
            )
        
        embed.set_footer(text="Use /load <prompt_id> to load a prompt")
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="load", description="Load a FlowGPT prompt by ID")
    @app_commands.describe(prompt_id="The ID of the prompt to load")
    async def load_command(self, interaction: discord.Interaction, prompt_id: str) -> None:
        """Handle /load command."""
        await interaction.response.defer(thinking=True)
        
        system_prompt = await self.chat_client.load_flowgpt_prompt(prompt_id)
        
        if system_prompt:
            conversation_id = self._get_conversation_id(interaction)
            self.chat_client.set_system_prompt(conversation_id, system_prompt)
            self.chat_client.clear_conversation(conversation_id)
            
            preview = system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt
            await interaction.followup.send(
                f"Prompt loaded successfully!\n\nPreview: {preview}"
            )
        else:
            await interaction.followup.send(
                "Could not load the prompt. Please check the ID and try again."
            )
    
    @app_commands.command(name="help", description="Show help information")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Handle /help command."""
        embed = discord.Embed(
            title="FlowGPT Bot Help",
            description="An AI assistant powered by FlowGPT prompts",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="/chat <message>",
            value="Chat with the AI assistant",
            inline=False
        )
        embed.add_field(
            name="/clear",
            value="Clear your conversation history",
            inline=False
        )
        embed.add_field(
            name="/prompt <text>",
            value="Set a custom system prompt",
            inline=False
        )
        embed.add_field(
            name="/search <query>",
            value="Search for FlowGPT prompts",
            inline=False
        )
        embed.add_field(
            name="/load <prompt_id>",
            value="Load a specific FlowGPT prompt",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def on_message(self, message: discord.Message) -> None:
        """Handle direct messages and mentions."""
        if message.author.bot:
            return
        
        if isinstance(message.channel, discord.DMChannel):
            conversation_id = self._get_conversation_id(message)
            
            async with message.channel.typing():
                try:
                    response = await self.chat_client.chat(
                        conversation_id,
                        message.content
                    )
                    
                    if len(response) > 2000:
                        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                        for chunk in chunks:
                            await message.channel.send(chunk)
                    else:
                        await message.channel.send(response)
                except Exception as e:
                    logger.error(f"Error handling DM: {e}")
                    await message.channel.send(
                        "Sorry, I encountered an error. Please try again."
                    )
        
        elif self.user.mentioned_in(message) and not message.mention_everyone:
            content = message.content.replace(f"<@{self.user.id}>", "").strip()
            if not content:
                await message.reply("Hello! Use `/chat` to talk to me or mention me with a message.")
                return
            
            conversation_id = self._get_conversation_id(message)
            
            async with message.channel.typing():
                try:
                    response = await self.chat_client.chat(conversation_id, content)
                    
                    if len(response) > 2000:
                        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                        await message.reply(chunks[0])
                        for chunk in chunks[1:]:
                            await message.channel.send(chunk)
                    else:
                        await message.reply(response)
                except Exception as e:
                    logger.error(f"Error handling mention: {e}")
                    await message.reply(
                        "Sorry, I encountered an error. Please try again."
                    )
        
        await self.process_commands(message)


async def create_discord_bot(config: DiscordConfig, chat_client: ChatClient) -> DiscordBot:
    """Create and configure a Discord bot instance."""
    bot = DiscordBot(config, chat_client)
    return bot


async def run_discord_bot(bot: DiscordBot, token: str) -> None:
    """Run the Discord bot."""
    logger.info("Starting Discord bot...")
    await bot.start(token)
