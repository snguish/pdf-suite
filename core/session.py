class SessionManager:
    def __init__(self):
        self.unsaved_changes = False
        self.history = []

    def mark_changed(self):
        self.unsaved_changes = True

    def mark_saved(self):
        self.unsaved_changes = False

    def reset(self):
        self.unsaved_changes = False
        self.history.clear()
