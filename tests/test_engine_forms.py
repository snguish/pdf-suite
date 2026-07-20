import os
import tempfile
import unittest
import uuid

import fitz

from core.engine import PDFEngine


class PDFFormEngineTests(unittest.TestCase):
    def setUp(self):
        test_root = os.environ.get("PDF_SUITE_TEST_TMP")
        self.temp_dir = None
        if test_root:
            prefix = uuid.uuid4().hex
            self.source_path = os.path.join(test_root, f"{prefix}-form.pdf")
            self.output_path = os.path.join(test_root, f"{prefix}-filled.pdf")
        else:
            self.temp_dir = tempfile.TemporaryDirectory()
            self.source_path = os.path.join(self.temp_dir.name, "form.pdf")
            self.output_path = os.path.join(self.temp_dir.name, "filled.pdf")
        self._create_form(self.source_path)

    def tearDown(self):
        if self.temp_dir:
            self.temp_dir.cleanup()
        else:
            for path in (self.source_path, self.output_path):
                if os.path.exists(path):
                    os.remove(path)

    @staticmethod
    def _create_form(path):
        document = fitz.open()
        page = document.new_page()

        text = fitz.Widget()
        text.field_name = "employee_name"
        text.field_label = "Employee name"
        text.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        text.field_value = "Before"
        text.rect = fitz.Rect(72, 72, 300, 100)
        page.add_widget(text)

        checkbox = fitz.Widget()
        checkbox.field_name = "approved"
        checkbox.field_label = "Approved"
        checkbox.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        checkbox.rect = fitz.Rect(72, 120, 92, 140)
        page.add_widget(checkbox)

        choice = fitz.Widget()
        choice.field_name = "department"
        choice.field_label = "Department"
        choice.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
        choice.choice_values = ["Audit", "Finance"]
        choice.field_value = "Audit"
        choice.rect = fitz.Rect(72, 160, 300, 188)
        page.add_widget(choice)

        document.save(path)
        document.close()

    def test_detect_update_and_save_form_fields(self):
        engine = PDFEngine(self.source_path)
        fields = engine.get_form_fields(0)
        by_name = {field["name"]: field for field in fields}

        self.assertEqual(set(by_name), {"employee_name", "approved", "department"})
        self.assertEqual(by_name["department"]["choices"], ["Audit", "Finance"])
        self.assertEqual(by_name["approved"]["kind"], "checkbox")

        engine.update_form_field(0, by_name["employee_name"]["xref"], "After")
        engine.update_form_field(0, by_name["approved"]["xref"], True)
        engine.update_form_field(0, by_name["department"]["xref"], "Finance")
        engine.save_file(self.output_path)
        engine.close()

        result = fitz.open(self.output_path)
        values = {widget.field_name: widget.field_value for widget in result[0].widgets()}
        result.close()

        self.assertEqual(values["employee_name"], "After")
        self.assertNotEqual(values["approved"], "Off")
        self.assertEqual(values["department"], "Finance")


if __name__ == "__main__":
    unittest.main()
