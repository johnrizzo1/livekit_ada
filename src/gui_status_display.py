from typing import Optional, Callable
from .status_display import StatusDisplay


class GUIStatusDisplay(StatusDisplay):
    """Enhanced status display for GUI"""
    def __init__(self, update_callback: Optional[Callable] = None):
        super().__init__()
        self.update_callback = update_callback
        
    def _print_status(self):
        """Override to use callback instead of direct printing"""
        if self.update_callback:
            self.update_callback()