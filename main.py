import asyncio
from typing import Any, Mapping
import aiohttp

from pprint import pprint as print

BASE_URL = 'https://discord.com/api/v8'

ENDPOINTS = {
    'send': BASE_URL + '/channels/{channel_id}/messages',
    'delete': BASE_URL + '/channels/{channel_id}/messages/{message_id}',
    'messages': BASE_URL + '/channels/{channel_id}/messages'
}

class Message:
    def __init__(self, data: Mapping[str, Any]) -> None:
        self.channel_id = data['channel_id']
        self.id = data['id']
        self.content = data['content']

    def __repr__(self) -> str:
        return '<Message id={0.id}>'.format(self)

class Bot:
    def __init__(self) -> None:
        headers = {
            'Authorization': 'Bot NzYzNzc0NDgxNTU0NDczMDAx.X38mag.b8tNypJfVchkXQjk9cUi37EuZTw'
        }
        
        self.session = aiohttp.ClientSession(headers=headers)

    async def handle_ratelimits(self, resp: aiohttp.ClientResponse):
        if resp.status == 429:
            data = await resp.json()
            retry = data['retry_after']

            await asyncio.sleep(retry)

    async def delete_message(self, message: Message):
        url = ENDPOINTS['delete'].format(
            channel_id=message.channel_id,
            message_id=message.id
        )

        async with self.session.delete(url) as resp:
            await self.handle_ratelimits(resp)

            if resp.status == 204:
                return

            data = await resp.json()
            return data

    async def get_messages(self, channel_id: int):
        params = {
            'limit': 10
        }

        url = ENDPOINTS['messages'].format(channel_id=channel_id)

        async with self.session.get(url, params=params) as resp:
            await self.handle_ratelimits(resp)

            data = await resp.json()
            return [Message(message) for message in data]
        

async def main():
    bot = Bot()
    messages = await bot.get_messages(757026518386868296)
    
    for message in messages:
        data = await bot.delete_message(message)
        if data is not None:
            print(data)


asyncio.run(main())
