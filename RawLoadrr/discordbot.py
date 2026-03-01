import asyncio
import datetime
import logging
from pathlib import Path

import discord
from discord.ext import commands

def config_load():
    """
    Loads the bot configuration from the config file.
    """
    from data.config import config  # Importing inside the function to avoid issues with module-level imports
    return config

async def run():
    """
    Initializes and starts the bot.
    If you need to create a database connection pool or other session for the bot to use,
    it's recommended to create it here and pass it to the bot as a keyword argument.
    """
    config = config_load()
    bot = Bot(config=config,
              description=config['DISCORD']['discord_bot_description'])
    try:
        await bot.start(config['DISCORD']['discord_bot_token'])
    except KeyboardInterrupt:
        await bot.logout()

class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix_,
            description=kwargs.pop('description')
        )
        self.start_time = None
        self.app_info = None
        self.config = config_load()

        # Start background tasks
        self.loop.create_task(self.track_start())
        self.loop.create_task(self.load_all_extensions())

    async def track_start(self):
        """
        Waits for the bot to connect to Discord and then records the start time.
        This can be used to calculate uptime.
        """
        await self.wait_until_ready()
        self.start_time = datetime.datetime.utcnow()

    async def get_prefix_(self, bot, message):
        """
        Returns the command prefix for the bot.
        This method is asynchronous to allow for dynamic prefix fetching, e.g., from a database.
        """
        prefix = [self.config['DISCORD']['command_prefix']]
        return commands.when_mentioned_or(*prefix)(bot, message)

    async def load_all_extensions(self):
        """
        Loads all extensions (cogs) from the 'cogs' directory.
        Extensions should be named with the .py extension.
        """
        await self.wait_until_ready()
        await asyncio.sleep(1)  # Ensure on_ready has completed and finished printing
        cogs = [x.stem for x in Path('cogs').glob('*.py')]
        for extension in cogs:
            try:
                self.load_extension(f'cogs.{extension}')
                print(f'Loaded {extension}')
            except Exception as e:
                error = f'{extension}\n {type(e).__name__}: {e}'
                print(f'Failed to load extension {error}')
            print('-' * 10)

    async def on_ready(self):
        """
        This event is called every time the bot connects or resumes connection.
        It prints bot information and sends a message to a specified channel.
        """
        print('-' * 10)
        self.app_info = await self.application_info()
        print(f'Logged in as: {self.user.name}\n'
              f'Using discord.py version: {discord.__version__}\n'
              f'Owner: {self.app_info.owner}\n')
        print('-' * 10)
        channel = self.get_channel(int(self.config['DISCORD']['discord_channel_id']))
        await channel.send(f'{self.user.name} is now online')

    async def on_message(self, message):
        """
        Handles incoming messages. This event triggers on every message received by the bot,
        including ones sent by the bot itself. All bot messages are ignored.
        """
        if message.author.bot:
            return  # Ignore all bot messages
        await self.process_commands(message)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)  # Set up logging for the bot

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())  # Run the bot
