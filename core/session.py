class SessionManager:
    def __init__(self):
        self.unsaved_changes = False
        self.history = []