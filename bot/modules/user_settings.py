from aiofiles.os import path as aiopath, makedirs
from ast import literal_eval
from asyncio import sleep, gather, Event, wait_for, wrap_future
from functools import partial
from html import escape
from os import path as ospath, getcwd
from pyrogram import Client
from pyrogram.filters import command, regex, create, user
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message
from time import time

from bot import bot, bot_loop, bot_dict, bot_lock, user_data, config_dict, DATABASE_URL, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import update_user_ldata, UserDaily, new_thread, new_task, is_premium_user
from bot.helper.ext_utils.commons_check import UseCheck
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.ext_utils.files_utils import clean_target
from bot.helper.ext_utils.help_messages import UsetString
from bot.helper.ext_utils.media_utils import createThumb
from bot.helper.ext_utils.status_utils import get_readable_time, get_readable_file_size
from bot.helper.ext_utils.telegram_helper import TeleContent
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message, sendPhoto, editPhoto, deleteMessage, editMessage, sendCustom


handler_dict = {}

_VID_PRESET_BACK = 'vid_compress'
_VID_HARDSUB_BACK = 'vid_hardsub'

_COMPRESS_PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium']


async def get_user_settings(from_user, data: str, uset_data: str):
    buttons = ButtonMaker()
    user_id = from_user.id
    thumbpath = ospath.join('thumbnails', f'{user_id}.jpg')
    rclone_path = ospath.join('rclone', f'{user_id}.conf')
    token_pickle = ospath.join('tokens', f'{user_id}.pickle')
    user_dict = user_data.get(user_id, {})
    premium_left = status_user = daily_limit = ''
    image = None

    # ──────────────────────── MAIN MENU ────────────────────────
    if not data:
        ON, OFF, SET, UNSET = '✅ ON', '❌ OFF', '✅ SET', '❌ UNSET'
        has_thumb = await aiopath.exists(thumbpath)
        has_rcc   = await aiopath.exists(rclone_path)
        has_gdx   = await aiopath.exists(token_pickle)

        AD = config_dict['AS_DOCUMENT']
        is_doc = (not user_dict and AD) or user_dict.get('as_doc')
        ltype = '📄 DOCUMENT' if is_doc else '🎞️ MEDIA'

        default_upload = user_dict.get('default_upload', '') or config_dict['DEFAULT_UPLOAD']
        du = 'GDrive API' if default_upload == 'gd' else 'RClone'

        buttons.button_data('⚙️ General',      f'userset {user_id} general',  'header')
        buttons.button_data('📥 Leech',         f'userset {user_id} leech',    'header')
        buttons.button_data('☁️ Mirror',        f'userset {user_id} mirror')
        buttons.button_data('🎬 FF / Metadata', f'userset {user_id} ffset')
        buttons.button_data('🎞️ Video Tools',   f'userset {user_id} vidtools')
        buttons.button_data('🔧 Advanced',      f'userset {user_id} advanced')

        _watch_keys = ['prename', 'sufname', 'remname', 'as_doc', 'media_group',
                       'enable_pm', 'enable_ss', 'metadata', 'captions', 'yt_opt',
                       'dump_ch', 'session_string', 'excluded_extensions', 'caption_style',
                       'zipmode', 'default_upload', 'stop_duplicate', 'use_sa',
                       'vid_264_preset', 'vid_265_preset', 'vid_banner',
                       'vid_hardsub_font', 'vid_hardsub_size']
        if user_dict and any(k in user_dict for k in _watch_keys) or has_thumb or has_rcc or has_gdx:
            buttons.button_data('🗑️ Reset All', f'userset {user_id} reset_all_confirm', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        if config_dict['PREMIUM_MODE']:
            if (user_premi := is_premium_user(user_id)) and (time_data := user_dict.get('premium_left')):
                if time_data - time() <= 0:
                    await gather(update_user_ldata(user_id, 'is_premium', False),
                                 update_user_ldata(user_id, 'premium_left', 0))
                else:
                    premium_left = f'├ ⏳ <b>Premium Left :</b> <i>{get_readable_time(time_data - time())}</i>\n'
            if user_id != config_dict['OWNER_ID']:
                status_user = ('├ 💎 <b>Status :</b> <b>PREMIUM</b>\n' if is_premium_user(user_id)
                               else '├ 👤 <b>Status :</b> <b>NORMAL</b>\n')
        if config_dict['DAILY_MODE'] and not is_premium_user(user_id):
            await UserDaily(user_id).get_daily_limit()
            daily_limit  = f'├ 📊 <b>Daily Limit :</b> <i>{get_readable_file_size(user_data[user_id]["daily_limit"])} / {config_dict["DAILY_LIMIT_SIZE"]}GB</i>\n'
            daily_limit += f'├ ⏰ <b>Reset In :</b> <i>{get_readable_time(user_data[user_id]["reset_limit"] - time())}</i>\n'

        text = ('<blockquote>┌━━━«★彡 <b>USER SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'{status_user}'
                f'{premium_left}'
                f'{daily_limit}'
                f'├ 🎞️ <b>Leech Type :</b> <i>{ltype}</i>\n'
                f'├ 🖼️ <b>Thumbnail :</b> <i>{"✅ SET" if has_thumb else "❌ UNSET"}</i>\n'
                f'├ ☁️ <b>RClone :</b> <i>{"✅ EXISTS" if has_rcc else "❌ NOT SET"}</i>\n'
                f'├ 🔑 <b>GDrive Token :</b> <i>{"✅ EXISTS" if has_gdx else "❌ NOT SET"}</i>\n'
                f'├ ⚙️ <b>Default Upload :</b> <i>{du}</i>\n'
                '├ ─────────────────────────\n'
                '├ 🗂️ Select a category below\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── GENERAL SETTINGS ────────────────────────
    elif data == 'general':
        ON, OFF, SET, UNSET = '✅ ON', '❌ OFF', '✅ SET', '❌ UNSET'

        sendpm = ON if user_dict.get('enable_pm') else OFF
        buttons.button_data(f'{"✅" if user_dict.get("enable_pm") else "📩"} Send PM',
                            f'userset {user_id} enable_pm')

        sendss = ON if user_dict.get('enable_ss') else OFF
        buttons.button_data(f'{"✅" if user_dict.get("enable_ss") else "📸"} Screenshot',
                            f'userset {user_id} enable_ss')

        AD = config_dict['AS_DOCUMENT']
        is_doc = (not user_dict and AD) or user_dict.get('as_doc')
        ltype = '📄 DOCUMENT' if is_doc else '🎞️ MEDIA'
        buttons.button_data(f'{"✅" if is_doc else "📄"} As Document',
                            f'userset {user_id} as_doc')

        MG = config_dict['MEDIA_GROUP']
        is_mg = user_dict.get('media_group') or ('media_group' not in user_dict and MG)
        mediagroup = ON if is_mg else OFF
        buttons.button_data(f'{"✅" if is_mg else "🗂️"} Media Group',
                            f'userset {user_id} media_group')

        default_upload = user_dict.get('default_upload', '') or config_dict['DEFAULT_UPLOAD']
        du  = 'GDrive API' if default_upload == 'gd' else 'RClone'
        dub = 'GDRIVE' if default_upload != 'gd' else 'RCLONE'
        buttons.button_data(f'⚙️ Engine: {dub}', f'userset {user_id} {default_upload}', 'header')

        has_ses = bool(user_dict.get('session_string'))
        sesmsg  = ON if has_ses else OFF
        buttons.button_data(f'{"✅" if has_ses else "🔐"} Session String',
                            f'userset {user_id} setdata session_string')

        YOPT = config_dict['YT_DLP_OPTIONS']
        if user_dict.get('yt_opt'):
            yto_status, ytset = SET, True
        elif 'yt_opt' not in user_dict and YOPT:
            yto_status, ytset = '✅ (Global)', True
        else:
            yto_status, ytset = UNSET, False
        buttons.button_data(f'{"✅" if ytset else "🎬"} YT-DLP Options',
                            f'userset {user_id} setdata yt_opt')

        buttons.button_data('« Back',   f'userset {user_id} back', 'footer')
        buttons.button_data('✘ Close',  f'userset {user_id} close', 'footer')

        text = ('<blockquote>┌━━━«★彡 <b>GENERAL SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'├ 📩 <b>Send PM :</b> <i>{sendpm}</i>\n'
                f'├ 📸 <b>Screenshot :</b> <i>{sendss}</i>\n'
                f'├ 📄 <b>Leech Type :</b> <i>{ltype}</i>\n'
                f'├ 🗂️ <b>Media Group :</b> <i>{mediagroup}</i>\n'
                f'├ ⚙️ <b>Default Upload :</b> <i>{du}</i>\n'
                f'├ 🔐 <b>Session String :</b> <i>{sesmsg}</i>\n'
                f'├ 🎬 <b>YT-DLP Options :</b> <i>{yto_status}</i>\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── LEECH SETTINGS ────────────────────────
    elif data == 'leech':
        ON, OFF, SET, UNSET = '✅ ON', '❌ OFF', '✅ SET', '❌ UNSET'

        has_thumb = await aiopath.exists(thumbpath)
        thumbmsg  = '✅ SET' if has_thumb else '❌ UNSET'
        buttons.button_data(f'{"✅" if has_thumb else "🖼️"} Thumbnail',
                            f'userset {user_id} setdata thumb')

        split_size = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])

        dch    = user_dict.get('dump_ch')
        dumpch = f'<code>{dch}</code>' if dch else UNSET
        buttons.button_data(f'{"✅" if dch else "📥"} Dump CH',
                            f'userset {user_id} setdata dump_ch')

        prename = user_dict.get('prename')
        premsg  = f'<code>{escape(prename)}</code>' if prename else UNSET
        buttons.button_data(f'{"✅" if prename else "🔠"} Prename',
                            f'userset {user_id} setdata prename')

        sufname = user_dict.get('sufname')
        sufmsg  = f'<code>{escape(sufname)}</code>' if sufname else UNSET
        buttons.button_data(f'{"✅" if sufname else "🔡"} Sufname',
                            f'userset {user_id} setdata sufname')

        remname = user_dict.get('remname')
        rmmsg   = ON if remname else OFF
        buttons.button_data(f'{"✅" if remname else "🧹"} Remname',
                            f'userset {user_id} setdata remname')

        has_cap = bool(user_dict.get('captions'))
        capmode = user_dict.get('caption_style', 'mono').upper()
        buttons.button_data(f'{"✅" if has_cap else "💬"} Caption',
                            f'userset {user_id} capmode')

        _zmap  = {'zfolder': 'Folders', 'zfpart': 'Cloud Part',
                  'zeach': 'Each Files', 'zpart': 'Part Mode', 'auto': 'Auto Mode'}
        zmode_raw = user_dict.get('zipmode', 'zfolder')
        zmode_display = _zmap.get(zmode_raw, zmode_raw)
        buttons.button_data('🗜️ Zip Mode', f'userset {user_id} zipmode')

        buttons.button_data('« Back',  f'userset {user_id} back', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = ('<blockquote>┌━━━«★彡 <b>LEECH SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'├ 🖼️ <b>Thumbnail :</b> <i>{thumbmsg}</i>\n'
                f'├ ✂️ <b>Leech Split Size :</b> <i>{split_size}</i>\n'
                f'├ 📥 <b>Dump CH :</b> <i>{dumpch}</i>\n'
                f'├ 🔠 <b>Prename :</b> <i>{premsg}</i>\n'
                f'├ 🔡 <b>Sufname :</b> <i>{sufmsg}</i>\n'
                f'├ 🧹 <b>Remname :</b> <i>{rmmsg}</i>\n'
                f'├ 💬 <b>Caption Mode :</b> <i>{capmode}</i>\n'
                f'├ 🗜️ <b>Zip Mode :</b> <i>{zmode_display}</i>\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── MIRROR SETTINGS ────────────────────────
    elif data == 'mirror':
        has_rcc  = await aiopath.exists(rclone_path)
        rccmsg   = '✅ EXISTS' if has_rcc else '❌ NOT SET'
        rc_path  = user_dict.get('rclone_path')
        rcpath   = f'<code>{rc_path}</code>' if rc_path else '❌ NOT SET'
        has_gdx  = await aiopath.exists(token_pickle)
        gdxmsg   = '✅ EXISTS' if has_gdx else '❌ NOT SET'
        gd_id    = user_dict.get('gdrive_id')
        gdidmsg  = f'<code>{gd_id}</code>' if gd_id else '❌ NOT SET'

        buttons.button_data('☁️ RClone Tools', f'userset {user_id} rctool')
        buttons.button_data('🔑 GDrive Tools', f'userset {user_id} gdtool')
        buttons.button_data('« Back',  f'userset {user_id} back', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = ('<blockquote>┌━━━«★彡 <b>MIRROR SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'├ ☁️ <b>RClone Config :</b> <b>{rccmsg}</b>\n'
                f'├ 📂 <b>RClone Path :</b> {rcpath}\n'
                f'├ 🔑 <b>GDrive Token :</b> <b>{gdxmsg}</b>\n'
                f'├ 🆔 <b>GDrive ID :</b> {gdidmsg}\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── FF / METADATA SETTINGS ────────────────────────
    elif data == 'ffset':
        metadata    = user_dict.get('metadata')
        meta_status = '✅ SET' if metadata else '❌ NOT SET'
        clean_meta  = user_dict.get('clean_metadata')
        clean_status= '✅ ON' if clean_meta else '❌ OFF'

        buttons.button_data(f'{"✅" if metadata else "🏷️"} Metadata',
                            f'userset {user_id} setdata metadata')
        buttons.button_data(f'{"✅" if clean_meta else "🗑️"} {"Clean" if clean_meta else "Overwrite"} Mode',
                            f'userset {user_id} setdata metadata {not clean_meta}')
        buttons.button_data('« Back',  f'userset {user_id} back', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = ('<blockquote>┌━━━«★彡 <b>FF / METADATA SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'├ 🏷️ <b>Metadata :</b> <i>{meta_status}</i>\n'
                f'├ 🗑️ <b>Clean Metadata :</b> <i>{clean_status}</i>\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── VIDEO TOOLS ────────────────────────
    elif data == 'vidtools':
        vid_264      = user_dict.get('vid_264_preset') or config_dict.get('LIB264_PRESET', 'superfast')
        vid_265      = user_dict.get('vid_265_preset') or config_dict.get('LIB265_PRESET', 'faster')
        vid_banner   = user_dict.get('vid_banner')     or config_dict.get('COMPRESS_BANNER', '')
        vid_font     = user_dict.get('vid_hardsub_font') or config_dict.get('HARDSUB_FONT_NAME', '')
        vid_fontsize = user_dict.get('vid_hardsub_size') or config_dict.get('HARDSUB_FONT_SIZE', '')

        buttons.button_data('🎥 Compress Settings', f'userset {user_id} vid_compress')
        buttons.button_data('📝 HardSub Settings',  f'userset {user_id} vid_hardsub')
        buttons.button_data('« Back',  f'userset {user_id} back', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = ('<blockquote>┌━━━«★彡 <b>VIDEO TOOLS SETTINGS</b> 彡★»━━━\n'
                 f'├ 👤 <b>User :</b> {from_user.mention}\n'
                 f'├ 🎥 <b>x264 Preset :</b> <code>{vid_264}</code>\n'
                 f'├ 🎞️ <b>x265 Preset :</b> <code>{vid_265}</code>\n'
                 f'├ 📝 <b>Compress Banner :</b> <code>{vid_banner or "Default"}</code>\n'
                 f'├ 🔤 <b>HardSub Font :</b> <code>{vid_font or "Default"}</code>\n'
                 f'├ 📏 <b>HardSub Font Size :</b> <code>{vid_fontsize or "Default"}</code>\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── VIDEO TOOLS → COMPRESS ────────────────────────
    elif data == 'vid_compress':
        vid_264    = user_dict.get('vid_264_preset') or config_dict.get('LIB264_PRESET', 'superfast')
        vid_265    = user_dict.get('vid_265_preset') or config_dict.get('LIB265_PRESET', 'faster')
        vid_banner = user_dict.get('vid_banner')     or config_dict.get('COMPRESS_BANNER', '')

        for p in _COMPRESS_PRESETS:
            mark = '🔥 ' if p == vid_264 else ''
            buttons.button_data(f'{mark}264:{p}', f'userset {user_id} set_vid264 {p}')

        for p in _COMPRESS_PRESETS:
            mark = '🔥 ' if p == vid_265 else ''
            buttons.button_data(f'{mark}265:{p}', f'userset {user_id} set_vid265 {p}')

        has_banner = bool(user_dict.get('vid_banner'))
        buttons.button_data(f'{"✅" if has_banner else "📝"} Compress Banner',
                            f'userset {user_id} setdata vid_banner')
        if has_banner:
            buttons.button_data('🗑️ Reset Banner', f'userset {user_id} rem_vid_banner')

        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = ('<blockquote>┌━━━«★彡 <b>COMPRESS SETTINGS</b> 彡★»━━━\n'
                 f'├ 👤 <b>User :</b> {from_user.mention}\n'
                 f'├ 🎥 <b>x264 Preset :</b> <code>{vid_264}</code>\n'
                 f'├ 🎞️ <b>x265 Preset :</b> <code>{vid_265}</code>\n'
                 f'├ 📝 <b>Compress Banner :</b> <code>{vid_banner or "Default"}</code>\n'
                 '├\n'
                 '├ <i>Select 264/265 presets above or set compress banner.</i>\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── VIDEO TOOLS → HARDSUB ────────────────────────
    elif data == 'vid_hardsub':
        vid_font     = user_dict.get('vid_hardsub_font') or config_dict.get('HARDSUB_FONT_NAME', 'Not Set')
        vid_fontsize = user_dict.get('vid_hardsub_size') or config_dict.get('HARDSUB_FONT_SIZE', 'Not Set')

        has_font = bool(user_dict.get('vid_hardsub_font'))
        buttons.button_data(f'{"✅" if has_font else "🔤"} Font Name',
                            f'userset {user_id} setdata vid_hardsub_font')
        if has_font:
            buttons.button_data('🗑️ Reset Font', f'userset {user_id} rem_vid_hardsub_font')

        has_size = bool(user_dict.get('vid_hardsub_size'))
        buttons.button_data(f'{"✅" if has_size else "📏"} Font Size',
                            f'userset {user_id} setdata vid_hardsub_size')
        if has_size:
            buttons.button_data('🗑️ Reset Size', f'userset {user_id} rem_vid_hardsub_size')

        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = ('<blockquote>┌━━━«★彡 <b>HARDSUB SETTINGS</b> 彡★»━━━\n'
                 f'├ 👤 <b>User :</b> {from_user.mention}\n'
                 f'├ 🔤 <b>HardSub Font :</b> <code>{vid_font}</code>\n'
                 f'├ 📏 <b>Font Size :</b> <code>{vid_fontsize}</code>\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── ADVANCED SETTINGS ────────────────────────
    elif data == 'advanced':
        if ext_filters := user_dict.get('excluded_extensions'):
            ex_ex = f'<code>{", ".join(ext_filters)}</code>'
        elif 'excluded_extensions' not in user_dict and GLOBAL_EXTENSION_FILTER:
            ex_ex = f'<code>{", ".join(GLOBAL_EXTENSION_FILTER)}</code>'
        else:
            ex_ex = '❌ UNSET'

        has_ext = bool(user_dict.get('excluded_extensions'))
        buttons.button_data(f'{"✅" if has_ext else "🚫"} Extensions Filter',
                            f'userset {user_id} setdata excluded_extensions')

        buttons.button_data('« Back',  f'userset {user_id} back', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = ('<blockquote>┌━━━«★彡 <b>ADVANCED SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'├ 🚫 <b>Excluded Extensions :</b> {ex_ex}\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── CAPTION MODE ────────────────────────
    elif data == 'capmode':
        ex_cap = 'Thor: Love and Thunder (2022) 1080p.mkv'
        if user_dict.get('prename'):
            ex_cap = f'{user_dict.get("prename")} {ex_cap}'
        if user_dict.get('sufname'):
            fname, ext = ex_cap.rsplit('.', maxsplit=1)
            ex_cap = f'{fname} {user_dict.get("sufname")}.{ext}'

        user_cap = user_dict.get('caption_style', 'mono')
        user_capmode = user_cap.upper()
        match user_cap:
            case 'italic':
                image, ex_cap = config_dict['IMAGE_ITALIC'], f'<i>{ex_cap}</i>'
            case 'bold':
                image, ex_cap = config_dict['IMAGE_BOLD'], f'<b>{ex_cap}</b>'
            case 'normal':
                image = config_dict['IMAGE_NORMAL']
            case 'mono':
                image, ex_cap = config_dict['IMAGE_MONO'], f'<code>{ex_cap}</code>'

        cap_modes = ['mono', 'italic', 'bold', 'normal']
        cap_modes.remove(user_cap)
        caption, fnamecap = user_dict.get('captions'), user_dict.get('fnamecap', True)
        cap_icons = {'mono': '🔠', 'italic': '✍️', 'bold': '🅱️', 'normal': '🔤'}
        if not user_dict or fnamecap:
            [buttons.button_data(f'{cap_icons.get(mode, "🔤")} {mode.title()}',
                                 f'userset {user_id} cap{mode}') for mode in cap_modes]
        buttons.button_data(f'{"✅" if caption else "💬"} Custom Caption',
                            f'userset {user_id} setdata setcap')
        buttons.button_data('« Back', f'userset {user_id} back leech')
        if caption:
            buttons.button_data(f'{"✅" if fnamecap else "📝"} FName Caption',
                                f'userset {user_id} fnamecap')
            custom_cap = f'\n<code>{escape(caption)}</code>'
            fname_cup  = ('├ 📝 <b>FName Caption :</b> <b>✅ ENABLED</b>\n' if fnamecap
                         else '├ 📝 <b>FName Caption :</b> <b>❌ DISABLED</b>\n')
            if not fnamecap:
                user_capmode, image, ex_cap = 'DISABLE', config_dict['IMAGE_CAPTION'], '<b>DISABLE</b>'
        else:
            custom_cap, fname_cup = '<b>❌ Not Set</b>', ''

        text = ('<blockquote>┌━━━«★彡 <b>CAPTION SETTINGS</b> 彡★»━━━\n'
                f'├ 👤 <b>User :</b> {from_user.mention}\n'
                f'├ 💬 <b>Caption Mode :</b> <b>{user_capmode}</b>\n'
                f'{fname_cup}'
                f'├ ✏️ <b>Custom Caption :</b> {custom_cap}\n'
                '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>\n\n'
                f'🔍 <b>Example :</b> {ex_cap}')

    # ──────────────────────── RCLONE TOOL ────────────────────────
    elif data == 'rctool':
        has_rcc = await aiopath.exists(rclone_path)
        rccmsg  = '✅ EXISTS' if has_rcc else '❌ NOT SET'
        rc_path = user_dict.get('rclone_path')
        rcpath  = f'<code>{rc_path}</code>' if rc_path else '❌ <b>NOT SET</b>'
        buttons.button_data(f'{"✅" if has_rcc else "☁️"} RClone Config',
                            f'userset {user_id} setdata rclone_config')
        buttons.button_data(f'{"✅" if rc_path else "📂"} RClone Path',
                            f'userset {user_id} setdata rclone_path')
        buttons.button_data('« Back', f'userset {user_id} back mirror')

        image = config_dict['IMAGE_RCLONE']
        text  = ('<blockquote>┌━━━«★彡 <b>RCLONE SETTINGS</b> 彡★»━━━\n'
                 f'├ 👤 <b>User :</b> {from_user.mention}\n'
                 f'├ ☁️ <b>RClone Config :</b> <b>{rccmsg}</b>\n'
                 f'├ 📂 <b>RClone Path :</b> {rcpath}\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── GDRIVE TOOL ────────────────────────
    elif data == 'gdtool':
        gd_id      = user_dict.get('gdrive_id')
        gdrive_id  = f'<code>{gd_id}</code>' if gd_id else '❌ <b>DISABLED</b>'
        buttons.button_data(f'{"✅" if gd_id else "🆔"} Drive ID',
                            f'userset {user_id} setdata gdrive_id')

        index     = user_dict.get('index_url')
        index_url = f'<code>{index}</code>' if index else '❌ <b>DISABLED</b>'
        buttons.button_data(f'{"✅" if index else "🔗"} Index URL',
                            f'userset {user_id} setdata index_url')

        has_tp          = await aiopath.exists(token_pickle)
        token_pickle_msg = '✅ EXISTS' if has_tp else '❌ NOT SET'
        buttons.button_data(f'{"✅" if has_tp else "🔑"} Token Pickle',
                            f'userset {user_id} setdata token_pickle')

        stop_dup = (user_dict.get('stop_duplicate') or
                    ('stop_duplicate' not in user_dict and config_dict['STOP_DUPLICATE']))
        stop_dup_msg = '✅ ENABLED' if stop_dup else '❌ DISABLED'
        buttons.button_data(f'{"✅" if stop_dup else "🛑"} Stop Duplicate',
                            f'userset {user_id} stop_duplicate {stop_dup}', 'header')

        if await aiopath.exists('accounts'):
            use_sa_v = user_dict.get('use_sa')
            use_sa   = '✅ ENABLED' if use_sa_v else '❌ DISABLED'
            buttons.button_data(f'{"✅" if use_sa_v else "👥"} Use SA',
                                f'userset {user_id} use_sa {use_sa_v}', 'header')
        else:
            use_sa = '⚠️ NOT AVAILABLE'

        buttons.button_data('« Back', f'userset {user_id} back mirror')

        image = config_dict['IMAGE_GD']
        text  = ('<blockquote>┌━━━«★彡 <b>GDRIVE SETTINGS</b> 彡★»━━━\n'
                 f'├ 👤 <b>User :</b> {from_user.mention}\n'
                 f'├ 🆔 <b>GDrive ID :</b> {gdrive_id}\n'
                 f'├ 🔗 <b>Index URL :</b> {index_url}\n'
                 f'├ 👥 <b>Use SA :</b> <b>{use_sa}</b>\n'
                 f'├ 🔑 <b>Token Pickle :</b> <b>{token_pickle_msg}</b>\n'
                 f'├ 🛑 <b>Stop Duplicate :</b> <b>{stop_dup_msg}</b>\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>')

    # ──────────────────────── ZIP MODE ────────────────────────
    elif data == 'zipmode':
        but_dict = {'zfolder': ['Folders',    f'userset {user_id} zipmode zfolder'],
                    'zfpart':  ['Cloud Part',  f'userset {user_id} zipmode zfpart'],
                    'zeach':   ['Each Files',  f'userset {user_id} zipmode zeach'],
                    'zpart':   ['Part Mode',   f'userset {user_id} zipmode zpart'],
                    'auto':    ['Auto Mode',   f'userset {user_id} zipmode auto']}
        def_data = but_dict[uset_data][0]
        but_dict[uset_data][0] = f'🔥 {def_data}'
        [buttons.button_data(key, value) for key, value in but_dict.values()]
        buttons.button_data('« Back', f'userset {user_id} back leech')
        part_size = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])
        image = config_dict['IMAGE_ZIP']
        text  = ('<blockquote>┌━━━«★彡 <b>ZIP MODE</b> 彡★»━━━\n'
                 '├ <b>Folders/Default:</b> Zip file/folder\n'
                 f'├ <b>Cloud Part:</b> Zip as part {part_size} (Mirror)\n'
                 '├ <b>Each Files:</b> Zip each file in folder/subfolder\n'
                 f'├ <b>Part Mode:</b> Zip each file as part if size >{part_size}\n'
                 f'├ <b>Auto Mode:</b> Auto zip if size >{part_size}\n'
                 '├\n'
                 f'├ <b>Current Mode:</b> {def_data}\n'
                 '└━━━«★彡 <b>SS Bots</b> 彡★»━━━</blockquote>\n\n'
                 '<i>*Seed torrent only works in <b>Default Mode</b></i>')

    # ──────────────────────── SET DATA ────────────────────────
    elif data == 'setdata':
        if uset_data in {'thumb', 'rclone_config', 'token_pickle'}:
            file_dict = {
                'thumb':        (thumbpath,    'Thumbnail', 'Send a photo to save it as custom thumbnail.',                              '',                           ''),
                'rclone_config':(rclone_path,  'RClone',    'Send a valid *.conf file for <b>config.conf</b>.',                          config_dict['IMAGE_RCLONE'],  'rctool'),
                'token_pickle': (token_pickle, 'Token',     'Send a valid *.pickle file for <b>token.pickle</b>.',                       config_dict['IMAGE_GD'],      'gdtool'),
            }
            file_path, butkey, text, image, qdata = file_dict[uset_data]
            if await aiopath.exists(file_path):
                buttons.button_data(f'Change {butkey}', f'userset {user_id} prepare {uset_data}')
                buttons.button_data(f'Delete {butkey}', f'userset {user_id} rem_{uset_data}')
            else:
                buttons.button_data(f'Set {butkey}', f'userset {user_id} prepare {uset_data}')
        else:
            uset_dict = {
                'excluded_extensions': ('excluded_extensions', 'Extension', UsetString.EXT,                                                                                    config_dict['IMAGE_EXTENSION'], ''),
                'setcap':              ('captions',            'Caption',   UsetString.CAP,                                                                                    config_dict['IMAGE_CAPTION'],   'capmode'),
                'rctool':              ('captions',            'Caption',   UsetString.CAP,                                                                                    config_dict['IMAGE_CAPTION'],   'rctool'),
                'rclone_path':         ('rclone_path',         'RClone Path', UsetString.RCP,                                                                                  config_dict['IMAGE_RCLONE'],    'rctool'),
                'dump_ch':             ('dump_ch',             'Dump',      UsetString.DUMP,                                                                                   config_dict['IMAGE_DUMP'],      ''),
                'gdrive_id':           ('gdrive_id',           'ID',        UsetString.GDID,                                                                                   config_dict['IMAGE_GD'],        'gdtool'),
                'index_url':           ('index_url',           'Index',     UsetString.INDX,                                                                                   config_dict['IMAGE_GD'],        'gdtool'),
                'prename':             ('prename',             'Prename',   UsetString.PRE,                                                                                    config_dict['IMAGE_PRENAME'],   ''),
                'sufname':             ('sufname',             'Sufname',   UsetString.SUF,                                                                                    config_dict['IMAGE_SUFNAME'],   ''),
                'remname':             ('remname',             'Remname',   UsetString.REM.format(user_dict.get('remname') or '~'),                                            config_dict['IMAGE_REMNAME'],   ''),
                'metadata':            ('metadata',            'Metadata',  UsetString.META.format(user_dict.get('metadata') or '~'),                                          config_dict['IMAGE_METADATA'],  ''),
                'session_string':      ('session_string',      'Session',   UsetString.SES,                                                                                    config_dict['IMAGE_USER'],      ''),
                'yt_opt':              ('yt_opt',              'YT-DLP',    UsetString.YT,                                                                                     config_dict['IMAGE_YT'],        ''),
                # ── Video Tools ──
                'vid_banner':          ('vid_banner',          'Banner',    'Send compress banner text.\nExample: <code>Re-Encoded by @MyChannel</code>\n┖ <b>Time Left:</b> <code>60 sec</code>',    config_dict['IMAGE_VIDTOOLS'], 'vid_compress'),
                'vid_hardsub_font':    ('vid_hardsub_font',    'Font',      'Send HardSub font name.\nExample: <code>Arial</code>\n┖ <b>Time Left:</b> <code>60 sec</code>',                          config_dict['IMAGE_VIDTOOLS'], 'vid_hardsub'),
                'vid_hardsub_size':    ('vid_hardsub_size',    'Font Size', 'Send HardSub font size as number.\nExample: <code>24</code>\n┖ <b>Time Left:</b> <code>60 sec</code>',                   config_dict['IMAGE_VIDTOOLS'], 'vid_hardsub'),
            }
            if uset_data == 'dump_ch':
                log_title = user_dict.get('log_title')
                buttons.button_data('🔥 Log Title' if log_title else 'Log Title',
                                    f'userset {user_id} setdata dump_ch {not log_title}')
            elif uset_data == 'metadata':
                clean_meta = user_dict.get('clean_metadata')
                buttons.button_data('🔥 Clean' if clean_meta else '🔥 Overwrite',
                                    f'userset {user_id} setdata metadata {not clean_meta}')

            key, butkey, text, image, qdata = uset_dict[uset_data]
            if user_dict.get(key) or key == 'yt_opt' and config_dict['YT_DLP_OPTIONS']:
                buttons.button_data(f'Change {butkey}', f'userset {user_id} prepare {key}')
                buttons.button_data(f'Remove {butkey}', f'userset {user_id} rem_{key}')
            else:
                buttons.button_data(f'Set {butkey}', f'userset {user_id} prepare {key}')
        if qdata:
            buttons.button_data('« Back', f'userset {user_id} {qdata}')
        text = text.replace('Timeout: 60s.', '')
        _setdata_back = {
            'thumb':               'leech',
            'dump_ch':             'leech',
            'prename':             'leech',
            'sufname':             'leech',
            'remname':             'leech',
            'excluded_extensions': 'advanced',
            'session_string':      'general',
            'yt_opt':              'general',
            'metadata':            'ffset',
        }
        _no_back = ['setcap', 'index_url', 'token_pickle', 'gdrive_id',
                    'rclone_path', 'rclone_config', 'vid_banner',
                    'vid_hardsub_font', 'vid_hardsub_size']
        if uset_data not in _no_back:
            _back_dest = _setdata_back.get(uset_data, '')
            _back_cb = f'userset {user_id} back {_back_dest}' if _back_dest else f'userset {user_id} back'
            if not qdata:
                buttons.button_data('« Back', _back_cb)

    # ──────────────────────── PREPARE INPUT ────────────────────────
    elif data == 'prepare':
        msg_thumb  = ('Send a photo to change current thumbnail.\n\n<i>Timeout: 60s.</i>'
                      if await aiopath.exists(thumbpath) else
                      'Send a photo to save it as custom thumbnail.\n\n<i>Timeout: 60s.</i>')
        msg_rclone = ('Send new valid *.conf file to change current <b>config.conf</b>.\n\n<i>Timeout: 60s.</i>'
                      if await aiopath.exists(rclone_path) else
                      'Send a valid *.conf file for <b>config.conf</b>.\n\n<i>Timeout: 60s.</i>')
        msg_token  = ('Send new valid *.pickle file to change current <b>token.pickle</b>.\n\n<i>Timeout: 60s.</i>'
                      if await aiopath.exists(token_pickle) else
                      'Send a valid *.pickle file for <b>token.pickle</b>.\n\n<i>Timeout: 60s.</i>')
        prepare_dict = {
            'thumb':              (msg_thumb,  image),
            'rclone_config':      (msg_rclone, config_dict['IMAGE_RCLONE']),
            'token_pickle':       (msg_token,  config_dict['IMAGE_GD']),
            'dump_ch':            (UsetString.DUMP,                                                       config_dict['IMAGE_DUMP']),
            'rclone_path':        (UsetString.RCP,                                                        config_dict['IMAGE_RCLONE']),
            'gdrive_id':          (UsetString.GDID,                                                       config_dict['IMAGE_GD']),
            'index_url':          (UsetString.INDX,                                                       config_dict['IMAGE_GD']),
            'excluded_extensions':(UsetString.EXT,                                                        config_dict['IMAGE_EXTENSION']),
            'captions':           (UsetString.CAP,                                                        config_dict['IMAGE_CAPTION']),
            'prename':            (UsetString.PRE,                                                        config_dict['IMAGE_PRENAME']),
            'sufname':            (UsetString.SUF,                                                        config_dict['IMAGE_SUFNAME']),
            'remname':            (UsetString.REM.format(user_dict.get('remname') or '~'),                config_dict['IMAGE_REMNAME']),
            'metadata':           (UsetString.META.format(user_dict.get('metadata') or '~'),              config_dict['IMAGE_METADATA']),
            'session_string':     (UsetString.SES,                                                        config_dict['IMAGE_USER']),
            'yt_opt':             (UsetString.YT,                                                         config_dict['IMAGE_YT']),
            'vid_banner':         ('Send compress banner text.\nExample: <code>Re-Encoded by @MyChannel</code>',  config_dict['IMAGE_VIDTOOLS']),
            'vid_hardsub_font':   ('Send HardSub font name.\nExample: <code>Arial</code>',                        config_dict['IMAGE_VIDTOOLS']),
            'vid_hardsub_size':   ('Send HardSub font size as number.\nExample: <code>24</code>',                 config_dict['IMAGE_VIDTOOLS']),
        }
        text, image = prepare_dict[uset_data]
        buttons.button_data('« Back', f'userset {user_id} setdata {uset_data}')

    buttons.button_data('✘ Close', f'userset {user_id} close')
    return text, image, buttons.build_menu(2)


async def update_user_settings(query: CallbackQuery, data: str = None, uset_data: str = None):
    text, image, button = await get_user_settings(query.from_user, data, uset_data)
    if not image:
        if await aiopath.exists(thumb := ospath.join('thumbnails', f'{query.from_user.id}.jpg')):
            image = thumb
        else:
            image = config_dict['IMAGE_USETIINGS']
    await editPhoto(text, query.message, image, button)


async def set_user_settings(_, message: Message, query: CallbackQuery, key: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value: str = message.text
    if (key == 'dump_ch' and value.isdigit() or value.startswith('-100')):
        value = int(value)
    elif key == 'excluded_extensions':
        fx = value.split()
        value = ['aria2', '!qB']
        for x in fx:
            x = x.lstrip('.')
            value.append(x.strip().lower())
    elif key == 'vid_hardsub_size' and value.isdigit():
        value = int(value)
    await gather(update_user_ldata(user_id, key, value), deleteMessage(message))
    match key:
        case 'index_url' | 'token_pickle' | 'gdrive_id':
            back_data = 'gdtool'
        case 'captions':
            back_data = 'capmode'
        case 'rclone_path':
            back_data = 'rctool'
        case 'vid_banner':
            back_data = 'vid_compress'
        case 'vid_hardsub_font' | 'vid_hardsub_size':
            back_data = 'vid_hardsub'
        case _:
            back_data = None
    if key == 'dump_ch':
        await update_user_settings(query, 'setdata', 'dump_ch')
    elif key == 'session_string':
        await intialize_savebot(value, True, user_id)
        async with bot_lock:
            save_bot = bot_dict[user_id]['SAVEBOT']
        if not save_bot:
            msg = await sendMessage('Something went wrong, or invalid string!', message)
            await update_user_ldata(user_id, key, '')
            bot_loop.create_task(auto_delete_message(message, msg, stime=5))
        await update_user_settings(query, back_data)
    else:
        await update_user_settings(query, back_data)


async def set_thumb(_, message: Message, query: CallbackQuery):
    user_id = query.from_user.id
    handler_dict[user_id] = False
    msg = await sendMessage('<i>Processing, please wait...</i>', message)
    des_dir = await createThumb(message, user_id)
    await gather(update_user_ldata(user_id, 'thumb', des_dir), deleteMessage(message, msg),
                 update_user_settings(query))
    if DATABASE_URL:
        await DbManager().update_user_doc(user_id, 'thumb', des_dir)


async def add_rclone_pickle(_, message: Message, query: CallbackQuery, key: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    file_path, ext_file = ('rclone', '.conf') if key == 'rclone_config' else ('tokens', '.pickle')
    fpath = ospath.join(getcwd(), file_path)
    await makedirs(fpath, exist_ok=True)
    if message.document.file_name.endswith(ext_file):
        des_dir = ospath.join(fpath, f'{user_id}{ext_file}')
        msg = await sendMessage('<i>Processing, please wait...</i>', message)
        await message.download(file_name=des_dir)
        qdata = 'rctool' if key == 'rclone_config' else 'gdtool'
        await gather(update_user_ldata(user_id, file_path, ospath.join(file_path, f'{user_id}{ext_file}')),
                     deleteMessage(message, msg),
                     update_user_settings(query, qdata))
        if DATABASE_URL:
            await DbManager().update_user_doc(user_id, key, des_dir)
    else:
        msg = await sendMessage(f'Invalid *{ext_file} file!', message)
        await gather(update_user_settings(query, 'setdata', key),
                     auto_delete_message(message, msg, stime=5))


@new_thread
async def edit_user_settings(client: Client, query: CallbackQuery):
    message  = query.message
    user_id  = query.from_user.id
    data     = query.data.split()
    user_dict = user_data.get(user_id, {})
    premi_features = ['caption', 'dump_ch', 'gdrive_id', 'media_group', 'prename', 'sufname',
                      'remname', 'metadata', 'session_string', 'enable_pm', 'enable_ss']
    pre_data = data[3] if data[2] == 'setdata' else data[2]
    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and pre_data in premi_features:
        await query.answer('Upss, Premium User Required!', True)
        is_modified = False
        for key in premi_features:
            if user_dict.get(key):
                is_modified = True
                await update_user_ldata(user_id, key, False)
        if is_modified:
            await update_user_settings(query)
        return
    if user_id != int(data[1]):
        await query.answer('Not Yours!', True)
        return

    match data[2]:
        # ── Category navigation ──
        case 'general' | 'leech' | 'mirror' | 'ffset' | 'vidtools' | \
             'vid_compress' | 'vid_hardsub' | 'advanced' | \
             'capmode' | 'gdtool' | 'rctool' as value:
            await gather(query.answer(), update_user_settings(query, value))

        case 'setdata':
            handler_dict[user_id] = False
            await query.answer()
            if data[3] in ('dump_ch', 'metadata') and len(data) == 5:
                key = 'log_title' if data[3] == 'dump_ch' else 'clean_metadata'
                await update_user_ldata(user_id, key, literal_eval(data[4]))
            await update_user_settings(query, 'setdata', data[3])

        case 'gd' | 'rc' as value:
            du = 'rc' if value == 'gd' else 'gd'
            await gather(query.answer(), update_user_ldata(user_id, 'default_upload', du))
            await update_user_settings(query, 'general')

        case 'back':
            handler_dict[user_id] = False
            stype = data[3] if len(data) >= 4 else None
            await gather(query.answer(), update_user_settings(query, stype))

        # ── Video preset selections ──
        case 'set_vid264':
            await query.answer(f'x264 preset set to {data[3]}!', True)
            await update_user_ldata(user_id, 'vid_264_preset', data[3])
            await update_user_settings(query, 'vid_compress')

        case 'set_vid265':
            await query.answer(f'x265 preset set to {data[3]}!', True)
            await update_user_ldata(user_id, 'vid_265_preset', data[3])
            await update_user_settings(query, 'vid_compress')

        # ── Remove video tool settings ──
        case 'rem_vid_banner':
            await update_user_ldata(user_id, 'vid_banner', '')
            await gather(query.answer('Banner reset!', True),
                         update_user_settings(query, 'vid_compress'))

        case 'rem_vid_hardsub_font':
            await update_user_ldata(user_id, 'vid_hardsub_font', '')
            await gather(query.answer('Font reset!', True),
                         update_user_settings(query, 'vid_hardsub'))

        case 'rem_vid_hardsub_size':
            await update_user_ldata(user_id, 'vid_hardsub_size', '')
            await gather(query.answer('Font size reset!', True),
                         update_user_settings(query, 'vid_hardsub'))

        # ── Remove settings ──
        case ('rem_prename' | 'rem_sufname' | 'rem_dump_ch' | 'rem_remname' |
              'rem_metadata' | 'rem_session_string' | 'rem_yt_opt' | 'rem_index_url' |
              'rem_gdrive_id' | 'rem_captions' | 'rem_excluded_extensions' |
              'rem_rclone_path') as value:
            qdata = uset_data = ''
            match value:
                case 'rem_dump_ch':
                    await update_user_ldata(user_id, 'log_title', False)
                case 'rem_session_string':
                    if savebot := bot_dict[user_id]['SAVEBOT']:
                        await savebot.stop()
                case 'rem_captions':
                    qdata = 'capmode'
                    await update_user_ldata(user_id, 'fnamecap', True)
                case 'rem_rclone_path':
                    qdata = 'rctool'
                case 'rem_index_url' | 'rem_gdrive_id':
                    qdata = 'gdtool'
            if value in ('rem_rclone_path', 'rem_gdrive_id') and value in user_data.get(user_id, {}):
                del user_data[user_id][value]
                if DATABASE_URL:
                    await DbManager().update_user_data(user_id)
            else:
                await update_user_ldata(user_id, value[4:], '')
            await gather(query.answer(), update_user_settings(query, qdata, uset_data))

        # ── Toggle buttons ──
        case ('enable_pm' | 'enable_ss' | 'as_doc' | 'media_group' |
              'fnamecap' | 'stop_duplicate' | 'use_sa') as value:
            qdata = uset_data = ''
            await update_user_ldata(user_id, value, not user_dict.get(value, False))
            if value == 'fnamecap':
                qdata = 'capmode'
            elif value in ('stop_duplicate', 'use_sa'):
                qdata = 'gdtool'
            elif value in ('enable_pm', 'enable_ss', 'as_doc', 'media_group'):
                qdata = 'general'
            await gather(query.answer(), update_user_settings(query, qdata, uset_data))

        # ── Zip mode ──
        case 'zipmode':
            try:
                zmode = data[3]
            except:
                zmode = user_dict.get('zipmode', 'zfolder')
            if zmode == user_dict.get('zipmode', '') and len(data) == 4:
                await query.answer('Already Selected!', True)
                return
            await gather(query.answer(), update_user_ldata(user_id, 'zipmode', zmode))
            await update_user_settings(query, 'zipmode', zmode)

        # ── Caption style ──
        case 'capmono' | 'capitalic' | 'capbold' | 'capnormal' as value:
            await update_user_ldata(user_id, 'caption_style', value.lstrip('cap'))
            await gather(query.answer(), update_user_settings(query, 'capmode'))

        # ── Reset All ──
        case 'reset_all_confirm':
            await query.answer()
            buttons = ButtonMaker()
            buttons.button_data('✅ Yes, Reset', f'userset {user_id} do_reset_all yes')
            buttons.button_data('❌ Cancel',     f'userset {user_id} do_reset_all no')
            buttons.button_data('✘ Close',       f'userset {user_id} close', 'footer')
            await editMessage('<blockquote><b>⚠️ Reset All Settings?</b>\n\n'
                              '<i>This will remove ALL your custom settings, files, and preferences.</i></blockquote>',
                              message, buttons.build_menu(2))

        case 'do_reset_all':
            if data[3] == 'yes':
                await query.answer('Reset Done!', True)
                user_dict = user_data.get(user_id, {})
                for k in list(user_dict.keys()):
                    if k not in ('SUDO', 'AUTH', 'VERIFY_TOKEN', 'VERIFY_TIME'):
                        del user_dict[k]
                for fpath in [ospath.join('thumbnails', f'{user_id}.jpg'),
                               ospath.join('rclone', f'{user_id}.conf'),
                               ospath.join('tokens', f'{user_id}.pickle')]:
                    if await aiopath.exists(fpath):
                        await clean_target(fpath)
                if DATABASE_URL:
                    await DbManager().update_user_data(user_id)
                await update_user_settings(query)
            else:
                await query.answer('Cancelled.', True)
                await update_user_settings(query)

        # ── Close ──
        case 'close':
            handler_dict[user_id] = False
            await gather(query.answer(), deleteMessage(message, message.reply_to_message))

        # ── Remove file settings ──
        case 'rem_thumb' | 'rem_rclone_config' | 'rem_token_pickle' as value:
            match value:
                case 'rem_thumb':
                    path = ospath.join('thumbnails', f'{user_id}.jpg')
                case 'rem_rclone_config':
                    path = ospath.join('rclone', f'{user_id}.conf')
                case _:
                    path = ospath.join('tokens', f'{user_id}.pickle')
            key = value.lstrip('rem_')
            await update_user_ldata(user_id, key, '')
            if await aiopath.exists(path):
                await gather(query.answer(), clean_target(path))
                await update_user_settings(query)
                if DATABASE_URL:
                    await DbManager().update_user_doc(user_id, key)
            else:
                await gather(query.answer('Old Settings', True), update_user_settings(query))

        # ── Prepare input ──
        case 'prepare':
            match data[3]:
                case 'rclone_config' | 'token_pickle':
                    await query.answer()
                    photo, document = False, True
                    pfunc = partial(add_rclone_pickle, query=query, key=data[3])
                case 'thumb':
                    await query.answer()
                    photo, document = True, False
                    pfunc = partial(set_thumb, query=query)
                case _:
                    handler_dict[user_id] = True
                    await query.answer('Don\'t forget add me to your chat!', True) if data[3] == 'dump_ch' else await query.answer()
                    photo = document = False
                    pfunc = partial(set_user_settings, query=query, key=data[3])
            await gather(update_user_settings(query, data[2], data[3]),
                         event_handler(client, query, pfunc, photo, document))


async def event_handler(client: Client, query: CallbackQuery, pfunc: partial,
                        photo: bool = False, document: bool = False):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(user.id == user_id and event.chat.id == query.message.chat.id and mtype)

    handler = client.add_handler(MessageHandler(pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await update_user_settings(query)
    client.remove_handler(*handler)


@new_task
async def user_settings(_, message: Message):
    from_user = message.from_user
    handler_dict[from_user.id] = False
    if fmsg := await UseCheck(message).run():
        await auto_delete_message(message, fmsg)
        return
    msg, image, buttons = await get_user_settings(from_user, None, None)
    if await aiopath.exists(thumb := ospath.join('thumbnails', f'{message.from_user.id}.jpg')):
        image = thumb
    await sendPhoto(msg, message, image or config_dict['IMAGE_USETIINGS'], buttons)


@new_task
async def set_premium_users(_, message: Message):
    if not config_dict['PREMIUM_MODE']:
        await sendMessage('<b>Premium Mode</b> is disable!', message)
        return
    reply_to = message.reply_to_message
    args = message.text.split()
    text = 'Reply to a user or send user ID with options (add/del) and duration time in day(s)'
    if not reply_to and len(args) == 1:
        await sendMessage(text, message)
        return
    if reply_to and len(args) > 1:
        premi_id = reply_to.from_user.id
        if args[1] == 'add':
            day = int(args[2])
    elif len(args) > 2:
        premi_id = int(args[2])
        if args[1] == 'add':
            day = int(args[3])
    elif len(args) == 2 and args[1] == 'list':
        text = 'Premium List:\n'
        i = 1
        for id_, value in user_data.items():
            if value.get('is_premium') and (time_left := value['premium_left']) - time() > 1:
                text += f'{i}. @{value.get("user_name")} (<code>{id_}</code>) ~ {get_readable_time(time_left - time())}\n'
                i += 1
    else:
        await sendMessage(text, message)
        return

    user_text = ''
    if args[1] == 'add':
        duartion = int(time() + (86400 * day))
        text = f'🌚 Yeay, <b>{premi_id}</b> has been added as <b>Premium User</b> for {day} day(s).'
        user_text = f'Yeay 🌚, you have been added as <b>Premium User</b> for {day}(s).'
        await gather(update_user_ldata(premi_id, 'premium_left', duartion),
                     update_user_ldata(premi_id, 'is_premium', True))
    elif args[1] == 'del':
        text = f'🤡 Hmm, <b>{premi_id}</b> has been remove as <b>Premium User</b>!'
        user_text = 'Huhu 🤡, you have been deleted as <b>Premium User</b>!'
        await gather(update_user_ldata(premi_id, 'premium_left', 0),
                     update_user_ldata(premi_id, 'is_premium', False))
    msg = await sendMessage(text, message)
    if user_text:
        await sendCustom(user_text, premi_id)
    await auto_delete_message(message, msg)


@new_task
async def reset_daily_limit(_, message: Message):
    reply_to = message.reply_to_message
    args = message.text.split()
    if not reply_to and len(args) == 1:
        await sendMessage('Reply to a user or send user ID to reset daily limit.', message)
        return
    if reply_to:
        user_id = reply_to.from_user.id
    elif len(args) > 1:
        user_id = int(args[1])
    await gather(update_user_ldata(user_id, 'daily_limit', 1),
                 update_user_ldata(user_id, 'reset_limit', time() + 86400))
    msg = await sendMessage('Daily limit has been reset.', message)
    await auto_delete_message(message, msg)


@new_task
async def send_users_settings(client: Client, message: Message):
    contents = []
    msg = ''
    if len(user_data) == 0:
        await sendMessage('No user data!', message)
        return
    for index, (uid, data) in enumerate(user_data.items(), start=1):
        if data.get('is_sudo') and 'sudo_left' in data and data['sudo_left'] - time() <= 0:
            del user_data[uid]['sudo_left']
            await update_user_ldata(uid, 'is_sudo', False)
        uname = user_data[uid].get('user_name')
        msg += f'<b><a href="https://t.me/{uname}">{uname}</a></b>\n'
        msg += f'⁍ <b>User ID:</b> <code>{uid}</code>\n'
        for key, value in data.items():
            if key in ('session_token', 'session_time') or value == '':
                continue
            if key == 'reset_limit':
                value -= time()
                value = get_readable_time(0 if value <= 1 else value)
            elif key == 'daily_limit':
                value = f'{get_readable_file_size(value)}/{config_dict["DAILY_LIMIT_SIZE"]}GB'
            elif key in ('premium_left', 'sudo_left'):
                value = f'{get_readable_time(value - time())}'
            elif key in ('caption_style', 'zipmode'):
                value = str(value).title()
            elif key in ['thumb', 'rclone_config', 'token_pickle']:
                value = 'Exists' if value else 'Not Exists'
            elif key in ['dump_ch', 'yt_opt', 'index_url', 'gdrive_id', 'prename', 'sufname', 'metadata']:
                value = f'<code>{value}</code>'
            elif str(value).lower() == 'true' or (key in ['session_string', 'remname', 'captions'] and value):
                value = 'Yes'
            elif str(value).lower() == 'false':
                value = 'No'
            if key != 'user_name' and value != '':
                msg += f'⁍ <b>{key.replace("_", " ").title()}:</b> {value}\n'
        contents.append(f'{str(index).zfill(3)}. {msg}\n')
        msg = ''
    tele = TeleContent(message, max_page=5, direct=False)
    tele.set_data(contents, f'<b>FOUND {len(contents)} USERS SETTINGS DATA</b>')
    text, buttons = await tele.get_content('usettings')
    msg = await sendMessage(text, message, buttons)
    event = Event()

    @new_thread
    async def __event_handler():
        pfunc = partial(users_handler, event=event, tele=tele)
        handler = client.add_handler(
            CallbackQueryHandler(pfunc, filters=regex('^usettings') & user(message.from_user.id)),
            group=-1)
        try:
            await wait_for(event.wait(), timeout=180)
        except:
            pass
        finally:
            client.remove_handler(*handler)

    await wrap_future(__event_handler())
    await deleteMessage(msg, message)


async def users_handler(_, query: CallbackQuery, event=Event, tele=TeleContent):
    message = query.message
    data = query.data.split()
    if data[2] == 'close':
        event.set()
        if tele:
            tele.cancel()
        await deleteMessage(message, message.reply_to_message)
    else:
        tdata = int(data[4]) if data[2] == 'foot' else int(data[3])
        text, buttons = await tele.get_content('usettings', data[2], tdata)
        if data[2] == 'page':
            await query.answer(f'Total Page ~ {tele.pages}', True)
            return
        if not buttons:
            await query.answer(text, True)
            return
        await gather(query.answer(), editMessage(text, message, buttons))


bot.add_handler(MessageHandler(set_premium_users,  filters=command(BotCommands.UserSetPremiCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(send_users_settings, filters=command(BotCommands.UsersCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(reset_daily_limit,  filters=command(BotCommands.DailyResetCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(user_settings,      filters=command(BotCommands.UserSetCommand)))
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=regex('^userset')))
