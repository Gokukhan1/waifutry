import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import MongoClient, ASCENDING

from telegram import Update, InlineQueryResultPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import InlineQueryHandler, CallbackContext, CommandHandler, CallbackQueryHandler

from shivu import user_collection, collection, application, db


# collection indexes
db.characters.create_index([('id', ASCENDING)])
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])

# user_collection indexes
db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])

all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    if query.startswith('collection.'):
        user_id, *search_terms = query.split(' ')[0].split('.')[1], ' '.join(query.split(' ')[1:])
        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await user_collection.find_one({'id': int(user_id)})
                user_collection_cache[user_id] = user

            if user:
                all_characters = list({v['id']: v for v in user['characters']}.values())
                if search_terms:
                    regex = re.compile(' '.join(search_terms), re.IGNORECASE)
                    all_characters = [character for character in all_characters if regex.search(character['name']) or regex.search(character['anime'])]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            all_characters = list(await collection.find({"$or": [{"name": regex}, {"anime": regex}]}).to_list(length=None))
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = list(await collection.find({}).to_list(length=None))
                all_characters_cache['all_characters'] = all_characters

    characters = all_characters[offset:offset+50]
    if len(characters) > 50:
        characters = characters[:50]
        next_offset = str(offset + 50)
    else:
        next_offset = str(offset + len(characters))

    results = []
    for character in characters:
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        anime_characters = await collection.count_documents({'anime': character['anime']})

        if query.startswith('collection.'):
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
            caption = f"<b> Look At <a href='tg://user?id={user['id']}'>{(escape(user.get('first_name', user['id'])))}</a>'s Character</b>\n\n🌸: <b>{character['name']} (x{user_character_count})</b>\n🏖️: <b>{character['anime']} ({user_anime_characters}/{anime_characters})</b>\n<b>{character['rarity']}</b>\n\n<b>🆔️:</b> {character['id']}"
        else:
            caption = f"<b>Look At This Character !!</b>\n\n🌸:<b> {character['name']}</b>\n🏖️: <b>{character['anime']}</b>\n<b>{character['rarity']}</b>\n🆔️: <b>{character['id']}</b>\n\n<b>Globally Guessed {global_count} Times...</b>"

        # Add the inline button for "Grabbed Globally"
        buttons = [[InlineKeyboardButton("🌎 Grabbed Globally", callback_data=f"grab_{character['id']}")]]
        reply_markup = InlineKeyboardMarkup(buttons)

        results.append(
            InlineQueryResultPhoto(
                thumbnail_url=character['img_url'],
                id=f"{character['id']}_{time.time()}",
                photo_url=character['img_url'],
                caption=caption,
                parse_mode='HTML',
                reply_markup=reply_markup  # Add the buttons to the result
            )
        )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)


async def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    character_id = query.data.split('_')[1]

    # Fetch global and chat-specific grab data for the character
    global_grabs = await user_collection.count_documents({'characters.id': int(character_id)})
    chat_id = query.message.chat_id

    # Get the top 10 grabbers in the current chat
    pipeline = [
        {"$match": {"characters.id": int(character_id), "chat_id": chat_id}},
        {"$unwind": "$characters"},
        {"$match": {"characters.id": int(character_id)}},
        {"$group": {"_id": "$id", "count": {"$sum": 1}, "name": {"$first": "$first_name"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_grabbers = await user_collection.aggregate(pipeline).to_list(length=None)

    # Prepare the response message
    top_grabbers_text = "\n".join([f"➥ {grabber['name']} x{grabber['count']}" for grabber in top_grabbers]) or "No grabbers in this chat yet."

    response_text = (
        f"🌎 Grabbed Globally: {global_grabs} Times\n\n"
        f"🎖️ Top 10 Grabbers Of This Waifu In This Chat:\n"
        f"{top_grabbers_text}"
    )

    await query.answer()
    await query.edit_message_caption(caption=response_text, parse_mode='HTML')


# Register the handlers
application.add_handler(InlineQueryHandler(inlinequery, block=False))
application.add_handler(CallbackQueryHandler(button_click))

