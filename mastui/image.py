from textual.widgets import Static
import httpx
from io import BytesIO
from textual_image.renderable import Image, SixelImage, HalfcellImage, TGPImage
from PIL import Image as PILImage


class ImageWidget(Static):
    """A widget to display an image."""

    def __init__(self, url: str, renderer: str, **kwargs):
        super().__init__("Loading image...", **kwargs)
        self.url = url
        self.renderer = renderer

    def on_mount(self):
        self.run_worker(self.load_image, thread=True)

    def load_image(self):
        """Loads the image from the URL."""
        try:
            with httpx.stream("GET", self.url, timeout=30) as response:
                response.raise_for_status()
                image_data = response.read()
            img = PILImage.open(BytesIO(image_data))
            self.app.call_from_thread(self.render_image, img)
        except Exception as e:
            self.app.call_from_thread(self.show_error)

    def show_error(self):
        """Displays an error message when the image fails to load."""
        self.update("[Image load failed]")

    def render_image(self, img: PILImage):
        """Renders the image."""
        renderer_map = {
            "auto": Image,
            "sixel": SixelImage,
            "ansi": HalfcellImage,
            "tgp": TGPImage,
        }
        renderer_class = renderer_map.get(self.renderer, Image)
        image = renderer_class(img, width=self.size.width, height="auto")

        # Set the height of the widget to match the image
        self.styles.height = "auto"

        self.update(image)
