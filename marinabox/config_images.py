import os

# Keep defaults exactly as the code currently uses (no tag suffix).
_DEFAULT_BROWSER = "marinabox/marinabox-browser"
_DEFAULT_DESKTOP = "marinabox/marinabox-desktop"

def get_browser_image() -> str:
    """
    Effective browser image name.
    Env override: MB_BROWSER_IMAGE (full repo[:tag] allowed).
    """
    val = os.environ.get("MB_BROWSER_IMAGE", "").strip()
    return val or _DEFAULT_BROWSER

def get_desktop_image() -> str:
    """
    Effective desktop image name.
    Env override: MB_DESKTOP_IMAGE (full repo[:tag] allowed).
    """
    val = os.environ.get("MB_DESKTOP_IMAGE", "").strip()
    return val or _DEFAULT_DESKTOP
