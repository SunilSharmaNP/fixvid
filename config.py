# =============================================================================
# Bot Configuration File (Python edition)
# =============================================================================
# This file replaces the old `config.env` file. Edit the values below to
# configure your bot. After importing this module, every UPPERCASE constant
# defined here is automatically pushed into os.environ, so the rest of the
# bot code (which uses os.environ.get(...)) keeps working without changes.
#
# How to use:
#   - Fill in the REQUIRED section (BOT_TOKEN, OWNER_ID, TELEGRAM_API,
#     TELEGRAM_HASH, DATABASE_URL).
#   - Adjust the OPTIONAL section as needed.
#   - Save the file and start the bot. A `config.env` file is no longer
#     required; if one is present it will be loaded as an additional
#     override (existing values in this file take precedence on first load).
# =============================================================================

import os
import sys


# =========================== REQUIRED ========================================
BOT_TOKEN = ""
OWNER_ID = 0
TELEGRAM_API = 0
TELEGRAM_HASH = ""
DATABASE_URL = ""

# =========================== OPTIONAL ========================================
USER_SESSION_STRING = ""
SAVE_SESSION_STRING = ""
USERBOT_LEECH = ""
SAVE_MESSAGE = ""

# --------- Telegram / chat ids ----------
AUTHORIZED_CHATS = ""
SUDO_USERS = ""
FSUB = ""
FSUB_CHANNEL_ID = ""
FSUB_BUTTON_NAME = "Join Group"
FUSERNAME = ""
CHANNEL_USERNAME = "MLTBRM"
LEECH_LOG = ""
LINK_LOG = ""
MIRROR_LOG = ""
OTHER_LOG = ""
LEECH_INFO_PIN = ""
ONCOMPLETE_LEECH_LOG = ""
LEECH_DUMP_CHAT = ""
RSS_CHAT = ""
MUTE_CHAT_ID = ""

# --------- Stickers ----------
STICKER_DELETE_DURATION = 5
STICKERID_COUNT = ""
STICKERID_ERROR = ""
STICKERID_LEECH = ""
STICKERID_MIRROR = ""

# --------- Auto delete / timing ----------
AUTO_DELETE_MESSAGE_DURATION = 30
AUTO_DELETE_UPLOAD_MESSAGE_DURATION = 0
AUTO_MUTE = ""
AUTO_MUTE_DURATION = ""
AUTO_THUMBNAIL = ""
SESSION_TIMEOUT = 0
MULTI_TIMEGAP = ""
TIME_ZONE = "Asia/Kolkata"
TIME_ZONE_TITLE = "UTC+5:30"

# --------- Status / progress ----------
STATUS_UPDATE_INTERVAL = 10
STATUS_LIMIT = 10
INCOMPLETE_TASK_NOTIFIER = True
INCOMPLETE_AUTO_RESUME = True
PROG_FINISH = "\u2b22"
PROG_UNFINISH = "\u2b21"

# --------- Limits ----------
NONPREMIUM_LIMIT = 5
PREMIUM_MODE = ""
DAILY_LIMIT_SIZE = 50
DAILY_MODE = ""
LEECH_LIMIT = ""
CLONE_LIMIT = ""
TORRENT_DIRECT_LIMIT = ""
ZIP_UNZIP_LIMIT = ""
MEGA_LIMIT = ""
STORAGE_THRESHOLD = ""
TOTAL_TASKS_LIMIT = ""
USER_TASKS_LIMIT = ""
MAX_YTPLAYLIST = ""

# --------- Download ----------
DOWNLOAD_DIR = "/usr/src/app/downloads/"
DEFAULT_UPLOAD = ""
EXTENSION_FILTER = ""
DISABLE_MIRROR_LEECH = ""
CMD_SUFFIX = ""
ENABLE_FASTDL = ""

# --------- Leech ----------
LEECH_SPLIT_SIZE = ""
AS_DOCUMENT = "False"
EQUAL_SPLITS = "False"
MEDIA_GROUP = "False"
USER_TRANSMISSION = "False"
MIXED_LEECH = "False"
LEECH_FILENAME_PREFIX = ""
THUMBNAIL_LAYOUT = ""

# --------- qBittorrent / Aria2 ----------
ARIA_NAME = "aria2c"
QBIT_NAME = "qbittorrent-nox"
FFMPEG_NAME = "ffmpeg"
TORRENT_TIMEOUT = ""
TORRENT_PORT = ""
BASE_URL = ""
BASE_URL_PORT = "40064"
WEB_PINCODE = "False"

# --------- Queueing ----------
QUEUE_ALL = ""
QUEUE_DOWNLOAD = ""
QUEUE_UPLOAD = ""
QUEUE_COMPLETE = ""

# --------- RSS ----------
RSS_DELAY = "900"

# --------- Torrent search ----------
SEARCH_API_LINK = ""
SEARCH_LIMIT = "0"
SEARCH_PLUGINS = (
    '["https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/piratebay.py",'
    '"https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/limetorrents.py",'
    '"https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torlock.py",'
    '"https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentscsv.py",'
    '"https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/eztv.py",'
    '"https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentproject.py",'
    '"https://raw.githubusercontent.com/MaurizioRicci/qBittorrent_search_engines/master/kickass_torrent.py",'
    '"https://raw.githubusercontent.com/MaurizioRicci/qBittorrent_search_engines/master/yts_am.py",'
    '"https://raw.githubusercontent.com/MadeOfMagicAndWires/qBit-plugins/master/engines/linuxtracker.py",'
    '"https://raw.githubusercontent.com/MadeOfMagicAndWires/qBit-plugins/master/engines/nyaasi.py",'
    '"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/ettv.py",'
    '"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/glotorrents.py",'
    '"https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/thepiratebay.py",'
    '"https://raw.githubusercontent.com/v1k45/1337x-qBittorrent-search-plugin/master/leetx.py",'
    '"https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/magnetdl.py",'
    '"https://raw.githubusercontent.com/msagca/qbittorrent_plugins/main/uniondht.py",'
    '"https://raw.githubusercontent.com/khensolomon/leyts/master/yts.py"]'
)
TSEARCH_TITLE = "Torrent Search"

# --------- Google Drive ----------
GDRIVE_ID = ""
INDEX_URL = ""
IS_TEAM_DRIVE = ""
USE_SERVICE_ACCOUNTS = ""
STOP_DUPLICATE = ""
DRIVE_SEARCH_TITLE = "Drive Search"
GD_INFO = "By @MLTBRM"
CRYPT_GDTOT = ""

# --------- Rclone ----------
RCLONE_PATH = ""
RCLONE_FLAGS = ""
RCLONE_SERVE_URL = ""
RCLONE_SERVE_PORT = ""
RCLONE_SERVE_USER = ""
RCLONE_SERVE_PASS = ""
RCLONE_TFSIMULATION = 4

# --------- Mega / GoFile / others ----------
MEGA_EMAIL = ""
MEGA_PASSWORD = ""
GOFILE = ""
GOFILEBASEFOLDER = ""
GOFILETOKEN = ""
UPTOBOX_TOKEN = ""
FILELION_API = ""
STREAMWISH_API = ""
SHARERPW_LARAVEL_SESSION = ""
SHARERPW_XSRF_TOKEN = ""
FORCE_SHORTEN = ""

# --------- yt-dlp ----------
YT_DLP_OPTIONS = ""

# --------- Cloud / hosting ----------
HEROKU_APP_NAME = ""
HEROKU_API_KEY = ""
ARGO_TOKEN = ""
PORT = ""
PING_URL = ""
UPDATE_EVERYTHING = ""
UPSTREAM_REPO = ""
UPSTREAM_BRANCH = "master"

# --------- Misc display ----------
AUTHOR_NAME = "MLTBRM"
AUTHOR_URL = "https://t.me/MLTBRM"
SOURCE_LINK = ""
SOURCE_LINK_TITLE = "Source Link"
VIEW_LINK = ""
START_MESSAGE = ""
CLOUD_LINK_FILTERS = ""

# --------- Buttons ----------
BUTTON_FOUR_NAME = ""
BUTTON_FOUR_URL = ""
BUTTON_FIVE_NAME = ""
BUTTON_FIVE_URL = ""
BUTTON_SIX_NAME = ""
BUTTON_SIX_URL = ""

# --------- Stream ----------
ENABLE_STREAM_LINK = ""
STREAM_BASE_URL = ""
STREAM_PORT = ""

# --------- Vid tools / encoding ----------
DISABLE_VIDTOOLS = "Nope"
DISABLE_MULTI_VIDTOOLS = False
VIDTOOLS_FAST_MODE = ""
COMPRESS_BANNER = "Re-Encoded by MLTBRM \u2013 RM Movie Flix"
LIB264_PRESET = "superfast"
LIB265_PRESET = "faster"
HARDSUB_FONT_NAME = "Simple Day Mistu"
HARDSUB_FONT_SIZE = 12

# --------- JDownloader ----------
JD_EMAIL = ""
JD_PASS = ""

# --------- Sabnzbd / usenet ----------
USENET_SERVERS = (
    "[{'name': 'main', 'host': '', 'port': 5126, 'timeout': 60, 'username': '',"
    " 'password': '', 'connections': 8, 'ssl': 1, 'ssl_verify': 2,"
    " 'ssl_ciphers': '', 'enable': 1, 'required': 0, 'optional': 0,"
    " 'retention': 0, 'send_group': 0, 'priority': 0}]"
)

# =============================================================================
# IMAGES
# =============================================================================
ENABLE_IMAGE_MODE = True
_DEFAULT_IMG = "https://i.ibb.co/TBnyB2jP/IMG-20260426-092557-460.jpg"
IMAGE_ARIA = _DEFAULT_IMG
IMAGE_AUTH = _DEFAULT_IMG
IMAGE_BOLD = _DEFAULT_IMG
IMAGE_BYE = _DEFAULT_IMG
IMAGE_CANCEL = _DEFAULT_IMG
IMAGE_CAPTION = _DEFAULT_IMG
IMAGE_COMMONS_CHECK = _DEFAULT_IMG
IMAGE_COMPLETE = _DEFAULT_IMG
IMAGE_CONEDIT = _DEFAULT_IMG
IMAGE_CONPRIVATE = _DEFAULT_IMG
IMAGE_CONSET = _DEFAULT_IMG
IMAGE_CONVIEW = _DEFAULT_IMG
IMAGE_DUMP = _DEFAULT_IMG
IMAGE_EXTENSION = _DEFAULT_IMG
IMAGE_GD = _DEFAULT_IMG
IMAGE_HELP = _DEFAULT_IMG
IMAGE_HTML = _DEFAULT_IMG
IMAGE_IMDB = _DEFAULT_IMG
IMAGE_INFO = _DEFAULT_IMG
IMAGE_ITALIC = _DEFAULT_IMG
IMAGE_JD = _DEFAULT_IMG
IMAGE_LOGS = _DEFAULT_IMG
IMAGE_MDL = _DEFAULT_IMG
IMAGE_MEDINFO = _DEFAULT_IMG
IMAGE_METADATA = _DEFAULT_IMG
IMAGE_MONO = _DEFAULT_IMG
IMAGE_NORMAL = _DEFAULT_IMG
IMAGE_OWNER = _DEFAULT_IMG
IMAGE_PAUSE = _DEFAULT_IMG
IMAGE_PRENAME = _DEFAULT_IMG
IMAGE_QBIT = _DEFAULT_IMG
IMAGE_RCLONE = _DEFAULT_IMG
IMAGE_REMNAME = _DEFAULT_IMG
IMAGE_RSS = _DEFAULT_IMG
IMAGE_SEARCH = _DEFAULT_IMG
IMAGE_STATS = _DEFAULT_IMG
IMAGE_STATUS = _DEFAULT_IMG
IMAGE_SUFNAME = _DEFAULT_IMG
IMAGE_TMDB = _DEFAULT_IMG
IMAGE_TXT = _DEFAULT_IMG
IMAGE_UNAUTH = _DEFAULT_IMG
IMAGE_UNKNOW = _DEFAULT_IMG
IMAGE_USER = _DEFAULT_IMG
IMAGE_USETIINGS = _DEFAULT_IMG
IMAGE_VIDTOOLS = _DEFAULT_IMG
IMAGE_WEL = _DEFAULT_IMG
IMAGE_WIBU = _DEFAULT_IMG
IMAGE_YT = _DEFAULT_IMG
IMAGE_ZIP = _DEFAULT_IMG


# =============================================================================
# Loader helpers (do not edit unless you know what you are doing)
# =============================================================================

def _iter_settings():
    """Yield (key, value) pairs for every UPPERCASE constant in this module."""
    module = sys.modules[__name__]
    for key in dir(module):
        if not key.isupper() or key.startswith("_"):
            continue
        value = getattr(module, key)
        if callable(value):
            continue
        yield key, value


def settings_to_dict():
    """Return all UPPERCASE settings as a string-valued dict.

    This mirrors the shape of `dotenv_values('config.env')` so that downstream
    code that compared/persisted env-style dicts keeps working unchanged.
    """
    result = {}
    for key, value in _iter_settings():
        if value is None:
            result[key] = ""
        elif isinstance(value, bool):
            result[key] = str(value)
        else:
            result[key] = str(value)
    return result


def load_into_environ(override=True):
    """Push every setting into os.environ as a string.

    Args:
        override: if True (default), values defined in config.py overwrite any
            pre-existing entries in os.environ. Set to False to make config.py
            act as a fallback only.
    """
    for key, value in _iter_settings():
        if not override and key in os.environ and os.environ[key] not in ("", None):
            continue
        if value is None:
            os.environ[key] = ""
        else:
            os.environ[key] = str(value)


# Auto-populate os.environ on import so existing `environ.get(...)` calls
# throughout the codebase find these values without any further changes.
load_into_environ(override=True)
