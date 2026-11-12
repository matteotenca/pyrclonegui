import json
from functools import cmp_to_key
from locale import strcoll
import subprocess
import tempfile
import time
from pathlib import Path
import datetime
from urllib.parse import urljoin
from logging import Logger

import httpx
from PyQt6.QtCore import pyqtSlot, Qt, QEvent, QPoint, QSettings, QTimer, QUrl
from PyQt6.QtWidgets import (QMainWindow, QApplication, QHBoxLayout, QHeaderView, QMenu, QPushButton, QStyle,
                             QSystemTrayIcon, QTableWidgetItem, QWidget)
from PyQt6.QtGui import QCloseEvent, QColor, QDesktopServices, QShowEvent
from typing import Optional, Union, Dict, List, Tuple, Sequence

from ._qtuicwindow import Ui_MainWindow
from ._theme import app_icon, palette, qss

SETTINGS_ORG = "pyrclonegui"
SETTINGS_APP = "pyrclonegui"


class PyRcloneGui(QMainWindow, Ui_MainWindow):
    tray: Optional[QSystemTrayIcon] = None
    server_start_delay = 1.0  # seconds to wait after launching rclone
    _dark = False
    _notice_until = 0.0  # monotonic time until which a _notify() message stays in the status bar

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super(PyRcloneGui, self).__init__(parent)
        self.base_url = "http://127.0.0.1:5572"
        # self.system = platform.system().lower() == "windows"
        # self.rclone = shutil.which("rclone")

        self.net_cmd_quit_server = urljoin(self.base_url, "core/quit")
        self.net_cmd_get_pid = urljoin(self.base_url, "core/pid")
        self.net_cmd_set_options = urljoin(self.base_url, "options/set")
        self.net_cmd_check_server = self.net_cmd_get_pid
        self.net_cmd_listremotes = urljoin(self.base_url, "config/listremotes")
        self.net_cmd_mount = urljoin(self.base_url, "mount/mount")
        self.net_cmd_unmount = urljoin(self.base_url, "mount/unmount")
        self.net_cmd_listmounts = urljoin(self.base_url, "mount/listmounts")

        self.cmd_start_server: str
        self.cmd_start_server_list: Optional[list[str]] = None
        self.mlog: Optional[Logger] = None
        self.remotes: List = []  # type: ignore[type-arg]
        self.mounts: Dict[str, str] = {}   # remote -> mount point of mounted remotes
        self.planned: Dict[str, str] = {}  # remote -> mount point chosen for the next mount
        # self.col_list_cpy = self.col_list
        self.client: Optional[httpx.Client] = None
        self.creationflags: Dict = {} # type: ignore[type-arg]
        # self.cmd_set_vfs_main: Optional[str] = None
        # self.cmd_set_vfs_main_list: Optional[list[str]] = None
        self.server: Optional(subprocess.Popen[str]) = None
        # if self.system:
        #     self.creationflags = {"creationflags": subprocess.CREATE_NO_WINDOW}
        # self.system = {"creationflags": subprocess.CREATE_NO_WINDOW} if platform.system().lower() == "windows" else {}

    def setupUi(self, MainWindow: QMainWindow) -> None:
        super().setupUi(MainWindow)  # type: ignore[no-untyped-call]
        self._polish()

    # ---- platform hooks, overridden by the OS classes ----
    def _fs_arg(self, name: str) -> str:
        return f"{name}:"

    def _mp_arg(self, mp: str) -> str:
        return mp

    def _default_mount_point(self, name: str, taken: set[str]) -> str:
        raise NotImplementedError

    def _prepare_mount(self, mp: str) -> None:
        """Raise OSError when the mount point cannot be prepared."""

    # ---- window setup ----
    def _polish(self) -> None:
        # Layout, menus, actions and the log dock come from pyrclonegui_4.ui.
        # Only what the .ui cannot express lives here: style icons, header sizing, tray, saved settings.
        style = self.style()
        assert style is not None
        self.refreshButton.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.setWindowIcon(app_icon())  # type: ignore[no-untyped-call]
        table = self.remotesTable
        header = table.horizontalHeader()
        assert header is not None
        rm = QHeaderView.ResizeMode
        for col, mode in enumerate((rm.ResizeToContents, rm.Stretch, rm.ResizeToContents, rm.Fixed)):
            header.setSectionResizeMode(col, mode)
        header.setMinimumSectionSize(110)
        header.resizeSection(3, 132)  # fixed: cell widgets do not feed ResizeToContents
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        vheader = table.verticalHeader()
        assert vheader is not None
        vheader.setDefaultSectionSize(42)
        table.itemChanged.connect(self._mp_edited)
        self.menuView.insertAction(self.actionDarkMode, self.logDock.toggleViewAction())
        self.logDock.hide()
        self.logDock.visibilityChanged.connect(lambda _visible: QTimer.singleShot(0, self._fit_height))
        self._rclone_log = Path(tempfile.gettempdir()) / "rclone.log"  # same file as --log-file in subclasses
        self._rclone_log_pos = self._rclone_log.stat().st_size if self._rclone_log.exists() else 0
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._tail_rclone_log)
        self._log_timer.start(500)
        self._build_tray()
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("state")  # log dock: visibility, floating, position, size
        if state is not None:
            self.restoreState(state)
        dark = settings.value("dark", False, type=bool)
        self.actionDarkMode.setChecked(bool(dark))
        self.set_dark(bool(dark))
        self.server_state_changed()

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        style = self.style()
        assert style is not None
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = QMenu(self)
        menu.addAction("Show", self._restore_from_tray)
        menu.addAction(self.actionServer)
        menu.addAction("Quit", self.close)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._restore_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()

    def showEvent(self, event: Optional[QShowEvent]) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_height)

    def _fit_height(self) -> None:
        # Max height = the window that shows every row (at least 5 rows, so an empty list is not tiny).
        # Using the delta to the current table height keeps this correct whatever else the window holds.
        table = self.remotesTable
        header, vheader = table.horizontalHeader(), table.verticalHeader()
        assert header is not None and vheader is not None
        wanted = header.height() + vheader.defaultSectionSize() * max(len(self.remotes), 5) + 2 * table.frameWidth() + 4  # +4: QSS border
        self.setMaximumHeight(max(self.minimumHeight(), self.height() + wanted - table.height()))

    def changeEvent(self, event: Optional[QEvent]) -> None:
        super().changeEvent(event)
        if event is not None and event.type() == QEvent.Type.WindowStateChange and self.isMinimized() \
                and self.tray is not None:
            self.hide()  # minimize to tray

    @pyqtSlot(bool)
    def server_state_changed(self, _on: bool = False) -> None:
        # Read the button, not the argument: a failed start unchecks it from inside toggle_server.
        on = self.serverToggleButton.isChecked()
        self.serverToggleButton.setText("Stop server" if on else "Start server")
        self.serverStatusLabel.setText("Server running" if on else "Server stopped")
        self.actionServer.setChecked(on)
        for w in (self.refreshButton, self.mountAllButton, self.unmountAllButton, self.filterEdit,
                  self.actionRefresh, self.actionMountAll, self.actionUnmountAll):
            w.setEnabled(on)
        if self.tray is not None:
            self.tray.setToolTip("pyRCloneGui: server " + ("running" if on else "stopped"))
        if not on:
            self.statusbar.showMessage("Server stopped. Press Start server.")

    @pyqtSlot(bool)
    def set_dark(self, on: bool) -> None:
        self._dark = on
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(qss(on))
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("dark", on)
        self._render()

    # ---- remote table ----
    def _render(self) -> None:
        table = self.remotesTable
        colors = palette(self._dark)
        read_only = ~Qt.ItemFlag.ItemIsEditable
        table.blockSignals(True)
        table.clearContents()
        table.setRowCount(len(self.remotes))
        for row, name in enumerate(self.remotes):
            mounted = name in self.mounts
            status = QTableWidgetItem("\u25cf Mounted" if mounted else "\u25cb Not mounted")
            status.setForeground(QColor(colors["ok"] if mounted else colors["muted"]))
            mount_point = QTableWidgetItem(self.mounts[name] if mounted else self.planned.get(name, ""))
            for col, item in enumerate((status, QTableWidgetItem(name), mount_point)):
                if col > 0:
                    item.setForeground(QColor(colors["text"]))
                if col != 2 or mounted:
                    item.setFlags(item.flags() & read_only)
                table.setItem(row, col, item)
            button = QPushButton("Unmount" if mounted else "Mount")
            button.setProperty("role", "danger" if mounted else "primary")
            button.clicked.connect(lambda _checked=False, n=name: self.toggle_mount(n))
            button.setFixedWidth(100)
            cell = QWidget()  # gives the button margins inside its cell
            layout = QHBoxLayout(cell)
            layout.setContentsMargins(8, 4, 16, 4)
            layout.addWidget(button)
            table.setCellWidget(row, 3, cell)
        table.blockSignals(False)
        self.apply_filter(self.filterEdit.text())
        QTimer.singleShot(0, self._fit_height)
        # don't wipe a fresh _notify() error with the counter
        if self.serverToggleButton.isChecked() and time.monotonic() > self._notice_until:
            self.statusbar.showMessage(f"{len(self.remotes)} remotes, {len(self.mounts)} mounted")

    @pyqtSlot(str)
    def apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row, name in enumerate(self.remotes):
            self.remotesTable.setRowHidden(row, needle not in name.lower())

    def _mp_edited(self, item: QTableWidgetItem) -> None:
        if item.column() != 2:
            return
        name_item = self.remotesTable.item(item.row(), 1)
        if name_item is not None:
            self.planned[name_item.text()] = item.text().strip().rstrip(":")

    @pyqtSlot()
    def refresh_lists(self) -> None:
        self.mylog("list remotes")
        ok, js = self.net_send_cmd(self.net_cmd_listremotes, {})
        remotes = js.get("remotes", []) if ok else []
        if not ok or not isinstance(remotes, list):
            self.mylog("listremotes failed")
            remotes = []
        self.remotes = sorted(remotes, key=cmp_to_key(strcoll))
        self.mylog("list current mounted remotes")
        ok, js = self.net_send_cmd(self.net_cmd_listmounts, {})
        self.mounts = {}
        mount_points = js.get("mountPoints", []) if ok else []
        if not ok:
            self.mylog("listmounts failed")
        if isinstance(mount_points, list):
            for mount in mount_points:
                if isinstance(mount, dict):
                    self.mounts[mount.get("Fs", "").rstrip(":")] = mount.get("MountPoint", "").rstrip(":")
        free = [n for n in self.remotes if n not in self.mounts]
        self.planned = {n: self.planned[n] for n in free if n in self.planned}
        for name in free:
            if name not in self.planned:
                taken = set(self.planned.values()) | set(self.mounts.values())
                self.planned[name] = self._default_mount_point(name, taken)
        self._render()

    def _notify(self, msg: str) -> None:
        self.mylog(msg)
        self._notice_until = time.monotonic() + 8
        self.statusbar.showMessage(msg, 8000)

    def mount_remote(self, name: str) -> bool:
        mp = self.planned.get(name, "").strip()
        if not mp:
            self._notify(f"mounting {name}: no mount point set")
            return False
        try:
            self._prepare_mount(mp)
        except OSError as e:
            self._notify(f"mounting {name} on {mp}: {e}")
            return False
        self.mylog(f"mounting '{name}' on {mp}")
        ok, js = self.net_send_cmd(self.net_cmd_mount, {"fs": self._fs_arg(name), "mountPoint": self._mp_arg(mp)})
        if not ok:
            self._notify(f"mounting {name} on {mp} failed: {js.get('error', 'unknown error')}")
            return False
        self.mounts[name] = mp
        self.planned.pop(name, None)
        self.mylog(f"mounting {name} on {mp}: successful")
        return True

    def unmount_remote(self, name: str) -> bool:
        mp = self.mounts.get(name, "")
        self.mylog(f"unmounting '{name}' from {mp}")
        ok, js = self.net_send_cmd(self.net_cmd_unmount, {"mountPoint": self._mp_arg(mp)})
        if not ok:
            self._notify(f"unmounting {name} from {mp} failed: {js.get('error', 'unknown error')}")
            return False
        del self.mounts[name]
        self.planned[name] = mp
        self.mylog(f"unmounting {name}: successful")
        return True

    def toggle_mount(self, name: str) -> None:
        if name in self.mounts:
            self.unmount_remote(name)
        elif self.mount_remote(name):
            self._open_mount(name)
        self._render()

    @pyqtSlot()
    def mount_all(self) -> None:
        for name in [n for n in self.remotes if n not in self.mounts]:
            self.mount_remote(name)
        self._render()

    @pyqtSlot()
    def unmount_all(self) -> None:
        for name in list(self.mounts):
            self.unmount_remote(name)
        self._render()

    @pyqtSlot(QPoint)
    def table_menu(self, pos: QPoint) -> None:
        item = self.remotesTable.itemAt(pos)
        name_item = self.remotesTable.item(item.row(), 1) if item is not None else None
        if name_item is None:
            return
        name = name_item.text()
        self.remotesTable.selectRow(item.row())  # type: ignore[union-attr]
        menu = QMenu(self.remotesTable)
        if name in self.mounts:
            menu.addAction("Unmount", lambda: self.toggle_mount(name))
            menu.addAction("Open folder", lambda: self._open_mount(name))
        else:
            menu.addAction("Mount", lambda: self.toggle_mount(name))
        viewport = self.remotesTable.viewport()
        assert viewport is not None
        menu.exec(viewport.mapToGlobal(pos))

    def _open_mount(self, name: str) -> None:
        mp = self.mounts.get(name, "")
        # shortcut: a single char is assumed to be a Windows drive letter
        QDesktopServices.openUrl(QUrl.fromLocalFile(f"{mp}:\\" if len(mp) == 1 else mp))

    def net_send_cmd(self, url: str,
                     jargs: Dict[str, Union[Dict, List, str]], # type: ignore[type-arg]
                    timeout: int = 8) -> Tuple[bool, Dict[str, Union[Dict, List, str]]]: # type: ignore[type-arg]
        rs: Optional[httpx.Response] = None
        if self.client is None:
            self.mylog("httpx client is None")
            return False, {}
        try:
            self._api_log(f"-> POST {url} {json.dumps(jargs)}")
            rs = self.client.post(url, json=jargs, timeout=timeout)
            self._api_log(f"<- {rs.status_code} {rs.text.strip()}")
            try:
                json_res = rs.json()
                return rs.is_success, json_res
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(e.msg, e.doc, e.pos) from e

            # if rs.status_code == httpx.codes.OK or rs.is_success:
            #     try:
            #         json_res = rs.json()
            #         return True, json_res
            #     except json.JSONDecodeError as e:
            #         raise json.JSONDecodeError(e.msg, e.doc, e.pos) from e
            # else:
            #     try:
            #         json_res= rs.json()
            #         return False, json_res
            #     except json.JSONDecodeError as e:
            #         raise json.JSONDecodeError(e.msg, e.doc, e.pos) from e
        except httpx.ConnectError as e:
            self.mylog(f"{e}")
            self._api_log(f"<- connect error: {e}")
            return False, {}
        except httpx.TimeoutException as e:
            self.mylog(f"{e}")
            self._api_log(f"<- timeout: {e}")
            return False, {}
        finally:
            if rs:
                rs.close()

    def closeEvent(self, event: Optional[QCloseEvent]) -> None:
        settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        if self.client is not None:
            self.client.close()
        if event:
            event.accept()

    @pyqtSlot(bool)
    def toggle_server(self, b: bool) -> None:
        led = self.led
        if led.isOn() != b:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                if not b:
                    self._stop_server()
                elif not self._start_server():
                    self.serverToggleButton.setChecked(False)
                    return
            finally:
                QApplication.restoreOverrideCursor()
        led.setOn(b)

    def _start_server(self) -> bool:
        self.mylog("cheking if server is up")
        ok, _js = self.net_send_cmd(self.net_cmd_check_server, {}, timeout=1)
        if not ok:
            self.mylog("starting server")
            self.async_send_cmd(self.cmd_start_server, shell=True, capture_output=False, skip_waiting=True)
            # time.sleep(self.server_start_delay)
            # Linux refuses a closed port instantly (Windows retries for ~2 s), so pause between tries
            for _ in range(10):
                time.sleep(0.5)
                ok, _js = self.net_send_cmd(self.net_cmd_check_server, {}, timeout=1)
                if ok:
                    break
            if not ok:
                self._notify("could not start rclone server (is rclone installed and in PATH?)")
                return False
            self.mylog("configuring main and vfs")
            ok, _js = self.net_send_cmd(self.net_cmd_set_options, dict(self.net_cmd_vfs_main))
            self.mylog("setting vfs/main succeded" if ok else "setting vfs/main returned failure")
        self.refresh_lists()
        return True

    def _stop_server(self) -> None:
        self.mylog("list mounts")
        ok, js = self.net_send_cmd(self.net_cmd_listmounts, {})
        mount_points = js.get("mountPoints", []) if ok else []
        if isinstance(mount_points, list):
            for mount in mount_points:
                if isinstance(mount, dict):
                    mp = mount.get("MountPoint", "").rstrip(":")
                    ok, _js = self.net_send_cmd(self.net_cmd_unmount, {"mountPoint": self._mp_arg(mp)})
                    self.mylog(f"unmounting {mp}: " + ("succeded" if ok else "returned failure"))
        self.mylog("quitting server")
        ok, _js = self.net_send_cmd(self.net_cmd_quit_server, {})
        self.mylog("stopping server " + ("succeded" if ok else "returned failure"))
        self.remotes, self.mounts, self.planned = [], {}, {}
        if self.server is not None:
            self.server.terminate()
            self.server = None
        self._render()

    def async_send_cmd(self, cmd: Union[List, str, Sequence], shell: bool= False,  # type: ignore[type-arg]
                       capture_output: bool = True,
                       skip_waiting: bool = False) -> Union[bool, dict[str, int]]:
        outs = False
        # ress: subprocess.Popen
        try:
            if not capture_output:
                ress = subprocess.Popen(cmd, shell=shell, **self.creationflags)
                # ress.wait(timeout=15)
                # if ress.returncode == 0:
                self.server = ress
                if self.server is not None:
                    outs = True
            else:
                # self.mylog(f"{cmd}")
                # assert isinstance(cmd, list)
                ress = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **self.creationflags)
                if not skip_waiting and ress is not None:
                    ress.wait(timeout=15)
                    if ress.returncode == 0:
                        outs = True
                    outst, errs = ress.communicate(timeout=15)
                    try:
                        outs_json = json.loads(outst)
                        if "error" not in outs_json.keys() and str(errs).find("Failed") == -1 and len(outs_json) > 0:
                            outs = outs_json
                    except json.decoder.JSONDecodeError as e:
                        self.mylog(f"{e}")
                        return False
                else:
                    outs = True
        except subprocess.TimeoutExpired as e:
            self.mylog(f"{e}")
            if ress:
                ress.kill()
            return False
        except Exception as e:
            raise Exception from e

        return outs

    def mylog(self, msg: str, *args: str) -> None:
        now = datetime.datetime.fromtimestamp(time.time()).isoformat(" ", timespec="seconds")
        msg = f"{now} {msg}"
        arg: str = ""
        for t in args:
            arg = f"{arg} {t} "
        if len(arg) > 0:
            msg = f"{msg} {arg}"
            msg = msg.strip(" ")
        if self.mlog is not None:
            self.mlog.info(msg)

    def _api_log(self, msg: str) -> None:
        """Show an rc API request/response in the log dock (long bodies are cut)."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.logView.appendPlainText(f"{now} [api] {msg[:2000]}")

    def _tail_rclone_log(self) -> None:
        """Append new lines of rclone's own log file to the log dock."""
        try:
            size = self._rclone_log.stat().st_size
            if size < self._rclone_log_pos:  # file truncated or rotated
                self._rclone_log_pos = 0
            if size == self._rclone_log_pos:
                return
            with open(self._rclone_log, "rb") as f:
                f.seek(self._rclone_log_pos)
                data = f.read()
            # keep an incomplete last line for the next tick
            end = data.rfind(b"\n") + 1
            if end == 0:
                return
            self._rclone_log_pos += end
            self.logView.appendPlainText(data[:end].decode("utf-8", "replace").rstrip())
        except OSError:
            pass

    # @property
    # def cmd_listmounts(self) -> str:
    #     return self._cmd_listmounts
    #
    # @property
    # def cmd_listmounts_list(self) -> list[str]:
    #     return self._cmd_listmounts_list
    #
    # @property
    # def cmd_unmount_list(self) -> list[str]:
    #     return self._cmd_unmount_list
    #
    # @property
    # def cmd_quit_server(self) -> str:
    #     return self._cmd_quit_server
    #
    # @property
    # def cmd_quit_server_list(self) -> list[str]:
    #     return self._cmd_quit_server_list

    # @property
    # def col_list_cpy(self) -> list[Any]:
    #     return self._col_list_cpy

    # @property
    # def cmd_check_server_list(self) -> list[str]:
    #     return self._cmd_check_server_list

    # @property
    # def cmd_start_server(self) -> str | None:
    #     return self._cmd_start_server
    # @cmd_start_server.setter
    # def cmd_start_server(self, value) -> None:
    #     self._cmd_start_server = value
    #
    # @property
    # def cmd_start_server_list(self) -> list[str] | None:
    #     return self._cmd_start_server_list
    # @cmd_start_server_list.setter
    # def cmd_start_server_list(self, value) -> None:
    #     self._cmd_start_server_list = value

    # @property
    # def cmd_check_server(self) -> str:
    #     return self._cmd_check_server
    #
    # @property
    # def cmd_listremotes(self) -> str:
    #     return self._cmd_listremotes
    #
    # @property
    # def cmd_listremotes_list(self) -> list[str]:
    #     return self._cmd_listremotes_list
    #
    # @property
    # def cmd_mount_list(self) -> list[str]:
    #     return self._cmd_mount_list
    #
    # @property
    # def cmd_mount(self) -> str:
    #     return self._cmd_mount

    # @property
    # def col_list(self) -> list[Any]:
    #     return self._col_list
    # @col_list.setter
    # def col_list(self, value) -> None:
    #     self._col_list = value
    #
    # @property
    # def remotes(self) -> list[str]:
    #     return self._remotes
    # @remotes.setter
    # def remotes(self, remotes) -> None:
    #     self._remotes = remotes
    #
    # @property
    # def two_dim_list_r(self) -> list[list[str]]:
    #     return self._two_dim_list_r
    # @two_dim_list_r.setter
    # def two_dim_list_r(self, value) -> None:
    #     self._two_dim_list_r = value
    #
    # @property
    # def two_dim_list(self) -> list[list[str]]:
    #     return self._two_dim_list
    # @two_dim_list.setter
    # def two_dim_list(self, value) -> None:
    #     self._two_dim_list = value

    # @property
    # def cmd_unmount(self) -> str:
    #     return self._cmd_unmount

    # @property
    # def cmd_set_vfs_main(self) -> str | None:
    #     return self._cmd_set_vfs_main
    # @cmd_set_vfs_main.setter
    # def cmd_set_vfs_main(self, value) -> None:
    #     self._cmd_set_vfs_main = value
    #
    # @property
    # def cmd_set_vfs_main_list(self) -> list[str] | None:
    #     return self._cmd_set_vfs_main_list
    # @cmd_set_vfs_main_list.setter
    # def cmd_set_vfs_main_list(self, value) -> None:
    #     self._cmd_set_vfs_main_list = value

    # @property
    # def mlog(self) -> Logger | None:
    #     return self._mlog
    # @mlog.setter
    # def mlog(self, value) -> None:
    #     self._mlog = value

    # @property
    # def client(self) -> httpx.Client | None:
    #     return self._client
    # @client.setter
    # def client(self, value: httpx.Client) -> None:
    #     self._client = value
