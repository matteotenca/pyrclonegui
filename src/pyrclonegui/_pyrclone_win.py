import logging
import shlex
import shutil
import string
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import win32api
import win32netcon
import win32wnet
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QMainWindow

from .pyrclone import PyRcloneGui


class PyRcloneGuiWin(PyRcloneGui):
    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        self.setupUi(MainWindow=self)
        self.led.setLightColor(QColor.fromRgb(0, 255, 0))
        self.led.setOn(False)
        self.creationflags = {"creationflags": subprocess.CREATE_NO_WINDOW}
        self.mlog = logging.Logger(__name__)
        templog: str = f"{Path(tempfile.gettempdir()).joinpath('pyrclonegui.log').absolute()}"
        self.mlog.addHandler(logging.FileHandler(templog, encoding="utf-8"))
        self.mlog.info("")
        self.mlog.info("")
        # noinspection PyDeprecation
        self.rclone = shutil.which("rclone.exe")

        # self.cmd_set_vfs_main = 'rclone rc options/set --json "' + r"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 16, \"MultiThreadWriteBufferSize\": \"20M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"30G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\" }}" + '"'
        # self.cmd_set_vfs_main_list = ["rclone", "rc", "options/set", "--json",
        #                               '"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\"}"']

        temp: str = f"{Path(tempfile.gettempdir()).joinpath('rclone.log').absolute()}"
        temp2 = Path(tempfile.gettempdir()).joinpath('rclone_cache').absolute()
        temp2.mkdir(exist_ok=True)
        self.cmd_start_server = f"{self.rclone} --cache-dir {temp2} rcd --rc-no-auth --log-file {temp} --no-console --log-level INFO"
        self.cmd_start_server_list = shlex.split(self.cmd_start_server, posix=False)
        self.cmd_set_vfs_main = f'{self.rclone} rc options/set --json "' + r"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 16, \"MultiThreadWriteBufferSize\": \"20M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"30G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\" }}" + '"'
        # self.cmd_set_vfs_main_list = [{self.rclone}, "rc", "options/set", "--json",
        #                               '"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\"}"']
        self.net_cmd_vfs_main = {
            "main": {"Progress": True,
                     "Transfers": 16,
                     "MultiThreadChunkSize": "64M",
                     "MultiThreadCutoff": 131072,
                     "MultiThreadSet": True,
                     "MultiThreadStreams": 16,
                     "MultiThreadWriteBufferSize": "20M"},
            "vfs": {"CacheMaxAge": "2m",
                    "Links": True,
                    "ChunkSize": "32M",
                    "ChunkSizeLimit": "100G",
                    "ChunkStreams": 16,
                    "FastFingerprint": True,
                    "CacheMaxSize": "30G",
                    "CacheMode": "full",
                    "Refresh": True,
                    "WriteBack": "5s"}}
        self.server_start_delay = 2.0
        self.client = httpx.Client()
        self.mylog("cheking if server is up")
        b, js = self.net_send_cmd(self.net_cmd_check_server, {}, timeout=1)
        if b:
            self.mylog("server is up, update gui")
            self.serverToggleButton.setChecked(True)
        else:
            self.mylog("server is down, gui not changed")

        # ress = self.async_send_cmd(self._cmd_check_server_list)
        # if ress:
        #     self.serverToggleButton.setChecked(True)

    def _mp_arg(self, mp: str) -> str:
        return f"{mp}:"

    def _default_mount_point(self, name: str, taken: set[str]) -> str:
        return next((letter for letter in self.get_free_letters if letter not in taken), "")

    @property
    def get_free_letters(self) -> list[str]:
        drives = set(string.ascii_uppercase[2:])
        for d in win32api.GetLogicalDriveStrings().split(':\\\x00'):
            drives.discard(d)
        # Discard persistent network drives, even if not connected.
        henum = win32wnet.WNetOpenEnum(win32netcon.RESOURCE_REMEMBERED,
                                       win32netcon.RESOURCETYPE_DISK, 0, win32wnet.NETRESOURCE())
        while True:
            result = win32wnet.WNetEnumResource(henum)
            if not result:
                break
            for r in result:
                if isinstance(r.lpLocalName, str) and len(r.lpLocalName) == 2 and r.lpLocalName[1] == ':':
                    drives.discard(r.lpLocalName[0])
        return sorted(drives)
