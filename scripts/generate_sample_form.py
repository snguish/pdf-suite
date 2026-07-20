"""Generate the approval-form fixture used by the README gallery."""

import argparse
import fitz


def add_label(page, text, x, y):
    page.insert_text((x, y), text.upper(), fontsize=7, color=(0.25, 0.32, 0.45))


def build_form(output_path):
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    navy = (0.08, 0.18, 0.36)
    muted = (0.35, 0.42, 0.52)

    page.draw_rect(fitz.Rect(42, 42, 570, 750), color=navy, width=1.2)
    page.insert_text((66, 82), "DOCUMENT APPROVAL", fontsize=22, color=navy)
    page.insert_text((66, 102), "Review, authorize, and route this document", fontsize=9, color=muted)

    fields = (
        ("full_name", "Full name", fitz.PDF_WIDGET_TYPE_TEXT, fitz.Rect(66, 140, 360, 172), "Ada Lovelace"),
        ("email", "Email address", fitz.PDF_WIDGET_TYPE_TEXT, fitz.Rect(66, 214, 360, 246), "ada@example.com"),
        ("department", "Department", fitz.PDF_WIDGET_TYPE_COMBOBOX, fitz.Rect(66, 288, 360, 320), "Research"),
    )
    for name, label, kind, rect, value in fields:
        add_label(page, label, rect.x0, rect.y0 - 10)
        widget = fitz.Widget()
        widget.field_name = name
        widget.field_label = label
        widget.field_type = kind
        widget.field_value = value
        widget.rect = rect
        widget.text_fontsize = 12
        widget.field_flags = 0
        if kind == fitz.PDF_WIDGET_TYPE_COMBOBOX:
            widget.choice_values = ["Research", "Engineering", "Finance", "Legal"]
        page.add_widget(widget)

    add_label(page, "Approval", 66, 372)
    checkbox = fitz.Widget()
    checkbox.field_name = "approved"
    checkbox.field_label = "Approved for release"
    checkbox.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    checkbox.rect = fitz.Rect(66, 384, 86, 404)
    page.add_widget(checkbox)
    page.insert_text((96, 400), "Approved for release", fontsize=10, color=navy)

    add_label(page, "Signatory", 66, 478)
    page.draw_line((66, 540), (360, 540), color=muted, width=0.8)
    page.insert_text((66, 558), "Authorized signature", fontsize=7, color=muted)
    page.insert_text((66, 710), "PDF Suite generated sample form", fontsize=7, color=muted)

    document.save(output_path)
    document.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="sample-approval-form.pdf")
    build_form(parser.parse_args().output)
