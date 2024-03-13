from dataclasses import dataclass, field
from typing import Callable

from PyQt5.QtWidgets import QPushButton


@dataclass
class BtnToolMap:
    """Class for associate a map button with its own tool (if exists)."""
    name: str
    iconPath: str
    btn: QPushButton
    fn: Callable
    checkable: bool
    # isLeft: bool = field(default=False, init=False)
    isAnnotation: bool = field(default=False, init=False)
    tool: any = field(default=None, init=False)
    additionalTool: any = field(default=None, init=False)
