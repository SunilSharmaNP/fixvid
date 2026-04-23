from __future__ import annotations
from aiofiles.os import path as aiopath, makedirs
from ast import literal_eval
from asyncio import Event, wait_for, wrap_future, gather
from functools import partial
from os import path as ospath
from PIL import Image
from pyrogram.filters import regex, user, text, photo, document
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from re import match as re_match
from time import time

from bot import config_dict, VID_MODE
from bot.helper.ext_utils.bot_utils import new_task, new_thread, sync_to_async
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.links_utils import is_media
from bot.helper.ext_utils.status_utils import get_readable_time
from bot.helper.listeners import tasks_listener as task
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage


class SelectMode():
    def __init__(self, listener: task.TaskListener, isLink=False):
        self._isLink = isLink
        self._time = time()
        self._reply = None
        self.listener = listener
        self.is_rename = False
        self.mode = ''
        self.extra_data = {}
        self.newname = ''
        self.event = Event()
        self.message_event = Event()
        self.is_cancelled = False

    @new_thread
    async def _event_handler(self):
        pfunc = partial(cb_vidtools, obj=self)
        handler = self.listener.client.add_handler(CallbackQueryHandler(pfunc, filters=regex('^vidtool') & user(self.listener.user_id)), group=-1)
        try:
            await wait_for(self.event.wait(), timeout=180)
        except:
            self.mode = 'Task has been cancelled, time out!'
            self.is_cancelled = True
            self.event.set()
        finally:
            self.listener.client.remove_handler(*handler)

    @new_thread
    async def message_event_handler(self, mode=''):
        pfunc = partial(message_handler, obj=self, is_sub=mode == 'subfile')
        handler = self.listener.client.add_handler(MessageHandler(pfunc, user(self.listener.user_id)), group=1)
        try:
            await wait_for(self.message_event.wait(), timeout=60)
        except:
            self.message_event.set()
        finally:
            self.listener.client.remove_handler(*handler)
            self.message_event.clear()

    async def _send_message(self, text: str, buttons):
        if not self._reply:
            self._reply = await sendMessage(text, self.listener.message, buttons)
        else:
            await editMessage(text, self._reply, buttons)

    def _captions(self, mode: str=None):
        # SS Bots styled professional Video Tools UI
        mode_icons = {
            'vid_vid': '🎞️', 'vid_aud': '🎵', 'vid_sub': '📝', 'subsync': '🔄',
            'compress': '🗜️', 'convert': '♻️', 'watermark': '💧',
            'extract': '📤', 'trim': '✂️', 'rmstream': '🚫',
        }
        # Professional tool descriptions shown under selected mode
        mode_desc = {
            'vid_vid':  'Merge two or more video files into one output.',
            'vid_aud':  'Mux extra audio track(s) into a video.',
            'vid_sub':  'Mux subtitle file(s) into a video (soft / hardsub).',
            'subsync':  'Auto / manually sync subtitle timings to the video.',
            'compress': 'Re-encode the video to a smaller size with chosen quality.',
            'convert':  'Change container / codec to a different format.',
            'watermark':'Burn an image watermark (or hardsub) onto the video.',
            'extract':  'Pull out video / audio / subtitle streams as files.',
            'trim':     'Cut a section from the video using a time range.',
            'rmstream': 'Remove unwanted audio / subtitle streams from the video.',
        }
        header = '┌━━━«★彡 <b>VIDEO TOOLS</b> 彡★»━━━'
        footer = '└━━━«★彡 <b>SS Bots</b> 彡★»━━━'
        lines = [header]
        vidmode = VID_MODE.get(self.mode)
        icon = mode_icons.get(self.mode, '🎬')
        if vidmode:
            lines.append(f'├ {icon} <b>Mode :</b> <i>{vidmode}</i>')
            if desc := mode_desc.get(self.mode):
                lines.append(f'├ 💡 <b>About :</b> <i>{desc}</i>')
        else:
            lines.append('├ 🎬 <b>Mode :</b> <i>Not selected</i>')
            lines.append('├ 💡 <b>Tip :</b> <i>Pick a tool below to get started.</i>')
        lines.append(f'├ 📝 <b>Name :</b> <code>{self.newname or "Default"}</code>')
        if self.extra_data and self.mode == 'trim':
            t = list(self.extra_data.values())
            lines.append(f'├ ✂️ <b>Trim :</b> <code>{" → ".join(map(str, t))}</code>')
        if self.mode in ('vid_sub', 'watermark'):
            hardsub = self.extra_data.get('hardsub')
            lines.append(f"├ 🔥 <b>Hardsub :</b> {'✅ Enabled' if hardsub else '❌ Disabled'}")
            if hardsub:
                lines.append(f"├ 🅱️ <b>Bold Style :</b> {'✅ On' if self.extra_data.get('boldstyle') else '❌ Off'}")
                if fontname := self.extra_data.get('fontname') or config_dict['HARDSUB_FONT_NAME']:
                    lines.append(f"├ 🔤 <b>Font Name :</b> <i>{fontname.replace('_', ' ')}</i>")
                if fontsize := self.extra_data.get('fontsize') or config_dict['HARDSUB_FONT_SIZE']:
                    lines.append(f'├ 🔡 <b>Font Size :</b> <i>{fontsize}</i>')
                if fontcolour := self.extra_data.get('fontcolour'):
                    lines.append(f'├ 🎨 <b>Font Colour :</b> <code>#{fontcolour}</code>')
        if quality := self.extra_data.get('quality'):
            lines.append(f'├ 📺 <b>Quality :</b> <i>{quality}</i>')
        if self.mode == 'watermark' and (wmsize := self.extra_data.get('wmsize')):
            lines.append(f'├ 📐 <b>WM Size :</b> <i>{wmsize}</i>')
            if wmsize and (wmposition := self.extra_data.get('wmposition')):
                pos_dict = {'5:5': '↖️ Top Left',
                            'main_w-overlay_w-5:5': '↗️ Top Right',
                            '5:main_h-overlay_h': '↙️ Bottom Left',
                            'w-overlay_w-5:main_h-overlay_h-5': '↘️ Bottom Right'}
                lines.append(f'├ 📍 <b>WM Position :</b> <i>{pos_dict[wmposition]}</i>')
            if popupwm := self.extra_data.get('popupwm'):
                lines.append(f'├ 💫 <b>Display :</b> <i>{popupwm}x / 20s</i>')
        if self.mode == 'subsync' and (typee := self.extra_data.get('type')):
            lines.append(f'├ 🔄 <b>Sync Mode :</b> <i>{typee.lstrip("sync_").title()}</i>')
        lines.append(footer)
        msg = '\n'.join(lines)
        # Action prompt
        prompts = {
            'rename':    '\n\n📝 <i>Send a valid file name with extension…</i>',
            'watermark': '\n\n💧 <i>Send a valid image to use as watermark…</i>',
            'subfile':   '\n\n📄 <i>Send a subtitle file (.ass or .srt) for hardsub…</i>',
            'wmsize':    '\n\n📐 <i>Pick the watermark size</i>',
            'fontsize':  ('\n\n🔡 <i>Pick a font size</i>\n'
                          '<b>Recommended:</b>\n'
                          '• 1080p — <b>21-26</b>\n'
                          '• 720p  — <b>16-21</b>\n'
                          '• 480p  — <b>11-16</b>'),
            'trim':      '\n\n✂️ <i>Send a trim range</i>\n<code>hh:mm:ss hh:mm:ss</code>',
        }
        if mode in prompts:
            msg += prompts[mode]
        msg += f'\n\n⏳ <i>Time Out :</i> <b>{get_readable_time(180 - (time()-self._time))}</b>'
        return f'<blockquote>{msg}</blockquote>'

    async def list_buttons(self, mode: str=''):
        buttons, bnum = ButtonMaker(), 2
        # Pretty button labels for tools (icon + name)
        mode_btn_labels = {
            'vid_vid':  '🎞️ Video + Video',
            'vid_aud':  '🎵 Video + Audio',
            'vid_sub':  '📝 Video + Subtitle',
            'subsync':  '🔄 SubSync',
            'compress': '🗜️ Compress',
            'convert':  '♻️ Convert',
            'watermark':'💧 Watermark',
            'extract':  '📤 Extract',
            'trim':     '✂️ Trim',
            'rmstream': '🚫 Remove Stream',
        }
        if not mode:
            vid_modes = dict(list(VID_MODE.items())[4:]) if self._isLink else VID_MODE
            for key, value in vid_modes.items():
                label = mode_btn_labels.get(key, value)
                buttons.button_data(f"{'✅ ' if self.mode == key else ''}{label}", f'vidtool {key}')
            buttons.button_data(f'{"✅ " if self.newname else "✏️ "}Rename', 'vidtool rename', 'header')
            buttons.button_data('❌ Cancel', 'vidtool cancel', 'footer')
            if self.mode:
                buttons.button_data('✔️ Done', 'vidtool done', 'footer')
            if self.mode in ('vid_sub', 'watermark') and await CustomFilters.sudo('', self.listener.message):
                hardsub = self.extra_data.get('hardsub')
                buttons.button_data(f"{'✅ ' if hardsub else '🔥 '}Hardsub", 'vidtool hardsub', 'header')
                if hardsub:
                    if self.mode == 'watermark':
                        has_sub = await aiopath.exists(self.extra_data.get('subfile', ''))
                        buttons.button_data(f"{'✅ ' if has_sub else '📄 '}Sub File", 'vidtool subfile', 'header')
                    buttons.button_data('🅰️ Font Style', 'vidtool fontstyle', 'header')

            if self.mode in ('compress', 'watermark') or self.extra_data.get('hardsub'):
                buttons.button_data('📺 Quality', 'vidtool quality', 'header')
            if self.mode == 'watermark':
                buttons.button_data('💫 Popup', 'vidtool popupwm', 'header')
        else:
            def _buttons_style(name=True, size=True, colour=True, position='header', cb='fontstyle'):
                if name:
                    buttons.button_data('🔤 Font Name', 'vidtool fontstyle fontname', position)
                if size:
                    buttons.button_data('🔡 Font Size', 'vidtool fontstyle fontsize', position)
                if colour:
                    buttons.button_data('🎨 Font Colour', 'vidtool fontstyle fontcolour', position)
                buttons.button_data('« Back', f'vidtool {cb}', 'footer')
                buttons.button_data('✔️ Done', 'vidtool done', 'footer')

            match mode:
                case 'subsync':
                    buttons.button_data('🛠️ Manual', 'vidtool sync_manual')
                    buttons.button_data('⚡ Auto', 'vidtool sync_auto')
                case 'quality':
                    bnum = 3
                    [buttons.button_data(f"{'✅ ' if self.extra_data.get('quality') == key else ''}{key}", f'vidtool quality {key}') for key in ['1080p', '720p', '540p', '480p', '360p']]
                    buttons.button_data('« Back', 'vidtool back', 'footer')
                    buttons.button_data('✔️ Done', 'vidtool done', 'footer')
                case 'popupwm':
                    bnum, popupwm = 5, self.extra_data.get('popupwm', 0)
                    if popupwm:
                        buttons.button_data('🔄 Reset', 'vidtool popupwm 0', 'header')
                    [buttons.button_data(f"{'✅ ' if popupwm == key else ''}{key}", f'vidtool popupwm {key}') for key in range(2, 21, 2)]
                    buttons.button_data('« Back', 'vidtool back', 'footer')
                    buttons.button_data('✔️ Done', 'vidtool done', 'footer')
                case 'wmsize':
                    bnum = 3
                    [buttons.button_data(f"{'✅ ' if str(btn) == str(self.extra_data.get('wmsize')) else ''}{btn}", f'vidtool wmsize {btn}') for btn in [5, 10, 15, 20, 25, 30]]
                case 'fontstyle':
                    bnum = 3
                    _buttons_style(position=None, cb='back')
                    buttons.button_data(f"{'✅ ' if self.extra_data.get('boldstyle') else '🅱️ '}Bold Style", f"vidtool fontstyle boldstyle {self.extra_data.get('boldstyle', False)}", 'header')
                case 'fontname':
                    _buttons_style(name=False)
                    [buttons.button_data(f"{'✅ ' if btn == self.extra_data.get('fontname') else ''}{btn.replace('_', ' ')}", f'vidtool fontstyle fontname {btn}')
                     for btn in ['Arial', 'Impact', 'Verdana', 'Consolas', 'DejaVu_Sans', 'Comic_Sans_MS', 'Simple_Day_Mistu']]
                case 'fontsize':
                    bnum = 5
                    _buttons_style(size=False)
                    [buttons.button_data(f"{'✅ ' if str(btn) == str(self.extra_data.get('fontsize')) else ''}{btn}", f'vidtool fontstyle fontsize {btn}') for btn in range(11, 31)]
                case 'fontcolour':
                    bnum = 3
                    _buttons_style(colour=False)
                    colours = [('🔴 Red', '0000ff'), ('🟢 Green', '00ff00'), ('🔵 Blue', 'ff0000'), ('🟡 Yellow', '00ffff'),
                               ('🟠 Orange', '0054ff'), ('🟣 Purple', '005aff'),
                               ('🌸 Soft Red', 'd470ff'), ('🍃 Soft Green', '80ff80'),
                               ('💧 Soft Blue', 'ffb84d'), ('🌼 Soft Yellow', '80ffff')]
                    [buttons.button_data(f"{'✅ ' if hexcolour == self.extra_data.get('fontcolour') else ''}{btn}", f'vidtool fontstyle fontcolour {hexcolour}') for btn, hexcolour in colours]
                case 'wmposition':
                    cur = self.extra_data.get('wmposition')
                    positions = [('↖️ Top Left', '5:5'),
                                 ('↗️ Top Right', 'main_w-overlay_w-5:5'),
                                 ('↙️ Bottom Left', '5:main_h-overlay_h'),
                                 ('↘️ Bottom Right', 'w-overlay_w-5:main_h-overlay_h-5')]
                    for label, val in positions:
                        buttons.button_data(f"{'✅ ' if cur == val else ''}{label}", f'vidtool wmposition {val}')
                case _:
                    buttons.button_data('« Back', 'vidtool back', 'footer')

        await self._send_message(self._captions(mode), buttons.build_menu(bnum, 3))

    async def get_buttons(self):
        future = self._event_handler()
        await gather(self.list_buttons(), wrap_future(future))
        if self.is_cancelled:
            await editMessage(self.mode, self._reply)
            return
        await deleteMessage(self._reply)
        return [self.mode, self.newname, self.extra_data]


async def message_handler(_, message: Message, obj: SelectMode, is_sub=False):
    data = None
    if obj.is_rename and message.text:
        obj.newname = message.text.strip().replace('/', '')
        obj.is_rename = False
    elif obj.mode == 'watermark' and (media := is_media(message)):
        if is_sub:
            if message.document and not media.file_name.lower().endswith(('.ass', '.srt')):
                await sendMessage('Only .ass or .srt allowed!', message)
                return
            obj.extra_data['subfile'] = await message.download(ospath.join('watermark', media.file_id))
        else:
            if message.document and 'image' not in getattr(media, 'mime_type', 'None'):
                await sendMessage('Only image document allowed!', message)
                return
            fpath = await message.download(ospath.join('watermark', media.file_id))
            await sync_to_async(Image.open(fpath).convert('RGBA').save, ospath.join('watermark', f'{obj.listener.mid}.png'), 'PNG')
            await clean_target(fpath)
            data = 'wmsize'
    elif obj.mode == 'trim' and message.text:
        if match := re_match(r'(\d{2}:\d{2}:\d{2})\s(\d{2}:\d{2}:\d{2})', message.text.strip()):
            obj.extra_data.update({'start_time': match.group(1), 'end_time': match.group(2)})
        else:
            await sendMessage('Invalid trim duration format!', message)
            return
    obj.message_event.set()
    await gather(obj.list_buttons(data), deleteMessage(message))


@new_task
async def cb_vidtools(_, query: CallbackQuery, obj: SelectMode):
    data = query.data.split()
    if data[1] in config_dict['DISABLE_VIDTOOLS']:
        await query.answer(f'{VID_MODE[data[1]]} has been disabled!', True)
        return
    await query.answer()
    if data[1] == obj.mode:
        return
    match data[1]:
        case 'done':
            obj.event.set()
        case 'back':
            if obj.message_event:
                obj.message_event.set()
            await obj.list_buttons()
        case 'cancel':
            obj.mode = 'Task has been cancelled!'
            obj.is_cancelled = True
            obj.event.set()
        case 'quality' | 'popupwm' as value:
            if len(data) == 3:
                obj.extra_data[value] = data[2] if value == 'quality' else int(data[2])
            await obj.list_buttons(value)
        case 'hardsub':
            hmode = not bool(obj.extra_data.get('hardsub'))
            if not hmode and obj.mode == 'vid_sub':
                obj.extra_data.clear()
            obj.extra_data['hardsub'] = hmode
            await obj.list_buttons()
        case 'subfile':
            future = obj.message_event_handler('subfile')
            await gather(obj.list_buttons('subfile'), wrap_future(future))
        case 'fontstyle':
            mode = 'fontstyle'
            if len(data) > 2:
                mode = data[2]
                is_bold = mode == 'boldstyle'
                if len(data) == 4:
                    if not is_bold and obj.extra_data.get(mode) == data[3]:
                        return
                    obj.extra_data[mode] = not literal_eval(data[3]) if is_bold else data[3]
                if is_bold:
                    mode = 'fontstyle'
            await obj.list_buttons(mode)
        case 'sync_manual' | 'sync_auto' as value:
            obj.extra_data['type'] = value
            await obj.list_buttons()
        case 'wmsize' | 'wmposition' as value:
            obj.extra_data[value] = data[2]
            await obj.list_buttons('wmposition' if value == 'wmsize' else None)
        case value:
            if value == 'rename':
                obj.is_rename = True
            else:
                obj.mode = value
                obj.extra_data.clear()
            if value in ['watermark', 'rename', 'trim']:
                future = obj.message_event_handler(value)
                await gather(obj.list_buttons(value), wrap_future(future))
                return
            await obj.list_buttons('subsync' if value == 'subsync' else '')
