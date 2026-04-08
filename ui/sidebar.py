import customtkinter as ctk
import threading
from tkinter import Menu

class Sidebar(ctk.CTkScrollableFrame):
    def __init__(self, master, engine, select_callback, rotate_callback, **kwargs):
        # We use width 280 to accommodate the new checkboxes
        super().__init__(master, width=280, label_text="Page Navigation", **kwargs)
        self.engine = engine
        self.select_callback = select_callback
        self.rotate_callback = rotate_callback
        
        self.is_running = True
        self.extraction_mode = False 
        self.buttons = {}
        self.checkboxes = {}
        self.frames = {} # NEW: Tracks the container frame for accurate scrolling
        self.selected_pages = set()

        # Load thumbnails in a separate thread to keep UI snappy
        self.loader_thread = threading.Thread(target=self._load_thumbnails, daemon=True)
        self.loader_thread.start()

    def stop_loading(self):
        self.is_running = False

    def _load_thumbnails(self):
        for i in range(len(self.engine.doc)):
            if not self.is_running: return
            self.after(10, lambda idx=i: self.refresh_thumbnail(idx))

    def toggle_extraction_mode(self, enabled):
        """Shows or hides checkboxes for the Extract Page(s) feature."""
        self.extraction_mode = enabled
        for cb in self.checkboxes.values():
            if enabled: cb.pack(side="left", padx=(5, 0))
            else: cb.pack_forget()
        if not enabled: self.clear_all_selections()

    def clear_all_selections(self):
        self.selected_pages.clear()
        for cb in self.checkboxes.values(): cb.deselect()

    def select_range(self, indices):
        self.selected_pages = set(indices)
        for i, cb in self.checkboxes.items():
            if i in self.selected_pages: cb.select()
            else: cb.deselect()

    def toggle_selection(self, idx):
        if self.checkboxes[idx].get(): self.selected_pages.add(idx)
        else: self.selected_pages.discard(idx)

    # --- SYNCHRONIZATION LOGIC (RESTORED & FIXED) ---

    def highlight_active(self, active_idx):
        """Visually marks the current page in the sidebar."""
        for i, btn in self.buttons.items():
            if i == active_idx:
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5")) # Highlight blue
            else:
                btn.configure(fg_color="transparent")

    def scroll_to_page(self, idx):
        """
        Uses the working logic from your original file, updated to 
        target the container frame rather than the button.
        """
        self.update_idletasks() # Ensure geometry is calculated
        
        if idx in self.frames:
            target_widget = self.frames[idx]
            canvas = self._parent_canvas # Reference to internal CTK canvas
            
            # Get dimensions of the scrollable content
            bbox = canvas.bbox("all")
            if not bbox: return
            
            total_h = bbox[3]
            view_h = canvas.winfo_height()
            
            if total_h > view_h:
                # We measure y from the frame, not the button inside the frame
                target_y = target_widget.winfo_y()
                target_h = target_widget.winfo_height()
                
                # Centering Math: (Position - Half Viewport + Half Widget)
                target_fraction = (target_y - (view_h / 2) + (target_h / 2)) / total_h
                canvas.yview_moveto(max(0, min(target_fraction, 1.0)))

    def refresh_thumbnail(self, i):
        pil_img = self.engine.get_thumbnail(i, width=110)
        w, h = pil_img.size
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(w, h))

        if i in self.buttons:
            self.buttons[i].configure(image=ctk_img)
            return

        # item_frame is the KEY: we must scroll to THIS, not the button
        item_frame = ctk.CTkFrame(self, fg_color="transparent")
        item_frame.pack(pady=8, padx=5, fill="x")
        self.frames[i] = item_frame

        cb = ctk.CTkCheckBox(item_frame, text="", width=24, 
                             command=lambda idx=i: self.toggle_selection(idx))
        if self.extraction_mode:
            cb.pack(side="left", padx=(5, 0))
        self.checkboxes[i] = cb

        btn = ctk.CTkButton(
            item_frame, image=ctk_img, text=f"Page {i+1}", compound="top",
            command=lambda p=i: self.select_callback(p),
            fg_color="transparent", hover_color="#333333", anchor="center"
        )
        btn.pack(side="right", expand=True, fill="x")
        btn.bind("<Button-3>", lambda e, p=i: self.show_context_menu(e, p))
        self.buttons[i] = btn

    def show_context_menu(self, event, idx):
        m = Menu(self, tearoff=0)
        m.add_command(label="Rotate 90°", command=lambda: self.rotate_callback(idx))
        m.post(event.x_root, event.y_root)