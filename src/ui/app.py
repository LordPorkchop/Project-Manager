import customtkinter as ctk

from src.services import logger

_MASTER = ctk.CTk()


class AppWindow:
    def __init__(
        self,
        title: str = "Project Manager",
        width: int = 600,
        height: int = 400,
        centered: bool = True,
        resizable_x: bool = True,
        resizable_y: bool = True,
    ):
        self._logger = logger.get_logger("AppWindow")
        self._logger.debug(f"New AppWindow instance '{title}' created")

        self._master = _MASTER
        self._master.title(title)

        geometry_str = f"{width}x{height}"
        if centered:
            screen_w = self._master.winfo_screenwidth()
            screen_h = self._master.winfo_screenheight()
            x_offset = (screen_w // 2) - (width // 2)
            y_offset = (screen_h // 2) - (height // 2)
            geometry_str += f"+{x_offset}+{y_offset}"

        self._master.geometry(geometry_str)

        self._master.resizable(resizable_x, resizable_y)
