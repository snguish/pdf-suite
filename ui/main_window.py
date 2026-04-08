import customtkinter as ctk
import csv, os
from tkinter import filedialog, messagebox, Menu
from core.engine import PDFEngine
from ui.sidebar import Sidebar
from ui.canvas import PDFCanvas

class MainWindow:
    def __init__(self, root, session, initial_file=None):
        self.root, self.session = root, session
        self.engine = self.sidebar = None
        self.current_file_path = None
        
        # --- APP STATE ---
        self.sidebar_visible = True
        self.inspector_visible = False
        self.current_zoom = 1.0      
        self.current_page_index = 0  
        self.extraction_mode = False
        self.active_note_coord = None 

        # 4-Column Layout: Sidebar(0) | Splitter(1) | Canvas(2) | Inspector(3)
        self.root.grid_columnconfigure(2, weight=1) 
        self.root.grid_columnconfigure(3, weight=0) 
        self.root.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.root.after(100, self.bind_shortcuts)
        if initial_file:
            self.check_ready_and_load(initial_file)

    def setup_ui(self):
        # --- RIBBON ---
        self.ribbon = ctk.CTkFrame(self.root, height=50, corner_radius=0, border_width=1, border_color="#333333")
        self.ribbon.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.ribbon.grid_columnconfigure((0, 1, 2), weight=1) 
        
        # Group 1: Navigation/File
        self.left_group = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.left_group.grid(row=0, column=0, sticky="w", padx=10)
        ctk.CTkButton(self.left_group, text="Open PDF", width=80, command=self.open_file, fg_color="#3d3d3d").pack(side="left", padx=2)
        ctk.CTkButton(self.left_group, text="+ Window", width=80, command=self.spawn_new_window, fg_color="#3d3d3d").pack(side="left", padx=2)
        ctk.CTkButton(self.left_group, text="▲", width=30, command=self.prev_page).pack(side="left", padx=2)
        ctk.CTkButton(self.left_group, text="▼", width=30, command=self.next_page).pack(side="left", padx=2)

        # Group 2: View Controls
        self.center_group = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.center_group.grid(row=0, column=1, sticky="n")
        ctk.CTkButton(self.center_group, text="-", width=30, command=lambda: self.adjust_zoom(-0.1)).pack(side="left", padx=5)
        self.zoom_label = ctk.CTkLabel(self.center_group, text="100%", width=50, font=("Segoe UI", 12, "bold"))
        self.zoom_label.pack(side="left")
        ctk.CTkButton(self.center_group, text="+", width=30, command=lambda: self.adjust_zoom(0.1)).pack(side="left", padx=5)
        ctk.CTkButton(self.center_group, text="Fit Page", width=80, command=self.zoom_to_fit).pack(side="left", padx=5)
        
        self.snap_var = ctk.BooleanVar(value=True)
        self.snap_switch = ctk.CTkSwitch(self.center_group, text="Text Snap", variable=self.snap_var)

        # Group 3: Note/Extraction Tools
        self.right_group = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.right_group.grid(row=0, column=2, sticky="e", padx=10)
        
        self.save_dropdown = ctk.CTkOptionMenu(
            self.right_group, 
            values=["Save Copy as PDF...", "Update Original File", "Snapshot Page as PNG"], 
            command=self.handle_save_action, 
            width=160
        )
        self.save_dropdown.set("File Actions")
        self.save_dropdown.pack(side="right", padx=5)

        ctk.CTkButton(self.right_group, text="Export Note(s)", width=110, fg_color="#2b7a78", command=self.export_comments).pack(side="right", padx=5)
        self.extract_mode_btn = ctk.CTkButton(self.right_group, text="Extract Page(s)", width=120, fg_color="#3d3d3d", command=self.toggle_extraction_mode)
        self.extract_mode_btn.pack(side="right", padx=5)
        self.save_extract_btn = ctk.CTkButton(self.right_group, text="Save Selection", width=100, fg_color="#28a745", command=self.execute_extraction)
        self.range_entry = ctk.CTkEntry(self.right_group, placeholder_text="e.g. 1-5, 10", width=100)
        self.range_entry.bind("<Return>", lambda e: self.apply_range_from_entry())
        self.highlight_btn = ctk.CTkButton(self.right_group, text="Highlight", width=80, fg_color="#4a4a4a", command=self.toggle_highlight_mode)
        self.highlight_btn.pack(side="right", padx=2)
        self.crop_btn = ctk.CTkButton(self.right_group, text="Crop", width=60, fg_color="#4a4a4a", command=self.toggle_crop_mode)
        self.crop_btn.pack(side="right", padx=2)
        self.apply_crop_btn = ctk.CTkButton(self.right_group, text="Apply", width=60, fg_color="#28a745", command=self.apply_crop)

        # --- PANELS ---
        self.left_panel = ctk.CTkFrame(self.root, width=280, corner_radius=0)
        self.left_panel.grid(row=1, column=0, sticky="nsew")
        self.nav_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.nav_container.pack(expand=True, fill="both")
        self.splitter = ctk.CTkButton(self.root, text="«", width=12, corner_radius=0, command=self.toggle_sidebar)
        self.splitter.grid(row=1, column=1, sticky="nsew")
        self.canvas_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.canvas_frame.grid(row=1, column=2, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1); self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas = PDFCanvas(self.canvas_frame)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Note Inspector (Hidden Initially)
        self.inspector_panel = ctk.CTkFrame(self.root, width=280, corner_radius=0, border_width=1, border_color="#333333")
        ctk.CTkLabel(self.inspector_panel, text="NOTE INSPECTOR", font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))
        self.created_info = ctk.CTkLabel(self.inspector_panel, text="Created: -", font=("Segoe UI", 10), text_color="#aaaaaa")
        self.created_info.pack(pady=0)
        self.modified_info = ctk.CTkLabel(self.inspector_panel, text="Modified: -", font=("Segoe UI", 10), text_color="#aaaaaa")
        self.modified_info.pack(pady=(0, 10))
        self.inspector_text = ctk.CTkTextbox(self.inspector_panel, width=260, height=300)
        self.inspector_text.pack(padx=10, pady=5)
        self.save_note_btn = ctk.CTkButton(self.inspector_panel, text="Update Note", fg_color="#28a745", command=self.save_inspector_note)
        self.save_note_btn.pack(pady=10)
        self.save_note_btn.configure(state="disabled")
        self.close_inspector_btn = ctk.CTkButton(self.inspector_panel, text="Close [X]", width=80, fg_color="#d35b5b", command=self.hide_inspector)
        self.close_inspector_btn.pack(pady=10)

        self.canvas.hover_callback = self.handle_hover
        self.canvas.double_click_callback = self.handle_double_click
        self.canvas.right_click_callback = self.handle_right_click
        self.status_label = ctk.CTkLabel(self.root, text=" Ready", anchor="w", height=25, fg_color="#1a1a1a")
        self.status_label.grid(row=2, column=0, columnspan=4, sticky="ew")

    # --- UPDATED KEYBOARD SHORTCUTS ---
    def bind_shortcuts(self):
        """Maps keys to functions. Fixed '+' binding for keypad and standard keys."""
        self.root.bind("<Up>", lambda e: self.prev_page())
        self.root.bind("<Down>", lambda e: self.next_page())
        self.root.bind("<MouseWheel>", self.handle_scroll)
        self.root.bind("<f>", lambda e: self.zoom_to_fit())
        self.root.bind("<b>", lambda e: self.reset_zoom())
        self.root.bind("<s>", lambda e: self.toggle_sidebar())
        self.root.bind("<h>", lambda e: self.toggle_highlight_mode())
        self.root.bind("<c>", lambda e: self.toggle_crop_mode())
        self.root.bind("<Control-e>", lambda e: self.export_comments())
        self.root.bind("<Control-s>", lambda e: self.save_overwrite())

        # Zoom In (+) variations
        self.root.bind("<plus>", lambda e: self.adjust_zoom(0.1))    # Numpad + or Shifted =
        self.root.bind("<KP_Add>", lambda e: self.adjust_zoom(0.1))  # Specific Numpad +
        self.root.bind("<equal>", lambda e: self.adjust_zoom(0.1))   # Standard = key (zoom without shift)

        # Zoom Out (-) variations
        self.root.bind("<minus>", lambda e: self.adjust_zoom(-0.1))
        self.root.bind("<KP_Subtract>", lambda e: self.adjust_zoom(-0.1))

    # --- COORDINATE & VIEW LOGIC ---
    def reset_zoom(self):
        self.current_zoom = 1.0
        self.update_zoom_view()

    def adjust_zoom(self, d):
        self.current_zoom += d
        self.update_zoom_view()

    def get_pdf_coords(self, cx, cy):
        if not self.engine: return 0, 0
        self.canvas.update()
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        page = self.engine.doc[self.current_page_index]
        rw, rh = page.rect.width * self.current_zoom, page.rect.height * self.current_zoom
        offset_x, offset_y = (max(cw, rw) - rw) / 2, (max(ch, rh) - rh) / 2
        return (cx - offset_x) / self.current_zoom, (cy - offset_y) / self.current_zoom

    # --- SAVE / EXPORT ---
    def handle_save_action(self, choice):
        if choice == "Update Original File": self.save_overwrite()
        elif choice == "Save Copy as PDF...": self.export_pdf()
        elif choice == "Snapshot Page as PNG": self.export_page_png()
        self.save_dropdown.set("File Actions")

    def export_page_png(self):
        if not self.engine: return
        path = filedialog.asksaveasfilename(title="Export PNG", defaultextension=".png", filetypes=[("PNG Image", "*.png")])
        if path:
            img = self.engine.get_display_page(self.current_page_index, zoom=2.0)
            img.save(path)
            self.status_label.configure(text=f" Snapshot saved: {os.path.basename(path)}")

    # --- INSPECTOR LOGIC ---
    def show_inspector(self):
        if not self.inspector_visible:
            self.inspector_panel.grid(row=1, column=3, sticky="nsew")
            self.inspector_visible = True; self.root.after(50, self.zoom_to_fit)

    def hide_inspector(self):
        if self.inspector_visible:
            self.inspector_panel.grid_remove()
            self.inspector_visible = False; self.active_note_coord = None
            self.root.after(50, self.zoom_to_fit)

    def handle_double_click(self, sx, sy):
        self.focus_note_in_inspector(self.get_pdf_coords(sx, sy))

    def focus_note_in_inspector(self, coords):
        content = self.engine.get_comment_at_pos(self.current_page_index, coords)
        if content:
            self.show_inspector()
            lines = content.split("\n")
            created_text, modified_text, body_text = "Created: -", "Modified: -", content
            if "---" in lines:
                idx = lines.index("---")
                body_text = "\n".join(lines[idx+1:])
                for line in lines[:idx]:
                    if line.startswith("CREATED:"): created_text = line.replace("CREATED:", "Created:")
                    if line.startswith("MODIFIED:"): modified_text = line.replace("MODIFIED:", "Modified:")
            self.created_info.configure(text=created_text)
            self.modified_info.configure(text=modified_text)
            self.inspector_text.delete("1.0", "end"); self.inspector_text.insert("1.0", body_text.strip())
            self.active_note_coord = coords; self.save_note_btn.configure(state="normal")

    def save_inspector_note(self):
        if self.active_note_coord and self.engine:
            new_text = self.inspector_text.get("1.0", "end-1c")
            self.engine.update_comment_at_pos(self.current_page_index, self.active_note_coord, new_text)
            self.load_page(self.current_page_index)

    # --- ANNOTATION MODES ---
    def apply_highlight(self, event):
        if not self.canvas.highlight_mode: return
        px = self.canvas.get_selection_pixels()
        if px:
            p1, p2 = self.get_pdf_coords(px[0], px[1]), self.get_pdf_coords(px[2], px[3])
            rect = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
            rects = self.engine.get_text_in_rect(self.current_page_index, rect) if self.snap_var.get() else [rect]
            self.engine.add_highlight(self.current_page_index, rects)
            self.load_page(self.current_page_index); self.sidebar.refresh_thumbnail(self.current_page_index)
            self.focus_note_in_inspector(rect[:2]); self.toggle_highlight_mode()

    def toggle_highlight_mode(self):
        if self.crop_btn.cget("text") == "Cancel Crop": self.toggle_crop_mode()
        is_on = self.highlight_btn.cget("text") == "Cancel Highlight"
        if not is_on:
            self.highlight_btn.configure(text="Cancel Highlight", fg_color="#d39e00")
            self.snap_switch.pack(side="left", padx=10); self.canvas.set_modes(highlight=True)
            self.canvas.bind("<ButtonRelease-1>", self.apply_highlight, add="+")
        else:
            self.highlight_btn.configure(text="Highlight", fg_color="#4a4a4a")
            self.snap_switch.pack_forget(); self.canvas.set_modes(highlight=False)
            self.canvas.unbind("<ButtonRelease-1>")

    def toggle_crop_mode(self):
        if self.highlight_btn.cget("text") == "Cancel Highlight": self.toggle_highlight_mode()
        is_on = self.crop_btn.cget("text") == "Cancel Crop"
        if not is_on:
            self.crop_btn.configure(text="Cancel Crop", fg_color="#d35b5b")
            self.apply_crop_btn.pack(side="right", padx=5); self.canvas.set_modes(crop=True)
        else:
            self.crop_btn.configure(text="Crop", fg_color="#4a4a4a")
            self.apply_crop_btn.pack_forget(); self.canvas.set_modes(crop=False)

    def apply_crop(self):
        px = self.canvas.get_selection_pixels()
        if px:
            p1, p2 = self.get_pdf_coords(px[0], px[1]), self.get_pdf_coords(px[2], px[3])
            rect = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
            self.engine.crop_page(self.current_page_index, rect)
            self.toggle_crop_mode(); self.zoom_to_fit()
            self.sidebar.refresh_thumbnail(self.current_page_index)

    # --- NAVIGATION & UTILITIES ---
    def load_page(self, idx):
        if self.engine:
            self.current_page_index = idx
            img = self.engine.get_display_page(idx, zoom=self.current_zoom)
            self.canvas.display_page(img)
            if self.sidebar:
                self.sidebar.highlight_active(idx)
                self.root.after(200, lambda: self.sidebar.scroll_to_page(idx))
            self.status_label.configure(text=f" Page {idx+1} of {len(self.engine.doc)}")

    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if p: self.load_external_file(p)

    def load_external_file(self, path):
        if path and os.path.exists(path):
            self.current_file_path = path; self.clear_nav_area(); self.engine = PDFEngine(path)
            self.sidebar = Sidebar(self.nav_container, self.engine, self.load_page, self.rotate_page)
            self.sidebar.pack(expand=True, fill="both", pady=5); self.zoom_to_fit(); self.load_page(0)

    def spawn_new_window(self):
        from core.session import SessionManager
        new_window = ctk.CTkToplevel(self.root)
        new_window.title("PDF Suite v1.0 - Secondary Window")
        try: new_window.after(200, lambda: new_window.iconbitmap(self.root.wm_iconbitmap()))
        except: pass
        MainWindow(new_window, SessionManager())

    def toggle_sidebar(self):
        if self.sidebar_visible: self.left_panel.grid_remove(); self.splitter.configure(text="»")
        else: self.left_panel.grid(); self.splitter.configure(text="«")
        self.sidebar_visible = not self.sidebar_visible; self.root.after(50, self.zoom_to_fit)

    def next_page(self):
        if self.engine and self.current_page_index < len(self.engine.doc)-1: self.load_page(self.current_page_index + 1)
    def prev_page(self):
        if self.engine and self.current_page_index > 0: self.load_page(self.current_page_index - 1)
    def handle_scroll(self, e):
        if e.delta > 0: self.prev_page()
        else: self.next_page()
    def zoom_to_fit(self):
        if not self.engine: return
        self.root.update(); cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        p = self.engine.doc[self.current_page_index]
        if cw > 40:
            self.current_zoom = min((cw*0.9)/p.rect.width, (ch*0.9)/p.rect.height); self.update_zoom_view()
    def update_zoom_view(self):
        if self.engine: self.zoom_label.configure(text=f"{int(self.current_zoom*100)}%"); self.load_page(self.current_page_index)
    def save_overwrite(self):
        if self.engine and self.current_file_path:
            if messagebox.askyesno("Confirm", "Update original file?"): self.engine.save_file(self.current_file_path)
    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path: self.engine.save_file(path)
    def export_comments(self):
        if not self.engine: return
        d = self.engine.get_all_comments()
        if not d: return messagebox.showinfo("Info", "No notes found.")
        path = filedialog.asksaveasfilename(title="Export Note(s)", defaultextension=".csv")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=["Page", "User", "Created At", "Last Modified", "Comment"])
                w.writeheader(); w.writerows(d)
    def handle_hover(self, sx, sy):
        if self.engine and not (self.canvas.crop_mode or self.canvas.highlight_mode or self.extraction_mode):
            c = self.engine.get_comment_at_pos(self.current_page_index, self.get_pdf_coords(sx, sy))
            if c:
                display_text = c.split("---\n", 1)[1] if "---" in c else c
                self.status_label.configure(text=f" Note: {display_text[:75]}...", text_color="#ffcc00")
            else: self.status_label.configure(text=f" Page {self.current_page_index+1}", text_color="white")
    def handle_right_click(self, sx, sy, rx, ry):
        if not self.engine: return
        coords = self.get_pdf_coords(sx, sy)
        if self.engine.get_comment_at_pos(self.current_page_index, coords):
            m = Menu(self.root, tearoff=0); m.add_command(label="Delete Note", command=lambda: self.confirm_delete(coords)); m.post(rx, ry)
    def confirm_delete(self, c):
        if self.engine.delete_highlight(self.current_page_index, c): self.load_page(self.current_page_index); self.sidebar.refresh_thumbnail(self.current_page_index)
    def toggle_extraction_mode(self):
        self.extraction_mode = not self.extraction_mode
        if self.extraction_mode:
            self.extract_mode_btn.configure(text="Cancel", fg_color="#d35b5b")
            self.range_entry.pack(side="right", padx=2); self.save_extract_btn.pack(side="right", padx=5)
            if self.sidebar: self.sidebar.toggle_extraction_mode(True)
        else:
            self.extract_mode_btn.configure(text="Extract Page(s)", fg_color="#3d3d3d")
            self.range_entry.pack_forget(); self.save_extract_btn.pack_forget()
            if self.sidebar: self.sidebar.toggle_extraction_mode(False)
    def execute_extraction(self):
        sel = self.sidebar.selected_pages
        if not sel: return messagebox.showwarning("Empty", "Select pages first.")
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path: self.engine.extract_pages(list(sel), path)
    def apply_range_from_entry(self):
        txt = self.range_entry.get()
        if not txt or not self.engine: return
        try:
            idx = []
            for p in txt.split(','):
                if '-' in p: s, e = map(int, p.strip().split('-')); idx.extend(range(s-1, e))
                else: idx.append(int(p.strip())-1)
            valid = [i for i in sorted(set(idx)) if 0 <= i < len(self.engine.doc)]
            if self.sidebar: self.sidebar.select_range(valid)
        except: messagebox.showerror("Range Error", "Invalid format.")
    def rotate_page(self, idx): self.engine.rotate_page(idx); self.sidebar.refresh_thumbnail(idx); self.load_page(idx) if idx == self.current_page_index else None
    def clear_nav_area(self):
        if self.sidebar: self.sidebar.stop_loading()
        for c in self.nav_container.winfo_children(): c.destroy()
        self.sidebar = None
    def check_ready_and_load(self, p, a=0):
        self.root.update()
        if self.canvas.winfo_width() > 100: self.load_external_file(p)
        elif a < 30: self.root.after(100, lambda: self.check_ready_and_load(p, a+1))