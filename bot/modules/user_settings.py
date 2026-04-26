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

from bot import bot, bot_loop, bot_dict, bot_lock, user_data, config_dict, DATABASE_URL, GLOBAL_EXTENSION_FILTER, VID_MODE
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

_COMPRESS_PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium']

_VID_ICONS = {
    'vid_vid':   '🎞️',
    'vid_aud':   '🎵',
    'vid_sub':   '📝',
    'subsync':   '🔄',
    'compress':  '🗜️',
    'convert':   '🔁',
    'watermark': '💧',
    'extract':   '📤',
    'trim':      '✂️',
    'rmstream':  '🗑️',
}

_VID_DESCRIPTIONS = {
    'vid_vid':   'Merge two or more video files together into a single output video.',
    'vid_aud':   'Mux external audio tracks (mp3 / aac / ac3) into your video file.',
    'vid_sub':   'Hardcode (burn-in) subtitle files into your video stream permanently.',
    'subsync':   'Synchronize external subtitles to match the video timing automatically.',
    'compress':  'Compress / re-encode videos using x264 or x265 with custom presets and banner.',
    'convert':   'Convert videos between formats and containers (mp4, mkv, webm, etc.).',
    'watermark': 'Apply image or text watermark on videos with adjustable position and opacity.',
    'extract':   'Extract specific streams (video / audio / subtitle) from the source file.',
    'trim':      'Trim and cut video by specified start and end timestamps without re-encoding.',
    'rmstream':  'Remove unwanted audio or subtitle streams from the video file.',
}

# Cyclable single-choice fields: tap to advance to the next option
_VID_FIELD_OPTIONS = {
    'vid_merge_mode':     ['sequential', 'concat'],
    'vid_audio_codec':    ['aac', 'mp3', 'ac3', 'opus'],
    'vid_convert_format': ['mp4', 'mkv', 'webm', 'mov'],
    'vid_watermark_pos':  ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'],
}

# Multi-select fields: each item toggles independently
_VID_MULTI_OPTIONS = {
    'vid_extract_streams': ['video', 'audio', 'subtitle'],
    'vid_rmstream_kind':   ['audio', 'subtitle'],
}

_VID_DEFAULTS = {
    'vid_merge_mode':       'sequential',
    'vid_audio_lang':       '',
    'vid_audio_codec':      'aac',
    'vid_subsync_delay':    '0',
    'vid_convert_format':   'mp4',
    'vid_watermark_text':   '',
    'vid_watermark_pos':    'bottom-right',
    'vid_watermark_opacity':'50',
    'vid_extract_streams':  ['audio', 'subtitle'],
    'vid_trim_start':       '00:00:00',
    'vid_trim_end':         '00:00:00',
    'vid_rmstream_kind':    [],
}


def _oo(on=True):
    return '✅' if on else '❌'


def _daily_str(user_id, user_dict):
    if config_dict.get('DAILY_MODE') and not is_premium_user(user_id):
        used = get_readable_file_size(user_dict.get('daily_limit', 0))
        limit = config_dict.get('DAILY_LIMIT_SIZE', '∞')
        return f'{used} / {limit}GB per day'
    return '∞ / ∞ per day'


async def get_user_settings(from_user, data: str, uset_data: str):
    buttons = ButtonMaker()
    user_id = from_user.id
    thumbpath    = ospath.join('thumbnails', f'{user_id}.jpg')
    rclone_path  = ospath.join('rclone', f'{user_id}.conf')
    token_pickle = ospath.join('tokens', f'{user_id}.pickle')
    user_dict = user_data.get(user_id, {})
    image = None

    # ═══════════════════════ MAIN MENU ═══════════════════════
    if not data:
        has_thumb = await aiopath.exists(thumbpath)
        has_rcc   = await aiopath.exists(rclone_path)
        has_gdx   = await aiopath.exists(token_pickle)
        AD        = config_dict['AS_DOCUMENT']
        is_doc    = (not user_dict and AD) or user_dict.get('as_doc')
        ltype     = 'Document' if is_doc else 'Media'
        default_upload = user_dict.get('default_upload', '') or config_dict['DEFAULT_UPLOAD']
        du = 'GDrive API' if default_upload == 'gd' else 'RClone'

        premium_status = daily_left = ''
        if config_dict['PREMIUM_MODE']:
            if (user_premi := is_premium_user(user_id)) and (time_data := user_dict.get('premium_left')):
                if time_data - time() <= 0:
                    await gather(update_user_ldata(user_id, 'is_premium', False),
                                 update_user_ldata(user_id, 'premium_left', 0))
                else:
                    premium_status = f'├ ⏳ <b>Premium Left :</b> <i>{get_readable_time(time_data - time())}</i>\n'
            if user_id != config_dict['OWNER_ID']:
                badge = '💎 PREMIUM' if is_premium_user(user_id) else '👤 NORMAL'
                premium_status = f'├ 🏷️ <b>Status :</b> <b>{badge}</b>\n' + premium_status
        if config_dict['DAILY_MODE'] and not is_premium_user(user_id):
            await UserDaily(user_id).get_daily_limit()
            daily_left = (f'├ 📊 <b>Daily Used :</b> <i>{get_readable_file_size(user_data[user_id]["daily_limit"])} / {config_dict["DAILY_LIMIT_SIZE"]}GB</i>\n'
                          f'├ ⏰ <b>Reset In :</b> <i>{get_readable_time(user_data[user_id]["reset_limit"] - time())}</i>\n')

        buttons.button_data('Universal Settings', f'userset {user_id} general')
        buttons.button_data('Mirror Settings',    f'userset {user_id} mirror')
        buttons.button_data('Leech Settings',     f'userset {user_id} leech')
        buttons.button_data('Video Tools',        f'userset {user_id} vidtools')
        buttons.button_data('Reset Setting', f'userset {user_id} reset_all_confirm', 'footer')
        buttons.button_data('Close',         f'userset {user_id} close',             'footer')

        text = (f'<blockquote>⊟ <b>User Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'{premium_status}'
                f'{daily_left}'
                f'├ 🆔 <b>ID :</b> <code>{user_id}</code>\n'
                f'├ 🌐 <b>Telegram DC :</b> <i>{getattr(from_user, "dc_id", "—")}</i>\n'
                f'├ 🎞️ <b>Leech Type :</b> <i>{ltype}</i>\n'
                f'├ 🖼️ <b>Thumbnail :</b> <i>{"Exists" if has_thumb else "Not Exists"}</i>\n'
                f'├ ☁️ <b>RClone Config :</b> <i>{"Exists" if has_rcc else "Not Exists"}</i>\n'
                f'├ 🔑 <b>GDrive Token :</b> <i>{"Exists" if has_gdx else "Not Exists"}</i>\n'
                f'├ ⚙️ <b>Upload Engine :</b> <i>{du}</i>\n'
                f'└ 📂 <b>Select a category below</b></blockquote>')

    # ═══════════════════════ UNIVERSAL SETTINGS ═══════════════════════
    elif data == 'general':
        sendpm  = user_dict.get('enable_pm', False)
        sendss  = user_dict.get('enable_ss', False)
        has_ses = bool(user_dict.get('session_string'))
        mi_on   = user_dict.get('mediainfo', False)
        save_md = user_dict.get('save_mode', 'botpm')
        default_upload = user_dict.get('default_upload', '') or config_dict['DEFAULT_UPLOAD']
        du_label = 'GDRIVE' if default_upload != 'gd' else 'RCLONE'

        YOPT = config_dict['YT_DLP_OPTIONS']
        if user_dict.get('yt_opt'):
            yto_val = f'<code>{escape(user_dict["yt_opt"])}</code>'
        elif 'yt_opt' not in user_dict and YOPT:
            yto_val = f'<code>{escape(YOPT)}</code>'
        else:
            yto_val = 'Not Exists'

        if ext_filters := user_dict.get('excluded_extensions'):
            ex_ex = ', '.join(ext_filters)
        elif 'excluded_extensions' not in user_dict and GLOBAL_EXTENSION_FILTER:
            ex_ex = ', '.join(GLOBAL_EXTENSION_FILTER)
        else:
            ex_ex = 'Not Exists'
        has_ext = bool(user_dict.get('excluded_extensions'))

        buttons.button_data('YT-Dlp Options',                          f'userset {user_id} setdata yt_opt')
        buttons.button_data(f'{"✅ " if has_ses else ""}User Session', f'userset {user_id} setdata session_string')
        buttons.button_data(f'{"Disable" if sendpm else "Enable"} Bot PM',     f'userset {user_id} enable_pm')
        buttons.button_data(f'{"Disable" if mi_on else "Enable"} MediaInfo',   f'userset {user_id} mediainfo')
        buttons.button_data(f'Save As {"BotPm" if save_md == "dump" else "Dump"}', f'userset {user_id} save_mode')
        buttons.button_data(f'{"Disable" if sendss else "Enable"} Screenshot',     f'userset {user_id} enable_ss')
        buttons.button_data(f'{"✅ " if has_ext else ""}Extensions Filter',   f'userset {user_id} setdata excluded_extensions')
        buttons.button_data(f'Engine : {du_label}',           f'userset {user_id} {default_upload}', 'header')
        buttons.button_data('« Back',  f'userset {user_id} back',  'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        pm_val  = 'Force Enabled'  if sendpm  else 'Force Disabled'
        ss_val  = 'Enabled'        if sendss  else 'Disabled'
        mi_val  = 'Enabled'        if mi_on   else 'Disabled'
        sm_val  = 'Save As Dump'   if save_md == 'dump' else 'Save As BotPm'
        ses_val = 'Active'         if has_ses else 'Not Exists'
        du_full = 'GDrive API'     if default_upload == 'gd' else 'RClone'

        text = (f'<blockquote>⊟ <b>Universal Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'├ <b>YT-DLP Options :</b> <i>{yto_val}</i>\n'
                f'├ <b>User Session :</b> <i>{ses_val}</i>\n'
                f'├ <b>MediaInfo Mode :</b> <i>{mi_val}</i>\n'
                f'├ <b>Save Mode :</b> <i>{sm_val}</i>\n'
                f'├ <b>User Bot PM :</b> <i>{pm_val}</i>\n'
                f'├ <b>Screenshot Mode :</b> <i>{ss_val}</i>\n'
                f'├ <b>Excluded Extensions :</b> <i>{ex_ex}</i>\n'
                f'└ <b>Upload Engine :</b> <i>{du_full}</i></blockquote>')

    # ═══════════════════════ LEECH SETTINGS ═══════════════════════
    elif data == 'leech':
        has_thumb  = await aiopath.exists(thumbpath)
        AD         = config_dict['AS_DOCUMENT']
        is_doc     = (not user_dict and AD) or user_dict.get('as_doc')
        MG         = config_dict['MEDIA_GROUP']
        is_mg      = user_dict.get('media_group') or ('media_group' not in user_dict and MG)
        EQ         = config_dict.get('EQUAL_SPLITS', False)
        equal_sp   = user_dict.get('equal_splits', EQ)
        split_size = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])
        prename    = user_dict.get('prename')
        sufname    = user_dict.get('sufname')
        remname    = user_dict.get('remname')
        dch        = user_dict.get('dump_ch')
        metadata   = user_dict.get('metadata')
        has_cap    = bool(user_dict.get('captions'))
        capmode    = user_dict.get('caption_style', 'mono')
        cap_val    = f'<code>{escape(user_dict["captions"])}</code>' if has_cap else f'<i>{capmode}</i>'

        daily_leech = _daily_str(user_id, user_dict)
        if config_dict['DAILY_MODE'] and not is_premium_user(user_id):
            await UserDaily(user_id).get_daily_limit()
            daily_leech = f'{get_readable_file_size(user_data[user_id]["daily_limit"])} / {config_dict["DAILY_LIMIT_SIZE"]}GB per day'

        buttons.button_data(f'{"✅ " if is_doc else ""}Send As Document', f'userset {user_id} as_doc')
        buttons.button_data(f'{"✅ " if has_thumb else ""}Thumbnail',     f'userset {user_id} setdata thumb')
        buttons.button_data('Leech Splits',                                f'userset {user_id} setdata split_size_info')
        buttons.button_data(f'{"✅ " if has_cap else ""}Leech Caption',   f'userset {user_id} capmode')
        buttons.button_data(f'{"✅ " if prename else ""}Leech Prefix',    f'userset {user_id} setdata prename')
        buttons.button_data(f'{"✅ " if sufname else ""}Leech Suffix',    f'userset {user_id} setdata sufname')
        buttons.button_data(f'{"✅ " if remname else ""}Leech Remname',   f'userset {user_id} setdata remname')
        buttons.button_data(f'{"✅ " if dch else ""}Leech Dump',          f'userset {user_id} setdata dump_ch')
        buttons.button_data(f'{"✅ " if metadata else ""}Metadata',       f'userset {user_id} setdata metadata')
        buttons.button_data(f'{"✅ " if is_mg else ""}Media Group',       f'userset {user_id} media_group')
        buttons.button_data('🗜️ Zip Mode',                                f'userset {user_id} zipmode')
        buttons.button_data('« Back',  f'userset {user_id} back',  'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        _zmap = {'zfolder': 'Folders', 'zfpart': 'Cloud Part', 'zeach': 'Each Files',
                 'zpart': 'Part Mode', 'auto': 'Auto Mode'}
        zmode_display = _zmap.get(user_dict.get('zipmode', 'zfolder'), 'Folders')

        text = (f'<blockquote>⊟ <b>Leech Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'├ <b>Daily Leech :</b> <i>{daily_leech}</i>\n'
                f'├ <b>Leech Type :</b> <i>{"Document" if is_doc else "Media"}</i>\n'
                f'├ <b>Custom Thumbnail :</b> <i>{"Exists" if has_thumb else "Not Exists"}</i>\n'
                f'├ <b>Leech Split Size :</b> <i>{split_size}</i>\n'
                f'├ <b>Equal Splits :</b> <i>{"Enabled" if equal_sp else "Disabled"}</i>\n'
                f'├ <b>Media Group :</b> <i>{"Enabled" if is_mg else "Disabled"}</i>\n'
                f'├ <b>Leech Caption :</b> <i>{cap_val}</i>\n'
                f'├ <b>Leech Prefix :</b> <i>{"<code>" + escape(prename) + "</code>" if prename else "Not Exists"}</i>\n'
                f'├ <b>Leech Suffix :</b> <i>{"<code>" + escape(sufname) + "</code>" if sufname else "Not Exists"}</i>\n'
                f'├ <b>Leech Dumps :</b> <i>{"<code>" + str(dch) + "</code>" if dch else "Not Exists"}</i>\n'
                f'├ <b>Leech Remname :</b> <i>{"<code>" + escape(remname) + "</code>" if remname else "Not Exists"}</i>\n'
                f'└ <b>Leech Metadata :</b> <i>{"<code>" + escape(str(metadata)) + "</code>" if metadata else "Not Exists"}</i></blockquote>')

    # ═══════════════════════ MIRROR / CLONE SETTINGS ═══════════════════════
    elif data == 'mirror':
        has_rcc  = await aiopath.exists(rclone_path)
        has_gdx  = await aiopath.exists(token_pickle)
        rc_path  = user_dict.get('rclone_path')
        gd_id    = user_dict.get('gdrive_id')
        index    = user_dict.get('index_url')
        stop_dup = (user_dict.get('stop_duplicate') or
                    ('stop_duplicate' not in user_dict and config_dict['STOP_DUPLICATE']))

        daily_mirror = _daily_str(user_id, user_dict)
        ddl_servers  = user_dict.get('ddl_servers') or {}
        user_tds     = user_dict.get('user_tds') or {}
        td_mode      = user_dict.get('user_td_mode', False)

        prename = user_dict.get('prename')
        sufname = user_dict.get('sufname')
        remname = user_dict.get('remname')

        buttons.button_data('RClone',                                                      f'userset {user_id} rctool')
        buttons.button_data(f'{"✅ " if prename else ""}Mirror Prefix',                    f'userset {user_id} setdata prename')
        buttons.button_data(f'{"✅ " if sufname else ""}Mirror Suffix',                    f'userset {user_id} setdata sufname')
        buttons.button_data(f'{"✅ " if remname else ""}Mirror Remname',                   f'userset {user_id} setdata remname')
        buttons.button_data(f'DDL Servers ({len(ddl_servers)})',                           f'userset {user_id} ddls_info')
        buttons.button_data(f'User TDs ({len(user_tds)})',                                 f'userset {user_id} gdtool')
        buttons.button_data(f'{"✅ " if stop_dup else ""}Stop Duplicate',                  f'userset {user_id} stop_duplicate {stop_dup}', 'header')
        buttons.button_data('« Back',  f'userset {user_id} back',  'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = (f'<blockquote>⊟ <b>Mirror/Clone Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'├ <b>RClone Config :</b> <i>{"Exists" if has_rcc else "Not Exists"}</i>\n'
                f'├ <b>RClone Path :</b> <i>{"<code>" + rc_path + "</code>" if rc_path else "Not Exists"}</i>\n'
                f'├ <b>Mirror Prefix :</b> <i>{"<code>" + escape(prename) + "</code>" if prename else "Not Exists"}</i>\n'
                f'├ <b>Mirror Suffix :</b> <i>{"<code>" + escape(sufname) + "</code>" if sufname else "Not Exists"}</i>\n'
                f'├ <b>Mirror Remname :</b> <i>{"<code>" + escape(remname) + "</code>" if remname else "Not Exists"}</i>\n'
                f'├ <b>DDL Server(s) :</b> <i>{len(ddl_servers)}</i>\n'
                f'├ <b>User TD Mode :</b> <i>{"Force Enabled" if td_mode else "Force Disabled"}</i>\n'
                f'├ <b>Total User TD(s) :</b> <i>{len(user_tds)}</i>\n'
                f'├ <b>Daily Mirror :</b> <i>{daily_mirror}</i>\n'
                f'├ <b>GDrive Token :</b> <i>{"Exists" if has_gdx else "Not Exists"}</i>\n'
                f'├ <b>GDrive ID :</b> <i>{"<code>" + gd_id + "</code>" if gd_id else "Not Exists"}</i>\n'
                f'├ <b>Index Link :</b> <i>{"<code>" + index + "</code>" if index else "Not Exists"}</i>\n'
                f'└ <b>Stop Duplicate :</b> <i>{"Enabled" if stop_dup else "Disabled"}</i></blockquote>')

    # ═══════════════════════ FF / METADATA ═══════════════════════
    elif data == 'ffset':
        metadata   = user_dict.get('metadata')
        clean_meta = user_dict.get('clean_metadata')

        if isinstance(metadata, dict) and metadata:
            meta_val = ', '.join(f'{k}={escape(str(v))}' for k, v in metadata.items())
            meta_val = f'<code>{meta_val}</code>'
        elif isinstance(metadata, str) and metadata:
            meta_val = f'<code>{escape(metadata)}</code>'
        else:
            meta_val = 'Not Exists'

        buttons.button_data(f'{"✅ " if metadata else ""}Metadata',          f'userset {user_id} setdata metadata')
        buttons.button_data(f'{"🔥 " if clean_meta else ""}{"Clean" if clean_meta else "Overwrite"} Mode',
                            f'userset {user_id} setdata metadata {not clean_meta}')
        buttons.button_data('« Back',  f'userset {user_id} back',  'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = (f'<blockquote>⊟ <b>FF / Metadata Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'├ <b>Metadata :</b> <i>{meta_val}</i>\n'
                f'└ <b>Clean Metadata :</b> <i>{"Enabled" if clean_meta else "Disabled"}</i></blockquote>')

    # ═══════════════════════ VIDEO TOOLS ═══════════════════════
    elif data == 'vidtools':
        # Each tool opens its own settings sub-menu — no toggles / marks here
        for key, label in VID_MODE.items():
            icon = _VID_ICONS.get(key, '🎬')
            buttons.button_data(f'{icon} {label}', f'userset {user_id} vid_setting {key}')

        buttons.button_data('« Back',  f'userset {user_id} back',  'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>Video Tools :</b> {from_user.mention}\n'
                 f'├\n'
                 f'└ <b>Total Tools :</b> <i>{len(VID_MODE)}</i></blockquote>\n\n'
                 '<i>Choose any video tool below to view & manage its settings.</i>')

    # ═══════════════════════ VIDEO TOOLS → MERGE (Video + Video) ═══════════════════════
    elif data == 'vid_merge':
        is_enabled = 'vid_vid' not in set(user_dict.get('disabled_vidtools', []))
        merge_mode = user_dict.get('vid_merge_mode') or _VID_DEFAULTS['vid_merge_mode']

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid vid_vid')
        buttons.button_data(f'Merge Mode : {merge_mode.title()}',
                            f'userset {user_id} vid_cycle vid_merge_mode')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>🎞️ Video + Video :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'└ <b>Merge Mode :</b> <i>{merge_mode.title()}</i></blockquote>\n\n'
                 '<i>Merge multiple videos. Sequential = play one after another, '
                 'Concat = ffmpeg concat demuxer (faster, same codec required).</i>')

    # ═══════════════════════ VIDEO TOOLS → AUDIO MUX (Video + Audio) ═══════════════════════
    elif data == 'vid_audmux':
        is_enabled  = 'vid_aud' not in set(user_dict.get('disabled_vidtools', []))
        audio_lang  = user_dict.get('vid_audio_lang')  or 'Auto'
        audio_codec = user_dict.get('vid_audio_codec') or _VID_DEFAULTS['vid_audio_codec']

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid vid_aud')
        has_lang = bool(user_dict.get('vid_audio_lang'))
        buttons.button_data(f'{"✅ " if has_lang else ""}Audio Language',
                            f'userset {user_id} setdata vid_audio_lang')
        if has_lang:
            buttons.button_data('🗑️ Reset Language', f'userset {user_id} rem_vid_audio_lang')
        buttons.button_data(f'Audio Codec : {audio_codec.upper()}',
                            f'userset {user_id} vid_cycle vid_audio_codec')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>🎵 Video + Audio :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'├ <b>Audio Language :</b> <code>{audio_lang}</code>\n'
                 f'└ <b>Audio Codec :</b> <i>{audio_codec.upper()}</i></blockquote>\n\n'
                 '<i>Mux external audio into your video. Set ISO 639 language code '
                 '(e.g. eng, hin, jpn) and target codec.</i>')

    # ═══════════════════════ VIDEO TOOLS → SUBSYNC ═══════════════════════
    elif data == 'vid_subsync':
        is_enabled = 'subsync' not in set(user_dict.get('disabled_vidtools', []))
        delay      = user_dict.get('vid_subsync_delay') or _VID_DEFAULTS['vid_subsync_delay']

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid subsync')
        has_delay = bool(user_dict.get('vid_subsync_delay'))
        buttons.button_data(f'{"✅ " if has_delay else ""}Sync Delay (ms)',
                            f'userset {user_id} setdata vid_subsync_delay')
        if has_delay:
            buttons.button_data('🗑️ Reset Delay', f'userset {user_id} rem_vid_subsync_delay')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>🔄 SubSync :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'└ <b>Sync Delay :</b> <code>{delay} ms</code></blockquote>\n\n'
                 '<i>Adjust subtitle timing. Positive value delays subtitles, '
                 'negative value advances them. Example: <code>-500</code> = subs appear 500ms earlier.</i>')

    # ═══════════════════════ VIDEO TOOLS → CONVERT ═══════════════════════
    elif data == 'vid_convert':
        is_enabled = 'convert' not in set(user_dict.get('disabled_vidtools', []))
        fmt        = user_dict.get('vid_convert_format') or _VID_DEFAULTS['vid_convert_format']

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid convert')
        for f in _VID_FIELD_OPTIONS['vid_convert_format']:
            mark = '🔥 ' if f == fmt else ''
            buttons.button_data(f'{mark}{f.upper()}', f'userset {user_id} vid_set vid_convert_format {f}')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>🔁 Convert :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'└ <b>Output Format :</b> <i>{fmt.upper()}</i></blockquote>\n\n'
                 '<i>Convert videos between container formats. Tap a format below to set it as default.</i>')

    # ═══════════════════════ VIDEO TOOLS → WATERMARK ═══════════════════════
    elif data == 'vid_watermark':
        is_enabled = 'watermark' not in set(user_dict.get('disabled_vidtools', []))
        wm_text    = user_dict.get('vid_watermark_text')    or 'Not Set'
        wm_pos     = user_dict.get('vid_watermark_pos')     or _VID_DEFAULTS['vid_watermark_pos']
        wm_opa     = user_dict.get('vid_watermark_opacity') or _VID_DEFAULTS['vid_watermark_opacity']

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid watermark')
        has_text = bool(user_dict.get('vid_watermark_text'))
        has_opa  = bool(user_dict.get('vid_watermark_opacity'))
        buttons.button_data(f'{"✅ " if has_text else ""}Watermark Text',
                            f'userset {user_id} setdata vid_watermark_text')
        if has_text:
            buttons.button_data('🗑️ Reset Text', f'userset {user_id} rem_vid_watermark_text')
        buttons.button_data(f'Position : {wm_pos.title()}',
                            f'userset {user_id} vid_cycle vid_watermark_pos')
        buttons.button_data(f'{"✅ " if has_opa else ""}Opacity (%)',
                            f'userset {user_id} setdata vid_watermark_opacity')
        if has_opa:
            buttons.button_data('🗑️ Reset Opacity', f'userset {user_id} rem_vid_watermark_opacity')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>💧 Watermark :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'├ <b>Text :</b> <code>{wm_text}</code>\n'
                 f'├ <b>Position :</b> <i>{wm_pos.title()}</i>\n'
                 f'└ <b>Opacity :</b> <i>{wm_opa}%</i></blockquote>\n\n'
                 '<i>Apply text watermark on output videos. Set position and opacity (0-100).</i>')

    # ═══════════════════════ VIDEO TOOLS → EXTRACT ═══════════════════════
    elif data == 'vid_extract':
        is_enabled = 'extract' not in set(user_dict.get('disabled_vidtools', []))
        selected   = user_dict.get('vid_extract_streams', _VID_DEFAULTS['vid_extract_streams'])

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid extract')
        for stream in _VID_MULTI_OPTIONS['vid_extract_streams']:
            mark = '✅' if stream in selected else '❌'
            buttons.button_data(f'{mark} {stream.title()}',
                                f'userset {user_id} vid_multi vid_extract_streams {stream}')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>📤 Extract :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'└ <b>Extract :</b> <i>{", ".join(s.title() for s in selected) or "None"}</i></blockquote>\n\n'
                 '<i>Toggle which streams to extract from the source media file.</i>')

    # ═══════════════════════ VIDEO TOOLS → TRIM ═══════════════════════
    elif data == 'vid_trim':
        is_enabled = 'trim' not in set(user_dict.get('disabled_vidtools', []))
        t_start    = user_dict.get('vid_trim_start') or _VID_DEFAULTS['vid_trim_start']
        t_end      = user_dict.get('vid_trim_end')   or _VID_DEFAULTS['vid_trim_end']

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid trim')
        has_s = bool(user_dict.get('vid_trim_start'))
        has_e = bool(user_dict.get('vid_trim_end'))
        buttons.button_data(f'{"✅ " if has_s else ""}Start Time',
                            f'userset {user_id} setdata vid_trim_start')
        if has_s:
            buttons.button_data('🗑️ Reset Start', f'userset {user_id} rem_vid_trim_start')
        buttons.button_data(f'{"✅ " if has_e else ""}End Time',
                            f'userset {user_id} setdata vid_trim_end')
        if has_e:
            buttons.button_data('🗑️ Reset End', f'userset {user_id} rem_vid_trim_end')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>✂️ Trim :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'├ <b>Start :</b> <code>{t_start}</code>\n'
                 f'└ <b>End :</b> <code>{t_end}</code></blockquote>\n\n'
                 '<i>Trim videos using HH:MM:SS format. Example start: <code>00:01:30</code>, '
                 'end: <code>00:05:00</code>.</i>')

    # ═══════════════════════ VIDEO TOOLS → REMOVE STREAM ═══════════════════════
    elif data == 'vid_rmstream':
        is_enabled = 'rmstream' not in set(user_dict.get('disabled_vidtools', []))
        selected   = user_dict.get('vid_rmstream_kind', _VID_DEFAULTS['vid_rmstream_kind'])

        buttons.button_data(f'{"❌ Disable" if is_enabled else "✅ Enable"} Tool',
                            f'userset {user_id} toggle_vid rmstream')
        for stream in _VID_MULTI_OPTIONS['vid_rmstream_kind']:
            mark = '✅' if stream in selected else '❌'
            buttons.button_data(f'{mark} Remove {stream.title()}',
                                f'userset {user_id} vid_multi vid_rmstream_kind {stream}')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>🗑️ Remove Stream :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Status :</b> <i>{"Enabled ✅" if is_enabled else "Disabled ❌"}</i>\n'
                 f'└ <b>Removing :</b> <i>{", ".join(s.title() for s in selected) or "None"}</i></blockquote>\n\n'
                 '<i>Toggle which stream types to strip from the output video.</i>')

    # ═══════════════════════ VIDEO TOOLS → COMPRESS ═══════════════════════
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
        buttons.button_data(f'{"✅ " if has_banner else ""}Compress Banner', f'userset {user_id} setdata vid_banner')
        if has_banner:
            buttons.button_data('🗑️ Reset Banner', f'userset {user_id} rem_vid_banner')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>Compress Settings :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>x264 Preset :</b> <code>{vid_264}</code>\n'
                 f'├ <b>x265 Preset :</b> <code>{vid_265}</code>\n'
                 f'└ <b>Compress Banner :</b> <i>{vid_banner or "Default"}</i></blockquote>\n\n'
                 '<i>Select preset for x264/x265 or set custom banner</i>')

    # ═══════════════════════ VIDEO TOOLS → HARDSUB ═══════════════════════
    elif data == 'vid_hardsub':
        vid_font     = user_dict.get('vid_hardsub_font') or config_dict.get('HARDSUB_FONT_NAME', 'Default')
        vid_fontsize = user_dict.get('vid_hardsub_size') or config_dict.get('HARDSUB_FONT_SIZE', 'Default')

        has_font = bool(user_dict.get('vid_hardsub_font'))
        has_size = bool(user_dict.get('vid_hardsub_size'))
        buttons.button_data(f'{"✅ " if has_font else ""}Font Name',  f'userset {user_id} setdata vid_hardsub_font')
        if has_font:
            buttons.button_data('🗑️ Reset Font', f'userset {user_id} rem_vid_hardsub_font')
        buttons.button_data(f'{"✅ " if has_size else ""}Font Size',  f'userset {user_id} setdata vid_hardsub_size')
        if has_size:
            buttons.button_data('🗑️ Reset Size', f'userset {user_id} rem_vid_hardsub_size')
        buttons.button_data('« Back',  f'userset {user_id} back vidtools', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',         'footer')

        image = config_dict['IMAGE_VIDTOOLS']
        text  = (f'<blockquote>⊟ <b>HardSub Settings :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>HardSub Font :</b> <code>{vid_font}</code>\n'
                 f'└ <b>Font Size :</b> <code>{vid_fontsize}</code></blockquote>')

    # ═══════════════════════ ADVANCED SETTINGS ═══════════════════════
    elif data == 'advanced':
        if ext_filters := user_dict.get('excluded_extensions'):
            ex_ex = ', '.join(ext_filters)
        elif 'excluded_extensions' not in user_dict and GLOBAL_EXTENSION_FILTER:
            ex_ex = ', '.join(GLOBAL_EXTENSION_FILTER)
        else:
            ex_ex = 'Not Exists'

        has_ext = bool(user_dict.get('excluded_extensions'))
        buttons.button_data(f'{"✅ " if has_ext else ""}Extensions Filter', f'userset {user_id} setdata excluded_extensions')
        buttons.button_data('« Back',  f'userset {user_id} back',  'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

        text = (f'<blockquote>⊟ <b>Advanced Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'└ <b>Excluded Extensions :</b> <i>{ex_ex}</i></blockquote>')

    # ═══════════════════════ CAPTION MODE ═══════════════════════
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
            case 'italic': image, ex_cap = config_dict['IMAGE_ITALIC'], f'<i>{ex_cap}</i>'
            case 'bold':   image, ex_cap = config_dict['IMAGE_BOLD'],   f'<b>{ex_cap}</b>'
            case 'normal': image = config_dict['IMAGE_NORMAL']
            case 'mono':   image, ex_cap = config_dict['IMAGE_MONO'],   f'<code>{ex_cap}</code>'

        cap_modes = ['mono', 'italic', 'bold', 'normal']
        cap_modes.remove(user_cap)
        caption, fnamecap = user_dict.get('captions'), user_dict.get('fnamecap', True)
        cap_icons = {'mono': '🔠', 'italic': '✍️', 'bold': '🅱️', 'normal': '🔤'}
        if not user_dict or fnamecap:
            [buttons.button_data(f'{cap_icons.get(m, "🔤")} {m.title()}', f'userset {user_id} cap{m}')
             for m in cap_modes]
        buttons.button_data(f'{"✅ " if caption else ""}Custom Caption', f'userset {user_id} setdata setcap')
        buttons.button_data('« Back',  f'userset {user_id} back leech', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',      'footer')
        if caption:
            buttons.button_data(f'{"✅ " if fnamecap else ""}FName Caption', f'userset {user_id} fnamecap')
            custom_cap = f'\n<code>{escape(caption)}</code>'
            fname_cup  = ('├ <b>FName Caption :</b> <b>✅ ENABLED</b>\n' if fnamecap
                         else '├ <b>FName Caption :</b> <b>❌ DISABLED</b>\n')
            if not fnamecap:
                user_capmode, image, ex_cap = 'DISABLE', config_dict['IMAGE_CAPTION'], '<b>DISABLE</b>'
        else:
            custom_cap, fname_cup = 'Not Set', ''

        text = (f'<blockquote>⊟ <b>Caption Settings :</b> {from_user.mention}\n'
                f'├\n'
                f'├ <b>Caption Mode :</b> <b>{user_capmode}</b>\n'
                f'{fname_cup}'
                f'└ <b>Custom Caption :</b> {custom_cap}</blockquote>\n\n'
                f'🔍 <b>Example :</b> {ex_cap}')

    # ═══════════════════════ RCLONE TOOL ═══════════════════════
    elif data == 'rctool':
        has_rcc = await aiopath.exists(rclone_path)
        rc_path = user_dict.get('rclone_path')
        buttons.button_data(f'{"✅ " if has_rcc else ""}RClone Config', f'userset {user_id} setdata rclone_config')
        buttons.button_data(f'{"✅ " if rc_path else ""}RClone Path',   f'userset {user_id} setdata rclone_path')
        buttons.button_data('« Back',  f'userset {user_id} back mirror', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',       'footer')

        image = config_dict['IMAGE_RCLONE']
        text  = (f'<blockquote>⊟ <b>RClone Settings :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>RClone Config :</b> <i>{"Exists" if has_rcc else "Not Exists"}</i>\n'
                 f'└ <b>RClone Path :</b> <i>{"<code>" + rc_path + "</code>" if rc_path else "Not Exists"}</i></blockquote>')

    # ═══════════════════════ GDRIVE TOOL ═══════════════════════
    elif data == 'gdtool':
        gd_id   = user_dict.get('gdrive_id')
        index   = user_dict.get('index_url')
        has_tp  = await aiopath.exists(token_pickle)
        stop_dup = (user_dict.get('stop_duplicate') or
                    ('stop_duplicate' not in user_dict and config_dict['STOP_DUPLICATE']))
        buttons.button_data(f'{"✅ " if gd_id else ""}Drive ID',      f'userset {user_id} setdata gdrive_id')
        buttons.button_data(f'{"✅ " if index else ""}Index URL',      f'userset {user_id} setdata index_url')
        buttons.button_data(f'{"✅ " if has_tp else ""}Token Pickle',  f'userset {user_id} setdata token_pickle')
        buttons.button_data(f'{"✅ " if stop_dup else ""}Stop Duplicate', f'userset {user_id} stop_duplicate {stop_dup}', 'header')
        if await aiopath.exists('accounts'):
            use_sa_v = user_dict.get('use_sa')
            buttons.button_data(f'{"✅ " if use_sa_v else ""}Use SA', f'userset {user_id} use_sa {use_sa_v}', 'header')
            use_sa_val = 'Enabled' if use_sa_v else 'Disabled'
        else:
            use_sa_val = 'Not Available'
        buttons.button_data('« Back',  f'userset {user_id} back mirror', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',       'footer')

        image = config_dict['IMAGE_GD']
        text  = (f'<blockquote>⊟ <b>GDrive Settings :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>GDrive ID :</b> <i>{"<code>" + gd_id + "</code>" if gd_id else "Not Exists"}</i>\n'
                 f'├ <b>Index Link :</b> <i>{"<code>" + index + "</code>" if index else "Not Exists"}</i>\n'
                 f'├ <b>GDrive Token :</b> <i>{"Exists" if has_tp else "Not Exists"}</i>\n'
                 f'├ <b>Use SA :</b> <i>{use_sa_val}</i>\n'
                 f'└ <b>Stop Duplicate :</b> <i>{"Enabled" if stop_dup else "Disabled"}</i></blockquote>')

    # ═══════════════════════ ZIP MODE ═══════════════════════
    elif data == 'zipmode':
        but_dict = {
            'zfolder': ['Folders',    f'userset {user_id} zipmode zfolder'],
            'zfpart':  ['Cloud Part', f'userset {user_id} zipmode zfpart'],
            'zeach':   ['Each Files', f'userset {user_id} zipmode zeach'],
            'zpart':   ['Part Mode',  f'userset {user_id} zipmode zpart'],
            'auto':    ['Auto Mode',  f'userset {user_id} zipmode auto'],
        }
        def_data = but_dict[uset_data][0]
        but_dict[uset_data][0] = f'🔥 {def_data}'
        [buttons.button_data(key, value) for key, value in but_dict.values()]
        buttons.button_data('« Back',  f'userset {user_id} back leech', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',      'footer')
        part_size = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])
        image = config_dict['IMAGE_ZIP']
        text  = (f'<blockquote>⊟ <b>Zip Mode :</b> {from_user.mention}\n'
                 f'├\n'
                 f'├ <b>Folders/Default :</b> Zip file/folder\n'
                 f'├ <b>Cloud Part :</b> Zip as part {part_size}\n'
                 f'├ <b>Each Files :</b> Zip each file in folder\n'
                 f'├ <b>Part Mode :</b> Zip each file as part if >{part_size}\n'
                 f'├ <b>Auto Mode :</b> Auto zip if size >{part_size}\n'
                 f'└ <b>Current Mode :</b> {def_data}</blockquote>\n\n'
                 '<i>*Seeding only works in Default Mode</i>')

    # ═══════════════════════ SET DATA ═══════════════════════
    elif data == 'setdata':
        if uset_data in {'thumb', 'rclone_config', 'token_pickle'}:
            file_dict = {
                'thumb':         (thumbpath,    'Thumbnail', 'Send a photo to save it as custom thumbnail.', '', ''),
                'rclone_config': (rclone_path,  'RClone',    'Send a valid <b>*.conf</b> file.',              config_dict['IMAGE_RCLONE'], 'rctool'),
                'token_pickle':  (token_pickle, 'Token',     'Send a valid <b>*.pickle</b> file.',            config_dict['IMAGE_GD'],     'gdtool'),
            }
            file_path, butkey, text, image, qdata = file_dict[uset_data]
            if await aiopath.exists(file_path):
                buttons.button_data(f'Change {butkey}', f'userset {user_id} prepare {uset_data}')
                buttons.button_data(f'Delete {butkey}', f'userset {user_id} rem_{uset_data}')
            else:
                buttons.button_data(f'Set {butkey}', f'userset {user_id} prepare {uset_data}')
        else:
            uset_dict = {
                'excluded_extensions': ('excluded_extensions', 'Extension', UsetString.EXT,                                                                             config_dict['IMAGE_EXTENSION'], ''),
                'setcap':              ('captions',  'Caption',   UsetString.CAP,                                                                                       config_dict['IMAGE_CAPTION'],   'capmode'),
                'rctool':              ('captions',  'Caption',   UsetString.CAP,                                                                                       config_dict['IMAGE_CAPTION'],   'rctool'),
                'rclone_path':         ('rclone_path', 'RClone Path', UsetString.RCP,                                                                                   config_dict['IMAGE_RCLONE'],    'rctool'),
                'dump_ch':             ('dump_ch',   'Dump',     UsetString.DUMP,                                                                                       config_dict['IMAGE_DUMP'],      ''),
                'gdrive_id':           ('gdrive_id', 'ID',       UsetString.GDID,                                                                                       config_dict['IMAGE_GD'],        'gdtool'),
                'index_url':           ('index_url', 'Index',    UsetString.INDX,                                                                                       config_dict['IMAGE_GD'],        'gdtool'),
                'prename':             ('prename',   'Prefix',   UsetString.PRE,                                                                                        config_dict['IMAGE_PRENAME'],   ''),
                'sufname':             ('sufname',   'Suffix',   UsetString.SUF,                                                                                        config_dict['IMAGE_SUFNAME'],   ''),
                'remname':             ('remname',   'Remname',  UsetString.REM.format(user_dict.get('remname') or '~'),                                                config_dict['IMAGE_REMNAME'],   ''),
                'metadata':            ('metadata',  'Metadata', UsetString.META.format(user_dict.get('metadata') or '~'),                                              config_dict['IMAGE_METADATA'],  ''),
                'session_string':      ('session_string', 'Session', UsetString.SES,                                                                                    config_dict['IMAGE_USER'],      ''),
                'yt_opt':              ('yt_opt',    'YT-DLP',   UsetString.YT,                                                                                         config_dict['IMAGE_YT'],        ''),
                'split_size_info':     ('leech_split_size', 'Split Size', f'Current split size: <b>{get_readable_file_size(config_dict["LEECH_SPLIT_SIZE"])}</b>\n(Split size is set by admin only)', '', ''),
                # ── Video Tools ──
                'vid_banner':       ('vid_banner',       'Banner',    'Send compress banner text.\n<i>Example:</i> <code>Re-Encoded by @MyChannel</code>',               config_dict['IMAGE_VIDTOOLS'], 'vid_compress'),
                'vid_hardsub_font': ('vid_hardsub_font', 'Font',      'Send HardSub font name.\n<i>Example:</i> <code>Arial</code>',                                     config_dict['IMAGE_VIDTOOLS'], 'vid_hardsub'),
                'vid_hardsub_size': ('vid_hardsub_size', 'Font Size', 'Send HardSub font size as number.\n<i>Example:</i> <code>24</code>',                              config_dict['IMAGE_VIDTOOLS'], 'vid_hardsub'),
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
            if uset_data == 'split_size_info':
                pass  # info only, no set/remove
            elif user_dict.get(key) or (key == 'yt_opt' and config_dict['YT_DLP_OPTIONS']):
                buttons.button_data(f'Change {butkey}', f'userset {user_id} prepare {key}')
                buttons.button_data(f'Remove {butkey}', f'userset {user_id} rem_{key}')
            else:
                buttons.button_data(f'Set {butkey}', f'userset {user_id} prepare {key}')
        if qdata:
            buttons.button_data('« Back', f'userset {user_id} {qdata}', 'footer')
        text = text.replace('Timeout: 60s.', '')
        _setdata_back = {
            'thumb': 'leech', 'dump_ch': 'leech', 'prename': 'leech', 'sufname': 'leech',
            'remname': 'leech', 'split_size_info': 'leech',
            'excluded_extensions': 'general',
            'session_string': 'general', 'yt_opt': 'general',
            'metadata': 'ffset',
        }
        _no_back = ['setcap', 'index_url', 'token_pickle', 'gdrive_id', 'rclone_path',
                    'rclone_config', 'vid_banner', 'vid_hardsub_font', 'vid_hardsub_size']
        if uset_data not in _no_back and not qdata:
            _bk = _setdata_back.get(uset_data, '')
            _cb = f'userset {user_id} back {_bk}' if _bk else f'userset {user_id} back'
            buttons.button_data('« Back', _cb, 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close', 'footer')

    # ═══════════════════════ PREPARE INPUT ═══════════════════════
    elif data == 'prepare':
        msg_thumb  = ('Send a photo to change current thumbnail.\n\n<i>Timeout: 60s.</i>'
                      if await aiopath.exists(thumbpath) else
                      'Send a photo to save it as custom thumbnail.\n\n<i>Timeout: 60s.</i>')
        msg_rclone = ('Send new <b>*.conf</b> to change current config.\n\n<i>Timeout: 60s.</i>'
                      if await aiopath.exists(rclone_path) else
                      'Send a valid <b>*.conf</b> file.\n\n<i>Timeout: 60s.</i>')
        msg_token  = ('Send new <b>*.pickle</b> to change current token.\n\n<i>Timeout: 60s.</i>'
                      if await aiopath.exists(token_pickle) else
                      'Send a valid <b>*.pickle</b> file.\n\n<i>Timeout: 60s.</i>')
        prepare_dict = {
            'thumb':               (msg_thumb,   image),
            'rclone_config':       (msg_rclone,  config_dict['IMAGE_RCLONE']),
            'token_pickle':        (msg_token,   config_dict['IMAGE_GD']),
            'dump_ch':             (UsetString.DUMP, config_dict['IMAGE_DUMP']),
            'rclone_path':         (UsetString.RCP,  config_dict['IMAGE_RCLONE']),
            'gdrive_id':           (UsetString.GDID, config_dict['IMAGE_GD']),
            'index_url':           (UsetString.INDX, config_dict['IMAGE_GD']),
            'excluded_extensions': (UsetString.EXT,  config_dict['IMAGE_EXTENSION']),
            'captions':            (UsetString.CAP,  config_dict['IMAGE_CAPTION']),
            'prename':             (UsetString.PRE,  config_dict['IMAGE_PRENAME']),
            'sufname':             (UsetString.SUF,  config_dict['IMAGE_SUFNAME']),
            'remname':             (UsetString.REM.format(user_dict.get('remname') or '~'), config_dict['IMAGE_REMNAME']),
            'metadata':            (UsetString.META.format(user_dict.get('metadata') or '~'), config_dict['IMAGE_METADATA']),
            'session_string':      (UsetString.SES,  config_dict['IMAGE_USER']),
            'yt_opt':              (UsetString.YT,   config_dict['IMAGE_YT']),
            'vid_banner':          ('Send compress banner text.\n<i>Example:</i> <code>Re-Encoded by @MyChannel</code>', config_dict['IMAGE_VIDTOOLS']),
            'vid_hardsub_font':    ('Send HardSub font name.\n<i>Example:</i> <code>Arial</code>',                      config_dict['IMAGE_VIDTOOLS']),
            'vid_hardsub_size':    ('Send HardSub font size as a number.\n<i>Example:</i> <code>24</code>',             config_dict['IMAGE_VIDTOOLS']),
        }
        text, image = prepare_dict[uset_data]
        buttons.button_data('« Back',  f'userset {user_id} setdata {uset_data}', 'footer')
        buttons.button_data('✘ Close', f'userset {user_id} close',               'footer')

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
    if key == 'dump_ch' and (value.isdigit() or value.startswith('-100')):
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
        case 'index_url' | 'token_pickle' | 'gdrive_id': back_data = 'gdtool'
        case 'captions':           back_data = 'capmode'
        case 'rclone_path':        back_data = 'rctool'
        case 'vid_banner':         back_data = 'vid_compress'
        case 'vid_hardsub_font' | 'vid_hardsub_size': back_data = 'vid_hardsub'
        case _:                    back_data = None
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
    await gather(update_user_ldata(user_id, 'thumb', des_dir),
                 deleteMessage(message, msg),
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
    message   = query.message
    user_id   = query.from_user.id
    data      = query.data.split()
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
        case ('general' | 'leech' | 'mirror' | 'ffset' | 'vidtools' |
              'vid_compress' | 'vid_hardsub' | 'advanced' |
              'capmode' | 'gdtool' | 'rctool') as value:
            await gather(query.answer(), update_user_settings(query, value))

        # ── Video Tools: open per-tool sub-menu ──
        case 'vid_setting':
            key = data[3] if len(data) >= 4 else ''
            if key == 'compress':
                target_data, target_uset = 'vid_compress', None
            elif key == 'vid_sub':
                target_data, target_uset = 'vid_hardsub', None
            elif key in VID_MODE:
                target_data, target_uset = 'vid_info', key
            else:
                await query.answer('Unknown tool!', True)
                return
            await gather(query.answer(), update_user_settings(query, target_data, target_uset))

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

        # ── Video Tools: toggle per-mode (called from per-tool info sub-menu) ──
        case 'toggle_vid':
            vid_mode = data[3]
            if vid_mode not in VID_MODE:
                await query.answer('Unknown tool!', True)
                return
            disabled = set(user_dict.get('disabled_vidtools', []))
            if vid_mode in disabled:
                disabled.discard(vid_mode)
                await query.answer(f'{VID_MODE[vid_mode]} Enabled ✅', True)
            else:
                disabled.add(vid_mode)
                await query.answer(f'{VID_MODE[vid_mode]} Disabled ❌', True)
            await update_user_ldata(user_id, 'disabled_vidtools', list(disabled))
            await update_user_settings(query, 'vid_info', vid_mode)

        # ── Video preset selections ──
        case 'set_vid264':
            await query.answer(f'x264 → {data[3]}', True)
            await update_user_ldata(user_id, 'vid_264_preset', data[3])
            await update_user_settings(query, 'vid_compress')

        case 'set_vid265':
            await query.answer(f'x265 → {data[3]}', True)
            await update_user_ldata(user_id, 'vid_265_preset', data[3])
            await update_user_settings(query, 'vid_compress')

        # ── Remove video settings ──
        case 'rem_vid_banner':
            await update_user_ldata(user_id, 'vid_banner', '')
            await gather(query.answer('Banner reset!', True), update_user_settings(query, 'vid_compress'))

        case 'rem_vid_hardsub_font':
            await update_user_ldata(user_id, 'vid_hardsub_font', '')
            await gather(query.answer('Font reset!', True), update_user_settings(query, 'vid_hardsub'))

        case 'rem_vid_hardsub_size':
            await update_user_ldata(user_id, 'vid_hardsub_size', '')
            await gather(query.answer('Font size reset!', True), update_user_settings(query, 'vid_hardsub'))

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
              'fnamecap' | 'stop_duplicate' | 'use_sa' | 'mediainfo') as value:
            qdata = uset_data = ''
            await update_user_ldata(user_id, value, not user_dict.get(value, False))
            if value == 'fnamecap':
                qdata = 'capmode'
            elif value in ('stop_duplicate', 'use_sa'):
                qdata = 'gdtool'
            elif value in ('enable_pm', 'enable_ss', 'mediainfo'):
                qdata = 'general'
            elif value in ('as_doc', 'media_group'):
                qdata = 'leech'
            await gather(query.answer(), update_user_settings(query, qdata, uset_data))

        # ── Save Mode toggle (BotPm <-> Dump) ──
        case 'save_mode':
            cur = user_dict.get('save_mode', 'botpm')
            new = 'dump' if cur == 'botpm' else 'botpm'
            await update_user_ldata(user_id, 'save_mode', new)
            await gather(query.answer(f'Save Mode → {"Save As Dump" if new == "dump" else "Save As BotPm"}', True),
                         update_user_settings(query, 'general'))

        # ── DDL Servers info popup ──
        case 'ddls_info':
            await query.answer('Use /ddl command to add or manage your DDL servers.', True)

        # ── Bulk enable/disable all video tools ──
        case 'vid_all':
            mode = data[3] if len(data) >= 4 else 'on'
            if mode == 'off':
                await update_user_ldata(user_id, 'disabled_vidtools', list(VID_MODE.keys()))
                msg = 'All video tools disabled ❌'
            else:
                await update_user_ldata(user_id, 'disabled_vidtools', [])
                msg = 'All video tools enabled ✅'
            await gather(query.answer(msg, True), update_user_settings(query, 'vidtools'))

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
            btns = ButtonMaker()
            btns.button_data('✅ Yes, Reset All', f'userset {user_id} do_reset_all yes')
            btns.button_data('❌ Cancel',          f'userset {user_id} do_reset_all no')
            btns.button_data('✘ Close',            f'userset {user_id} close', 'footer')
            await editMessage(
                '<blockquote>⚠️ <b>Reset All Settings?</b>\n\n'
                '<i>This will remove ALL your custom settings, files, and preferences.</i></blockquote>',
                message, btns.build_menu(2))

        case 'do_reset_all':
            if data[3] == 'yes':
                await query.answer('All settings reset!', True)
                udict = user_data.get(user_id, {})
                for k in list(udict.keys()):
                    if k not in ('SUDO', 'AUTH', 'VERIFY_TOKEN', 'VERIFY_TIME'):
                        del udict[k]
                for fpath in [ospath.join('thumbnails', f'{user_id}.jpg'),
                               ospath.join('rclone',    f'{user_id}.conf'),
                               ospath.join('tokens',    f'{user_id}.pickle')]:
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
                case 'rem_thumb':         path = ospath.join('thumbnails', f'{user_id}.jpg')
                case 'rem_rclone_config': path = ospath.join('rclone',    f'{user_id}.conf')
                case _:                   path = ospath.join('tokens',    f'{user_id}.pickle')
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
                    if data[3] == 'dump_ch':
                        await query.answer("Don't forget to add me to your chat!", True)
                    else:
                        await query.answer()
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
        await sendMessage('<b>Premium Mode</b> is disabled!', message)
        return
    reply_to = message.reply_to_message
    args = message.text.split()
    text = 'Reply to a user or send user ID with options (add/del) and duration in days.'
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
        duartion  = int(time() + (86400 * day))
        text      = f'🌚 <b>{premi_id}</b> added as Premium User for {day} day(s).'
        user_text = f'🌚 You have been added as <b>Premium User</b> for {day} day(s).'
        await gather(update_user_ldata(premi_id, 'premium_left', duartion),
                     update_user_ldata(premi_id, 'is_premium', True))
    elif args[1] == 'del':
        text      = f'🤡 <b>{premi_id}</b> removed as Premium User!'
        user_text = '🤡 You have been removed as <b>Premium User</b>!'
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


bot.add_handler(MessageHandler(set_premium_users,   filters=command(BotCommands.UserSetPremiCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(send_users_settings, filters=command(BotCommands.UsersCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(reset_daily_limit,   filters=command(BotCommands.DailyResetCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(user_settings,       filters=command(BotCommands.UserSetCommand)))
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=regex('^userset')))
