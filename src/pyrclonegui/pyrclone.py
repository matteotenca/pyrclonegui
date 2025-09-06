import json
import logging
import shlex
import subprocess
import time
import datetime
from logging import Logger

from PyQt6.QtCore import QStringListModel, QModelIndex, pyqtSlot, QVariant, QThreadPool
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6 import QtCore
from PyQt6.QtGui import QColor, QCloseEvent
from typing import Optional

from ._qtuicwindow import Ui_MainWindow
from ._table_model import TableModel


class PyRcloneGui(QMainWindow, Ui_MainWindow):

    def __init__(self, **kwargs) -> None:
        super(PyRcloneGui, self).__init__(**kwargs)

        self.setupUi(MainWindow=self)
        self.led.setLightColor(QColor.fromRgb(0, 255, 0))
        self.led.setOn(False)
        self.show()

        self._mlog = Logger(__name__)
        self._mlog.addHandler(logging.FileHandler("r:\\logfile.log",encoding="utf-8"))
        self._mlog.info("")
        self._cmd_quit_server = "rclone rc core/quit"
        self._cmd_quit_server_list = shlex.split(self._cmd_quit_server, posix=False)
        self._cmd_get_pid = "rclone rc core/pid"
        self._cmd_get_pid_list = shlex.split(self._cmd_get_pid, posix=False)
        self._cmd_listremotes = "rclone rc config/listremotes"
        self._cmd_listremotes_list = shlex.split(self._cmd_listremotes, posix=False)
        self._cmd_start_server = "cmd /C rclone -v rcd --rc-no-auth --log-file r:\\rclone.log --no-console"
        self._cmd_start_server_list = shlex.split(self._cmd_start_server, posix=False)
        self._cmd_check_server = "rclone rc core/pid"
        self._cmd_check_server_list = shlex.split(self._cmd_check_server, posix=False)
        self._cmd_mount = "rclone rc mount/mount "
        self._cmd_mount_list = shlex.split(self._cmd_mount, posix=False)
        self._cmd_unmount = "rclone rc mount/unmount "
        self._cmd_unmount_list = shlex.split(self._cmd_unmount, posix=False)
        self._cmd_listmounts = "rclone rc mount/listmounts"
        self._cmd_listmounts_list = shlex.split(self._cmd_listmounts, posix=False)
        self._cmd_set_vfs_main = 'rclone rc options/set --json "' + r"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\" }}" + '"'
        # self._cmd_set_vfs_main = r'rclone rc options/set --json "{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\" }}"'
        # self._cmd_set_vfs_main_list = shlex.split(self._cmd_set_vfs_main, posix=False)
        self._cmd_set_vfs_main_list = ["rclone", "rc", "options/set", "--json", '"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\"}"']

        self._remotes: list[str] = []
        self._two_dim_list: list[list[str]] = [[]]
        self._two_dim_list_r: list[list[str]] = [[]]

        self.remotesActiveList.setModel(TableModel(self._two_dim_list_r))
        self.remotesInactiveList.setModel(TableModel(self._two_dim_list))
        self._col_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
        self._col_list_cpy = self._col_list
        self.threadpool = QThreadPool()

        ress = self.async_send_cmd(self._cmd_check_server_list)
        if ress:
            self.serverToggleButton.setChecked(True)

    @pyqtSlot()
    def move_element_right(self) -> None:

        model: TableModel = self.remotesInactiveList.model()
        current_index: QModelIndex = self.remotesInactiveList.currentIndex()
        current_row: QModelIndex = model.index(current_index.row(), 0)
        current_row2: QModelIndex = model.index(current_index.row(), 1)
        data = model.data(current_row)
        data2 = model.data(current_row2)
        if data is None or data2 is None or isinstance(data, QVariant) or isinstance(data2, QVariant):
            return
        ress = self.async_send_cmd(self._cmd_mount_list + [f"fs={data}:"] + [f"mountPoint={data2}:"], shell=False, capture_output=True)
        if not ress:
            msg = f"Mounting {data} on {data2}: returned failure"
            title = "Warning!"
            alert = QMessageBox()
            alert.warning(self, title, msg, QMessageBox.StandardButton.Ok)
            return

        model.removeRow(current_index.row())

        new_data = [list(a) for a in zip([data], [data2])]
        self._two_dim_list_r.extend(new_data)
        if len(self._two_dim_list_r[0]) == 0:
            self._two_dim_list_r.pop(0)
        self.remotesActiveList.setModel(TableModel(self._two_dim_list_r))
        self.remotesInactiveList.setModel(model)
        self.remotesInactiveList.update()
        self.remotesActiveList.update()

    @pyqtSlot()
    def move_element_left(self) -> None:

        model: TableModel = self.remotesInactiveList.model()
        active_model: TableModel = self.remotesActiveList.model()
        current_index: QModelIndex = self.remotesActiveList.currentIndex()
        current_row: QModelIndex = active_model.index(current_index.row(), 0)
        current_row2: QModelIndex = active_model.index(current_index.row(), 1)
        data = active_model.data(current_row)
        data2 = active_model.data(current_row2)
        if data is None or data2 is None or isinstance(data, QVariant) or isinstance(data2, QVariant):
            return
        ress = self.async_send_cmd(self._cmd_unmount_list + [f"mountPoint={data2}:"], shell=False, capture_output=True)
        if not ress:
            msg = f"Unmounting {data} on {data2}: returned failure"
            title = "Warning!"
            alert = QMessageBox()
            alert.warning(self, title, msg, QMessageBox.StandardButton.Ok)
            return
        active_model.removeRow(current_index.row())

        model_len = model.rowCount()

        model_index = model.createIndex(model_len, 0)
        model_index2 = model.createIndex(model_len, 1)
        model.insertRow(model_len)

        model.setData(model_index, data, QtCore.Qt.ItemDataRole.EditRole)
        model.setData(model_index2, data2, QtCore.Qt.ItemDataRole.EditRole)
        self.remotesInactiveList.setModel(model)
        self.remotesInactiveList.update()
        self.remotesActiveList.setModel(active_model)
        self.remotesActiveList.update()


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
        led  = self.led
        if led.isOn() != b:
            if not b:
                ress = self.async_send_cmd(self._cmd_listmounts_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog("listmounts failed")
                else:
                    self.mylog("listmounts succeded")
                if isinstance(ress, dict):
                    mounts = ress.get("mountPoints", [])
                    # mounted = []
                    new_mounts = []
                    for mount in mounts:
                        name = mount.get("Fs", "").rstrip(":")
                        mpoint = mount["MountPoint"].rstrip(":")
                        ress = self.async_send_cmd(self._cmd_unmount_list + [f"mountPoint={mpoint}:"], shell=False, capture_output=True)
                        if not ress:
                            self.mylog(f"Unmounting {name} on {mpoint}: returned failure")
                        # mounted.append(name)
                        # self._remotes.remove(name)
                        # new_mounts.append([name, mpoint])
                ress = self.async_send_cmd(self._cmd_check_server_list, shell=False, capture_output=True)
                if isinstance(ress, list) or ress == True:
                    active_model: QStringListModel = self.remotesActiveList.model()
                    coun = active_model.rowCount()
                    for i in range(coun):
                        index = active_model.index(i, 0)
                        index2 = active_model.index(i, 1)
                        data = index.data()
                        data2 = index2.data()
                        if data is None or data2 is None or isinstance(data, QVariant) or isinstance(data2, QVariant):
                            continue
                        ress = self.async_send_cmd(self._cmd_unmount_list + [f"mountPoint={data2}:"], shell=False, capture_output=True)
                        if not ress:
                            self.mylog(f"Unmounting {data} on {data2}: returned failure")
                ress = self.async_send_cmd(self._cmd_quit_server_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog("stopping server returned failure")
                time.sleep(2)
                self._two_dim_list = [[]]
                self._two_dim_list_r = [[]]
                qt_left_model = TableModel(self._two_dim_list)
                self.remotesInactiveList.setModel(qt_left_model)
                qt_right_model = TableModel(self._two_dim_list_r)
                self.remotesActiveList.setModel(qt_right_model)
                self._col_list = self._col_list_cpy
            else:
                ress = self.async_send_cmd(self._cmd_check_server_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog(self._cmd_start_server)
                    self.async_send_cmd(self._cmd_start_server, shell=True, capture_output=True, skip_waiting=True)
                    self.mylog("server started")
                    time.sleep(3)
                self.mylog(self._cmd_check_server)
                ress = self.async_send_cmd(self._cmd_check_server_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog("check server failed")
                else:
                    self.mylog(self._cmd_set_vfs_main)
                    ress = self.async_send_cmd(self._cmd_set_vfs_main, shell=True, capture_output=True)
                    if not ress:
                        self.mylog("setting vfs/main returned failure")
                    self.mylog(self._cmd_listremotes)
                    ress = self.async_send_cmd(self._cmd_listremotes_list, shell=False, capture_output=True)
                    if not ress:
                        self.mylog("listremotes failed")
                    else:
                        self.mylog(f"list remotes successful, {ress}")
                    self.mylog("getting remotes from json and putting in self._remotes")
                    self._remotes: list = ress.get("remotes", [])
                    self.mylog("extending list")
                    self._col_list.clear()
                    self._col_list.extend(self.get_free_letters())
                    self.mylog(f"ending loop, free letters: {self._col_list}")
                    self.mylog(self._cmd_listmounts)
                    ress = self.async_send_cmd(self._cmd_listmounts_list, shell=False, capture_output=True)
                    if not ress:
                        self.mylog("listmounts failed")
                    else:
                        self.mylog("listmounts succeded")
                    if isinstance(ress, dict):
                        mounts = ress.get("mountPoints", [])
                        # mounted = []
                        new_mounts = []
                        for mount in mounts:
                            name = mount.get("Fs", "").rstrip(":")
                            mpoint = mount["MountPoint"].rstrip(":")
                            # mounted.append(name)
                            self._remotes.remove(name)
                            new_mounts.append([name, mpoint])
                        # self.mylog("mapping")
                        # mapping = dict(zip(self._remotes, self._col_list))
                        self._two_dim_list = [list(a) for a in zip(self._remotes, self._col_list)]
                        self._two_dim_list_r = new_mounts if len(new_mounts) > 0 else self._two_dim_list_r
                        qt_left_model = TableModel(self._two_dim_list)
                        self.remotesInactiveList.setModel(qt_left_model)
                        qt_right_model = TableModel(self._two_dim_list_r)
                        self.remotesActiveList.setModel(qt_right_model)
        led.setOn(b)


    def left_item_selected(self, i: QModelIndex):
        # TODO: switch to QTableWidget from QTableView
        pass

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
                ress  = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        now = datetime.datetime.fromtimestamp(time.time()).isoformat(" ", timespec="seconds")
        msg = f"{now} {msg}"
        arg: str = ""
        for t in args:
            arg = f"{arg} {t} "
        if len(arg) > 0:
            msg = f"{msg} {arg}"
            msg = msg.strip(" ")
        self._mlog.info(msg)

    def get_free_letters(self) -> list[str]:
        import string
        import win32api
        import win32wnet
        import win32netcon

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
                if len(r.lpLocalName) == 2 and r.lpLocalName[1] == ':':
                    drives.discard(r.lpLocalName[0])
        return sorted(drives)
