from asyncio import sleep, gather
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message

from bot import bot, task_dict, task_dict_lock, user_data, config_dict, multi_tags, OWNER_ID
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import getTaskByGid, getAllTasks, MirrorStatus
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendingMessage, auto_delete_message, deleteMessage, editPhoto, editMessage


@new_task
async def cancel_task(_, message: Message):
    user_id = message.from_user.id if message.from_user else message.sender_chat.id
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        if len(gid) == 4:
            multi_tags.discard(gid)
            return
        task = await getTaskByGid(gid)
        if not task:
            cancelmsg = await sendMessage(f'⚠️ {message.from_user.mention}, GID <code>{gid}</code> Not Found!', message)
            await auto_delete_message(message, cancelmsg)
            return
    elif reply_to_id := message.reply_to_message_id:
        async with task_dict_lock:
            task = task_dict.get(reply_to_id)
        if not task:
            cancelmsg = await sendMessage(f'⚠️ {message.from_user.mention}, This Is Not An Active Task!', message)
            await auto_delete_message(message, cancelmsg)
            return
    elif len(msg) == 1:
        cancelmsg = ('<blockquote>┌━━━«★彡 <b>HOW TO CANCEL</b> 彡★»━━━\n'
                     f'├ ↩️ Reply to active <code>/{BotCommands.MirrorCommand}</code> message\n'
                     f'├ 🆔 Or send <code>/{BotCommands.CancelTaskCommand} GID</code>\n'
                     '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')
        cancelmsg = await sendMessage(cancelmsg, message)
        await auto_delete_message(message, cancelmsg)
        return

    if OWNER_ID != user_id and task.listener.user_id != user_id and (user_id not in user_data or not user_data[user_id].get('is_sudo')):
        cancelmsg = await sendMessage(f'🚫 {message.from_user.mention}, This Task Is Not Yours!', message)
        await auto_delete_message(message, cancelmsg)
        return

    obj = task.task()
    await gather(obj.cancel_task(), auto_delete_message(message))


async def cancel_multi(_, query: CallbackQuery):
    data = query.data.split()
    user_id = query.from_user.id
    if user_id != int(data[1]) and not await CustomFilters.sudo('', query):
        await query.answer('Not Yours!', True)
        return
    tag = int(data[2])
    if tag in multi_tags:
        multi_tags.discard(int(data[2]))
        msg = '⛔ Stopped!'
    else:
        msg = '✅ Already Stopped / Finished!'
    await gather(query.answer(msg, True), deleteMessage(query.message))


async def cancel_all(message: Message, status: str, user_id: int):
    matches = await getAllTasks(status)
    if matches:
        success = 0
        for task in matches:
            if user_id and task.listener.user_id != user_id:
                continue
            obj = task.task()
            await obj.cancel_task()
            success += 1
            await sleep(1)
        text = (f'✅ Successfully Cancelled <b>{len(matches)}</b> task(s) for <b>{status}</b>.'
                if success else f'ℹ️ No active tasks for <b>{status}</b>.')
    else:
        text = f'ℹ️ No active tasks for <b>{status}</b>.'
    await gather(sendMessage(text, message.reply_to_message), deleteMessage(message))


def create_cancel_buttons(user_id: int):
    buttons = ButtonMaker()
    [buttons.button_data(name, f'canall {user_id} ms {name}') for stats, name in MirrorStatus.__dict__.items() if stats.startswith('STATUS')]
    buttons.button_data('👤 All (USER)', f'canall {user_id} ms user')
    buttons.button_data('👑 All (SUDO)', f'canall {user_id} ms all')
    buttons.button_data('✘ Close', f'canall {user_id} close', 'footer')
    return buttons.build_menu(2)


async def cancell_all_buttons(_, message: Message):
    async with task_dict_lock:
        if len(task_dict) == 0:
            await sendMessage('ℹ️ <b>No active tasks to cancel!</b>', message)
            return
    text = ('<blockquote>┌━━━«★彡 <b>CANCEL TASKS</b> 彡★»━━━\n'
            '├ ⛔ Choose which task category to cancel:\n'
            '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')
    await sendingMessage(text, message, config_dict['IMAGE_CANCEL'], create_cancel_buttons(message.from_user.id))


@new_task
async def cancel_all_update(_, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    user_id = int(data[1])
    if user_id != query.from_user.id:
        await query.answer('🚫 Not Yours!', True)
        return
    if data[2] == 'all' and not await CustomFilters.sudo('', message.reply_to_message):
        await query.answer('🚫 Sudo only option!', True)
        return
    await query.answer()
    base_text = ('<blockquote>┌━━━«★彡 <b>CANCEL TASKS</b> 彡★»━━━\n'
                 '├ ⛔ Choose which task category to cancel:\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')
    match data[2]:
        case 'close':
            await deleteMessage(message, message.reply_to_message)
        case 'back':
            await editMessage(base_text, message, create_cancel_buttons(user_id))
        case 'ms':
            buttons = ButtonMaker()
            buttons.button_data('✅ Yes, Cancel', f'canall {user_id} {data[3]}')
            buttons.button_data('« Back', f'canall {user_id} back')
            buttons.button_data('✘ Close', f'canall {user_id} close')
            confirm_text = ('<blockquote>┌━━━«★彡 <b>CONFIRM CANCEL</b> 彡★»━━━\n'
                            f'├ ⚠️ Cancel all <b>{data[3]}</b> tasks?\n'
                            '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')
            await editMessage(confirm_text, message, buttons.build_menu(2))
        case value:
            if value == 'all':
                user_id = 0
            elif value == 'user':
                value = 'all'

            wait_text = f"⏳ <i>Cancelling <b>{value.replace('...', '')}</b> task(s), please wait...</i>"
            if config_dict['ENABLE_IMAGE_MODE']:
                await editPhoto(wait_text, message, config_dict['IMAGE_CANCEL'])
            else:
                await editMessage(wait_text, message)
            await cancel_all(message, value, user_id)


bot.add_handler(MessageHandler(cancel_task, filters=command(BotCommands.CancelTaskCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(cancell_all_buttons, filters=command(BotCommands.CancelAllCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex('^canall')))
