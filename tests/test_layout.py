import unittest

from ui.layout import clamp_sidebar_width, layout_mode


class LayoutTests(unittest.TestCase):
    def test_breakpoints(self):
        self.assertEqual(layout_mode(800), "drawer")
        self.assertEqual(layout_mode(850), "compact")
        self.assertEqual(layout_mode(1024), "compact")
        self.assertEqual(layout_mode(1180), "wide")

    def test_sidebar_width_is_bounded(self):
        self.assertEqual(clamp_sidebar_width(20), 176)
        self.assertEqual(clamp_sidebar_width(224), 224)
        self.assertEqual(clamp_sidebar_width(900), 360)


if __name__ == "__main__":
    unittest.main()
