from textual.widgets import Static
import httpx
from io import BytesIO
from textual_image.renderable import Image, SixelImage, HalfcellImage, TGPImage
from PIL import Image as PILImage
from mastui.config import config
import hashlib


class ImageWidget(Static):
    """A widget to display an image."""

    def __init__(self, url: str, renderer: str, **kwargs):
        super().__init__("Loading image...", **kwargs)
        self.url = url
        self.renderer = renderer

    def on_mount(self):
        self.run_worker(self.load_image, thread=True)

    def load_image(self):
        """Loads the image from the cache or URL."""
        try:
            # Create a unique filename from the URL
            filename = hashlib.sha256(self.url.encode()).hexdigest()
            cache_path = config.image_cache_dir / filename

            if cache_path.exists():
                # Load from cache
                image_data = cache_path.read_bytes()
            else:
                # Download from URL
                with httpx.stream("GET", self.url, timeout=30, verify=config.ssl_verify) as response:
                    response.raise_for_status()
                    image_data = response.read()
                # Save to cache
                cache_path.write_bytes(image_data)

            img = PILImage.open(BytesIO(image_data))
            self.app.call_from_thread(self.render_image, img)
        except Exception as e:
            self.app.call_from_thread(self.show_error)

    def show_error(self):
        """Displays an error message when the image fails to load."""
        self.update("[Image load failed]")

    def render_image(self, img: PILImage):
        """Renders the image."""
        if img.width == 0 or img.height == 0:
            self.show_error()
            return

        renderer_map = {
            "auto": Image,
            "sixel": SixelImage,
            "ansi": HalfcellImage,
            "tgp": TGPImage,
        }
        renderer_class = renderer_map.get(self.renderer, Image)

        width = self.size.width - 4
        if width <= 0:
            self.show_error()
            return

        image = renderer_class(img, width=width)

        # Set the height of the widget to match the image
        self.styles.height = "auto"

        self.update(image)
