import fitz
import os
from PIL import Image
import getpass
from datetime import datetime

class PDFEngine:
    def __init__(self, filepath):
        fitz.TOOLS.mupdf_display_errors(False)
        self.doc = fitz.open(filepath)

    def close(self):
        if self.doc and not self.doc.is_closed:
            self.doc.close()

    def get_display_page(self, page_index, zoom=1.0):
        page = self.doc[page_index]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, annots=True)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    def get_thumbnail(self, page_index, width=120):
        page = self.doc[page_index]
        zoom = width / page.rect.width
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, annots=True)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    def rotate_page(self, page_index):
        page = self.doc[page_index]
        page.set_rotation((page.rotation + 90) % 360)

    def move_page(self, page_index, destination_index):
        self.doc.move_page(page_index, destination_index)

    def delete_page(self, page_index):
        if len(self.doc) <= 1:
            raise ValueError("A PDF must contain at least one page.")
        self.doc.delete_page(page_index)

    def crop_page(self, page_index, coords):
        page = self.doc[page_index]
        page.set_cropbox(fitz.Rect(coords))

    def get_text_in_rect(self, page_index, pdf_coords):
        page = self.doc[page_index]
        words = page.get_text("words", clip=fitz.Rect(pdf_coords))
        if words:
            lines = {}
            for w in words:
                l_idx = w[6]
                if l_idx not in lines:
                    lines[l_idx] = list(w[:4])
                else:
                    lines[l_idx][0], lines[l_idx][1] = min(lines[l_idx][0], w[0]), min(lines[l_idx][1], w[1])
                    lines[l_idx][2], lines[l_idx][3] = max(lines[l_idx][2], w[2]), max(lines[l_idx][3], w[3])
            return list(lines.values())
        return [pdf_coords]

    def add_highlight(self, page_index, rects, comment_text=""):
        page = self.doc[page_index]
        user = getpass.getuser().upper()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_text = comment_text.strip() if comment_text else ""
        full_string = f"CREATED: {user} @ {ts}\nMODIFIED: {user} @ {ts}\n---\n{clean_text}"
        annot = page.add_highlight_annot(rects)
        annot.set_info(content=full_string, title=user)
        annot.set_flags(fitz.PDF_ANNOT_IS_PRINT)
        annot.update()

    def update_comment_at_pos(self, page_index, pdf_coords, new_text):
        page = self.doc[page_index]
        point = fitz.Point(pdf_coords)
        user = getpass.getuser().upper()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for annot in page.annots():
            if annot.rect.contains(point):
                old_content = annot.info.get("content", "")
                created_line = f"CREATED: {user} @ {ts}"
                for line in old_content.split("\n"):
                    if line.startswith("CREATED:"):
                        created_line = line
                        break
                full_string = f"{created_line}\nMODIFIED: {user} @ {ts}\n---\n{new_text}"
                annot.set_info(content=full_string, title=user)
                annot.update()
                return True
        return False

    def get_comment_at_pos(self, page_index, pdf_coords):
        page = self.doc[page_index]
        point = fitz.Point(pdf_coords)
        for annot in page.annots():
            if annot.rect.contains(point):
                return annot.info.get("content", "")
        return ""

    def get_all_comments(self):
        report = []
        for i, page in enumerate(self.doc):
            for annot in page.annots():
                content = annot.info.get("content", "")
                if not content: continue
                created_ts = "Unknown"; modified_ts = "Unknown"; text = content
                if "---\n" in content:
                    meta, text = content.split("---\n", 1)
                    for line in meta.split("\n"):
                        if line.startswith("CREATED:"): created_ts = line.split("@ ")[1] if "@ " in line else line
                        if line.startswith("MODIFIED:"): modified_ts = line.split("@ ")[1] if "@ " in line else line
                report.append({
                    "Page": i + 1, "User": annot.info.get("title", "Unknown"), 
                    "Created At": created_ts, "Last Modified": modified_ts, "Comment": text.strip()
                })
        return report

    def delete_highlight(self, page_index, pdf_coords):
        page = self.doc[page_index]
        point = fitz.Point(pdf_coords)
        for annot in page.annots():
            if annot.rect.contains(point):
                page.delete_annot(annot)
                return True
        return False

    def extract_pages(self, page_indices, output_path):
        new_doc = fitz.open()
        for idx in sorted(page_indices):
            new_doc.insert_pdf(self.doc, from_page=idx, to_page=idx)
        new_doc.save(output_path)
        new_doc.close()

    def append_documents(self, filepaths):
        """Append complete PDFs atomically, leaving the current document intact on failure."""
        sources = []
        combined = fitz.open()
        try:
            combined.insert_pdf(self.doc)
            for filepath in filepaths:
                source = fitz.open(filepath)
                sources.append(source)
                if source.needs_pass:
                    raise ValueError(f"Password required: {os.path.basename(filepath)}")
                combined.insert_pdf(source)
        except Exception:
            combined.close()
            raise
        finally:
            for source in sources:
                source.close()

        self.doc.close()
        self.doc = combined

    def save_file(self, output_path):
        try:
            norm_output = os.path.normpath(output_path)
            source_name = self.doc.name
            norm_source = os.path.normpath(source_name) if source_name else None
            if norm_source and norm_output == norm_source:
                self.doc.save(output_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            else:
                self.doc.save(output_path)
        except Exception as e:
            raise Exception(f"Save failed: {str(e)}")
