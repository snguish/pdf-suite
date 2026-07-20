import ctypes
import sys


def apply_dark_title_bar(window):
    """Ask Windows to use native dark chrome without replacing accessibility or resizing."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        enabled = ctypes.c_int(1)
        for attribute in (20, 19):  # Windows 11/10, then older Windows 10 fallback.
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
            if result == 0:
                break
    except (AttributeError, OSError, ctypes.ArgumentError):
        pass
