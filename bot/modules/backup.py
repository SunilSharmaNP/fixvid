from asyncio import sleep, gather
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from random import choice
from time import time

from bot import bot, bot_name, bot_dict, bot_lock, config_dict, user_data
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.status_utils import get_readable_time, get_progress_bar_string
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage, sendingMessage, handle_message, auto_delete_message

hanlder_dict = {}


class Backup:
    CANCEL = False
    TYPE = 'all'
    ID = 0


@new_task
async def backup_message(client: Client, message: Message):
    if fmsg := await UseCheck(message).run(forpremi=True, session=True):
        await auto_delete_message(message, fmsg, message.reply_to_message)
        return

    try:
        _, start, end, source_id, des_id = message.text.split()
    except:
        await sendMessage('⚠️ <b>Send a valid format:</b> <code>start, end, source_id, destination_id</code>', message)
        return

    if bool(list(filter(lambda x: x.ID == int(des_id), hanlder_dict.values()))):
        await sendMessage('⚠️ <b>Only one backup is allowed at a time to the same destination!</b>', message)
        return

    user_id = message.from_user.id
    Bot, is_session = client, False
    await intialize_savebot(user_data.get(user_id, {}).get('session_string', ''), True, user_id)
    async with bot_lock:
        ubot = bot_dict[user_id]['SAVEBOT']
    if ubot:
        Bot = ubot
        is_session = True

    try:
        chat = await Bot.get_chat(int(source_id))
        stitle = chat.title
        if chat.has_protected_content:
            await sendMessage('🚫 <b>Cannot copy directly from a chat with restricted content!</b>', message)
            return
    except:
        await sendMessage('⚠️ <b>Your userbot account must join the source chat!</b>' if is_session else '⚠️ <b>You must add me to the source chat!</b>', message)
        return
    try:
        dtitle = (await client.get_chat(int(des_id))).title
        user = await client.get_chat_member(int(des_id), bot_name)
        if user.status != ChatMemberStatus.ADMINISTRATOR:
            await sendMessage('🛡️ <b>Admin privileges required in destination chat to copy messages!</b>', message)
            return
    except:
        await sendMessage('⚠️ <b>You must add me to the destination chat!</b>', message)
        return

    buttons = ButtonMaker()
    buttons.button_data('🗂️ All', f'backup all {user_id} {message.id}')
    buttons.button_data('🖼️ Photo', f'backup photo {user_id} {message.id}')
    buttons.button_data('🎬 Video', f'backup video {user_id} {message.id}')
    buttons.button_data('🎵 Audio', f'backup audio {user_id} {message.id}')
    buttons.button_data('📄 Document', f'backup document {user_id} {message.id}')
    buttons.button_data('⛔ Stop', f'backup stop {user_id} {message.id}', 'footer')
    backup = Backup()
    backup.ID = int(des_id)
    hanlder_dict[message.id] = backup
    cmsg = await sendMessage('🚀 <b>Starting backup, please choose a filter...</b>', message, buttons.build_menu(3))
    await sleep(2)
    succ = fail = empy = 0
    status, first_id = 'Done', None
    same_id = source_id == des_id
    count_time = time()

    @handle_message
    async def _copy(chat_id: int, message: Message):
        return await Bot.copy_message(chat_id, message.chat.id, message.id, disable_notification=True)

    @handle_message
    async def _get(message_id: int):
        return await Bot.get_messages(int(source_id), message_id)

    ids = list(range(int(start), int(end) + 1))
    total_msg = len(ids)
    for x, id_ in enumerate(ids, 1):
        msg = await _get(id_)
        if backup.CANCEL:
            status = f'Cancelled ({total_msg - x})'
            break
        if msg.empty:
            empy += 1
            continue
        if (typee := backup.TYPE) and typee != 'all' and not getattr(msg, typee, None):
            continue
        if time() - count_time > 10:
            progress = f'{round(x / total_msg * 100, 2)}%'
            text = (f'<b>┌ <i>Copying Message...</i></b>\n'
                    f'<b>├ </b>{get_progress_bar_string(progress)}\n'
                    f'<b>├ Progress:</b> {progress}\n'
                    f'<b>├ Processed:</b> {x}\n'
                    f'<b>├ Total:</b> {total_msg}\n'
                    f'<b>├ Elapsed:</b> {get_readable_time(time() - message.date.timestamp())}\n'
                    f'<b>├ Source:</b> {stitle}\n'
                    f'<b>├ Destination:</b> {dtitle}\n'
                    f'<b>├ By:</b> {message.from_user.mention}\n'
                    f'<b>└ Type:</b> {"USER" if is_session else "BOT"} / {backup.TYPE.upper()}')
            await editMessage(text, cmsg, buttons.build_menu(3))
            count_time = time()

        if same_id and msg.id == first_id:
            break
        if copyed := await _copy(int(des_id), msg):
            await sleep(10)
            succ += 1
            if same_id and not first_id:
                first_id = copyed.id
        else:
            fail += 1
        if same_id:
            await deleteMessage(msg)

    del hanlder_dict[message.id]
    text = (f'<b>Backup Message {status}!</b>\n'
            f'<b>┌ By:</b> {message.from_user.mention}\n'
            f'<b>├ Source:</b> {stitle}\n'
            f'<b>├ Destination:</b> {dtitle}\n'
            f'<b>├ Total:</b> {total_msg}\n'
            f'<b>├ Success:</b> {succ}\n'
            f'<b>├ Empty:</b> {empy}\n'
            f'<b>├ Failed:</b> {fail}\n'
            f'<b>├ Client:</b> {"USER" if is_session else "BOT"}\n'
            f'<b>└ Time Taken:</b> {get_readable_time(time() - message.date.timestamp())}')
    await gather(deleteMessage(cmsg), sendingMessage(text, message, choice(config_dict['IMAGE_COMPLETE'].split())))


async def backup_message_hanlder(_, query: CallbackQuery):
    data = query.data.split()
    if int(data[2]) != query.from_user.id:
        await query.answer('Not yours!', True)
        return
    backup: Backup = hanlder_dict.get(int(data[3]))
    if not backup:
        await query.answer('Old Task', True)
        return
    if data[1] == 'stop':
        await query.answer('Cancelling backup mmessage(s)...')
        backup.CANCEL = True
    else:
        await query.answer(f'Change media type to: {data[1].title()}')
        backup.TYPE = data[1]


bot.add_handler(MessageHandler(backup_message, filters=command(BotCommands.BackupCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(backup_message_hanlder, filters=regex('^backup')))
