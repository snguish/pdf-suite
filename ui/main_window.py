import customtkinter as ctk
import csv, io, os
from tkinter import filedialog, messagebox, Menu
from PIL import Image, ImageDraw, ImageFont
from core.engine import PDFEngine
from ui.sidebar import Sidebar
from ui.canvas import PDFCanvas
from ui.layout import DEFAULT_SIDEBAR_WIDTH, clamp_sidebar_width, layout_mode
from ui.tooltip import ToolTip
from ui.menu_bar import DarkMenuBar

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
        self.pending_signature_bytes = None
        self._auto_hidden_sidebar = False
        self.form_controls = {}
        self._forms_page_index = None
        self.sidebar_width = DEFAULT_SIDEBAR_WIDTH
        self._layout_mode = None
        self._resize_job = None

        # 4-Column Layout: Sidebar(0) | Splitter(1) | Canvas(2) | Inspector(3)
        self.root.grid_columnconfigure(2, weight=1) 
        self.root.grid_columnconfigure(3, weight=0) 
        self.root.grid_rowconfigure(1, weight=1)

        self.setup_ui()
        self.root.bind("<Configure>", self._schedule_responsive_layout, add="+")
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.after(100, self.bind_shortcuts)
        if initial_file:
            self.check_ready_and_load(initial_file)

    def setup_ui(self):
        self.top_chrome = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.top_chrome.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.setup_menu()
        # --- TOOLBAR ---
        self.ribbon = ctk.CTkFrame(self.top_chrome, height=54, corner_radius=0, border_width=1, border_color="#3f4650")
        self.ribbon.pack(fill="x")
        self.ribbon.grid_propagate(False)
        self.ribbon.grid_columnconfigure((0, 1, 2), weight=1) 
        
        # Group 1: Navigation/File
        self.left_group = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.left_group.grid(row=0, column=0, sticky="w", padx=12, pady=8)
        self.open_btn = ctk.CTkButton(self.left_group, text="Open", width=62, command=self.open_file, fg_color="#454b54")
        self.open_btn.pack(side="left", padx=3)
        self.save_btn = ctk.CTkButton(self.left_group, text="Save", width=62, command=self.save_overwrite, fg_color="#454b54")
        self.save_btn.pack(side="left", padx=3)
        self.prev_btn = ctk.CTkButton(self.left_group, text="‹", width=32, command=self.prev_page)
        self.prev_btn.pack(side="left", padx=(10, 3))
        self.page_entry = ctk.CTkEntry(self.left_group, width=42, justify="center", placeholder_text="—")
        self.page_entry.pack(side="left", padx=2)
        self.page_entry.bind("<Return>", self.go_to_page_from_entry)
        self.page_total_label = ctk.CTkLabel(self.left_group, text="/ —", width=42, anchor="w")
        self.page_total_label.pack(side="left")
        self.next_btn = ctk.CTkButton(self.left_group, text="›", width=32, command=self.next_page)
        self.next_btn.pack(side="left", padx=3)

        # Group 2: View Controls
        self.center_group = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.center_group.grid(row=0, column=1, sticky="n", pady=8)
        ctk.CTkButton(self.center_group, text="-", width=30, command=lambda: self.adjust_zoom(-0.1)).pack(side="left", padx=5)
        self.zoom_label = ctk.CTkLabel(self.center_group, text="100%", width=50, font=("Segoe UI", 12, "bold"))
        self.zoom_label.pack(side="left")
        ctk.CTkButton(self.center_group, text="+", width=30, command=lambda: self.adjust_zoom(0.1)).pack(side="left", padx=5)
        ctk.CTkButton(self.center_group, text="Fit Page", width=72, command=self.zoom_to_fit).pack(side="left", padx=(8, 2))
        ctk.CTkButton(self.center_group, text="Fit Width", width=76, command=self.zoom_to_width).pack(side="left", padx=2)
        
        self.snap_var = ctk.BooleanVar(value=True)
        self.snap_switch = ctk.CTkSwitch(self.center_group, text="Text Snap", variable=self.snap_var)

        # Group 3: Note/Extraction Tools
        self.right_group = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.right_group.grid(row=0, column=2, sticky="e", padx=12, pady=8)
        
        self.save_dropdown = ctk.CTkOptionMenu(
            self.right_group, 
            values=["Save Copy as PDF...", "Update Original File", "Snapshot Page as PNG"], 
            command=self.handle_save_action, 
            width=160
        )
        self.save_dropdown.set("File Actions")
        self.save_dropdown.pack(side="right", padx=5)

        self.context_btn = ctk.CTkButton(self.right_group, text="Details", width=68, fg_color="#3d3d3d", command=self.toggle_inspector)
        self.context_btn.pack(side="right", padx=2)
        self.extract_mode_btn = ctk.CTkButton(self.right_group, text="Extract Page(s)", width=120, fg_color="#3d3d3d", command=self.toggle_extraction_mode)
        self.save_extract_btn = ctk.CTkButton(self.right_group, text="Save Selection", width=100, fg_color="#28a745", command=self.execute_extraction)
        self.range_entry = ctk.CTkEntry(self.right_group, placeholder_text="e.g. 1-5, 10", width=100)
        self.range_entry.bind("<Return>", lambda e: self.apply_range_from_entry())
        self.apply_crop_btn = ctk.CTkButton(self.right_group, text="Apply Crop", width=84, fg_color="#28a745", command=self.apply_crop)

        # --- PANELS ---
        self.left_panel = ctk.CTkFrame(self.root, width=self.sidebar_width, corner_radius=0, border_width=1, border_color="#3f4650")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid(row=1, column=0, sticky="nsew")
        self.nav_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.nav_container.pack(expand=True, fill="both")
        self.splitter = ctk.CTkButton(self.root, text="«", width=14, corner_radius=0, command=self.toggle_sidebar, fg_color="#30363d")
        self.splitter.grid(row=1, column=1, sticky="nsew")
        self.splitter.bind("<ButtonPress-1>", self._start_sidebar_resize, add="+")
        self.splitter.bind("<B1-Motion>", self._resize_sidebar, add="+")
        self.canvas_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.canvas_frame.grid(row=1, column=2, sticky="nsew")
        self.canvas_frame.grid_rowconfigure(0, weight=1); self.canvas_frame.grid_columnconfigure(1, weight=1)
        self.tool_rail = ctk.CTkFrame(self.canvas_frame, width=72, corner_radius=0)
        self.tool_rail.grid(row=0, column=0, sticky="ns")
        ctk.CTkLabel(self.tool_rail, text="TOOLS", font=("Segoe UI", 9, "bold"), text_color="#b8c0cc").pack(pady=(10, 6))
        self.pointer_btn = ctk.CTkButton(self.tool_rail, text="Pointer", width=62, command=self.activate_pointer_mode, border_width=2, border_color="#8cc8ff")
        self.pointer_btn.pack(padx=5, pady=3)
        self.highlight_btn = ctk.CTkButton(self.tool_rail, text="Highlight", width=62, fg_color="#3d3d3d", command=self.toggle_highlight_mode)
        self.highlight_btn.pack(padx=5, pady=3)
        self.crop_btn = ctk.CTkButton(self.tool_rail, text="Crop", width=62, fg_color="#3d3d3d", command=self.toggle_crop_mode)
        self.crop_btn.pack(padx=5, pady=3)
        self.forms_btn = ctk.CTkButton(self.tool_rail, text="Forms", width=62, fg_color="#454b54", command=lambda: self.open_context_tab("Forms"))
        self.forms_btn.pack(padx=5, pady=(14, 3))
        self.sign_btn = ctk.CTkButton(self.tool_rail, text="Sign", width=62, fg_color="#454b54", command=lambda: self.open_context_tab("Sign"))
        self.sign_btn.pack(padx=5, pady=3)
        self.canvas = PDFCanvas(self.canvas_frame)
        self.canvas.grid(row=0, column=1, sticky="nsew")
        
        # Reusable contextual workspace (hidden initially)
        self.inspector_panel = ctk.CTkFrame(self.root, width=280, corner_radius=0, border_width=1, border_color="#3f4650")
        self.inspector_panel.grid_propagate(False)
        context_header = ctk.CTkFrame(self.inspector_panel, fg_color="transparent")
        context_header.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkLabel(context_header, text="DOCUMENT DETAILS", font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkButton(context_header, text="X", width=28, fg_color="transparent", command=self.hide_inspector).pack(side="right")
        self.context_tabs = ctk.CTkTabview(self.inspector_panel, width=280)
        self.context_tabs.pack(expand=True, fill="both", padx=6, pady=6)
        self.note_tab = self.context_tabs.add("Notes")
        self.forms_tab = self.context_tabs.add("Forms")
        self.sign_tab = self.context_tabs.add("Sign")

        self.created_info = ctk.CTkLabel(self.note_tab, text="Created: -", font=("Segoe UI", 10), text_color="#aaaaaa")
        self.created_info.pack(pady=0)
        self.modified_info = ctk.CTkLabel(self.note_tab, text="Modified: -", font=("Segoe UI", 10), text_color="#aaaaaa")
        self.modified_info.pack(pady=(0, 10))
        self.inspector_text = ctk.CTkTextbox(self.note_tab, width=250, height=300)
        self.inspector_text.pack(expand=True, fill="both", padx=6, pady=5)
        self.save_note_btn = ctk.CTkButton(self.note_tab, text="Update Note", fg_color="#28a745", command=self.save_inspector_note)
        self.save_note_btn.pack(pady=10)
        self.save_note_btn.configure(state="disabled")
        self.forms_content = ctk.CTkScrollableFrame(self.forms_tab, fg_color="transparent")
        self.forms_content.pack(expand=True, fill="both")
        ctk.CTkLabel(
            self.sign_tab,
            text="VISUAL SIGNATURE",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(
            self.sign_tab,
            text="Placed signatures become permanent page content.\nThey are not certificate-backed digital signatures.",
            text_color="#aaaaaa",
            justify="left",
            wraplength=240,
        ).pack(anchor="w", padx=8, pady=(0, 12))
        ctk.CTkButton(self.sign_tab, text="Import Signature Image...", command=self.choose_signature_image).pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(self.sign_tab, text="Draw Signature...", command=self.open_signature_pad).pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(self.sign_tab, text="Typed signature", anchor="w").pack(fill="x", padx=8, pady=(14, 2))
        self.typed_signature_entry = ctk.CTkEntry(self.sign_tab, placeholder_text="Enter signer name")
        self.typed_signature_entry.pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(self.sign_tab, text="Place Typed Signature", command=self.prepare_typed_signature).pack(fill="x", padx=8, pady=4)
        self.signature_status = ctk.CTkLabel(
            self.sign_tab,
            text="Choose a signature, then drag its area on the page.",
            text_color="#aaaaaa",
            justify="left",
            wraplength=240,
        )
        self.signature_status.pack(anchor="w", padx=8, pady=14)

        self.canvas.hover_callback = self.handle_hover
        self.canvas.double_click_callback = self.handle_double_click
        self.canvas.right_click_callback = self.handle_right_click
        self.canvas.wheel_callback = self.handle_canvas_wheel
        self.canvas.selection_callback = self.handle_selection_release
        self.status_label = ctk.CTkLabel(self.root, text="  Ready   |   Page — / —   |   Zoom 100%   |   Saved", anchor="w", height=28, fg_color="#111827", text_color="#e5e7eb", font=("Segoe UI", 11, "bold"))
        self.status_label.grid(row=2, column=0, columnspan=4, sticky="ew")
        self._standardize_controls()
        self._install_tooltips()

    def _standardize_controls(self):
        """Apply one compact, high-contrast control language across the window."""
        def visit(widget):
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(height=32, font=("Segoe UI", 11, "bold"), hover_color="#596270")
                    self._add_focus_ring(child)
                elif isinstance(child, (ctk.CTkEntry, ctk.CTkOptionMenu)):
                    child.configure(height=32, font=("Segoe UI", 11))
                    self._add_focus_ring(child)
                visit(child)
        visit(self.root)
        self.save_note_btn.configure(text_color_disabled="#9ca3af")

    def _add_focus_ring(self, widget):
        """Expose keyboard focus on composite CustomTkinter controls."""
        try:
            widget.configure(takefocus=True, border_width=1, border_color="#596270")
            widget.bind("<FocusIn>", lambda _e, w=widget: w.configure(border_width=2, border_color="#8cc8ff"), add="+")
            widget.bind("<FocusOut>", lambda _e, w=widget: w.configure(border_width=1, border_color="#596270"), add="+")
        except (ValueError, TypeError):
            pass

    def _install_tooltips(self):
        tips = (
            (self.pointer_btn, "Pointer (Esc): select and inspect the page"),
            (self.highlight_btn, "Highlight (H): drag over text or an area"),
            (self.crop_btn, "Crop (C): drag the new page boundary"),
            (self.forms_btn, "Forms: inspect fields on the current page"),
            (self.sign_btn, "Sign: place a visual signature"),
        )
        self._tooltips = [ToolTip(widget, message) for widget, message in tips]

    def _schedule_responsive_layout(self, event):
        if event.widget is not self.root:
            return
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(60, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        self._resize_job = None
        width = self.root.winfo_width()
        mode = layout_mode(width)

        # Two toolbar rows keep every action usable at the supported narrow sizes.
        if width < 1100:
            self.ribbon.configure(height=96)
            self.left_group.grid_configure(row=0, column=0, columnspan=2, sticky="w", pady=(7, 2))
            self.right_group.grid_configure(row=0, column=2, sticky="e", pady=(7, 2))
            self.center_group.grid_configure(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(2, 7))
        else:
            self.ribbon.configure(height=54)
            self.left_group.grid_configure(row=0, column=0, columnspan=1, sticky="w", padx=12, pady=8)
            self.center_group.grid_configure(row=0, column=1, columnspan=1, sticky="n", padx=0, pady=8)
            self.right_group.grid_configure(row=0, column=2, sticky="e", pady=8)

        if mode == "drawer":
            self.splitter.grid_remove()
            if self.inspector_visible and self.sidebar_visible:
                self.left_panel.grid_remove()
                self.left_panel.place_forget()
                self.sidebar_visible = False
                self._auto_hidden_sidebar = True
            if self.sidebar_visible:
                self._place_drawer(self.left_panel, "left", self.sidebar_width)
            if self.inspector_visible:
                self._place_drawer(self.inspector_panel, "right", min(320, width - 80))
        else:
            self.left_panel.place_forget()
            self.inspector_panel.place_forget()
            if self.sidebar_visible:
                self.left_panel.grid(row=1, column=0, sticky="nsew")
            self.splitter.grid(row=1, column=1, sticky="nsew")
            if self.inspector_visible:
                self.inspector_panel.grid(row=1, column=3, sticky="nsew")
        self._layout_mode = mode

    def _place_drawer(self, panel, side, width):
        panel.grid_remove()
        panel.lift()
        x = 0 if side == "left" else self.root.winfo_width() - width
        chrome_height = self.top_chrome.winfo_height()
        height = max(1, self.root.winfo_height() - chrome_height - self.status_label.winfo_height())
        panel.configure(width=width, height=height)
        panel.place(x=x, y=chrome_height)

    def _start_sidebar_resize(self, event):
        self._resize_origin_x = event.x_root
        self._resize_origin_width = self.sidebar_width

    def _resize_sidebar(self, event):
        if self._layout_mode == "drawer":
            return
        self.sidebar_width = clamp_sidebar_width(self._resize_origin_width + event.x_root - self._resize_origin_x)
        self.left_panel.configure(width=self.sidebar_width)

    def setup_menu(self):
        menus = [
            ("File", [
                {"label": "Open PDF...", "accelerator": "Ctrl+O", "command": self.open_file},
                None,
                {"label": "Save", "accelerator": "Ctrl+S", "command": self.save_overwrite},
                {"label": "Save Copy as...", "accelerator": "Ctrl+Shift+S", "command": self.export_pdf},
                {"label": "Export Notes...", "accelerator": "Ctrl+E", "command": self.export_comments},
                None,
                {"label": "Close", "command": self.close_window},
            ]),
            ("Pages", [
                {"label": "Combine PDFs...", "command": self.combine_pdfs},
                {"label": "Extract Pages...", "command": self.toggle_extraction_mode},
            ]),
            ("View", [
                {"label": "Zoom In", "accelerator": "+", "command": lambda: self.adjust_zoom(0.1)},
                {"label": "Zoom Out", "accelerator": "-", "command": lambda: self.adjust_zoom(-0.1)},
                {"label": "Actual Size", "accelerator": "Ctrl+1", "command": self.reset_zoom},
                {"label": "Fit Page", "accelerator": "Ctrl+0", "command": self.zoom_to_fit},
                {"label": "Fit Width", "accelerator": "Ctrl+2", "command": self.zoom_to_width},
                None,
                {"label": "Toggle Thumbnails", "accelerator": "S", "command": self.toggle_sidebar},
                {"label": "Toggle Details", "accelerator": "Ctrl+D", "command": self.toggle_inspector},
            ]),
        ]
        self.menu_bar = DarkMenuBar(self.top_chrome, menus)
        self.menu_bar.pack(fill="x")

    # --- UPDATED KEYBOARD SHORTCUTS ---
    def bind_shortcuts(self):
        """Maps keys to functions. Fixed '+' binding for keypad and standard keys."""
        self.root.bind("<Up>", lambda e: self.run_shortcut(e, self.prev_page))
        self.root.bind("<Down>", lambda e: self.run_shortcut(e, self.next_page))
        self.root.bind("<Prior>", lambda e: self.run_shortcut(e, self.prev_page))
        self.root.bind("<Next>", lambda e: self.run_shortcut(e, self.next_page))
        self.root.bind("<MouseWheel>", self.handle_scroll)
        self.root.bind("<f>", lambda e: self.run_shortcut(e, self.zoom_to_fit))
        self.root.bind("<b>", lambda e: self.run_shortcut(e, self.reset_zoom))
        self.root.bind("<s>", lambda e: self.run_shortcut(e, self.toggle_sidebar))
        self.root.bind("<h>", lambda e: self.run_shortcut(e, self.toggle_highlight_mode))
        self.root.bind("<c>", lambda e: self.run_shortcut(e, self.toggle_crop_mode))
        self.root.bind("<Escape>", lambda e: self.cancel_active_tool())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-e>", lambda e: self.export_comments())
        self.root.bind("<Control-s>", lambda e: self.save_overwrite())
        self.root.bind("<Control-Shift-S>", lambda e: self.export_pdf())
        self.root.bind("<Control-Key-0>", lambda e: self.zoom_to_fit())
        self.root.bind("<Control-Key-1>", lambda e: self.reset_zoom())
        self.root.bind("<Control-Key-2>", lambda e: self.zoom_to_width())
        self.root.bind("<Control-d>", lambda e: self.run_shortcut(e, self.toggle_inspector))
        self.root.bind("<Control-Alt-f>", lambda e: self.run_shortcut(e, lambda: self.open_context_tab("Forms")))
        self.root.bind("<Control-Alt-s>", lambda e: self.run_shortcut(e, lambda: self.open_context_tab("Sign")))

        # Zoom In (+) variations
        self.root.bind("<plus>", lambda e: self.adjust_zoom(0.1))    # Numpad + or Shifted =
        self.root.bind("<KP_Add>", lambda e: self.adjust_zoom(0.1))  # Specific Numpad +
        self.root.bind("<equal>", lambda e: self.adjust_zoom(0.1))   # Standard = key (zoom without shift)

        # Zoom Out (-) variations
        self.root.bind("<minus>", lambda e: self.adjust_zoom(-0.1))
        self.root.bind("<KP_Subtract>", lambda e: self.adjust_zoom(-0.1))

    def run_shortcut(self, event, callback):
        """Do not trigger single-key document shortcuts while the user types."""
        widget_class = event.widget.winfo_class()
        if widget_class in {"Entry", "Text", "TEntry", "TCombobox", "Spinbox"}:
            return None
        callback()
        return "break"

    def cancel_active_tool(self):
        if self.highlight_btn.cget("text") == "Cancel Highlight":
            self.toggle_highlight_mode()
        elif self.crop_btn.cget("text") == "Cancel Crop":
            self.toggle_crop_mode()
        elif self.canvas.signature_mode:
            self.cancel_signature_placement()
        elif self.extraction_mode:
            self.toggle_extraction_mode()

    # --- COORDINATE & VIEW LOGIC ---
    def reset_zoom(self):
        self.current_zoom = 1.0
        self.update_zoom_view()

    def adjust_zoom(self, d):
        self.current_zoom = max(0.1, min(8.0, self.current_zoom + d))
        self.update_zoom_view()

    def zoom_at_pointer(self, delta, widget_x, widget_y):
        """Zoom while keeping the PDF location under the pointer stationary."""
        if not self.engine:
            return

        old_zoom = self.current_zoom
        new_zoom = max(0.1, min(8.0, old_zoom + delta))
        if new_zoom == old_zoom:
            return

        old_canvas_x = self.canvas.canvasx(widget_x)
        old_canvas_y = self.canvas.canvasy(widget_y)
        pdf_x, pdf_y = self.get_pdf_coords(old_canvas_x, old_canvas_y)

        self.current_zoom = new_zoom
        self.zoom_label.configure(text=f"{int(new_zoom * 100)}%")
        self.load_page(self.current_page_index)
        self.canvas.update_idletasks()

        page = self.engine.doc[self.current_page_index]
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        rendered_w = page.rect.width * new_zoom
        rendered_h = page.rect.height * new_zoom
        region_w = max(cw, rendered_w)
        region_h = max(ch, rendered_h)
        offset_x = (region_w - rendered_w) / 2
        offset_y = (region_h - rendered_h) / 2

        target_x = offset_x + pdf_x * new_zoom
        target_y = offset_y + pdf_y * new_zoom
        if region_w > cw:
            self.canvas.xview_moveto(max(0.0, min(1.0, (target_x - widget_x) / region_w)))
        if region_h > ch:
            self.canvas.yview_moveto(max(0.0, min(1.0, (target_y - widget_y) / region_h)))

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
            mode = layout_mode(self.root.winfo_width())
            if mode in {"compact", "drawer"} and self.sidebar_visible:
                self.left_panel.grid_remove()
                self.left_panel.place_forget()
                self.splitter.configure(text="»")
                self.sidebar_visible = False
                self._auto_hidden_sidebar = True
            self.inspector_visible = True
            self.context_btn.configure(text="Hide Details", width=88)
            if mode == "drawer":
                self._place_drawer(self.inspector_panel, "right", min(320, self.root.winfo_width() - 80))
            else:
                self.inspector_panel.grid(row=1, column=3, sticky="nsew")
            self.root.after(50, self.zoom_to_fit)

    def hide_inspector(self):
        if self.inspector_visible:
            self.inspector_panel.grid_remove()
            self.inspector_panel.place_forget()
            self.inspector_visible = False; self.active_note_coord = None
            self.context_btn.configure(text="Details", width=68)
            if self._auto_hidden_sidebar:
                self.splitter.configure(text="«")
                self.sidebar_visible = True
                if layout_mode(self.root.winfo_width()) == "drawer":
                    self._place_drawer(self.left_panel, "left", self.sidebar_width)
                else:
                    self.left_panel.grid(row=1, column=0, sticky="nsew")
            self._auto_hidden_sidebar = False
            self.root.after(50, self.zoom_to_fit)

    def open_context_tab(self, tab_name):
        self.show_inspector()
        self.context_tabs.set(tab_name)

    def toggle_inspector(self):
        if self.inspector_visible:
            self.hide_inspector()
        else:
            self.show_inspector()

    def handle_double_click(self, sx, sy):
        self.focus_note_in_inspector(self.get_pdf_coords(sx, sy))

    def focus_note_in_inspector(self, coords):
        content = self.engine.get_comment_at_pos(self.current_page_index, coords)
        if content:
            self.show_inspector()
            self.context_tabs.set("Notes")
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
            self.mark_document_changed()
            self.load_page(self.current_page_index)

    # --- PDF FORM FIELDS ---
    def refresh_form_fields(self):
        self._forms_page_index = self.current_page_index if self.engine else None
        self.form_controls.clear()
        for child in self.forms_content.winfo_children():
            child.destroy()

        if not self.engine:
            ctk.CTkLabel(self.forms_content, text="Open a PDF to inspect form fields.", text_color="#aaaaaa").pack(pady=20)
            return

        fields = self.engine.get_form_fields(self.current_page_index)
        if not fields:
            ctk.CTkLabel(
                self.forms_content,
                text="No interactive form fields\non this page.",
                text_color="#aaaaaa",
                justify="center",
            ).pack(pady=20)
            return

        ctk.CTkLabel(
            self.forms_content,
            text=f"{len(fields)} field(s) on page {self.current_page_index + 1}",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=6, pady=(4, 10))

        radio_groups = {}
        for field in fields:
            if field["kind"] == "radio":
                radio_groups.setdefault(field["name"], []).append(field)
                continue
            self.add_form_control(field)

        for name, group in radio_groups.items():
            frame = ctk.CTkFrame(self.forms_content, fg_color="transparent")
            frame.pack(fill="x", padx=4, pady=5)
            ctk.CTkLabel(frame, text=group[0]["label"], anchor="w").pack(fill="x")
            variable = ctk.StringVar(value=str(group[0]["value"] or ""))
            for field in group:
                option = str(field["on_value"] or field["value"] or "Option")
                ctk.CTkRadioButton(
                    frame,
                    text=option,
                    variable=variable,
                    value=option,
                    state="disabled" if field["read_only"] else "normal",
                ).pack(anchor="w", padx=8, pady=2)
            self.form_controls[f"radio:{name}"] = ("radio", variable, group)

        ctk.CTkButton(
            self.forms_content,
            text="Apply Form Changes",
            fg_color="#28a745",
            command=self.apply_form_changes,
        ).pack(fill="x", padx=6, pady=14)

    def add_form_control(self, field):
        frame = ctk.CTkFrame(self.forms_content, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=5)
        label_text = field["label"]
        if field["read_only"]:
            label_text += " (read-only)"
        ctk.CTkLabel(frame, text=label_text, anchor="w").pack(fill="x")
        state = "disabled" if field["read_only"] else "normal"

        if field["kind"] == "checkbox":
            variable = ctk.BooleanVar(value=str(field["value"]).lower() not in {"", "0", "false", "off", "none"})
            control = ctk.CTkCheckBox(frame, text="Selected", variable=variable, state=state)
            kind = "checkbox"
        elif field["kind"] == "choice" and field["choices"]:
            value = str(field["value"] or field["choices"][0])
            choices = [str(choice) for choice in field["choices"]]
            if value not in choices:
                choices.insert(0, value)
            variable = ctk.StringVar(value=value)
            control = ctk.CTkOptionMenu(frame, values=choices, variable=variable, state=state)
            kind = "choice"
        elif field["kind"] == "signature":
            variable = ctk.StringVar(value="")
            control = ctk.CTkLabel(frame, text="Certificate signature field (not editable here)", text_color="#aaaaaa")
            kind = "signature"
        else:
            variable = ctk.StringVar(value=str(field["value"] or ""))
            control = ctk.CTkEntry(frame, textvariable=variable, state=state)
            kind = "text"

        control.pack(fill="x", pady=(2, 0))
        self.form_controls[field["xref"]] = (kind, variable, field)

    def apply_form_changes(self):
        if not self.engine:
            return
        updated = 0
        try:
            for key, (kind, variable, field_data) in self.form_controls.items():
                if kind == "signature":
                    continue
                if kind == "radio":
                    fields = field_data
                    if fields and all(field["read_only"] for field in fields):
                        continue
                    if fields and self.engine.update_form_field(self.current_page_index, fields[0]["xref"], variable.get()):
                        updated += 1
                    continue
                if field_data["read_only"]:
                    continue
                if self.engine.update_form_field(self.current_page_index, key, variable.get()):
                    updated += 1
        except Exception as exc:
            messagebox.showerror("Form Error", f"Could not update the form:\n{exc}")
            return

        if updated:
            self.mark_document_changed()
            self._forms_page_index = None
            self.load_page(self.current_page_index)
            self.context_tabs.set("Forms")
            self.status_label.configure(text=f" Updated {updated} form field(s)")

    # --- VISUAL SIGNATURES ---
    def choose_signature_image(self):
        path = filedialog.askopenfilename(
            title="Choose Signature Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")],
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                signature = image.convert("RGBA")
                signature.thumbnail((1600, 600), Image.Resampling.LANCZOS)
                stream = io.BytesIO()
                signature.save(stream, format="PNG")
            self.prepare_signature(stream.getvalue(), os.path.basename(path))
        except Exception as exc:
            messagebox.showerror("Signature Error", f"Could not read the signature image:\n{exc}")

    def prepare_typed_signature(self):
        text = self.typed_signature_entry.get().strip()
        if not text:
            messagebox.showinfo("Typed Signature", "Enter the signer name first.")
            return
        try:
            font = None
            for font_path in (
                r"C:\Windows\Fonts\segoesc.ttf",
                r"C:\Windows\Fonts\ariali.ttf",
            ):
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, 72)
                    break
            if font is None:
                font = ImageFont.load_default()
            probe = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
            bounds = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font, stroke_width=1)
            width = max(20, bounds[2] - bounds[0] + 20)
            height = max(20, bounds[3] - bounds[1] + 20)
            signature = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            ImageDraw.Draw(signature).text((10 - bounds[0], 10 - bounds[1]), text, fill=(20, 40, 90, 255), font=font, stroke_width=1)
            stream = io.BytesIO()
            signature.save(stream, format="PNG")
            self.prepare_signature(stream.getvalue(), f"Typed: {text}")
        except Exception as exc:
            messagebox.showerror("Signature Error", f"Could not create the typed signature:\n{exc}")

    def open_signature_pad(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Draw Signature")
        dialog.geometry("680x300")
        dialog.transient(self.root)
        strokes = []
        active_stroke = []
        pad = ctk.CTkCanvas(dialog, width=640, height=190, bg="white", highlightthickness=1, highlightbackground="#777777")
        pad.pack(fill="both", expand=True, padx=20, pady=(20, 8))

        def start_stroke(event):
            active_stroke.clear()
            active_stroke.append((event.x, event.y))
            strokes.append(active_stroke.copy())

        def draw_stroke(event):
            if not active_stroke:
                return
            previous = active_stroke[-1]
            active_stroke.append((event.x, event.y))
            strokes[-1] = active_stroke.copy()
            pad.create_line(previous[0], previous[1], event.x, event.y, fill="#14285a", width=3, capstyle="round", smooth=True)

        def clear_pad():
            strokes.clear()
            active_stroke.clear()
            pad.delete("all")

        def use_drawing():
            if not strokes:
                messagebox.showinfo("Draw Signature", "Draw a signature first.", parent=dialog)
                return
            width = max(1, pad.winfo_width())
            height = max(1, pad.winfo_height())
            signature = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            drawing = ImageDraw.Draw(signature)
            for stroke in strokes:
                if len(stroke) == 1:
                    x, y = stroke[0]
                    drawing.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(20, 40, 90, 255))
                elif len(stroke) > 1:
                    drawing.line(stroke, fill=(20, 40, 90, 255), width=4, joint="curve")
            bbox = signature.getbbox()
            if bbox:
                signature = signature.crop(bbox)
            stream = io.BytesIO()
            signature.save(stream, format="PNG")
            dialog.destroy()
            self.prepare_signature(stream.getvalue(), "Drawn signature")

        pad.bind("<ButtonPress-1>", start_stroke)
        pad.bind("<B1-Motion>", draw_stroke)
        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(0, 14))
        ctk.CTkButton(buttons, text="Clear", fg_color="#555555", command=clear_pad).pack(side="left")
        ctk.CTkButton(buttons, text="Use Signature", fg_color="#28a745", command=use_drawing).pack(side="right")
        dialog.grab_set()

    def prepare_signature(self, image_bytes, description):
        if not self.engine:
            messagebox.showinfo("Visual Signature", "Open a PDF before placing a signature.")
            return
        if self.highlight_btn.cget("text") == "Cancel Highlight":
            self.toggle_highlight_mode()
        if self.crop_btn.cget("text") == "Cancel Crop":
            self.toggle_crop_mode()
        self.pending_signature_bytes = image_bytes
        self.canvas.set_modes(signature=True)
        self.pointer_btn.configure(fg_color="#3d3d3d")
        self.context_tabs.set("Sign")
        self.show_inspector()
        self.signature_status.configure(text=f"Ready: {description}\nDrag a rectangle on the page. Press Esc to cancel.", text_color="#2f9bff")

    def cancel_signature_placement(self):
        self.pending_signature_bytes = None
        self.canvas.set_modes(signature=False)
        self.pointer_btn.configure(fg_color=("#3B8ED0", "#1F6AA5"))
        self.signature_status.configure(text="Choose a signature, then drag its area on the page.", text_color="#aaaaaa")

    def apply_signature(self):
        if not self.canvas.signature_mode or not self.pending_signature_bytes or not self.engine:
            return
        pixels = self.canvas.get_selection_pixels()
        if not pixels:
            return
        p1 = self.get_pdf_coords(pixels[0], pixels[1])
        p2 = self.get_pdf_coords(pixels[2], pixels[3])
        page_rect = self.engine.doc[self.current_page_index].rect
        rect = (
            max(page_rect.x0, min(p1[0], p2[0])),
            max(page_rect.y0, min(p1[1], p2[1])),
            min(page_rect.x1, max(p1[0], p2[0])),
            min(page_rect.y1, max(p1[1], p2[1])),
        )
        if rect[2] - rect[0] < 10 or rect[3] - rect[1] < 10:
            messagebox.showwarning("Visual Signature", "Drag a larger signature area.")
            return
        try:
            self.engine.add_signature_image(self.current_page_index, rect, self.pending_signature_bytes)
        except Exception as exc:
            messagebox.showerror("Signature Error", f"Could not place the signature:\n{exc}")
            return
        self.mark_document_changed()
        self.cancel_signature_placement()
        self.load_page(self.current_page_index)
        if self.sidebar:
            self.sidebar.refresh_thumbnail(self.current_page_index)
        self.context_tabs.set("Sign")
        self.status_label.configure(text=" Visual signature placed")

    # --- ANNOTATION MODES ---
    def handle_selection_release(self, event):
        if self.canvas.highlight_mode:
            self.apply_highlight(event)
        elif self.canvas.signature_mode:
            self.apply_signature()

    def apply_highlight(self, event):
        if not self.canvas.highlight_mode: return
        px = self.canvas.get_selection_pixels()
        if px:
            p1, p2 = self.get_pdf_coords(px[0], px[1]), self.get_pdf_coords(px[2], px[3])
            rect = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
            rects = self.engine.get_text_in_rect(self.current_page_index, rect) if self.snap_var.get() else [rect]
            self.engine.add_highlight(self.current_page_index, rects)
            self.mark_document_changed()
            self.load_page(self.current_page_index); self.sidebar.refresh_thumbnail(self.current_page_index)
            self.focus_note_in_inspector(rect[:2]); self.toggle_highlight_mode()

    def toggle_highlight_mode(self):
        if self.crop_btn.cget("text") == "Cancel Crop": self.toggle_crop_mode()
        if self.canvas.signature_mode: self.cancel_signature_placement()
        is_on = self.highlight_btn.cget("text") == "Cancel Highlight"
        if not is_on:
            self.highlight_btn.configure(text="Cancel Highlight", fg_color="#d39e00", border_width=2, border_color="#ffe08a")
            self.pointer_btn.configure(fg_color="#454b54", border_width=1, border_color="#596270")
            self.snap_switch.pack(side="left", padx=10); self.canvas.set_modes(highlight=True)
        else:
            self.highlight_btn.configure(text="Highlight", fg_color="#454b54", border_width=1, border_color="#596270")
            self.snap_switch.pack_forget(); self.canvas.set_modes(highlight=False)
            self.pointer_btn.configure(fg_color=("#3B8ED0", "#1F6AA5"), border_width=2, border_color="#8cc8ff")

    def toggle_crop_mode(self):
        if self.highlight_btn.cget("text") == "Cancel Highlight": self.toggle_highlight_mode()
        if self.canvas.signature_mode: self.cancel_signature_placement()
        is_on = self.crop_btn.cget("text") == "Cancel Crop"
        if not is_on:
            self.crop_btn.configure(text="Cancel Crop", fg_color="#d35b5b", border_width=2, border_color="#ffb4b4")
            self.pointer_btn.configure(fg_color="#454b54", border_width=1, border_color="#596270")
            self.apply_crop_btn.pack(side="right", padx=5); self.canvas.set_modes(crop=True)
        else:
            self.crop_btn.configure(text="Crop", fg_color="#454b54", border_width=1, border_color="#596270")
            self.apply_crop_btn.pack_forget(); self.canvas.set_modes(crop=False)
            self.pointer_btn.configure(fg_color=("#3B8ED0", "#1F6AA5"), border_width=2, border_color="#8cc8ff")

    def activate_pointer_mode(self):
        if self.highlight_btn.cget("text") == "Cancel Highlight":
            self.highlight_btn.configure(text="Highlight", fg_color="#4a4a4a")
            self.snap_switch.pack_forget()
        if self.crop_btn.cget("text") == "Cancel Crop":
            self.crop_btn.configure(text="Crop", fg_color="#4a4a4a")
            self.apply_crop_btn.pack_forget()
        if self.canvas.signature_mode:
            self.pending_signature_bytes = None
            self.signature_status.configure(text="Choose a signature, then drag its area on the page.", text_color="#aaaaaa")
        self.canvas.set_modes()
        self.pointer_btn.configure(fg_color=("#3B8ED0", "#1F6AA5"), border_width=2, border_color="#8cc8ff")

    def apply_crop(self):
        px = self.canvas.get_selection_pixels()
        if px:
            p1, p2 = self.get_pdf_coords(px[0], px[1]), self.get_pdf_coords(px[2], px[3])
            rect = (min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
            self.engine.crop_page(self.current_page_index, rect)
            self.mark_document_changed()
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
            self.page_entry.delete(0, "end")
            self.page_entry.insert(0, str(idx + 1))
            self.page_total_label.configure(text=f"/ {len(self.engine.doc)}")
            self.update_status()
            if self._forms_page_index != idx:
                self.refresh_form_fields()

    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if p and self.confirm_discard_changes():
            self.load_external_file(p)

    def load_external_file(self, path):
        if path and os.path.exists(path):
            try:
                new_engine = PDFEngine(path)
            except Exception as exc:
                messagebox.showerror("Open Error", f"Could not open the PDF:\n{exc}")
                return

            old_engine = self.engine
            self.clear_nav_area()
            self.engine = new_engine
            if old_engine:
                old_engine.close()
            self.current_file_path = path
            self.session.reset()
            self._forms_page_index = None
            self.cancel_signature_placement()
            self.update_window_title()
            self.sidebar = Sidebar(self.nav_container, self.engine, self.load_page, self.rotate_page, self.handle_page_action)
            self.sidebar.pack(expand=True, fill="both", pady=5); self.zoom_to_fit(); self.load_page(0)

    def combine_pdfs(self):
        paths = list(filedialog.askopenfilenames(
            title="Select PDFs to append",
            filetypes=[("PDF", "*.pdf")],
        ))
        if not paths:
            return

        if not self.engine:
            first, paths = paths[0], paths[1:]
            self.load_external_file(first)
            if not self.engine or not paths:
                return

        try:
            self.engine.append_documents(paths)
        except Exception as exc:
            messagebox.showerror("Combine Error", f"Could not combine the selected PDFs:\n{exc}")
            return

        current_page = min(self.current_page_index, len(self.engine.doc) - 1)
        self.clear_nav_area()
        self.sidebar = Sidebar(self.nav_container, self.engine, self.load_page, self.rotate_page, self.handle_page_action)
        self.sidebar.pack(expand=True, fill="both", pady=5)
        self._forms_page_index = None
        self.mark_document_changed()
        self.load_page(current_page)
        self.status_label.configure(text=f" Combined document: {len(self.engine.doc)} pages")

    def spawn_new_window(self):
        from core.session import SessionManager
        new_window = ctk.CTkToplevel(self.root)
        new_window.title("PDF Suite v1.0 - Secondary Window")
        try: new_window.after(200, lambda: new_window.iconbitmap(self.root.wm_iconbitmap()))
        except: pass
        MainWindow(new_window, SessionManager())

    def toggle_sidebar(self):
        target_visible = not self.sidebar_visible
        drawer = layout_mode(self.root.winfo_width()) == "drawer"
        if not target_visible:
            self.left_panel.grid_remove(); self.left_panel.place_forget(); self.splitter.configure(text="»")
        elif drawer:
            if self.inspector_visible:
                self.hide_inspector()
            self._place_drawer(self.left_panel, "left", self.sidebar_width); self.splitter.configure(text="«")
        else:
            self.left_panel.grid(row=1, column=0, sticky="nsew"); self.splitter.configure(text="«")
        self._auto_hidden_sidebar = False
        self.sidebar_visible = target_visible; self.root.after(50, self.zoom_to_fit)

    def go_to_page_from_entry(self, event=None):
        if not self.engine:
            return "break"
        try:
            page_number = int(self.page_entry.get().strip())
        except ValueError:
            page_number = self.current_page_index + 1
        page_number = max(1, min(page_number, len(self.engine.doc)))
        self.load_page(page_number - 1)
        self.canvas.focus_set()
        return "break"

    def next_page(self):
        if self.engine and self.current_page_index < len(self.engine.doc)-1: self.load_page(self.current_page_index + 1)
    def prev_page(self):
        if self.engine and self.current_page_index > 0: self.load_page(self.current_page_index - 1)
    def handle_scroll(self, e):
        if e.delta > 0: self.prev_page()
        else: self.next_page()
    def handle_canvas_wheel(self, e):
        if e.state & 0x0004:
            self.zoom_at_pointer(0.1 if e.delta > 0 else -0.1, e.x, e.y)
        else:
            self.handle_scroll(e)
    def zoom_to_fit(self):
        if not self.engine: return
        self.root.update(); cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        p = self.engine.doc[self.current_page_index]
        if cw > 40:
            self.current_zoom = min((cw*0.9)/p.rect.width, (ch*0.9)/p.rect.height); self.update_zoom_view()
    def zoom_to_width(self):
        if not self.engine:
            return
        self.root.update()
        canvas_width = self.canvas.winfo_width()
        page = self.engine.doc[self.current_page_index]
        if canvas_width > 40:
            self.current_zoom = max(0.1, min(8.0, (canvas_width * 0.96) / page.rect.width))
            self.update_zoom_view()
    def update_zoom_view(self):
        if self.engine: self.zoom_label.configure(text=f"{int(self.current_zoom*100)}%"); self.load_page(self.current_page_index)
    def save_overwrite(self):
        if self.engine and self.current_file_path:
            if messagebox.askyesno("Confirm", "Update original file?"):
                try:
                    self.engine.save_file(self.current_file_path)
                    self.session.mark_saved()
                    self.update_window_title()
                    self.update_status("Changes saved")
                except Exception as exc:
                    messagebox.showerror("Save Error", str(exc))
    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path:
            try:
                self.engine.save_file(path)
                self.status_label.configure(text=f" Copy saved: {os.path.basename(path)}")
            except Exception as exc:
                messagebox.showerror("Save Error", str(exc))
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
                self.update_status(f"Note: {display_text[:75]}…", tone="warning")
            else:
                self.update_status()
    def handle_right_click(self, sx, sy, rx, ry):
        if not self.engine: return
        coords = self.get_pdf_coords(sx, sy)
        if self.engine.get_comment_at_pos(self.current_page_index, coords):
            m = Menu(self.root, tearoff=0); m.add_command(label="Delete Note", command=lambda: self.confirm_delete(coords)); m.post(rx, ry)
    def confirm_delete(self, c):
        if self.engine.delete_highlight(self.current_page_index, c):
            self.mark_document_changed()
            self.load_page(self.current_page_index)
            self.sidebar.refresh_thumbnail(self.current_page_index)
    def toggle_extraction_mode(self):
        self.extraction_mode = not self.extraction_mode
        if self.extraction_mode:
            self.extract_mode_btn.configure(text="Cancel", fg_color="#d35b5b")
            self.extract_mode_btn.pack(side="right", padx=2)
            self.range_entry.pack(side="right", padx=2); self.save_extract_btn.pack(side="right", padx=5)
            if self.sidebar: self.sidebar.toggle_extraction_mode(True)
        else:
            self.extract_mode_btn.configure(text="Extract Page(s)", fg_color="#3d3d3d")
            self.extract_mode_btn.pack_forget()
            self.range_entry.pack_forget(); self.save_extract_btn.pack_forget()
            if self.sidebar: self.sidebar.toggle_extraction_mode(False)
    def parse_page_range_entry(self):
        txt = self.range_entry.get().strip()
        if not txt or not self.engine:
            return []

        idx = []
        for part in txt.split(','):
            token = part.strip()
            if not token:
                continue
            if '-' in token:
                bounds = [b.strip() for b in token.split('-', 1)]
                if len(bounds) != 2 or not bounds[0] or not bounds[1]:
                    raise ValueError
                start, end = map(int, bounds)
                if start > end:
                    raise ValueError
                idx.extend(range(start - 1, end))
            else:
                idx.append(int(token) - 1)

        return [i for i in sorted(set(idx)) if 0 <= i < len(self.engine.doc)]

    def execute_extraction(self):
        if not self.engine or not self.sidebar:
            return

        try:
            range_selection = self.parse_page_range_entry()
        except ValueError:
            return messagebox.showerror("Range Error", "Invalid format. Use values like 1-5, 10.")

        if range_selection:
            self.sidebar.select_range(range_selection)
            selected_pages = set(range_selection)
        else:
            selected_pages = set(self.sidebar.selected_pages)

        if not selected_pages:
            return messagebox.showwarning("Empty", "Select pages using checkboxes or enter a page range.")

        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path:
            self.engine.extract_pages(sorted(selected_pages), path)

    def apply_range_from_entry(self):
        if not self.engine:
            return
        try:
            valid = self.parse_page_range_entry()
            if self.sidebar:
                self.sidebar.select_range(valid)
        except ValueError:
            messagebox.showerror("Range Error", "Invalid format. Use values like 1-5, 10.")
    def rotate_page(self, idx):
        self.engine.rotate_page(idx)
        self.mark_document_changed()
        self.sidebar.refresh_thumbnail(idx)
        if idx == self.current_page_index:
            self.load_page(idx)

    def handle_page_action(self, action, idx):
        if not self.engine:
            return
        if action == "delete":
            if not messagebox.askyesno("Delete Page", f"Delete page {idx + 1}?"):
                return
            try:
                self.engine.delete_page(idx)
            except ValueError as exc:
                messagebox.showwarning("Delete Page", str(exc))
                return
            target = min(idx, len(self.engine.doc) - 1)
        else:
            target = idx - 1 if action == "up" else idx + 1
            self.engine.move_page(idx, target)

        self.clear_nav_area()
        self.sidebar = Sidebar(self.nav_container, self.engine, self.load_page, self.rotate_page, self.handle_page_action)
        self.sidebar.pack(expand=True, fill="both", pady=5)
        self.current_page_index = target
        self._forms_page_index = None
        self.mark_document_changed()
        self.load_page(target)

    def mark_document_changed(self):
        self.session.mark_changed()
        self.update_window_title()
        self.update_status()

    def update_status(self, message=None, tone=None):
        if self.engine:
            page = f"Page {self.current_page_index + 1} / {len(self.engine.doc)}"
        else:
            page = "Page — / —"
        modified = "Modified" if self.session.unsaved_changes else "Saved"
        lead = message or ("Ready" if self.engine else "No document")
        self.status_label.configure(
            text=f"  {lead}   |   {page}   |   Zoom {int(self.current_zoom * 100)}%   |   {modified}",
            text_color="#fbbf24" if tone == "warning" or self.session.unsaved_changes else "#e5e7eb",
        )

    def update_window_title(self):
        name = os.path.basename(self.current_file_path) if self.current_file_path else "PDF Suite"
        marker = " *" if self.session.unsaved_changes else ""
        self.root.title(f"{name}{marker} - PDF Suite")

    def confirm_discard_changes(self):
        if not self.session.unsaved_changes:
            return True
        return messagebox.askyesno(
            "Unsaved Changes",
            "This document has unsaved changes. Discard them?",
        )

    def close_window(self):
        if not self.confirm_discard_changes():
            return
        if self.sidebar:
            self.sidebar.stop_loading()
        if self.engine:
            self.engine.close()
        self.root.destroy()
    def clear_nav_area(self):
        if self.sidebar: self.sidebar.stop_loading()
        for c in self.nav_container.winfo_children(): c.destroy()
        self.sidebar = None
    def check_ready_and_load(self, p, a=0):
        self.root.update()
        if self.canvas.winfo_width() > 100: self.load_external_file(p)
        elif a < 30: self.root.after(100, lambda: self.check_ready_and_load(p, a+1))
