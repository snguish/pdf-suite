import fitz
import os
from PIL import Image
import getpass
import copy
import uuid
import io
import tempfile
from datetime import datetime

class PDFEngine:
    def __init__(self, filepath):
        fitz.TOOLS.mupdf_display_errors(False)
        self.doc = fitz.open(filepath)
        self.filepath = os.path.normpath(filepath)
        self._undo_stack = []
        self._redo_stack = []
        self.signatures = []
        self._next_history_id = 1
        self.history_id = self.saved_history_id = 0

    def _snapshot(self):
        # Do not garbage-collect here: compacting can renumber live widget/image
        # xrefs that the UI and editable-signature records still reference.
        return (self.doc.tobytes(deflate=True), copy.deepcopy(self.signatures), self.history_id)

    def _restore(self, snapshot):
        data, signatures, history_id = snapshot
        old_doc = self.doc
        self.doc = fitz.open(stream=data, filetype="pdf")
        old_doc.close()
        self.signatures = copy.deepcopy(signatures)
        self.history_id = history_id

    def _record_change(self):
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self.history_id = self._next_history_id
        self._next_history_id += 1

    @property
    def can_undo(self):
        return bool(self._undo_stack)

    @property
    def can_redo(self):
        return bool(self._redo_stack)

    @property
    def is_modified(self):
        return self.history_id != self.saved_history_id

    def undo(self):
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())
        return True

    def mark_saved(self):
        self.saved_history_id = self.history_id

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

    def get_form_fields(self, page_index):
        page = self.doc[page_index]
        fields = []
        widgets = page.widgets()
        if not widgets:
            return fields

        for widget in widgets:
            choices = list(widget.choice_values or [])
            kind = {
                fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
                fitz.PDF_WIDGET_TYPE_COMBOBOX: "choice",
                fitz.PDF_WIDGET_TYPE_LISTBOX: "choice",
                fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
                fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
                fitz.PDF_WIDGET_TYPE_TEXT: "text",
            }.get(widget.field_type, "text")
            fields.append({
                "xref": widget.xref,
                "name": widget.field_name or f"Field {widget.xref}",
                "label": widget.field_label or widget.field_name or f"Field {widget.xref}",
                "type": widget.field_type,
                "type_name": widget.field_type_string or "Unknown",
                "kind": kind,
                "value": widget.field_value,
                "choices": choices,
                "read_only": bool(widget.field_flags & 1),
                "on_value": widget.on_state() if widget.field_type in (
                    fitz.PDF_WIDGET_TYPE_CHECKBOX,
                    fitz.PDF_WIDGET_TYPE_RADIOBUTTON,
                ) else None,
            })
        return fields

    def update_form_field(self, page_index, xref, value):
        page = self.doc[page_index]
        widgets = page.widgets()
        if not widgets:
            return False

        for widget in widgets:
            if widget.xref != xref:
                continue
            if widget.field_flags & 1:
                raise ValueError(f"Field '{widget.field_name}' is read-only.")
            field_type = widget.field_type
            on_value = widget.on_state() if field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX else None
            self._record_change()
            widget = next(item for item in self.doc[page_index].widgets() if item.xref == xref)
            if field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                widget.field_value = on_value if value else "Off"
            else:
                widget.field_value = value
            widget.update()
            return True
        return False

    def rotate_page(self, page_index):
        self._record_change()
        page = self.doc[page_index]
        page.set_rotation((page.rotation + 90) % 360)

    def move_page(self, page_index, destination_index):
        self._record_change()
        self.doc.move_page(page_index, destination_index)
        for signature in self.signatures:
            page = signature["page"]
            if page == page_index:
                signature["page"] = destination_index
            elif page_index < destination_index and page_index < page <= destination_index:
                signature["page"] -= 1
            elif destination_index < page_index and destination_index <= page < page_index:
                signature["page"] += 1

    def delete_page(self, page_index):
        if len(self.doc) <= 1:
            raise ValueError("A PDF must contain at least one page.")
        self._record_change()
        self.doc.delete_page(page_index)
        self.signatures = [s for s in self.signatures if s["page"] != page_index]
        for signature in self.signatures:
            if signature["page"] > page_index:
                signature["page"] -= 1

    def crop_page(self, page_index, coords):
        self._record_change()
        page = self.doc[page_index]
        page.set_cropbox(fitz.Rect(coords))

    def add_signature_image(self, page_index, coords, image_bytes):
        rect = fitz.Rect(coords)
        if rect.width < 1 or rect.height < 1:
            raise ValueError("The signature area is too small.")
        self._record_change()
        page = self.doc[page_index]
        image_bytes = self._make_unique_signature_image(image_bytes)
        xref = page.insert_image(rect, stream=image_bytes, keep_proportion=True, overlay=True)
        signature = {"id": uuid.uuid4().hex, "page": page_index, "rect": tuple(rect),
                     "image": image_bytes, "xref": xref}
        self.signatures.append(signature)
        return signature["id"]

    @staticmethod
    def _make_unique_signature_image(image_bytes):
        """Prevent MuPDF from reusing an image xref that an edit just blanked."""
        with Image.open(io.BytesIO(image_bytes)) as source:
            unique_image = source.convert("RGBA")
        marker = uuid.uuid4().bytes
        _r, _g, _b, a = unique_image.getpixel((0, 0))
        unique_image.putpixel((0, 0), (marker[0], marker[1], marker[2], a))
        stream = io.BytesIO()
        unique_image.save(stream, format="PNG")
        return stream.getvalue()

    def get_signatures(self, page_index):
        return [copy.deepcopy(s) for s in self.signatures if s["page"] == page_index]

    def update_signature(self, signature_id, coords):
        rect = fitz.Rect(coords)
        if rect.width < 1 or rect.height < 1:
            raise ValueError("The signature area is too small.")
        signature = next((s for s in self.signatures if s["id"] == signature_id), None)
        if signature is None:
            raise ValueError("The signature is no longer available.")
        self._record_change()
        page = self.doc[signature["page"]]
        page.delete_image(signature["xref"])
        signature["image"] = self._make_unique_signature_image(signature["image"])
        signature["xref"] = page.insert_image(
            rect, stream=signature["image"], keep_proportion=True, overlay=True,
        )
        signature["rect"] = tuple(rect)

    def delete_signature(self, signature_id):
        signature = next((s for s in self.signatures if s["id"] == signature_id), None)
        if signature is None:
            return False
        self._record_change()
        self.doc[signature["page"]].delete_image(signature["xref"])
        self.signatures.remove(signature)
        return True

    def get_text_in_rect(self, page_index, pdf_coords):
        page = self.doc[page_index]
        words = page.get_text("words", clip=fitz.Rect(pdf_coords))
        if words:
            lines = {}
            for w in words:
                line_key = (w[5], w[6])
                if line_key not in lines:
                    lines[line_key] = list(w[:4])
                else:
                    lines[line_key][0], lines[line_key][1] = min(lines[line_key][0], w[0]), min(lines[line_key][1], w[1])
                    lines[line_key][2], lines[line_key][3] = max(lines[line_key][2], w[2]), max(lines[line_key][3], w[3])
            return list(lines.values())
        return [pdf_coords]

    def add_highlight(self, page_index, rects, comment_text=""):
        self._record_change()
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
                self._record_change()
                page = self.doc[page_index]
                annot = next(a for a in page.annots() if a.rect.contains(point))
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
                self._record_change()
                page = self.doc[page_index]
                annot = next(a for a in page.annots() if a.rect.contains(point))
                page.delete_annot(annot)
                return True
        return False

    def extract_pages(self, page_indices, output_path):
        new_doc = fitz.open()
        try:
            for idx in sorted(page_indices):
                new_doc.insert_pdf(self.doc, from_page=idx, to_page=idx)
            new_doc.save(output_path)
        finally:
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

        self._record_change()
        self.doc.close()
        self.doc = combined

    def save_file(self, output_path, mark_saved=False):
        try:
            norm_output = os.path.normpath(output_path)
            source_name = self.doc.name
            norm_source = os.path.normpath(source_name) if source_name else None
            if norm_source and norm_output == norm_source:
                self.doc.save(output_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            elif norm_output == self.filepath and os.path.exists(output_path):
                directory = os.path.dirname(os.path.abspath(output_path))
                handle, temporary_path = tempfile.mkstemp(prefix=".pdf-suite-", suffix=".pdf", dir=directory)
                os.close(handle)
                try:
                    self.doc.save(temporary_path, garbage=3, deflate=True)
                    os.replace(temporary_path, output_path)
                finally:
                    if os.path.exists(temporary_path):
                        os.remove(temporary_path)
            else:
                self.doc.save(output_path)
            if mark_saved:
                self.mark_saved()
        except Exception as e:
            raise Exception(f"Save failed: {str(e)}")
