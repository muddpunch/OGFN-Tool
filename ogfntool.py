"""
OGFN Support Tool - simple PyQt6 UI.

pip install PyQt6
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    from PyQt6.QtCore import QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QTextCursor
    from PyQt6.QtWidgets import (
        QApplication,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    print("PyQt6 not installed. Run: pip install PyQt6")
    sys.exit(1)


LogFn = Callable[[str, str], None]


def _resolve(p: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.expandvars(p)))


LOCAL = os.environ.get("LOCALAPPDATA", "")
APPDATA = os.environ.get("APPDATA", "")
PROGRAMDATA = os.environ.get("PROGRAMDATA", "")
TEMP = os.environ.get("TEMP", "")

SAFE_PREFIXES = [
    _resolve(r"%LOCALAPPDATA%\FortniteGame\Saved"),
    _resolve(r"%LOCALAPPDATA%\EpicGamesLauncher\Saved"),
    _resolve(r"%APPDATA%\EasyAntiCheat"),
    _resolve(r"%LOCALAPPDATA%\EasyAntiCheat"),
    _resolve(r"%PROGRAMDATA%\EasyAntiCheat"),
    _resolve(r"%PROGRAMDATA%\BattlEye"),
    _resolve(r"%TEMP%"),
]

CLEAR_LOCAL_DATA_PATHS = [
    os.path.join(LOCAL, r"FortniteGame\Saved\Logs"),
    os.path.join(LOCAL, r"FortniteGame\Saved\Crashes"),
    os.path.join(LOCAL, r"FortniteGame\Saved\WebCache"),
    os.path.join(LOCAL, r"FortniteGame\Saved\PersistentDownloadDir"),
    os.path.join(LOCAL, r"EpicGamesLauncher\Saved\webcache"),
    os.path.join(LOCAL, r"EpicGamesLauncher\Saved\Logs"),
]

ANTICHEAT_PATHS = [
    os.path.join(APPDATA, "EasyAntiCheat"),
    os.path.join(LOCAL, "EasyAntiCheat"),
    os.path.join(PROGRAMDATA, "EasyAntiCheat"),
    os.path.join(PROGRAMDATA, "BattlEye"),
]

CONFIG_PATHS = [os.path.join(LOCAL, r"FortniteGame\Saved\Config")]

FORTNITE_PROCS = [
    "FortniteClient-Win64-Shipping.exe",
    "FortniteClient-Win64-Shipping_EAC.exe",
    "FortniteLauncher.exe",
    "EpicGamesLauncher.exe",
    "EpicWebHelper.exe",
    "EasyAntiCheat.exe",
    "BEService.exe",
]


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> None:
    try:
        script = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
    except Exception:
        pass
    sys.exit(0)


def is_safe_path(path: str) -> bool:
    resolved = Path(_resolve(path))
    for prefix in SAFE_PREFIXES:
        try:
            resolved.relative_to(prefix)
            return True
        except ValueError:
            continue
    return False


def safe_delete(path: str, log: LogFn) -> bool:
    if not path:
        log("WARNING", "Empty path skipped.")
        return False

    abs_path = os.path.abspath(os.path.expandvars(path))
    if not is_safe_path(abs_path):
        log("BLOCKED", f"{abs_path} is outside allowed paths.")
        return False

    if not os.path.exists(abs_path):
        log("SKIP", f"Does not exist: {abs_path}")
        return False

    try:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        log("DELETED", abs_path)
        return True
    except PermissionError as exc:
        log("ERROR", f"Permission denied: {abs_path} ({exc})")
    except OSError as exc:
        log("ERROR", f"OS error: {abs_path} ({exc})")
    return False


def kill_fortnite_processes(log: LogFn) -> None:
    log("SECTION", "Kill Processes")
    killed = 0
    for proc in FORTNITE_PROCS:
        try:
            result = subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, text=True)
        except FileNotFoundError:
            log("ERROR", "taskkill not found.")
            break
        except Exception as exc:
            log("ERROR", f"{proc}: {exc}")
            continue

        if result.returncode == 0:
            killed += 1
            log("KILLED", proc)
        else:
            log("SKIP", f"Not running: {proc}")
    log("DONE", f"Terminated {killed}/{len(FORTNITE_PROCS)} processes.")


def clear_local_data(log: LogFn) -> None:
    log("SECTION", "Clear Local Data")
    extra = []
    if TEMP and os.path.isdir(TEMP):
        extra = [
            os.path.join(TEMP, name)
            for name in os.listdir(TEMP)
            if any(key in name.lower() for key in ("epic", "fortnite", "eac"))
        ]

    deleted = sum(1 for path in CLEAR_LOCAL_DATA_PATHS + extra if safe_delete(path, log))
    log("DONE", f"Removed {deleted} location(s).")


def delete_anticheat_cache(log: LogFn) -> None:
    log("SECTION", "Anti-Cheat Cache")
    deleted = sum(1 for path in ANTICHEAT_PATHS if safe_delete(path, log))
    log("DONE", f"Removed {deleted} location(s).")


def reset_config(log: LogFn) -> None:
    log("SECTION", "Reset Config")
    deleted = sum(1 for path in CONFIG_PATHS if safe_delete(path, log))
    log("DONE", f"Reset {deleted} config(s).")


def full_clean(log: LogFn) -> None:
    log("START", "Full clean started.")
    kill_fortnite_processes(log)
    clear_local_data(log)
    delete_anticheat_cache(log)
    reset_config(log)
    log("DONE", "Full clean complete.")


class Worker(QThread):
    log_signal = pyqtSignal(str, str)
    done_signal = pyqtSignal()

    def __init__(self, op: str):
        super().__init__()
        self.op = op

    def run(self) -> None:
        ops = {
            "kill": kill_fortnite_processes,
            "local": clear_local_data,
            "anticheat": delete_anticheat_cache,
            "config": reset_config,
            "full": full_clean,
        }
        ops.get(self.op, lambda _log: None)(self.log_signal.emit)
        self.done_signal.emit()


QSS = """
QWidget#root {
    background: #101114;
    color: #e8e8e8;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel#title {
    color: #ffffff;
    font-size: 18pt;
    font-weight: 700;
}
QLabel#badge {
    border: 1px solid #3a3d45;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton {
    background: #24272e;
    color: #f0f0f0;
    border: 1px solid #3a3d45;
    border-radius: 4px;
    padding: 9px 12px;
    text-align: left;
}
QPushButton:hover { background: #2c3038; }
QPushButton:pressed { background: #1d2026; }
QPushButton:disabled {
    background: #191b20;
    color: #70747d;
}
QPushButton#danger {
    background: #5c161a;
    border-color: #8e252b;
}
QPushButton#danger:hover { background: #6b1a1f; }
QTextEdit#log {
    background: #0b0c0f;
    color: #d7d7d7;
    border: 1px solid #30333a;
    border-radius: 4px;
    font-family: Consolas;
    font-size: 9pt;
    padding: 8px;
}
QLabel#status {
    color: #aeb3bd;
}
"""


class OGFNSupportTool(QMainWindow):
    CONFIRMS = {
        "kill": ("Kill Processes", "This will terminate Fortnite and Epic Games processes.\nContinue?"),
        "local": ("Clear Local Data", "Delete Fortnite/Epic logs, cache, and temp data.\nGame files stay intact.\nContinue?"),
        "anticheat": ("Anti-Cheat Cache", "Delete EasyAntiCheat and BattlEye cache folders.\nContinue?"),
        "config": ("Reset Config", "Delete the Fortnite config folder.\nGraphics/keybinds will reset.\nContinue?"),
        "full": ("Full Clean", "Run every operation: kill processes, clear local data, anti-cheat cache, reset config.\nContinue?"),
    }

    OPS = [
        ("Kill Processes", "kill"),
        ("Clear Local Data", "local"),
        ("Anti-Cheat Cache", "anticheat"),
        ("Reset Config", "config"),
        ("Full Clean", "full"),
    ]

    def __init__(self):
        super().__init__()
        self.worker: Worker | None = None
        self.buttons: list[QPushButton] = []

        self.setWindowTitle("OGFN Support Tool")
        self.resize(860, 560)
        self.setMinimumSize(720, 460)
        self._build()
        self._startup_log()

    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet(QSS)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("OGFN Support Tool")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        admin = is_admin()
        badge = QLabel("ADMIN" if admin else "NO ADMIN")
        badge.setObjectName("badge")
        badge.setStyleSheet(
            "color: #43d17a; border-color: #2b6a42;"
            if admin
            else "color: #ff6666; border-color: #7a3030;"
        )
        header.addWidget(badge)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (label, key) in enumerate(self.OPS):
            btn = QPushButton(label)
            btn.setMinimumHeight(42)
            if key == "full":
                btn.setObjectName("danger")
            btn.clicked.connect(lambda _checked=False, op=key: self._confirm(op))
            grid.addWidget(btn, i // 2, i % 2)
            self.buttons.append(btn)
        layout.addLayout(grid)

        log_row = QHBoxLayout()
        log_row.addWidget(QLabel("Log"))
        log_row.addStretch()

        clear = QPushButton("Clear")
        clear.setFixedWidth(90)
        clear.clicked.connect(self._clear_log)
        log_row.addWidget(clear)
        layout.addLayout(log_row)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("log")
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(4000)
        layout.addWidget(self.log_view, stretch=1)

        self.status = QLabel("Ready.")
        self.status.setObjectName("status")
        layout.addWidget(self.status)

    def _clear_log(self) -> None:
        self.log_view.clear()
        self.status.setText("Ready.")

    def _log(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        cur = self.log_view.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(f"{ts}  {level:<9} {message}\n")
        self.log_view.setTextCursor(cur)
        self.log_view.ensureCursorVisible()
        self.status.setText(message[:130])

    def _startup_log(self) -> None:
        admin = is_admin()
        self._log("START", "OGFN Support Tool initialised.")
        self._log("DONE" if admin else "WARNING", f"Administrator privileges: {'YES' if admin else 'NO'}")

    def _confirm(self, op: str) -> None:
        title, body = self.CONFIRMS[op]
        answer = QMessageBox.question(
            self,
            title,
            body,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._run(op)

    def _run(self, op: str) -> None:
        self._set_busy(True)
        self._log("START", f"Running: {self.CONFIRMS[op][0]}")

        self.worker = Worker(op)
        self.worker.log_signal.connect(self._log)
        self.worker.done_signal.connect(self._done)
        self.worker.start()

    def _set_busy(self, busy: bool) -> None:
        for btn in self.buttons:
            btn.setEnabled(not busy)
        self.status.setText("Running..." if busy else "Ready.")

    def _done(self) -> None:
        self._set_busy(False)
        self._log("DONE", "Operation finished.")
        self.worker = None


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = app.palette()
    for role, color in [
        (palette.ColorRole.Window, "#101114"),
        (palette.ColorRole.WindowText, "#e8e8e8"),
        (palette.ColorRole.Base, "#0b0c0f"),
        (palette.ColorRole.Text, "#d7d7d7"),
        (palette.ColorRole.Button, "#24272e"),
        (palette.ColorRole.ButtonText, "#f0f0f0"),
    ]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)

    if not is_admin():
        answer = QMessageBox.warning(
            None,
            "No Admin Privileges",
            "Running without administrator privileges.\nSome operations may fail.\n\nRestart as administrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            run_as_admin()
            return

    window = OGFNSupportTool()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
