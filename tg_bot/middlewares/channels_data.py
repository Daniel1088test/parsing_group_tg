from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import json
import os
import logging
from tg_bot.config import FILE_JSON
from admin_panel.models import Channel, Category

logger = logging.getLogger('middleware')

class ChannelsDataMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # loading data or creating an empty dictionary if the file does not exist
        channels_data = {}
        try:
            # first get data from the database
            channels = await self.get_channels_from_db()
            if channels:
                channels_data = channels
                logger.debug(f"Received {len(channels_data)} channels in middleware")
        except Exception as e:
            logger.error(f"Error getting channel data: {e}")
        
        # add data to the handler context
        data["channels_data"] = channels_data
        
        # call the next handler
        return await handler(event, data)
    
    @staticmethod
    async def get_channels_from_db():
        """Getting channels from the database in a format compatible with file.json"""
        channels_data = {}
        
        # convert QuerySet to a dictionary
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_all_channels():
            channels = {}
            for channel in Channel.objects.all():
                channels[str(channel.id)] = {
                    "Group_Name": channel.name,
                    "Invite_link": channel.url,
                    "category": str(channel.category_id) if channel.category_id else "0",
                    "Work": "True" if channel.is_active else "False"
                }
            return channels
        
        channels_data = await get_all_channels()
        return channels_data 