from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.storage import MemoryStorage
import json
import heapq
from thefuzz import fuzz
import os   
class MaxPriorityQueue:
    def __init__(self):
        self._queue = []
        self._index = 0

    def push(self, item, priority):
        # Negate the priority to convert the min-heap into a max-heap
        heapq.heappush(self._queue, (-priority, self._index, item))
        self._index += 1

    def pop(self):
        # Return the item with the highest priority
        return heapq.heappop(self._queue)[-1]
    def clear(self):
        # Clear the queue and reset the index
        self._queue = []
        self._index = 0
    def is_empty(self):
        return len(self._queue) == 0
    def __iter__(self):
            # Create an iterator that yields items in descending order of priority
            items = [(item, -priority) for priority, index, item in self._queue]
            items.sort(key=lambda x: x[1], reverse=True)  # Sort by priority in descending order
            for item, priority in items:
                yield item
    def __str__(self):
            # Create a string representation of the queue
            items = [(item, -priority) for priority, index, item in self._queue]
            items.sort(key=lambda x: x[1], reverse=True)  # Sort by priority in descending order
            item_names = [item for item, priority in items]  # Extract the item names
            return '\n'.join(f"{item}" for item in item_names) + "."
found_performers = MaxPriorityQueue()
pfile = open('performers.txt', 'r', encoding='utf-8')
sfile = open('performer_title_id.json', 'r', encoding='utf-8')
def findP(input):
    global found_performers
    pfile.seek(0)
    lines = [line.strip() for line in pfile]
    for performer in lines:
        ratio = fuzz.ratio(performer.lower(), input)
        if ratio >= 85:
            found_performers.push(performer, ratio)
# Function to search for messages
def message_search_single(artist, song):
    global fnd_art
    sfile.seek(0)
    data = json.load(sfile)
    findP(artist)
    found_ids = set()
    print(f"Found these artists {found_performers}")
    for performer in found_performers:
        #print(performer)
        songs = data.get(performer, {})
        for title, song_id in songs.items():
            if fuzz.ratio(title.lower(), song) >= 90:
                fnd_art = performer
                found_ids.add(song_id)
    return found_ids

def message_search_all(input):
    sfile.seek(0)
    data = json.load(sfile)
    findP(input)
    performer = found_performers.pop()
    global fnd_art
    fnd_art = performer
    songs = data.get(performer, {})
    found_ids = set()
    for title, song_id in songs.items():
        found_ids.add(song_id)
    return found_ids
# Define the Pyrogram client
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

app = Client("hifimusic_bot", storage=MemoryStorage(), api_id=api_id, api_hash=api_hash, bot_token=bot_token)
ids = []
channel_id = os.getenv("CHANNEL_ID")
@app.on_message(filters.command("hifi"))
async def send_song(client, message):
    # Extract the song ID from the user's message
    query = ''.join(message.text.split()[1:]).lower().split('-')
    artist = query[0]
    song = query[1]
    ids = message_search_single(artist, song)
    limit = 10
    count = 0
    if len(ids) == 0:
        await message.reply(f'{artist} with song {song} is not found')
    else:
        for id in ids:
            if count >= limit:
                break
            await client.forward_messages(message.chat.id, channel_id, id)
            count += 1
@app.on_message(filters.command("artist"))
async def send_songS(message):
    # Extract the song ID from the user's message
    query = ' '.join(message.text.split()[1:])
    print(query)
    # Replace with your channel ID
    # Search for message IDs
    query = query.lower()
    global ids
    found_performers.clear()
    print (found_performers)
    ids = message_search_all(query)
    if ids is not None:
        buttons = [
            [
                InlineKeyboardButton("Yes", callback_data="proceed_yes"),
                InlineKeyboardButton("No", callback_data="proceed_no")
            ],
            [
                InlineKeyboardButton("The wrong artist", callback_data="proceed_wrong")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(f'there are {len(ids)} song of {fnd_art}. Do you want to proceed ?', reply_markup=reply_markup)
    else:
        await message.reply(f'{query} is not found')
@app.on_callback_query(filters.regex(r"proceed_"))
async def handle_callback_query(client, callback_query):
    if callback_query.data == "proceed_yes":
        mss = await client.get_messages(callback_query.message.chat.id, callback_query.message.id - 1)
        query = ' '.join(mss.text.split()[1:])
        ids = message_search_all(query)
        for id in ids:
            await client.forward_messages(callback_query.message.chat.id, channel_id, id)
        await client.delete_messages(callback_query.message.chat.id, callback_query.message.id)
        # Add logic to handle proceeding with the search
    elif callback_query.data == "proceed_no":
        await callback_query.message.reply("You chose not to proceed.")
        await client.delete_messages(callback_query.message.chat.id, callback_query.message.id)
    elif callback_query.data == "proceed_wrong":
        await callback_query.message.reply(f'I found:\n{found_performers}')
        await client.delete_messages(callback_query.message.chat.id, callback_query.message.id)
    found_performers.clear()
    await callback_query.answer()  # Acknowledge the callback query

if __name__ == "__main__":
    app.run()



