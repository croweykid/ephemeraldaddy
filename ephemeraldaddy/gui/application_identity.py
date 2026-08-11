"""Configure the native and Qt application identity before any window exists."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QCoreApplication


APP_DISPLAY_NAME = "Ephemeral Daddy"
APP_SHELL_DISPLAY_NAME = "EphemeralDaddy"
APP_DESKTOP_ID = "io.github.ephemeraldaddy.EphemeralDaddy"
WINDOWS_APP_USER_MODEL_ID = "ephemeraldaddy.desktop"


def configure_pre_qapplication_identity() -> None:
    """Set identity values which native window systems read at app creation.

    Calling the equivalent setters after the startup splash has been created is
    too late for several Linux shells and for parts of macOS's Cocoa bridge.
    """
    QCoreApplication.setApplicationName(APP_SHELL_DISPLAY_NAME)
    QCoreApplication.setOrganizationName(APP_DISPLAY_NAME)
    QCoreApplication.setDesktopFileName(APP_DESKTOP_ID)

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(  # type: ignore[attr-defined]
                WINDOWS_APP_USER_MODEL_ID
            )
        except Exception:
            pass
    elif sys.platform == "darwin":
        # This improves interpreter launches where Cocoa honors the process
        # name. A real .app bundle remains the only fully reliable Dock identity.
        try:
            libc = ctypes.CDLL(None)
            setprogname = getattr(libc, "setprogname", None)
            if setprogname is not None:
                setprogname.argtypes = [ctypes.c_char_p]
                setprogname.restype = None
                setprogname(APP_SHELL_DISPLAY_NAME.encode())
        except Exception:
            pass


def configure_qapplication_identity(app) -> None:
    """Apply identity properties exposed by a constructed QApplication."""
    app.setApplicationName(APP_SHELL_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_SHELL_DISPLAY_NAME)
    app.setOrganizationName(APP_DISPLAY_NAME)
    app.setDesktopFileName(APP_DESKTOP_ID)
