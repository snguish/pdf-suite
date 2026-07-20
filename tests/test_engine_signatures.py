import io
import os
import tempfile
import unittest
import uuid

import fitz
from PIL import Image, ImageDraw

from core.engine import PDFEngine


class PDFSignatureEngineTests(unittest.TestCase):
    def setUp(self):
        test_root = os.environ.get("PDF_SUITE_TEST_TMP")
        self.temp_dir = None
        if test_root:
            prefix = uuid.uuid4().hex
            self.source_path = os.path.join(test_root, f"{prefix}-source.pdf")
            self.output_path = os.path.join(test_root, f"{prefix}-signed.pdf")
        else:
            self.temp_dir = tempfile.TemporaryDirectory()
            self.source_path = os.path.join(self.temp_dir.name, "source.pdf")
            self.output_path = os.path.join(self.temp_dir.name, "signed.pdf")

        document = fitz.open()
        document.new_page()
        document.save(self.source_path)
        document.close()

    def tearDown(self):
        if self.temp_dir:
            self.temp_dir.cleanup()
        else:
            for path in (self.source_path, self.output_path):
                if os.path.exists(path):
                    os.remove(path)

    @staticmethod
    def _signature_png():
        image = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
        drawing = ImageDraw.Draw(image)
        drawing.line([(10, 70), (80, 20), (150, 75), (290, 30)], fill=(20, 40, 90, 255), width=5)
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()

    def test_insert_signature_as_page_image(self):
        engine = PDFEngine(self.source_path)
        engine.add_signature_image(0, (72, 600, 300, 680), self._signature_png())
        engine.save_file(self.output_path)
        engine.close()

        result = fitz.open(self.output_path)
        images = result[0].get_images(full=True)
        result.close()

        self.assertEqual(len(images), 1)

    def test_reject_tiny_signature_area(self):
        engine = PDFEngine(self.source_path)
        with self.assertRaises(ValueError):
            engine.add_signature_image(0, (72, 72, 72, 72), self._signature_png())
        engine.close()

    def test_signature_can_be_moved_undone_and_redone(self):
        engine = PDFEngine(self.source_path)
        signature_id = engine.add_signature_image(0, (72, 600, 300, 680), self._signature_png())
        engine.update_signature(signature_id, (100, 500, 360, 590))
        self.assertEqual(engine.get_signatures(0)[0]["rect"], (100.0, 500.0, 360.0, 590.0))
        moved = engine.doc[0].get_pixmap(clip=fitz.Rect(100, 500, 360, 590), alpha=False)
        self.assertLess(min(moved.samples), 240, "Moved signature rendered as an empty box")

        self.assertTrue(engine.undo())
        self.assertEqual(engine.get_signatures(0)[0]["rect"], (72.0, 600.0, 300.0, 680.0))
        self.assertTrue(engine.redo())
        self.assertEqual(engine.get_signatures(0)[0]["rect"], (100.0, 500.0, 360.0, 590.0))
        engine.close()

    def test_identical_signatures_are_independently_editable(self):
        engine = PDFEngine(self.source_path)
        image = self._signature_png()
        first = engine.add_signature_image(0, (72, 600, 300, 680), image)
        second = engine.add_signature_image(0, (72, 450, 300, 530), image)
        engine.update_signature(first, (100, 610, 340, 690))

        signatures = {item["id"]: item for item in engine.get_signatures(0)}
        self.assertEqual(signatures[second]["rect"], (72.0, 450.0, 300.0, 530.0))
        self.assertNotEqual(signatures[first]["xref"], signatures[second]["xref"])
        engine.close()

    def test_undo_state_can_replace_original_file(self):
        engine = PDFEngine(self.source_path)
        engine.add_signature_image(0, (72, 600, 300, 680), self._signature_png())
        engine.add_signature_image(0, (72, 450, 300, 530), self._signature_png())
        self.assertTrue(engine.undo())
        engine.save_file(self.source_path, mark_saved=True)
        engine.close()

        result = fitz.open(self.source_path)
        self.assertGreaterEqual(len(result[0].get_images(full=True)), 1)
        result.close()


if __name__ == "__main__":
    unittest.main()
