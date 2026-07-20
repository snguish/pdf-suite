"""Small, testable layout decisions used by the desktop UI."""

NARROW_WIDTH = 850
DETAILS_COLLAPSE_WIDTH = 1180
DEFAULT_SIDEBAR_WIDTH = 224
MIN_SIDEBAR_WIDTH = 176
MAX_SIDEBAR_WIDTH = 360


def layout_mode(width):
    """Return the responsive presentation mode for a window width."""
    if width < NARROW_WIDTH:
        return "drawer"
    if width < DETAILS_COLLAPSE_WIDTH:
        return "compact"
    return "wide"


def clamp_sidebar_width(width):
    return max(MIN_SIDEBAR_WIDTH, min(MAX_SIDEBAR_WIDTH, int(width)))
