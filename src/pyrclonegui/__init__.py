import platform

system = platform.system().lower()
if system == "windows":
    from ._pyrclone_win import PyRcloneGuiWin as PyRclone
elif system == "linux":
    from ._pyrclone_linux import PyRcloneGuiLin as PyRclone
else:
    raise NotImplementedError(f"Unsupported OS: {system}")

__all__ = ['PyRclone']
__version__ = "0.0.7"
