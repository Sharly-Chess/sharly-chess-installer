import asyncio
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import toga
from packaging.version import Version
from travertino.constants import COLUMN

from common import UPDATER_DIR, APP_VERSION, IMAGES_DIR, logger
from common.i18n import _
from version_installer.installer import VersionInstaller


class UpdaterApp(toga.App):
    def __init__(
        self,
        version: Version | None = None,
        check_beta: bool = False,
    ):
        icon_ext = 'ico' if sys.platform == 'win32' else 'icns'
        super().__init__(
            formal_name='Sharly Chess Updater',
            app_id='com.sharlychessupdater.app',
            icon=IMAGES_DIR / f'sharly-chess.{icon_ext}',
            version=str(APP_VERSION),
            home_page='https://sharly-chess.com',
        )
        self.sc_version = version
        self.check_beta = check_beta

        # Loops
        self.gui_loop = asyncio.get_event_loop()
        self.installer_loop = asyncio.SelectorEventLoop()

        # Widgets
        self.main_box: Optional[toga.Box] = None
        self.install_progress_bar: Optional[toga.ProgressBar] = None
        self.progress_label: Optional[toga.Label] = None

    def startup(self):
        self.progress_label = toga.Label(
            _('Installer startup...'),
            width=400,
        )
        self.install_progress_bar = toga.ProgressBar(max=100)
        self.main_box = toga.Box(direction=COLUMN, margin=10)
        self.main_box.add(
            self.progress_label,
            self.install_progress_bar,
        )
        self.main_window = toga.Window(
            title=_('Sharly Chess update'),
            size=(400,100),
            content=self.main_box,
            resizable=False,
        )
        self.main_window.show()

    def on_running(self):
        assert self.progress_label is not None
        assert self.install_progress_bar is not None

        self.install_progress_bar.value = 1
        self.install_progress_bar.start()
        self._install_version()


    def _install_version(self):
        def set_status(status: str):
            self.progress_label.text = status
            print(status)

        def set_progress(progress: float):
            self.install_progress_bar.value = progress

        VersionInstaller.install_version(
            install_dir=UPDATER_DIR,
            set_progress=set_progress,
            set_status=set_status,
            version=self.sc_version,
            check_beta=self.check_beta,
        )



