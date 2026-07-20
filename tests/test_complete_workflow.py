import io
import os
import tempfile
import unittest
import uuid

import fitz
from PIL import Image, ImageDraw

from core.engine import PDFEngine


class CompleteWorkflowTests(unittest.TestCase):
    def setUp(self):
        root = os.environ.get("PDF_SUITE_TEST_TMP")
        self.temp_dir = None if root else tempfile.TemporaryDirectory()
        root = root or self.temp_dir.name
        prefix = uuid.uuid4().hex
        self.source = os.path.join(root, f"{prefix}-workflow.pdf")
        self.output = os.path.join(root, f"{prefix}-workflow-output.pdf")

        document = fitz.open()
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 100), "Highlight this workflow text", fontsize=14)
        name = fitz.Widget()
        name.field_name = "employee_name"
        name.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        name.rect = fitz.Rect(72, 140, 300, 170)
        page.add_widget(name)
        document.save(self.source)
        document.close()

    def tearDown(self):
        for path in (self.source, self.output):
            if os.path.exists(path):
                os.remove(path)
        if self.temp_dir:
            self.temp_dir.cleanup()

    @staticmethod
    def signature_png():
        image = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
        ImageDraw.Draw(image).line(
            [(10, 70), (80, 20), (150, 75), (290, 30)],
            fill=(20, 40, 90, 255), width=5,
        )
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()

    def test_highlight_comment_crop_form_signature_and_history(self):
        engine = PDFEngine(self.source)
        original_crop = tuple(engine.doc[0].cropbox)

        highlight_rect = (70, 82, 280, 108)
        engine.add_highlight(0, [highlight_rect], "Initial workflow note")
        self.assertIn("Initial workflow note", engine.get_comment_at_pos(0, (100, 95)))
        self.assertTrue(engine.update_comment_at_pos(0, (100, 95), "Updated workflow comment"))
        self.assertIn("Updated workflow comment", engine.get_comment_at_pos(0, (100, 95)))

        engine.crop_page(0, (36, 36, 576, 756))
        self.assertEqual(tuple(engine.doc[0].cropbox), (36.0, 36.0, 576.0, 756.0))

        field = engine.get_form_fields(0)[0]
        self.assertTrue(engine.update_form_field(0, field["xref"], "Test User"))
        self.assertEqual(engine.get_form_fields(0)[0]["value"], "Test User")

        signature_id = engine.add_signature_image(0, (90, 600, 310, 680), self.signature_png())
        engine.update_signature(signature_id, (120, 580, 380, 670))
        self.assertEqual(engine.get_signatures(0)[0]["rect"], (120.0, 580.0, 380.0, 670.0))

        self.assertTrue(engine.undo())
        self.assertEqual(engine.get_signatures(0)[0]["rect"], (90.0, 600.0, 310.0, 680.0))
        self.assertTrue(engine.redo())
        self.assertEqual(engine.get_signatures(0)[0]["rect"], (120.0, 580.0, 380.0, 670.0))

        engine.save_file(self.output)
        engine.close()

        result = fitz.open(self.output)
        self.assertEqual(tuple(result[0].cropbox), (36.0, 36.0, 576.0, 756.0))
        self.assertEqual(next(result[0].widgets()).field_value, "Test User")
        self.assertTrue(any("Updated workflow comment" in a.info.get("content", "") for a in result[0].annots()))
        self.assertGreaterEqual(len(result[0].get_images(full=True)), 1)
        result.close()
        self.assertNotEqual(original_crop, (36.0, 36.0, 576.0, 756.0))


if __name__ == "__main__":
    unittest.main()
