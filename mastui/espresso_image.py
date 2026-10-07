"""Image rendering, caching, and modal preview for Mastui on Espresso TUI."""

from __future__ import annotations

import hashlib
import math
import os
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Any

from espresso.beans.modal_stack import ModalCloseMsg
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width, truncate_ansi
from mastui.espresso_clipboard import copy_to_clipboard

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PILImage = None


def get_image_cache_dirs(profile_dir: Path | None = None) -> list[Path]:
    """Return search directories for cached media files across profiles."""
    dirs: list[Path] = []
    if profile_dir:
        dirs.append(profile_dir / "image_cache")
    base_profiles = Path.home() / ".config" / "mastui" / "profiles"
    if base_profiles.exists():
        for p in base_profiles.iterdir():
            cache_p = p / "image_cache"
            if cache_p.exists() and cache_p not in dirs:
                dirs.append(cache_p)
    default_dir = Path.home() / ".config" / "mastui" / "profiles" / "default" / "image_cache"
    if default_dir not in dirs:
        dirs.append(default_dir)
    import tempfile
    tmp_cache = Path(tempfile.gettempdir()) / "mastui_cache"
    if tmp_cache not in dirs:
        dirs.append(tmp_cache)
    return dirs


def find_cached_image_file(url: str, profile_dir: Path | None = None) -> Path | None:
    """Find a locally cached image file corresponding to the media URL."""
    if not url:
        return None
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    for d in get_image_cache_dirs(profile_dir):
        candidate = d / url_hash
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def find_cached_attachment_file(attachment: dict[str, Any], profile_dir: Path | None = None) -> Path | None:
    """Find a cached image file for any URL key present in the attachment."""
    for key in ("url", "preview_url", "remote_url"):
        val = str(attachment.get(key) or "")
        if val:
            found = find_cached_image_file(val, profile_dir)
            if found:
                return found
    return None


def generate_demo_image(save_path: Path) -> Path | None:
    """Generate a vibrant procedural demo image (sunset gradient over mountains/sea)."""
    if not PIL_AVAILABLE:
        return None
    try:
        w, h = 80, 40
        im = PILImage.new("RGB", (w, h))
        pixels = im.load()
        for y in range(h):
            for x in range(w):
                if y < h // 2:
                    t = y / (h / 2.0)
                    r = int(120 + 135 * t)
                    g = int(30 + 120 * t)
                    b = int(140 - 80 * t)
                else:
                    t = (y - h / 2.0) / (h / 2.0)
                    r = int(255 - 180 * t + 20 * math.sin(x / 4.0))
                    g = int(150 - 100 * t + 15 * math.sin(x / 3.0))
                    b = int(60 + 120 * t + 25 * math.cos(x / 5.0))
                pixels[x, y] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            im.save(save_path, "JPEG")
            return save_path
        except OSError:
            import tempfile
            tmp_cache = Path(tempfile.gettempdir()) / "mastui_cache"
            tmp_cache.mkdir(parents=True, exist_ok=True)
            fallback_path = tmp_cache / save_path.name
            im.save(fallback_path, "JPEG")
            return fallback_path
    except Exception:
        return None


def download_and_cache_image(
    url: str, profile_dir: Path | None = None, allow_network: bool = True
) -> Path | None:
    """Download image from url or generate colorful demo image, saving to cache."""
    if not url:
        return None
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    target_dir = (profile_dir / "image_cache") if profile_dir else (Path.home() / ".config" / "mastui" / "profiles" / "default" / "image_cache")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        import tempfile
        target_dir = Path(tempfile.gettempdir()) / "mastui_cache"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    target_file = target_dir / url_hash
    if target_file.exists() and target_file.is_file():
        return target_file

    # If mock/demo URL, generate procedural demo image without network
    if "mastui.app" in url or "example.com" in url or "demo" in url:
        return generate_demo_image(target_file)

    if allow_network and (url.startswith("http://") or url.startswith("https://")):
        try:
            import httpx
            with httpx.Client(timeout=3.0, follow_redirects=True, headers={"User-Agent": "Mastui/1.0"}) as client:
                resp = client.get(url)
                if resp.status_code == 200 and resp.content:
                    target_file.write_bytes(resp.content)
                    return target_file
        except Exception:
            pass

    return None


_HALFBLOCK_CACHE: dict[tuple, str] = {}


def render_halfblock_ansi(
    image: Any, max_width: int = 50, max_height: int = 16
) -> str:
    """Render a PIL Image into 24-bit TrueColor ANSI upper-half-block (▀) text scaled to width."""
    if not PIL_AVAILABLE or image is None:
        return "[Image preview unavailable - PIL not installed]"

    img_key = getattr(image, "filename", None) or id(image)
    cache_key = (img_key, max_width, max_height)
    if cache_key in _HALFBLOCK_CACHE:
        return _HALFBLOCK_CACHE[cache_key]

    try:
        w, h = image.size
        if w <= 0 or h <= 0:
            return ""

        aspect = (h / 2.0) / w
        target_w = max_width
        target_h = int(target_w * aspect * 2)

        if target_h > max_height * 2:
            target_h = max_height * 2
            target_w = int(target_h / (aspect * 2))

        target_w = max(4, target_w)
        target_h = max(2, target_h + (target_h % 2))

        resized = image.resize((target_w, target_h), PILImage.Resampling.BILINEAR).convert("RGB")
        pixels = resized.load()

        lines: list[str] = []
        for y in range(0, target_h, 2):
            row_chunks: list[str] = []
            for x in range(target_w):
                r1, g1, b1 = pixels[x, y]
                r2, g2, b2 = pixels[x, y + 1]
                row_chunks.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀\033[0m")
            lines.append("".join(row_chunks))

        res = "\n".join(lines)
        if len(_HALFBLOCK_CACHE) > 200:
            _HALFBLOCK_CACHE.clear()
        _HALFBLOCK_CACHE[cache_key] = res
        return res
    except Exception as e:
        return f"[Error rendering image: {e}]"


class ImageModal(Model):
    """Full modal dialog for viewing an image attachment with metadata and external launcher."""

    def __init__(
        self,
        attachment: dict[str, Any],
        profile_dir: Path | None = None,
        width: int = 76,
        height: int = 24,
        renderer: str = "ansi",
    ) -> None:
        self.attachment = attachment
        self.url = str(attachment.get("url") or attachment.get("preview_url") or "")
        self.description = attachment.get("description") or "No description provided"
        self.media_type = attachment.get("type", "image")
        self.profile_dir = profile_dir
        self.width = max(40, width)
        self.height = max(14, height)
        self.renderer = renderer

        self.cached_file = (
            find_cached_attachment_file(attachment, profile_dir)
            or find_cached_image_file(self.url, profile_dir)
            or download_and_cache_image(self.url, profile_dir)
        )
        self.pil_image = None
        self.image_ansi = ""
        self.dimensions_str = ""

        if self.cached_file and PIL_AVAILABLE:
            try:
                self.pil_image = PILImage.open(self.cached_file)
                self.dimensions_str = f"{self.pil_image.width} × {self.pil_image.height} ({self.pil_image.format})"
                max_img_w = max(20, self.width - 6)
                max_img_h = max(6, self.height - 8)
                self.image_ansi = render_halfblock_ansi(self.pil_image, max_width=max_img_w, max_height=max_img_h)
            except Exception:
                self.image_ansi = "[Corrupted image cache file]"
        else:
            self.image_ansi = f"🖼️  [Online image: {self.url[:50]}...]\n(Press 'o' to open directly in web browser/viewer)"

    def init(self) -> Cmd | None:
        if self.renderer == "external":
            def _open_ext() -> Msg | None:
                target = str(self.cached_file) if self.cached_file else self.url
                try:
                    if os.uname().sysname == "Darwin":
                        subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return None
            return _open_ext
        return None

    def update(self, msg: Msg) -> tuple[ImageModal, Cmd | None]:
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "esc" | "q":
                    def _close() -> Msg:
                        return ModalCloseMsg()
                    return self, _close
                case "o" | "enter":
                    # Open in system viewer / browser
                    target = str(self.cached_file) if self.cached_file else self.url
                    try:
                        if os.uname().sysname == "Darwin":
                            subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                    return self, None
                case "y":
                    copy_to_clipboard(self.url)
                    return self, None
        return self, None

    def view(self) -> str:
        inner_w = max(36, self.width - 2)

        # Title bar
        title = Style().bold(True).foreground("#00E5FF").render("🖼️  MEDIA ATTACHMENT PREVIEW")

        # Metadata
        meta_items = [f"Type: {self.media_type.capitalize()}"]
        if self.dimensions_str:
            meta_items.append(self.dimensions_str)
        meta_line = Style().faint(True).foreground("#8888AA").render("  │  ".join(meta_items))

        # Description
        desc_line = Style().foreground("#DDDDDD").render(f"Alt text: {self.description}")
        if len(self.description) > inner_w - 6:
            desc_line = truncate_ansi(desc_line, inner_w - 6)

        # Keys
        keys_hint = Style().foreground("#777799").render(
            "[o/Enter] Open in external viewer   [y] Copy link   [Esc/q] Close"
        )

        body = (
            f" {title}\n"
            f" {meta_line}\n"
            f" {desc_line}\n\n"
            f"{self.image_ansi}\n\n"
            f" {keys_hint}"
        )

        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF")
            .width(inner_w)
            .align(Align.CENTER)
            .render(body)
        )
