
# PDF Suite v1.0 - Professional Document Review Tool

**PDF Suite** is a high-speed document viewer optimized for rapid audit review and data extraction. It features an automated audit trail, hybrid text highlighting, and precise content cropping.

---

### **1. Windows Build**
Run **`build_windows.ps1`** from PowerShell to create a self-contained application folder. The executable is produced at **`dist\PDF Suite\PDF Suite.exe`** and does not require Python on the destination computer.

---

### **2. Desktop Integration**
* **Double-Click to Open:** Right-click any `.pdf` > **Open with** > **Choose another app** > **Choose an app on your PC** > Select **`PDF Suite.exe`**.
* **Desktop Shortcut:** Right-click `PDF Suite.exe` and choose **Send to Desktop (shortcut)**. The application icon is embedded in the executable.

---

### **3. Navigation & Shortcuts**
Efficiency is the core of this tool. Fixed keyboard variations are supported for both standard and numeric keypad users.

The compact page control displays `‹ [current page] / total ›`. Enter a page number and press **Enter** to jump directly to it. Editing modes are grouped in the vertical tool rail beside the document.

| Key | Action |
| :--- | :--- |
| **`Up` / `Down`** | Previous / Next Page |
| **`Mouse Wheel`** | **Page Navigation** (Scroll to change pages) |
| **`Ctrl` + `Mouse Wheel`** | **Zoom at Pointer** (Keeps the pointed area in view) |
| **`f`** | **Fit Page** (Frame entire page in window) |
| **`Ctrl + 2`** | **Fit Width** (Fill the available canvas width) |
| **`b`** | **Reset View** (Return to 100% zoom) |
| **`+` / `-`** | **Zoom In / Out** (Works on Numpad and Main keys) |
| **`s`** | Show / Hide Sidebar Navigation |
| **`h`** | Toggle **Highlight Mode** (Shows "Text Snap" option) |
| **`c`** | Toggle **Crop Mode** (Shows "Apply" button) |
| **`Ctrl + E`** | **Export Note(s)** to a CSV log |
| **`Ctrl + S`** | **Update Original File** (Quick Save) |

---

### **4. Key Interaction Features**
* **Contextual Details Panel:** Use **Details** to open Notes, Forms, and Sign workspaces. Note double-clicks open the Notes workspace automatically.
* **PDF Form Filling:** Open **Details > Forms** to edit interactive text fields, checkboxes, radio buttons, dropdowns, and lists on the current page. Select **Apply Form Changes** before leaving the page or saving.
* **Visual Signatures:** Open **Details > Sign** to import a signature image, type a signer name, or draw a signature. Then drag its placement area on the page. Visual signatures are flattened page content, not certificate-backed digital signatures.
* **Enhanced Audit Trail:** Every note tracks who created it and when, as well as the details of the last person to modify the text.
* **Dynamic Note Inspector:** A side panel appears automatically on **double-click**. It allows for instant text updates without blocking the document view.
* **Hybrid Highlighting:** Use the **"Text Snap"** toggle during highlight mode. Turn it **ON** for clean text selection or **OFF** to highlight precise areas like signatures or stamps.
* **PNG Snapshots:** Use **"Snapshot Page as PNG"** under the **File Actions** menu to save a high-resolution 2.0x zoom image of the current page.
* **Secondary View:** Click **"+ Window"** to open another document side-by-side for comparison.

---

### **5. File Actions Menu**
To align with audit standards, saving and exporting are grouped under **File Actions**:
* **Save Copy as PDF...**: Create a new annotated file.
* **Update Original File**: Save changes directly to the source document.
* **Snapshot Page as PNG**: Export the current view as a high-quality image.

---

### **6. Troubleshooting**
* **"File in Use" Errors:** If running from **OneDrive**, ensure sync is active. The launcher is optimized to prevent library conflicts when multiple PDFs are open.
* **Note Visibility:** If a note is not visible in the Inspector, ensure you are double-clicking within the highlighted area.

---
*Internal Release v1.0 | April 2026*
