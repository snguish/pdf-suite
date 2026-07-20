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


if __name__ == "__main__":
    unittest.main()
