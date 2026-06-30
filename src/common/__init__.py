import importlib.metadata
import logging
import sys

from packaging.version import Version

APP_NAME = 'sharly-chess-installer'
APP_VERSION = Version(importlib.metadata.version(APP_NAME))

DEV_ENV = not getattr(sys, 'frozen', False)

logger = logging.getLogger(__name__)