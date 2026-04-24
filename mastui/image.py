from textual.widgets import Static
from textual import events
import httpx
from io import BytesIO
from textual_image.renderable import Image, HalfcellImage, TGPImage
from textual_image.widget.sixel import Image as SixelWidget
from PIL import Image as PILImage
import hashlib
import logging
import time

log = logging.getLogger(__name__)
MAX_IMAGE_RETRIES = 3
RETRY_BACKOFF_SECONDS = 0.5


class ImageWidget(Static):
    """A widget to display an image."""

    def __init__(self, url: str, config, **kwargs):
        super().__init__("🖼️  Loading image...", **kwargs)
        self.url = url
        self.config = config
        self.pil_image = None
        self._is_mounted = False
        self._sixel_widget = None

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
                image_data = None
                for attempt in range(1, MAX_IMAGE_RETRIES + 1):
                    try:
                        log.debug(
                            f"Image not in cache, downloading: {self.url} (attempt {attempt}/{MAX_IMAGE_RETRIES})"
                        )
                        with httpx.stream(
                            "GET", self.url, timeout=30, verify=self.config.ssl_verify
                        ) as response:
                            response.raise_for_status()
                            image_data = response.read()
                        cache_path.write_bytes(image_data)
                        break
                    except (httpx.TimeoutException, httpx.NetworkError) as e:
                        if attempt < MAX_IMAGE_RETRIES:
                            log.debug(
                                "Image download retry for %s after network/timeout error: %s",
                                self.url,
                                e,
                            )
                            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                            continue
                        log.debug(
                            "Image download failed after %s attempts for %s: %s",
                            MAX_IMAGE_RETRIES,
                            self.url,
                            e,
                        )
                        raise
                    except Exception as e:
                        log.debug("Image download failed for %s: %s", self.url, e)
                        raise

                if image_data is None:
                    raise RuntimeError("Image download did not return data")

            self.pil_image = PILImage.open(BytesIO(image_data))
            if self._is_mounted:
                self.app.call_from_thread(self.render_image)
        except Exception as e:
            log.debug(f"Error loading image: {e}")
            if self._is_mounted:
                self.app.call_from_thread(self.show_error)

    def on_resize(self, event: events.Resize) -> None:
        """Re-render the image when the widget is resized."""
        self.render_image()

    def show_error(self):
        """Displays an error message when the image fails to load."""
        self._remove_sixel_widget()
        self.update("[Image load failed]")

    def _remove_sixel_widget(self):
        if self._sixel_widget is None:
            return
        try:
            self._sixel_widget.remove()
        except Exception:
            # Widget may have already been removed from DOM
            pass
        self._sixel_widget = None

    def _render_sixel_widget(self, width: int):
        if self._sixel_widget is None:
            self._sixel_widget = SixelWidget(self.pil_image)
            self.mount(self._sixel_widget)
        else:
            self._sixel_widget.image = self.pil_image

        self.update("")
        self._sixel_widget.styles.width = width
        self._sixel_widget.styles.height = "auto"
        self.styles.height = "auto"

    def render_image(self):
        """Renders the image."""
        if not self.pil_image:
            return  # Image not loaded yet

        if self.pil_image.width == 0 or self.pil_image.height == 0:
            self.show_error()
            return

        width = self.size.width - 4
        if width <= 0:
            self._remove_sixel_widget()
            self.update("...")  # Too small to render
            return

        if self.config.image_renderer == "sixel":
            self._render_sixel_widget(width)
            return

        self._remove_sixel_widget()
        renderer_map = {
            "auto": Image,
            "ansi": HalfcellImage,
            "tgp": TGPImage,
        }
        renderer_class = renderer_map.get(self.config.image_renderer, Image)
        image = renderer_class(self.pil_image, width=width, height="auto")
        self.styles.height = "auto"
        self.update(image)
