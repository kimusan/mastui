from textual.widgets import Static
from textual import events
import httpx
from io import BytesIO
from textual_image.renderable import Image, SixelImage, HalfcellImage, TGPImage
from PIL import Image as PILImage
import hashlib
import logging

log = logging.getLogger(__name__)


class ImageWidget(Static):
    """A widget to display an image."""

    def __init__(self, url: str, config, **kwargs):
        super().__init__("🖼️  Loading image...", **kwargs)
        self.url = url
        self.config = config
        self.pil_image = None
        self._is_mounted = False

    def on_mount(self) -> None:
        """Load the image when the widget is mounted."""
        self._is_mounted = True
        self.run_worker(self.load_image, thread=True)

    def on_unmount(self) -> None:
        """Set the mounted flag to False when the widget is unmounted."""
        self._is_mounted = False

    def load_image(self):
        """Loads the image from the cache or URL."""
        try:
            # Create a unique filename from the URL
            filename = hashlib.sha256(self.url.encode()).hexdigest()
            cache_path = self.config.image_cache_dir / filename
            log.debug(f"Image cache path: {cache_path}")

            if cache_path.exists():
                log.debug(f"Loading image from cache: {self.url}")
                image_data = cache_path.read_bytes()
            else:
                log.debug(f"Image not in cache, downloading: {self.url}")
                with httpx.stream(
                    "GET", self.url, timeout=30, verify=self.config.ssl_verify
                ) as response:
                    response.raise_for_status()
                    image_data = response.read()
                cache_path.write_bytes(image_data)

            self.pil_image = PILImage.open(BytesIO(image_data))
            if self._is_mounted:
                self.app.call_from_thread(self.render_image)
        except Exception as e:
            log.error(f"Error loading image: {e}", exc_info=True)
            if self._is_mounted:
                self.app.call_from_thread(self.show_error)

    def on_resize(self, event: events.Resize) -> None:
        """Re-render the image when the widget is resized."""
        self.render_image()

    def show_error(self):
        """Displays an error message when the image fails to load."""
        self.update("[Image load failed]")

    def render_image(self):
        """Renders the image."""
        if not self.pil_image:
            return  # Image not loaded yet

        if self.pil_image.width == 0 or self.pil_image.height == 0:
            self.show_error()
            return

        renderer_map = {
            "auto": Image,
            "sixel": SixelImage,
            "ansi": HalfcellImage,
            "tgp": TGPImage,
        }
        renderer_class = renderer_map.get(self.config.image_renderer, Image)

        width = self.size.width - 4
        if width <= 0:
            self.update("...")  # Too small to render
            return

        image = renderer_class(self.pil_image, width=width, height="auto")
        self.styles.height = "auto"
        self.update(image)
