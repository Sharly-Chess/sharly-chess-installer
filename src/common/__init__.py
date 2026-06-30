import importlib.metadata
import logging
import sys
from pathlib import Path

from packaging.version import Version

APP_NAME = 'sharly-chess-installer'
APP_VERSION = Version(importlib.metadata.version(APP_NAME))

logger = logging.getLogger(__name__)

DEV_ENV = not getattr(sys, 'frozen', False)

def _app_base_dir() -> Path:
    """
    Return the directory that holds bundled resources (project root with pyproject.toml):
      - Dev:      repo/source tree (where pyproject.toml is)
      - Onefile:  sys._MEIPASS
      - macOS .app onedir: .../My.app/Contents/Resources
      - Linux AppImage: AppDir/usr/share (bundled resources)
      - Other frozen onedir: directory next to the executable
    """

    # PyInstaller onefile
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        return Path(meipass)

    # macOS .app onedir
    try:
        exe = Path(sys.argv[0]).resolve()
        # .../My.app/Contents/MacOS/<exe>
        contents = exe.parent.parent
        if contents.name == 'Contents' and contents.parent.suffix == '.app':
            resources = contents / 'Resources'
            if resources.is_dir():
                return resources
    except Exception:
        pass

    # Other frozen (non-.app) onedir
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent

    # Dev: project / package root (where pyproject.toml is)
    return Path(__file__).resolve().parents[2]

BASE_DIR = _app_base_dir()
DEV_DIR = BASE_DIR / 'test-install'
IMAGES_DIR = BASE_DIR / 'images'

UPDATER_DIR = DEV_DIR if DEV_ENV else BASE_DIR.parent
DEFAULT_INSTALLER_DIR = DEV_DIR if DEV_ENV else Path('C:/') / 'Program Files' / 'Sharly Chess'
