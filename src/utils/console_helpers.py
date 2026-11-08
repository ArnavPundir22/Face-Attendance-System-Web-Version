"""
BioSecure AI — Windows Console Management Helpers.

Provides lightweight utilities to prevent Windows Command Prompt QuickEdit mode
from pausing stdout writes and freezing WSGI application servers.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

STD_INPUT_HANDLE = -10
ENABLE_QUICK_EDIT_MODE = 0x0040
ENABLE_EXTENDED_FLAGS = 0x0080


def disable_windows_console_quickedit() -> bool:
    """
    Disable Windows Command Prompt QuickEdit mode to prevent console clicks
    from pausing stdout and freezing the server.

    Safe no-op on non-Windows platforms.

    Returns:
        bool: True if QuickEdit mode was successfully disabled, else False.
    """
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import byref, c_ulong, c_void_p

        kernel32 = ctypes.windll.kernel32

        # Explicit prototypes for 64-bit handle safety
        kernel32.GetStdHandle.argtypes = [ctypes.c_long]
        kernel32.GetStdHandle.restype = c_void_p

        kernel32.GetConsoleMode.argtypes = [c_void_p, ctypes.POINTER(c_ulong)]
        kernel32.GetConsoleMode.restype = ctypes.c_int

        kernel32.SetConsoleMode.argtypes = [c_void_p, c_ulong]
        kernel32.SetConsoleMode.restype = ctypes.c_int

        h_stdin = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        # Check for NULL (0) or INVALID_HANDLE_VALUE (-1 / 0xFFFFFFFFFFFFFFFF)
        if not h_stdin or h_stdin == c_void_p(-1).value or h_stdin == -1:
            logger.debug(
                "Windows console stdin handle is invalid or detached."
            )
            return False

        mode = c_ulong()
        if not kernel32.GetConsoleMode(h_stdin, byref(mode)):
            logger.debug(
                "Failed to get console mode (redirected stdin or no console)."
            )
            return False

        # Clear ENABLE_QUICK_EDIT_MODE and include ENABLE_EXTENDED_FLAGS
        new_mode = (
            mode.value & ~ENABLE_QUICK_EDIT_MODE
        ) | ENABLE_EXTENDED_FLAGS
        if not kernel32.SetConsoleMode(h_stdin, new_mode):
            logger.debug("Failed to set Windows console mode.")
            return False

        logger.info("Windows console QuickEdit mode successfully disabled.")
        return True
    except Exception as exc:
        logger.debug(
            "Exception while disabling Windows console QuickEdit: %s", exc
        )
        return False
