import json
import platform
import shlex
import shutil
import subprocess
import time
import datetime
from logging import Logger

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtGui import QCloseEvent
from typing import Optional, Any

from ._qtuicwindow import Ui_MainWindow


class PyRcloneGui(QMainWindow, Ui_MainWindow):

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super(PyRcloneGui, self).__init__(parent)
        self.system = platform.system().lower() == "windows"
        self._mlog: Optional[Logger] = None
        self.rclone = shutil.which("rclone")
        self._cmd_quit_server = f"{self.rclone} rc core/quit"
        self._cmd_quit_server_list = shlex.split(self._cmd_quit_server, posix=not self.system)
        self._cmd_get_pid = f"{self.rclone} rc core/pid"
        self._cmd_get_pid_list = shlex.split(self._cmd_get_pid, posix=not self.system)
        self._cmd_listremotes = f"{self.rclone} rc config/listremotes"
        self._cmd_listremotes_list = shlex.split(self._cmd_listremotes, posix=not self.system)
        self._cmd_start_server: Optional[str] = None
        self._cmd_start_server_list: Optional[list[str]] = None
        self._cmd_check_server = f"{self.rclone} rc core/pid"
        self._cmd_check_server_list = shlex.split(self._cmd_check_server, posix=not self.system)
        self._cmd_mount = f"{self.rclone} rc mount/mount "
        self._cmd_mount_list = shlex.split(self._cmd_mount, posix=not self.system)
        self._cmd_unmount = f"{self.rclone} rc mount/unmount "
        self._cmd_unmount_list = shlex.split(self._cmd_unmount, posix=not self.system)
        self._cmd_listmounts = f"{self.rclone} rc mount/listmounts"
        self._cmd_listmounts_list = shlex.split(self._cmd_listmounts, posix=not self.system)

        self._cmd_set_vfs_main: Optional[str] = None
        self._cmd_set_vfs_main_list: Optional[list[str]] = None
        self._remotes: list[str] = []
        self._two_dim_list: list[list[str]] = [[]]
        self._two_dim_list_r: list[list[str]] = [[]]

        self._col_list = []
        self._col_list_cpy = self._col_list

        self.creationflags = {}
        if self.system:
            self.creationflags = {"creationflags": subprocess.CREATE_NO_WINDOW}
        # self.system = {"creationflags": subprocess.CREATE_NO_WINDOW} if platform.system().lower() == "windows" else {}

    @pyqtSlot()
    def move_element_right(self) -> None:
        pass

    @pyqtSlot()
    def move_element_left(self) -> None:
        pass

    def closeEvent(self, event: Optional[QCloseEvent]) -> None:

        # res = subprocess.run(self._cmd_check_server, shell=True, capture_output=True)
        # if res.returncode == 0:
        #     active_model: QStringListModel = self.remotesActiveList.model()
        #     coun = active_model.rowCount()
        #     for i in range(coun):
        #         index = active_model.index(i, 0)
        #         index2 = active_model.index(i, 1)
        #         element = index.data()
        #         element2 = index2.data()
        #         res = subprocess.run(self._cmd_unmount + f"mountPoint={element2}:", shell=True, capture_output=True)
        #         if res.returncode != 0:
        #             msg = f"Unmounting '{element}' from {element2}: returned failure"
        #             title = "Warning!"
        #             alert = QMessageBox()
        #             r = alert.warning(self, title, msg, QMessageBox.StandardButton.Ok)
        #     res = subprocess.run(self._cmd_quit_server, shell=True, capture_output=True)
        #     if res.returncode != 0:
        #         msg = "Stopping server returned failure"
        #         title = "Warning!"
        #         alert = QMessageBox()
        #         r = alert.warning(self, title, msg, QMessageBox.StandardButton.Ok)
        if event:
            event.accept()

    @pyqtSlot(bool)
    def toggle_server(self, b: bool) -> None:
        pass

    @pyqtSlot()
    def left_item_sel_changed(self) -> None:
        sel = self.remotesInactiveList.selectedItems()
        if len(sel) > 0:
            self.buttonToRight.setEnabled(True)
        else:
            self.buttonToRight.setEnabled(False)

    @pyqtSlot()
    def right_item_sel_changed(self) -> None:
        sel = self.remotesActiveList.selectedItems()
        if len(sel) > 0:
            self.buttonToLeft.setEnabled(True)
        else:
            self.buttonToLeft.setEnabled(False)

    @staticmethod
    def send_cmd(cmd: list, shell: bool= False, capture_output: bool = True) -> bool:
        retcode = False
        ress = subprocess.run(cmd, shell=shell, capture_output=capture_output)
        if ress.returncode == 0:
            retcode = True
        return retcode

    def async_send_cmd(self, cmd: list | str, shell: bool= False, capture_output: bool = True, skip_waiting: bool = False) -> bool | dict[str, int]:
        outs = False
        ress:  subprocess.Popen | None = None
        try:
            if not capture_output:
                ress = subprocess.Popen(cmd, shell=shell)
                ress.wait(timeout=15)
                if ress.returncode != 0:
                    return outs
            else:
                self.mylog(f"{cmd}")
                ress  = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **self.creationflags)
                if not skip_waiting and ress is not None:
                    ress.wait(timeout=15)
                    if ress.returncode == 0:
                        outs = True
                    outst, errs = ress.communicate(timeout=15)
                    try:
                        outs_json = json.loads(outst)
                        if "error" not in outs_json.keys() and errs.find("Failed") == -1 and len(outs_json) > 0:
                            outs = outs_json
                    except json.decoder.JSONDecodeError as e:
                        self.mylog(f"{e}")
                        return False
                else:
                    outs = True
        except subprocess.TimeoutExpired as e:
            if ress:
                ress.kill()
            return False
        except Exception as e:
            raise Exception from e

        return outs

    def mylog(self, msg: str, *args) -> None:
        if self._mlog is None:
            return
        now = datetime.datetime.fromtimestamp(time.time()).isoformat(" ", timespec="seconds")
        msg = f"{now} {msg}"
        arg: str = ""
        for t in args:
            arg = f"{arg} {t} "
        if len(arg) > 0:
            msg = f"{msg} {arg}"
            msg = msg.strip(" ")
        self._mlog.info(msg)

    @property
    def cmd_listmounts(self) -> str:
        return self._cmd_listmounts

    @property
    def cmd_listmounts_list(self) -> list[str]:
        return self._cmd_listmounts_list

    @property
    def cmd_unmount_list(self) -> list[str]:
        return self._cmd_unmount_list

    @property
    def cmd_quit_server(self) -> str:
        return self._cmd_quit_server

    @property
    def cmd_quit_server_list(self) -> list[str]:
        return self._cmd_quit_server_list

    @property
    def col_list_cpy(self) -> list[Any]:
        return self._col_list_cpy

    @property
    def cmd_check_server_list(self) -> list[str]:
        return self._cmd_check_server_list

    @property
    def cmd_start_server(self) -> str | None:
        return self._cmd_start_server
    @cmd_start_server.setter
    def cmd_start_server(self, value) -> None:
        self._cmd_start_server = value

    @property
    def cmd_start_server_list(self) -> list[str] | None:
        return self._cmd_start_server_list
    @cmd_start_server_list.setter
    def cmd_start_server_list(self, value) -> None:
        self._cmd_start_server_list = value

    @property
    def cmd_check_server(self) -> str:
        return self._cmd_check_server

    @property
    def cmd_listremotes(self) -> str:
        return self._cmd_listremotes

    @property
    def cmd_listremotes_list(self) -> list[str]:
        return self._cmd_listremotes_list

    @property
    def cmd_mount_list(self) -> list[str]:
        return self._cmd_mount_list

    @property
    def cmd_mount(self) -> str:
        return self._cmd_mount

    @property
    def col_list(self) -> list[Any]:
        return self._col_list
    @col_list.setter
    def col_list(self, value) -> None:
        self._col_list = value

    @property
    def remotes(self) -> list[str]:
        return self._remotes
    @remotes.setter
    def remotes(self, remotes) -> None:
        self._remotes = remotes

    @property
    def two_dim_list_r(self) -> list[list[str]]:
        return self._two_dim_list_r
    @two_dim_list_r.setter
    def two_dim_list_r(self, value) -> None:
        self._two_dim_list_r = value

    @property
    def two_dim_list(self) -> list[list[str]]:
        return self._two_dim_list
    @two_dim_list.setter
    def two_dim_list(self, value) -> None:
        self._two_dim_list = value

    @property
    def cmd_unmount(self) -> str:
        return self._cmd_unmount

    @property
    def cmd_set_vfs_main(self) -> str | None:
        return self._cmd_set_vfs_main
    @cmd_set_vfs_main.setter
    def cmd_set_vfs_main(self, value) -> None:
        self._cmd_set_vfs_main = value

    @property
    def cmd_set_vfs_main_list(self) -> list[str] | None:
        return self._cmd_set_vfs_main_list
    @cmd_set_vfs_main_list.setter
    def cmd_set_vfs_main_list(self, value) -> None:
        self._cmd_set_vfs_main_list = value

    @property
    def mlog(self) -> Logger | None:
        return self._mlog
    @mlog.setter
    def mlog(self, value) -> None:
        self._mlog = value
