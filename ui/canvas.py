import customtkinter as ctk
from PIL import ImageTk

class PDFCanvas(ctk.CTkCanvas):
    def __init__(self, master, **kwargs):
        super().__init__(
            master, bg="#1e1e1e", highlightthickness=2,
            highlightbackground="#30363d", highlightcolor="#58a6ff",
            takefocus=True, **kwargs
        )
        self.tk_image = None
        
        # State Tracking
        self.start_x = self.start_y = 0
        self._pan_start_x = self._pan_start_y = 0
        self.selection_rect_id = None
        self.signature_overlays = []
        self.selected_signature_id = None
        self._signature_drag = None
        self.crop_mode = self.highlight_mode = self.signature_mode = False
        
        # Callbacks
        self.hover_callback = self.double_click_callback = self.right_click_callback = None
        self.wheel_callback = None
        self.selection_callback = None
        self.signature_change_callback = None

        # Bindings
        self.bind("<ButtonPress-1>", self.on_left_click)
        self.bind("<B1-Motion>", self.on_left_drag)
        self.bind("<ButtonRelease-1>", self.on_left_release)
        self.bind("<ButtonPress-3>", self.start_pan)
        self.bind("<B3-Motion>", self.do_pan)
        self.bind("<ButtonRelease-3>", self.stop_pan)
        self.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<Motion>", self.on_mouse_move)
        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.bind("<Button-1>", lambda _event: self.focus_set(), add="+")

    def display_page(self, img):
        """Forces a layout refresh to ensure the page is centered in the ACTUAL window space."""
        self.tk_image = ImageTk.PhotoImage(img)
        self.delete("all")
        
        # Force the widget to update its internal dimensions
        self.update() 
        cw, ch = self.winfo_width(), self.winfo_height()
        iw, ih = img.size
        
        # Calculate true center coordinates
        pos_x = max(cw, iw) / 2
        pos_y = max(ch, ih) / 2
        
        # Update scroll region and place image
        self.config(scrollregion=(0, 0, max(cw, iw), max(ch, ih)))
        self.create_image(pos_x, pos_y, anchor="center", image=self.tk_image)

    def set_modes(self, crop=False, highlight=False, signature=False):
        self.crop_mode, self.highlight_mode, self.signature_mode = crop, highlight, signature
        self.config(cursor="cross" if crop or signature else "pencil" if highlight else "")
        self.clear_selection()

    def on_left_click(self, e):
        if not (self.crop_mode or self.highlight_mode or self.signature_mode):
            self._begin_signature_edit(self.canvasx(e.x), self.canvasy(e.y))
            return
        self.start_x, self.start_y = self.canvasx(e.x), self.canvasy(e.y)
        self.clear_selection()
        color = "red" if self.crop_mode else "#2f9bff" if self.signature_mode else "#FFD700"
        self.selection_rect_id = self.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=color, width=2, dash=(4,4))

    def on_left_drag(self, e):
        if self._signature_drag:
            self._drag_signature(self.canvasx(e.x), self.canvasy(e.y))
            return
        if self.selection_rect_id:
            self.coords(self.selection_rect_id, self.start_x, self.start_y, self.canvasx(e.x), self.canvasy(e.y))

    def on_left_release(self, e):
        if self._signature_drag:
            signature_id, _mode, _start, original = self._signature_drag
            self._signature_drag = None
            overlay = next((item for item in self.signature_overlays if item["id"] == signature_id), None)
            if overlay and tuple(overlay["rect"]) != tuple(original) and self.signature_change_callback:
                self.signature_change_callback(signature_id, tuple(overlay["rect"]))
            return
        self.end_x, self.end_y = self.canvasx(e.x), self.canvasy(e.y)
        if self.selection_callback:
            self.selection_callback(e)

    def clear_selection(self):
        if self.selection_rect_id: self.delete(self.selection_rect_id); self.selection_rect_id = None

    def set_signature_overlays(self, overlays):
        self.signature_overlays = [{"id": item["id"], "rect": list(item["rect"])} for item in overlays]
        if self.selected_signature_id not in {item["id"] for item in overlays}:
            self.selected_signature_id = None
        self._draw_signature_overlays()

    def _draw_signature_overlays(self):
        self.delete("signature-ui")
        for item in self.signature_overlays:
            if item["id"] != self.selected_signature_id:
                continue
            x0, y0, x1, y1 = item["rect"]
            self.create_rectangle(x0, y0, x1, y1, outline="#2f9bff", width=2,
                                  dash=(5, 3), tags="signature-ui")
            for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                self.create_rectangle(x - 5, y - 5, x + 5, y + 5, fill="white",
                                      outline="#2f9bff", width=2, tags="signature-ui")

    def _begin_signature_edit(self, x, y):
        hit = None
        mode = "move"
        for item in reversed(self.signature_overlays):
            x0, y0, x1, y1 = item["rect"]
            corners = {"nw": (x0, y0), "ne": (x1, y0), "sw": (x0, y1), "se": (x1, y1)}
            corner = next((name for name, point in corners.items()
                           if abs(x - point[0]) <= 9 and abs(y - point[1]) <= 9), None)
            if corner or (x0 <= x <= x1 and y0 <= y <= y1):
                hit, mode = item, corner or "move"
                break
        self.selected_signature_id = hit["id"] if hit else None
        self._draw_signature_overlays()
        if hit:
            self._signature_drag = (hit["id"], mode, (x, y), tuple(hit["rect"]))

    def _drag_signature(self, x, y):
        signature_id, mode, (start_x, start_y), original = self._signature_drag
        item = next(item for item in self.signature_overlays if item["id"] == signature_id)
        x0, y0, x1, y1 = original
        dx, dy = x - start_x, y - start_y
        if mode == "move":
            item["rect"] = [x0 + dx, y0 + dy, x1 + dx, y1 + dy]
        else:
            if "w" in mode: x0 += dx
            if "e" in mode: x1 += dx
            if "n" in mode: y0 += dy
            if "s" in mode: y1 += dy
            item["rect"] = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
        self._draw_signature_overlays()

    def get_selection_pixels(self):
        return (self.start_x, self.start_y, self.end_x, self.end_y) if self.selection_rect_id else None

    def start_pan(self, e):
        self.focus_set(); self.config(cursor="fleur")
        self._pan_start_x, self._pan_start_y = e.x, e.y
        self.scan_mark(e.x, e.y)

    def do_pan(self, e): self.scan_dragto(e.x, e.y, gain=1)
    def stop_pan(self, e):
        self.config(cursor="cross" if self.crop_mode or self.signature_mode else "pencil" if self.highlight_mode else "")
        if ((e.x - self._pan_start_x)**2 + (e.y - self._pan_start_y)**2)**0.5 < 5:
            if self.right_click_callback: self.right_click_callback(self.canvasx(e.x), self.canvasy(e.y), e.x_root, e.y_root)

    def on_mouse_move(self, e):
        if self.hover_callback: self.hover_callback(self.canvasx(e.x), self.canvasy(e.y))
    def on_double_click(self, e):
        if self.double_click_callback: self.double_click_callback(self.canvasx(e.x), self.canvasy(e.y))

    def on_mouse_wheel(self, e):
        if self.wheel_callback:
            self.wheel_callback(e)
        return "break"
