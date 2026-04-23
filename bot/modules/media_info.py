from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.links_utils import is_url, get_url_name, get_link, is_media
from bot.helper.ext_utils.media_utils import post_media_info
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.stream_utils.file_properties import gen_link
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendPhoto, editPhoto, copyMessage, deleteMessage
from bot.helper.video_utils.executor import get_metavideo
@new_task
async def medinfo(_, message: Message):
    link, media, cmsg = get_link(message), None, None
    if (reply_to := message.reply_to_message) and (media := is_media(reply_to)) and (chat_id := config_dict['LEECH_LOG']):
        cmsg = await copyMessage(chat_id, reply_to)
        link = (await gen_link(cmsg or reply_to))[1]
    if link and is_url(link):
        img = config_dict['IMAGE_MEDINFO']
        msg = await sendPhoto('<i>Processing, please wait...</i>', message, img)
        if (size := int((await get_metavideo(link))[1].get('size', 0))) and (result := await post_media_info(link, size, is_link=True)):
            buttons = ButtonMaker()
            buttons.button_link('Media Info', result)
            if not media:
                buttons.button_link('Source', link)
            text = ('<blockquote>┌━━━«★彡 <b>MEDIA INFO</b> 彡★»━━━\n'
                    f'├ 📄 <b>Name :</b> <code>{get_url_name(link)}</code>\n'
                    f'├ 💾 <b>Size :</b> <i>{get_readable_file_size(size)}</i>\n'
                    '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')
            await editPhoto(text, msg, img, buttons.build_menu(1))
        else:
            await editPhoto('❌ <b>Error fetching media info!</b>', msg, img)
    else:
        await sendMessage('⚠️ <b>Send the command with a link, or reply to a link / media file!</b>', message)
    if cmsg:
        await deleteMessage(cmsg)
bot.add_handler(MessageHandler(medinfo, command(BotCommands.MediaInfoCommand) & CustomFilters.authorized))
