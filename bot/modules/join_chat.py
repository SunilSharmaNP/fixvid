from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, bot_dict, bot_lock, LOGGER
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.ext_utils.links_utils import get_link
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message


async def join_chat(_, message: Message):
    async with bot_lock:
        savebot = bot_dict['SAVEBOT']
    if savebot:
        link = get_link(message)
        if not link:
            msg = await sendMessage('⚠️ <b>Please provide a chat join link!</b>', message)
            return
        try:
            await savebot.join_chat(link)
            text = '✅ <b>Successfully joined the chat!</b>'
        except UserAlreadyParticipant:
            text = 'ℹ️ <b>Already joined the chat.</b>'
        except InviteHashExpired:
            text = '⏰ <b>Invite link expired!</b>'
        except Exception as e:
            LOGGER.error(e)
            text = '❌ <b>Invalid link!</b>'
        msg = await sendMessage(text, message)
    else:
        msg = await sendMessage(f'⚠️ <b>Default save content mode is disabled!</b>\nUse a custom session string via <code>/{BotCommands.UserSetCommand}</code>.', message)
    await auto_delete_message(message, msg, message.reply_to_message)


bot.add_handler(MessageHandler(join_chat, filters=command(BotCommands.JoinChatCommand) & CustomFilters.authorized))
