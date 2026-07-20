import customtkinter as ctk
import sys
import os

# Ensure the app can find its internal modules from source and packaged builds.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.session import SessionManager
from ui.main_window import MainWindow

def resource_path(relative_path):
    """Resolve resources both from source and from a PyInstaller bundle."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def main():
    # --- 1. GLOBAL UI SETTINGS ---
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Ensures the UI looks crisp on high-resolution laptop screens
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)

    # --- 2. WINDOW INITIALIZATION ---
    root = ctk.CTk()
    root.title("PDF Suite v1.0")
    root.geometry("1280x820")
    
    # --- 3. SET WINDOW ICON (SAFE LOADING) ---
    # We check if the file exists first so the app doesn't crash if it's missing
    icon_path = resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            # Silently skip if the icon format is invalid or locked
            pass

    # Python and Windows preserve a quoted path as one argument.
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None

    # --- 5. LAUNCH THE APPLICATION ---
    try:
        session = SessionManager()
        # MainWindow handles the 'check_ready_and_load' logic internally
        app = MainWindow(root, session, initial_file=initial_file)
        root.mainloop()
        
    except Exception as e:
        # If the app crashes on startup, show a clear error message to the user
        from tkinter import messagebox
        messagebox.showerror("Startup Error", f"PDF Suite failed to launch:\n{str(e)}")

if __name__ == "__main__":
    main()
