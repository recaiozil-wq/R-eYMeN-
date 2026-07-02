"""Windows sistem tepsisi (win32gui)."""
from __future__ import annotations
import logging
import sys
import threading
import time
from pathlib import Path
import win32api, win32con, win32gui, win32gui_struct

logger = logging.getLogger(__name__)

def _make_icon(bg_rgb, letter="R"):
    """Dinamik ikon olustur (GDI)."""
    import win32ui, win32gdi
    w, h = 16, 16
    desk_dc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    dc = win32ui.CreateDC()
    dc.CreateCompatibleDC(desk_dc)
    bmp = win32gdi.CreateBitmap(w, h, 1, 32, None)
    dc.SelectObject(bmp)
    brush = win32gdi.CreateSolidBrush(win32gdi.RGB(*bg_rgb))
    dc.FillRect((0, 0, w, h), brush)
    dc.SetTextColor(win32gdi.RGB(255, 255, 255))
    dc.SetBkMode(1)
    dc.TextOut(2, 0, letter)
    desk_dc.DeleteDC()
    info = win32gui_struct.PackerIconInfo(True, win32gui.GetCursorInfo()[2], bmp.GetHandle(), bmp.GetHandle())
    return win32gui.CreateIconFromResourceEx(info[2], False, 0x00030000, w, h, 0)

class TrayApp:
    def __init__(self, server):
        self.server = server
        self._icon_run = _make_icon((0, 140, 60))
        self._icon_stop = _make_icon((30, 60, 120))
        self._cur_icon = self._icon_stop
        self._run = False
        self._hwnd = None

    def _wnd_proc(self, hwnd, msg, wp, lp):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0); return 0
        if msg == win32con.WM_TRAYICON:
            if lp == win32con.WM_LBUTTONUP:
                self._open_browser()
            elif lp == win32con.WM_RBUTTONUP:
                self._menu()
        return win32gui.DefWindowProc(hwnd, msg, wp, lp)

    def _setup(self):
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "ReYMeNTray"
        wc.lpfnWndProc = self._wnd_proc
        self._hwnd = win32gui.CreateWindow(
            win32gui.RegisterClass(wc), "Tray",
            win32con.WS_OVERLAPPED, 0,0,0,0, 0,0,wc.hInstance,None)

    def _update_icon(self):
        s = self.server.status
        tip = f"ReYMeN Desktop | {s}"
        if s == "running":
            tip += f"\n{self.server.url}\nUptime: {int(self.server.uptime_seconds)}s"
            self._cur_icon = self._icon_run
        else:
            self._cur_icon = self._icon_stop
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        self._idata = (self._hwnd, 0, flags, win32con.WM_USER+20, self._cur_icon, tip)
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self._idata)

    def _add(self):
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        self._idata = (self._hwnd, 0, flags, win32con.WM_USER+20, self._cur_icon, "ReYMeN Desktop")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self._idata)
        win32gui.Shell_NotifyIcon(win32gui.NIM_SETVERSION, self._idata, 4)

    def _open_browser(self):
        import subprocess
        subprocess.Popen(["cmd","/c","start",self.server.url], shell=True)

    def _menu(self):
        from reymen.desktop.autostart import AutoStartManager
        h = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(h, win32con.MF_STRING, 1, f"Status: {self.server.status.upper()}")
        win32gui.AppendMenu(h, win32con.MF_SEPARATOR, 0, None)
        if self.server.status == "running":
            win32gui.AppendMenu(h, win32con.MF_STRING, 2, "Stop Server")
        else:
            win32gui.AppendMenu(h, win32con.MF_STRING, 3, "Start Server")
        win32gui.AppendMenu(h, win32con.MF_STRING, 4, "Restart Server")
        win32gui.AppendMenu(h, win32con.MF_SEPARATOR, 0, None)
        win32gui.AppendMenu(h, win32con.MF_STRING, 5, "Open Browser")
        win32gui.AppendMenu(h, win32con.MF_SEPARATOR, 0, None)
        as_on = AutoStartManager.is_enabled()
        win32gui.AppendMenu(h, win32con.MF_STRING, 6, f"{'[X]' if as_on else '[ ]'} Auto-start")
        win32gui.AppendMenu(h, win32con.MF_SEPARATOR, 0, None)
        win32gui.AppendMenu(h, win32con.MF_STRING, 7, "Exit")
        pos = win32gui.GetCursorPos()
        cmd = win32gui.TrackPopupMenu(h, win32con.TPM_RETURNCMD|win32con.TPM_NONOTIFY,
                                       pos[0],pos[1],0,self._hwnd,None)
        win32gui.DestroyMenu(h)
        if cmd == 2: self.server.stop(); self._update_icon()
        elif cmd == 3: self.server.start(); self._update_icon()
        elif cmd == 4: self.server.restart(); self._update_icon()
        elif cmd == 5: self._open_browser()
        elif cmd == 6: AutoStartManager.toggle()
        elif cmd == 7:
            self.server.stop()
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self._idata)
            win32gui.PostQuitMessage(0)

    def run(self):
        self._setup()
        self._add()
        self._update_icon()
        self._run = True
        def _tick():
            while self._run:
                time.sleep(5)
                self._update_icon()
        threading.Thread(target=_tick, daemon=True).start()
        win32gui.PumpMessages()

def run_tray(server=None):
    if server is None:
        from reymen.desktop.server import web_server
        server = web_server
    TrayApp(server).run()
