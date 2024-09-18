from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto
import asyncio
import html
from shivu import shivuu, collection, user_collection, group_user_totals_collection, db

# MongoDB Collections
groups_collection = db['top_global_groups']
users_collection = db['user_collection_lmaoooo']
characters_collection = db['anime_characters_lol']

async def get_user_collection():
    return await user_collection.find({}).to_list(length=None)

async def get_user_rarity_counts(user_id):
    rarity_counts = {
        "Legendary": 0,
        "Rare": 0,
        "Medium": 0,
        "Common": 0,
        "Cosmic": 0,
        "Exclusive": 0,
        "Limited Edition": 0
    }

    user = await user_collection.find_one({'id': user_id})
    if user:
        characters = user.get('characters', [])
        for char in characters:
            rarity = char.get('rarity', 'Common')
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1

    return rarity_counts

async def get_progress_bar(user_waifus_count, total_waifus_count):
    bar_width = 20  # Define the width of the progress bar
    progress = min(user_waifus_count / total_waifus_count, 1)  # Ensure it doesn't exceed 100%
    progress_percent = min(progress * 100, 100)  # Ensure it doesn't exceed 100%

    filled_width = int(progress * bar_width)
    empty_width = bar_width - filled_width

    progress_bar = "▰" * filled_width + "▱" * empty_width
    return progress_bar, progress_percent

async def get_chat_top(chat_id, user_id):
    try:
        pipeline = [
            {"$match": {"group_id": chat_id}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        cursor = group_user_totals_collection.aggregate(pipeline)
        leaderboard_data = await cursor.to_list(length=None)
        
        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('user_id') == user_id:
                return i
        
        return 'N/A'
    except Exception as e:
        print(f"Error getting chat top: {e}")
        return 'N/A'

async def get_global_top(user_id):
    try:
        pipeline = [
            {"$project": {"id": 1, "characters_count": {"$size": {"$ifNull": ["$characters", []]}}}},
            {"$sort": {"characters_count": -1}}
        ]
        cursor = user_collection.aggregate(pipeline)
        leaderboard_data = await cursor.to_list(length=None)
        
        for i, user in enumerate(leaderboard_data, start=1):
            if user.get('id') == user_id:
                return i
        
        return 'N/A'
    except Exception as e:
        print(f"Error getting global top: {e}")
        return 'N/A'

def get_rank(progress_percent):
    ranks = [
        (5, "Bronze I"),
        (10, "Bronze II"),
        (15, "Bronze III"),
        (20, "Silver I"),
        (25, "Silver II"),
        (30, "Silver III"),
        (35, "Gold I"),
        (40, "Gold II"),
        (45, "Gold III"),
        (50, "Gold IV"),
        (55, "Platinum I"),
        (60, "Platinum II"),
        (65, "Platinum III"),
        (70, "Platinum IV"),
        (75, "Diamond I"),
        (80, "Diamond II"),
        (85, "Diamond III"),
        (90, "Diamond IV"),
        (95, "Heroic I"),
        (100, "Heroic II"),
        (105, "Heroic III"),
        (110, "Elite Heroic"),
        (115, "Master"),
        (120, "Crown"),
        (130, "Grandmaster I"),
        (140, "Grandmaster II"),
        (150, "Grandmaster III"),
        (160, "Conqueror")
    ]

    for percent, rank in ranks:
        if progress_percent <= percent:
            return rank

    return "Conqueror"  # If progress_percent is above 160%

@shivuu.on_message(filters.command(["find"]))
async def find_character(client, message):
    try:
        character_id = " ".join(message.text.split()[1:]).strip()

        if not character_id:
            await message.reply("Please provide a character ID.")
            return

        character = await characters_collection.find_one({"id": character_id})

        if not character:
            await message.reply("No character found with that ID.")
            return

        response_message = (
            f"🧩 𝖶𝖺𝗂𝖿𝗎 𝖨𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇:\n\n"
            f"🪭 𝖭𝖺𝗆𝗂: {html.escape(character['name'])}\n"
            f"⚕️ 𝖱𝖺𝗋𝗂𝗍𝗒: {html.escape(character['rarity'])}\n"
            f"⚜️ 𝖠𝗇𝗂𝗆𝖾: {html.escape(character['anime'])}\n"
            f"🪅 𝖨𝖳: {html.escape(character['id'])}\n\n"
        )

        if 'image_url' in character:
            await message.reply_photo(
                photo=character['image_url'],
                caption=response_message
            )
        else:
            await message.reply_text(response_message)

        user_list_message = "✳️ 𝖧𝖾𝗋𝖾 𝗂𝗌 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝗎𝗌𝖾𝗋𝗌 𝗐𝗁𝗈 𝗁𝖺𝗏𝖾 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗋𝖺𝒸𝗍𝖾𝗋 〽️:\n"
        user_cursor = characters_collection.find({"id": character['id']})
        user_list = []
        async for user in user_cursor:
            user_list.append(f"{user['username']} x{user['count']}")

        if user_list:
            user_list_message += "\n".join(user_list)
        else:
            user_list_message += "No users found."

        await message.reply_text(user_list_message)

    except Exception as e:
        print(f"Error: {e}")

@shivuu.on_message(filters.command(["status", "mystatus"]))
async def send_grabber_status(client, message):
    try:
        loading_message = await message.reply("🔄 Fetching Grabber Status...")

        for i in range(1, 6):
            await asyncio.sleep(1)
            await loading_message.edit_text("🔄 Fetching Grabber Status" + "." * i)

        user_id = message.from_user.id
        user = await user_collection.find_one({'id': user_id})

        if user:
            user_characters = user.get('characters', [])
            total_count = len(user_characters)
        else:
            total_count = 0

        total_waifus_count = await user_collection.count_documents({})

        chat_top = await get_chat_top(message.chat.id, user_id)
        global_top = await get_global_top(user_id)

        progress_bar, progress_percent = await get_progress_bar(total_count, total_waifus_count)
        rank = get_rank(progress_percent)
        current_xp = total_count
        next_level_xp = min(100, total_waifus_count)  # Ensure XP does not exceed total character count

        # Fetch user-specific rarity counts
        rarity_counts = await get_user_rarity_counts(user_id)

        # Fetch the user's profile photo
        profile_photos = shivuu.get_chat_photos(user_id)
        profile_image = None
        async for photo in profile_photos:
            profile_image = photo.file_id
            break  # Get the first profile photo and break

        rarity_message = (
            f"╔════════ • ✧ • ════════╗\n"
            f"          ⛩  『𝗨𝘀𝗲𝗿 𝗽𝗿𝗼𝗳𝗶𝗹𝗲』  ⛩\n"
            f"══════════════════════\n"
            f"➣ ❄️ 𝗡𝗮𝗺𝗲: {message.from_user.full_name}\n"
            f"➣ 🍀 𝗨𝘀𝗲𝗿 𝗜𝗗: {user_id}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 👾 𝗖𝗵𝗮𝗿𝗮𝗰𝘁𝗲𝗿𝘀 𝗖𝗼𝗹𝗹𝗲𝗰𝘁𝗲𝗱: {total_count}\n"
            f"➣ 💯 𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲: {progress_percent:.2f}%\n"
            f"➣ {progress_bar} {current_xp}/{next_level_xp}\n"
            f"➣ 🎖 𝗥𝗮𝗻𝗸: {rank}\n"
            f"➣ 🏆 𝗧𝗼𝗽 𝗜𝗻 𝗖𝗵𝗮𝘁: {chat_top}\n"
            f"➣ 🌍 𝗚𝗹𝗼𝗯𝗮𝗹 𝗧𝗼𝗽: {global_top}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➣ 🟡 𝗟𝗲𝗴𝗲𝗻𝗱𝗮𝗿𝘆: {rarity_counts['Legendary']}\n"
            f"➣ 🟠 𝗥𝗮𝗿𝗲: {rarity_counts['Rare']}\n"
            f"➣ 🟢 𝗠𝗲𝗱𝗶𝘂𝗺: {rarity_counts['Medium']}\n"
            f"➣ ⚪ 𝗖𝗼𝗺𝗺𝗼𝗻: {rarity_counts['Common']}\n"
            f"💠 𝗖𝗼𝘀𝗺𝗶𝗰: {rarity_counts['Cosmic']}\n"
            f"💮 𝗘𝘅𝗰𝗹𝘂𝘀𝗶𝘃𝗲: {rarity_counts['Exclusive']}\n"
            f"🔮 𝗟𝗶𝗺𝗶𝘁𝗲𝗱 𝗘𝗱𝗶𝘁𝗶𝗼𝗻: {rarity_counts['Limited Edition']}\n"
            f"╚════════ • ✧ • ════════╝\n"
        )

        # Update with the user's profile picture if available
        if profile_image:
            await loading_message.edit_media(InputMediaPhoto(profile_image, caption=rarity_message))
        else:
            await loading_message.edit_text(rarity_message)

    except Exception as e:
        print(f"Error: {e}")
        await message.reply(f"An error occurred: {e}")
