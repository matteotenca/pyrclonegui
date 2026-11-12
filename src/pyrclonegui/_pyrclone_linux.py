import logging
import shlex
import shutil
import tempfile
from typing import Optional
from pathlib import Path

import httpx
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QMainWindow

from .pyrclone import PyRcloneGui


class PyRcloneGuiLin(PyRcloneGui):
    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        self.setupUi(MainWindow=self)
        self.led.setLightColor(QColor.fromRgb(0, 255, 0))
        self.led.setOn(False)
        self.creationflags = {}
        self.mlog = logging.Logger(__name__)
        temp_log: str = f"{Path(tempfile.gettempdir()).joinpath('pyrclonegui.log').absolute()}"
        self.mlog.addHandler(logging.FileHandler(temp_log, encoding="utf-8"))
        self.mylog("")
        self.mylog("")
        self.rclone = shutil.which("rclone")

        temp: str = f"{Path(tempfile.gettempdir()).joinpath('rclone.log').absolute()}"
        temp2 = Path(tempfile.gettempdir()).joinpath('rclone_cache').absolute()
        temp2.mkdir(exist_ok=True)
        self.cmd_start_server = f"{self.rclone} -v --cache-dir {temp2} rcd --rc-no-auth --log-file {temp}"
        self.cmd_start_server_list = shlex.split(self.cmd_start_server, posix=True)


        self.cmd_set_vfs_main = 'rclone rc options/set --json "' + r"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\" }}" + '"'
        # self.cmd_set_vfs_main_list = ["rclone", "rc", "options/set", "--json", '"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\"}"']
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

        # self.remotesInactiveList.resizeColumnsToContents()

        self.client = httpx.Client()
        self.mylog("cheking if server is up")
        b, js = self.net_send_cmd(self.net_cmd_check_server, {}, timeout=3)
        if b:
            self.mylog("server is up, update gui")
            self.serverToggleButton.setChecked(True)
        else:
            self.mylog("server is down, gui not changed")
        # self.cmd_start_server_list = shlex.split(self.cmd_start_server, posix=True)
        # ress = self.async_send_cmd(self._cmd_check_server_list)
        # if ress:
        #     self.serverToggleButton.setChecked(True)

    def _default_mount_point(self, name: str, taken: set[str]) -> str:
        return f"/tmp/{name}"

    def _prepare_mount(self, mp: str) -> None:
        p = Path(mp)
        if not p.is_dir():
            p.mkdir()
