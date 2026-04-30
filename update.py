from sys import exit
# `config.py` is the new Python configuration source. The defensive loaders
# below push every UPPERCASE non-empty constant into os.environ and provide
# a snapshot helper -- both work whether the user kept the full template
# `config.py` or wrote a minimal Colab-style one with just BOT_TOKEN etc.
import config as _bot_config  # noqa: F401  (side-effect import)
from dotenv import load_dotenv, dotenv_values
from logging import (
    FileHandler,
    StreamHandler,
    INFO,
    basicConfig,
    error as log_error,
    info as log_info,
    getLogger,
    ERROR,
)
from os import path, environ, remove


def _push_config_to_environ(mod):
    """Push UPPERCASE, non-empty, non-callable attrs of *mod* into os.environ.

    Skips empty strings / None so downstream `environ.get(KEY, default)`
    falls back to the in-code default and we never crash on int('')."""
    for _k in dir(mod):
        if not _k.isupper() or _k.startswith("_"):
            continue
        _v = getattr(mod, _k)
        if callable(_v) or _v is None:
            continue
        _t = str(_v)
        if _t == "":
            continue
        environ[_k] = _t


def _config_settings_dict():
    """Snapshot all UPPERCASE constants of the user `config.py` to a dict."""
    fn = getattr(_bot_config, "settings_to_dict", None)
    if callable(fn):
        return fn()
    out = {}
    for _k in dir(_bot_config):
        if not _k.isupper() or _k.startswith("_"):
            continue
        _v = getattr(_bot_config, _k)
        if callable(_v):
            continue
        out[_k] = "" if _v is None else str(_v)
    return out


_push_config_to_environ(_bot_config)
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from subprocess import run as srun

getLogger("pymongo").setLevel(ERROR)

if path.exists("log.txt"):
    with open("log.txt", "r+") as f:
        f.truncate(0)

if path.exists("rlog.txt"):
    remove("rlog.txt")

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

# Optional legacy fallback: if `config.env` is still around, load it on top
# of the values that `config.py` already populated. New deployments only need
# `config.py`.
if path.exists("config.env"):
    load_dotenv("config.env", override=True)

try:
    if bool(environ.get("_____REMOVE_THIS_LINE_____")):
        log_error("The README.md file there to be read! Exiting now!")
        exit(1)
except:
    pass

BOT_TOKEN = environ.get("BOT_TOKEN", "")
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

BOT_ID = BOT_TOKEN.split(":", 1)[0]

DATABASE_URL = environ.get("DATABASE_URL", "")
if len(DATABASE_URL) == 0:
    DATABASE_URL = None

if DATABASE_URL is not None:
    try:
        conn = MongoClient(DATABASE_URL, server_api=ServerApi("1"))
        db = conn.mltb
        old_config = db.settings.deployConfig.find_one({"_id": BOT_ID})
        config_dict = db.settings.config.find_one({"_id": BOT_ID})
        if old_config is not None:
            del old_config["_id"]
        # Compare against the active deploy config. Use config.env's values
        # when that file exists (legacy installs), otherwise pull the snapshot
        # from config.py.
        if path.exists("config.env"):
            _active_deploy_config = dict(dotenv_values("config.env"))
        else:
            _active_deploy_config = _config_settings_dict()
        if (
            old_config is not None
            and old_config == _active_deploy_config
            or old_config is None
        ) and config_dict is not None:
            environ["UPSTREAM_REPO"] = config_dict["UPSTREAM_REPO"]
            environ["UPSTREAM_BRANCH"] = config_dict["UPSTREAM_BRANCH"]
        conn.close()
    except Exception as e:
        log_error(f"Database ERROR: {e}")

UPSTREAM_REPO = environ.get("UPSTREAM_REPO", "")
if len(UPSTREAM_REPO) == 0:
    UPSTREAM_REPO = None

UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "")
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = "master"

if UPSTREAM_REPO is not None:
    if path.exists(".git"):
        srun(["rm", "-rf", ".git"])

    update = srun(
        [
            f"git init -q \
                     && git config --global user.email e.anastayyar@gmail.com \
                     && git config --global user.name mltb \
                     && git add . \
                     && git commit -sm update -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q"
        ],
        shell=True,
    )

    if update.returncode == 0:
        log_info("Successfully updated with latest commit from UPSTREAM_REPO")
    else:
        log_error(
            "Something went wrong while updating, check UPSTREAM_REPO if valid or not!"
        )
