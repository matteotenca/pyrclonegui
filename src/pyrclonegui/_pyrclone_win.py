import logging
import shlex
import string
from typing import Optional

import win32api
import win32wnet
import win32netcon
import time

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QVariant, QModelIndex, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMainWindow

from .pyrclone import PyRcloneGui


class PyRcloneGuiWin(PyRcloneGui):
    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        self.setupUi(MainWindow=self)
        self.led.setLightColor(QColor.fromRgb(0, 255, 0))
        self.buttonToLeft.setEnabled(False)
        self.buttonToRight.setEnabled(False)
        self.led.setOn(False)
        self.cmd_set_vfs_main = 'rclone rc options/set --json "' + r"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\" }}" + '"'
        self.cmd_set_vfs_main_list = ["rclone", "rc", "options/set", "--json", '"{\"main\": {\"Progress\": true, \"Transfers\": 16, \"MultiThreadChunkSize\": \"64M\", \"MultiThreadCutoff\": 131072, \"MultiThreadSet\": true, \"MultiThreadStreams\": 8, \"MultiThreadWriteBufferSize\": \"2M\"}, \"vfs\": {\"CacheMaxAge\": \"2m\", \"Links\": true, \"ChunkSize\": \"32M\", \"ChunkSizeLimit\": \"100G\", \"ChunkStreams\": 16, \"FastFingerprint\": true, \"CacheMaxSize\": \"3G\", \"CacheMode\": \"full\", \"Refresh\": true, \"WriteBack\": \"5s\"}"']
        self.mlog = logging.Logger(__name__)
        self.mlog.addHandler(logging.FileHandler("r:\\logfile.log", encoding="utf-8"))
        self.mylog("")
        self.mylog("")
        self.cmd_start_server = "cmd /C rclone -v rcd --rc-no-auth --log-file r:\\rclone.log --no-console"
        self.cmd_start_server_list = shlex.split(self.cmd_start_server, posix=False)

        hheader = self.remotesInactiveList.horizontalHeader()
        hheader.setStretchLastSection(True)
        self.remotesInactiveList.setHorizontalHeader(hheader)
        hheader = self.remotesActiveList.horizontalHeader()
        hheader.setStretchLastSection(True)
        self.remotesActiveList.setHorizontalHeader(hheader)

        ress = self.async_send_cmd(self._cmd_check_server_list)
        if ress:
            self.serverToggleButton.setChecked(True)

    @pyqtSlot(bool)
    def toggle_server(self, b: bool) -> None:
        led  = self.led
        if led.isOn() != b:
            if not b:
                self.mylog(self.cmd_listmounts)
                ress = self.async_send_cmd(self.cmd_listmounts_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog("listmounts failed")
                else:
                    self.mylog("listmounts succeded")
                if isinstance(ress, dict):
                    mounts = ress.get("mountPoints", [])
                    for mount in mounts:
                        name = mount.get("Fs", "").rstrip(":")
                        mpoint = mount["MountPoint"].rstrip(":")
                        ress = self.async_send_cmd(self.cmd_unmount_list + [f"mountPoint={mpoint}:"], shell=False, capture_output=True)
                        if not ress:
                            self.mylog(f"unmounting {name} on {mpoint}: returned failure")
                        else:
                            self.mylog(f"unmounting {name} on {mpoint}: succeded")
                self.mylog(self.cmd_quit_server)
                ress = self.async_send_cmd(self.cmd_quit_server_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog("stopping server returned failure")
                self.empty_lists()
            else:
                ress = self.async_send_cmd(self.cmd_check_server_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog(self.cmd_start_server)
                    self.async_send_cmd(self.cmd_start_server, shell=True, capture_output=True, skip_waiting=True)
                    self.mylog("server started")
                    time.sleep(1)
                self.mylog(self.cmd_check_server)
                ress = self.async_send_cmd(self.cmd_check_server_list, shell=False, capture_output=True)
                if not ress:
                    self.mylog("check server failed")
                else:
                    ress = self.async_send_cmd(self._cmd_set_vfs_main, shell=True, capture_output=True)
                    if not ress:
                        self.mylog("setting vfs/main returned failure")
                self.populate_lists()


        self.remotesInactiveList.resizeColumnsToContents()
        self.remotesActiveList.resizeColumnsToContents()
        led.setOn(b)

    @pyqtSlot()
    def refresh_lists(self) -> None:
        self.empty_lists()
        self.populate_lists()

    def empty_lists(self) -> None:
        self.two_dim_list = [[]]
        self.two_dim_list_r = [[]]
        row_count = self.remotesInactiveList.rowCount()
        for i in range(row_count):
            self.remotesInactiveList.removeRow(0)
        self.remotesInactiveList.update()

        row_count = self.remotesActiveList.rowCount()
        for i in range(row_count):
            self.remotesActiveList.removeRow(0)
        self.remotesActiveList.update()
        self.col_list = self.col_list_cpy

    def populate_lists(self) -> None:
        self.mylog(self.cmd_listremotes)
        ress = self.async_send_cmd(self.cmd_listremotes_list, shell=False, capture_output=True)
        if not ress:
            self.mylog("listremotes failed")
        else:
            self.mylog(f"list remotes successful, {ress}")
        self.mylog("getting remotes from json and putting in self._remotes")

        # tmp = ress.get("remotes", [])
        # self.mylog(f"{tmp}")
        # tmp2 = sorted(tmp, key=cmp_to_key(strcoll))
        # self.mylog(f"{tmp2}")
        # self.remotes = tmp2

        self.remotes = ress.get("remotes", [])
        self.col_list.clear()
        self.col_list.extend(self.get_free_letters)
        self.mylog(self.cmd_listmounts)
        ress = self.async_send_cmd(self.cmd_listmounts_list, shell=False, capture_output=True)
        if not ress:
            self.mylog("listmounts failed")
        else:
            self.mylog("listmounts succeded")
        if isinstance(ress, dict):
            mounts = ress.get("mountPoints", [])
            new_mounts_name = []
            new_mounts_mpoint = []
            for mount in mounts:
                name = mount.get("Fs", "").rstrip(":")
                mpoint = mount["MountPoint"].rstrip(":")
                self.remotes.remove(name)
                new_mounts_name.append(name)
                new_mounts_mpoint.append(mpoint)

            self.two_dim_list = [list(a) for a in zip(self.remotes, self.col_list)]
            temp_list = [list(a) for a in zip(new_mounts_name, new_mounts_mpoint)]
            self.two_dim_list_r.extend(temp_list)
            if len(self.two_dim_list_r[0]) == 0:
                self.two_dim_list_r.pop(0)

            for row in self.two_dim_list:
                pos = self.remotesInactiveList.rowCount()
                self.remotesInactiveList.insertRow(pos)
                self.remotesInactiveList.setItem(pos, 0, QtWidgets.QTableWidgetItem(row[0]))
                self.remotesInactiveList.setItem(pos, 1, QtWidgets.QTableWidgetItem(row[1]))

            for row in temp_list:
                if len(row) == 0:
                    continue
                pos = self.remotesActiveList.rowCount()
                self.remotesActiveList.insertRow(pos)
                self.remotesActiveList.setItem(pos, 0, QtWidgets.QTableWidgetItem(row[0]))
                self.remotesActiveList.setItem(pos, 1, QtWidgets.QTableWidgetItem(row[1]))

    @pyqtSlot()
    def move_element_right(self) -> None:
        current_index: QModelIndex = self.remotesInactiveList.currentIndex()
        widg: QTableWidgetItem = self.remotesInactiveList.item(current_index.row(), 0)
        widg2: QTableWidgetItem = self.remotesInactiveList.item(current_index.row(), 1)
        data = widg.data(QtCore.Qt.ItemDataRole.DisplayRole)
        data2 = widg2.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if data is None or data2 is None or isinstance(data, QVariant) or isinstance(data2, QVariant):
            return
        ress = self.async_send_cmd(self.cmd_mount_list + [f"fs={data}:"] + [f"mountPoint={data2}:"], shell=False, capture_output=True)
        if not ress:
            self.mylog(f"mounting {data} on {data2}: returned failure")
        else:
            self.remotesInactiveList.removeRow(current_index.row())
            new_data = [list(a) for a in zip([data], [data2])]
            self.two_dim_list_r.extend(new_data)
            if len(self.two_dim_list_r[0]) == 0:
                self.two_dim_list_r.pop(0)

            for dt in new_data:
                model_len = self.remotesActiveList.rowCount()
                self.remotesActiveList.insertRow(model_len)
                self.remotesActiveList.setItem(model_len, 0, QtWidgets.QTableWidgetItem(dt[0]))
                self.remotesActiveList.setItem(model_len, 1, QtWidgets.QTableWidgetItem(dt[1]))

            self.remotesInactiveList.sortItems(1, QtCore.Qt.SortOrder.AscendingOrder)
            self.remotesActiveList.sortItems(1, QtCore.Qt.SortOrder.AscendingOrder)
            self.remotesInactiveList.resizeColumnsToContents()
            self.remotesActiveList.resizeColumnsToContents()
            self.remotesInactiveList.update()
            self.remotesActiveList.update()

    @pyqtSlot()
    def move_element_left(self) -> None:
        current_index: QModelIndex = self.remotesActiveList.currentIndex()
        widg: QTableWidgetItem = self.remotesActiveList.item(current_index.row(), 0)
        widg2: QTableWidgetItem = self.remotesActiveList.item(current_index.row(), 1)
        data = widg.data(QtCore.Qt.ItemDataRole.DisplayRole)
        data2 = widg2.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if data is None or data2 is None or isinstance(data, QVariant) or isinstance(data2, QVariant):
            return
        self.mylog(self.cmd_unmount)
        ress = self.async_send_cmd(self.cmd_unmount_list + [f"mountPoint={data2}:"], shell=False, capture_output=True)
        if not ress:
            self.mylog(f"unmounting {data} on {data2}: returned failure")
        else:
            self.mylog(f"unmounting {data} on {data2}: returned success")
        self.remotesActiveList.removeRow(current_index.row())

        model_len = self.remotesInactiveList.rowCount()
        self.remotesInactiveList.insertRow(model_len)
        self.remotesInactiveList.setItem(model_len, 0, QtWidgets.QTableWidgetItem(data))
        self.remotesInactiveList.setItem(model_len, 1, QtWidgets.QTableWidgetItem(data2))
        self.remotesInactiveList.sortItems(1, QtCore.Qt.SortOrder.AscendingOrder)
        self.remotesActiveList.sortItems(1, QtCore.Qt.SortOrder.AscendingOrder)
        self.remotesInactiveList.resizeColumnsToContents()
        self.remotesActiveList.resizeColumnsToContents()
        self.remotesInactiveList.update()
        self.remotesActiveList.update()

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
                if len(r.lpLocalName) == 2 and r.lpLocalName[1] == ':':
                    drives.discard(r.lpLocalName[0])
        return sorted(drives)
