# Technical Documentation: PDF Suite v1.0

This technical documentation provides a high-level overview of the **PDF Suite v1.0** architecture, component interactions, and deployment logic. It is designed to serve as a reference for maintenance or auditing the tool's data integrity.

---

## 1. System Overview
**PDF Suite** is a modular desktop application built in Python. Its primary purpose is to provide a high-performance environment for reviewing PDF documents, performing precise crops, and generating audit-ready interaction logs. 

### Core Tech Stack:
* **GUI Framework:** `customtkinter` (Modernized `tkinter` with High-DPI scaling and Dark Mode support).
* **PDF Engine:** `PyMuPDF` (under the `fitz` module), chosen for its industry-leading rendering speed and robust annotation support.
* **Environment:** Isolated Virtual Environment (`venv`) to ensure zero-conflict deployment on enterprise machines.

---

## 2. Architecture Logic
The application follows a **Modular Layered Architecture**. By separating the "Logic" from the "Interface," the tool remains stable and easy to troubleshoot.

### A. The Entry Layer (`app.pyw`)
The "Receptionist" of the app. It handles global configurations, parses command-line arguments for "Open With" functionality, and initializes the primary window instance.

### B. The UI Layer (`ui/`)
* **`main_window.py`:** The "Conductor." It manages a dynamic **4-column layout** (Sidebar | Splitter | Canvas | Inspector). It handles all top-level events, including file actions, coordinate translation, and secondary window branding.
* **`canvas.py`:** A custom canvas that handles PDF rendering, centering logic, and mouse-event capturing for cropping and highlighting.
* **`sidebar.py`:** Manages page thumbnails using background threading to prevent interface freezing during document load.
* **Note Inspector (Dynamic):** A specialized panel that remains hidden until triggered by a double-click on an annotation. It allows users to edit note text while viewing audit metadata.

### C. The Core Layer (`core/`)
* **`engine.py`:** Wraps `PyMuPDF`. It manages structured metadata for annotations, specifically preserving a permanent `CREATED` stamp while updating a `MODIFIED` stamp during edits.
* **`session.py`:** Manages temporary user data and state during a single run.

---

## 3. Project Structure
```text
PDF_Suite_v1.0/
├── app.pyw                  # Application Entry Point
├── Run_PDF_Suite.bat        # Multi-instance Optimized Launcher
├── requirements.txt         # Dependency List
├── README.md                # User Manual & Licensing
├── app_icon.ico             # Branded Application Icon
├── core/                    # Logic Layer
│   ├── engine.py            # PDF Logic & Metadata Parsing
│   └── session.py           # Session Management
├── ui/                      # Presentation Layer
│   ├── main_window.py       # Layout, Bindings & Coordination
│   ├── canvas.py            # Rendering & Mouse Events
│   └── sidebar.py           # Thumbnail Navigation
└── utils/                   # Helper Layer
    └── math_tools.py        # Shared Math Utilities
```

---

## 4. Data Flow
The application processes data through a specific lifecycle:

Ingestion: app.pyw passes a file path to MainWindow.

Rendering: MainWindow requests a high-quality render from PDFEngine.

Display: The render is sent to PDFCanvas, which applies centering offsets.

Interaction: The user draws a highlight; MainWindow.get_pdf_coords translates screen pixels to PDF points by subtracting workspace offsets.

Audit Enrichment: PDFEngine creates a structured metadata block (CREATED vs MODIFIED) and attaches it to the annotation.

Persistence: Changes are saved incrementally to the PDF, and audit logs are exported as multi-timestamp CSVs.

---

## 5. Deployment & Environment Strategy
The tool uses a Self-Bootstrapping Launcher (Run_PDF_Suite.bat) optimized for multi-instance use.

Optimized Boot Sequence:
Environment Check: If \venv\ exists, it skips directly to launch to avoid "File in Use" errors when opening multiple documents.

Sync: If missing, it creates the environment and installs dependencies from requirements.txt.

Silent Launch: Executes the app via pythonw.exe from within the local venv.

---

## 6. Security & Privacy
Data Residency: All PDF processing is performed locally. No data is transmitted to external servers.

Audit Integrity: Interaction logs (CSV) include both Created At and Last Modified timestamps, along with system IDs, ensuring a robust trail of evidence.

Internal Technical Document | v1.0 | April 2026