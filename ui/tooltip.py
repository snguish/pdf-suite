import customtkinter as ctk


class ToolTip:
    """A lightweight tooltip which also appears for keyboard focus."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.popup = None
        self._timer = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<FocusIn>", self.show, add="+")
        widget.bind("<FocusOut>", self.hide, add="+")

    def _schedule(self, _event=None):
        self._timer = self.widget.after(450, self.show)

    def show(self, _event=None):
        if self.popup or not self.widget.winfo_exists():
            return
        if self._timer:
            self.widget.after_cancel(self._timer)
            self._timer = None
        self.popup = ctk.CTkToplevel(self.widget)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.geometry(f"+{self.widget.winfo_rootx() + self.widget.winfo_width() + 6}+{self.widget.winfo_rooty()}")
        ctk.CTkLabel(
            self.popup, text=self.text, fg_color="#111827", text_color="#f3f4f6",
            corner_radius=5, padx=8, pady=4, font=("Segoe UI", 10),
        ).pack()

    def hide(self, _event=None):
        if self._timer:
            self.widget.after_cancel(self._timer)
            self._timer = None
        if self.popup:
            self.popup.destroy()
            self.popup = None
