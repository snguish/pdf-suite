import customtkinter as ctk


class DarkMenuBar(ctk.CTkFrame):
    """In-window dark menu bar with lightweight keyboard-friendly popups."""

    def __init__(self, master, menus, **kwargs):
        super().__init__(master, height=30, corner_radius=0, fg_color="#202020", **kwargs)
        self.pack_propagate(False)
        self._popup = None
        self._active_button = None
        self._buttons = {}
        self.winfo_toplevel().bind("<Button-1>", self._root_click, add="+")
        for label, items in menus:
            button = ctk.CTkButton(
                self, text=label, width=max(48, len(label) * 9 + 20), height=28,
                corner_radius=0, fg_color="transparent", hover_color="#3d3d3d",
                font=("Segoe UI", 11), command=lambda l=label, i=items: self.toggle_menu(l, i),
            )
            button.pack(side="left", padx=(2, 0), pady=1)
            self._buttons[label] = button
            button.bind("<Enter>", lambda _e, l=label, i=items, b=button: self._switch_on_hover(l, i, b), add="+")

    def toggle_menu(self, label, items):
        button = self._buttons[label]
        if self._popup and self._active_button is button:
            self.close_menu()
            return
        self.open_menu(button, items)

    def open_menu(self, button, items):
        self.close_menu()
        self._active_button = button
        button.configure(fg_color="#3d3d3d")
        popup = ctk.CTkToplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color="#242424")
        popup.bind("<Escape>", lambda _e: self.close_menu())
        self._popup = popup

        width = max(190, max((len(item.get("label", "")) + len(item.get("accelerator", ""))) * 8 + 44
                             for item in items if item is not None))
        first_action = None
        for item in items:
            if item is None:
                ctk.CTkFrame(popup, height=1, fg_color="#4a4a4a").pack(fill="x", padx=8, pady=4)
                continue
            row = ctk.CTkFrame(popup, height=30, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            row.pack_propagate(False)
            command = item["command"]
            action = ctk.CTkButton(
                row, text=item["label"], anchor="w", height=28, corner_radius=3,
                fg_color="transparent", hover_color="#3d3d3d", font=("Segoe UI", 11),
                command=lambda c=command: self._invoke(c),
            )
            action.pack(side="left", expand=True, fill="both")
            if item.get("accelerator"):
                ctk.CTkLabel(
                    row, text=item["accelerator"], width=72, anchor="e",
                    text_color="#aaaaaa", font=("Segoe UI", 10),
                ).pack(side="right", padx=(4, 8))
            if first_action is None:
                first_action = action

        popup.update_idletasks()
        popup.geometry(f"{width}x{popup.winfo_reqheight()}+{button.winfo_rootx()}+{button.winfo_rooty() + button.winfo_height()}")
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        if first_action:
            first_action.focus_set()

    def close_menu(self):
        if self._popup:
            self._popup.destroy()
            self._popup = None
        if self._active_button:
            self._active_button.configure(fg_color="transparent")
            self._active_button = None

    def _invoke(self, command):
        self.close_menu()
        self.after_idle(command)

    def _root_click(self, event):
        if self._popup and not str(event.widget).startswith(str(self)):
            self.close_menu()

    def _switch_on_hover(self, label, items, button):
        if self._popup and self._active_button is not button:
            self.open_menu(button, items)
