from asyncio import sleep
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from time import time

from bot import bot, user_data, OWNER_ID
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, copyMessage, sendCustom


@new_task
async def broadcast_message(_, message: Message):
    reply_to = message.reply_to_message
    args = message.text.split(maxsplit=1)
    if not reply_to and len(args) == 1:
        await sendMessage('⚠️ <b>Please provide a message with the command, or reply to a message!</b>', message)
        return
    users = {x for x in user_data if not user_data[x].get('is_auth')}
    if message.chat.type.name != 'PRIVATE':
        async for x in message.chat.get_members():
            if not x.user.is_bot or x.user.id != OWNER_ID:
                users.add(x.user.id)
    count = len(users)
    msg = await sendMessage('⏳ <i>Checking user data, please wait...</i>', message)
    await sleep(2)
    if count:
        await editMessage(f'📢 <i>Found <b>{count}</b> recipients. Starting broadcast...</i>', msg)
        await sleep(1)
        await editMessage(f'📢 <i>Sending broadcast to <b>{count}</b> users, please wait...</i>', msg)
        succ = fail = 0
        for user_id in users:
            if reply_to:
                bmsg = await copyMessage(user_id, reply_to, nolog=True)
            else:
                bmsg = await sendCustom(args[1], user_id, nolog=True)

            if bmsg:
                succ += 1
            else:
                fail += 1
        text = ('<blockquote>┌━━━«★彡 <b>BROADCAST DONE</b> 彡★»━━━\n'
                f'├ ⏱️ <b>Time Taken :</b> <i>{get_readable_time(time() - message.date.timestamp())}</i>\n'
                f'├ 👥 <b>Total :</b> <i>{count}</i>\n'
                f'├ ✅ <b>Success :</b> <i>{succ}</i>\n'
                f'├ ❌ <b>Failed :</b> <i>{fail}</i>\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')
    else:
        text = 'ℹ️ <b>No users found to send broadcast message!</b>'
    await editMessage(text, msg)


bot.add_handler(MessageHandler(broadcast_message, filters=command(BotCommands.BroadcaseCommand) & CustomFilters.owner))
