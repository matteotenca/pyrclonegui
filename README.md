# pyrclonegui

A small Qt desktop front-end for [rclone](https://rclone.org). It lists the remotes from your rclone
configuration and lets you mount and unmount them with one click.

Rclone manages files on cloud storage and supports more than 70 providers, including S3 object stores,
consumer and business file services, and standard transfer protocols. pyrclonegui does not replace its
command line. It makes the everyday job, mounting remotes as drives or folders, convenient.

## Features

- One table with every configured remote: status, name, mount point and a Mount/Unmount button.
- Edit the mount point (drive letter or folder) by double-clicking it before mounting.
- Mount all and Unmount all, plus a filter box for long remote lists.
- A successful mount opens the drive in your file manager.
- Starts and stops the rclone server for you. Stopping it unmounts everything first.
- Log panel (View, Log) showing what the program is doing.
- System tray icon with show, server on/off and quit. Minimizing hides the window to the tray.
- Light and dark theme, remembered between runs.
- Windows and Linux.

## Requirements

- Python 3.10 or newer
- [rclone](https://rclone.org/downloads/) installed and available in `PATH`
- Something that lets rclone mount:
  - Windows: [WinFsp](https://winfsp.dev)
  - Linux: FUSE
- Python packages (installed automatically): PyQt6, httpx, and pywin32 on Windows

Remotes are read from your normal rclone configuration. Run `rclone config` to add or change them. The
program never edits that file.

## Install and run

```
pip install .
rclonegui
```

For development, install it editable and run the module:

```
pip install -e .
python -m pyrclonegui
```

Then press **Start server**. The remotes appear in the table.

## How it works

pyrclonegui starts `rclone rcd`, rclone's remote control daemon, on `127.0.0.1:5572` and talks to it over
HTTP (`config/listremotes`, `mount/mount`, `mount/unmount`, `mount/listmounts`). If a server is already
running there when the program starts, it attaches to it.

- On Windows each remote is mounted on a free drive letter.
- On Linux each remote is mounted on `/tmp/<remote>`, and the folder is created if missing.
- Mounts use VFS full cache mode with a 30 GB cache limit and 16 transfers. These values are set in
  `_pyrclone_win.py` and `_pyrclone_linux.py` (`net_cmd_vfs_main`).

Files written to the temporary directory: `pyrclonegui.log` (this program), `rclone.log` (the rclone
daemon) and `rclone_cache/` (the VFS cache).

> **Security note:** the daemon runs with `--rc-no-auth`. It only listens on localhost, but any program on
> your machine can then control rclone, including mounting and reading your remotes. Do not use this on a
> shared machine you do not trust.

## Development

The window layout lives in `pyrclonegui.ui`, which you can open in Qt Designer. The Python module
`src/pyrclonegui/_qtuicwindow.py` is generated from it. Never edit that file by hand. After changing the
`.ui` file, regenerate it:

```
pyuic6 pyrclonegui.ui -o src/pyrclonegui/_qtuicwindow.py
```

| File | Role |
|------|------|
| `src/pyrclonegui/pyrclone.py` | Shared window logic: table, mounting, server control, tray, log |
| `src/pyrclonegui/_pyrclone_win.py` | Windows specifics: drive letters, start command |
| `src/pyrclonegui/_pyrclone_linux.py` | Linux specifics: mount folders, start command |
| `src/pyrclonegui/_theme.py` | Stylesheet (light and dark) and the app icon |
| `src/led/` | The server status LED widget |

## License

GPL-3.0. See [LICENSE](LICENSE).
