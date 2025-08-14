from textual.widget import Widget
from textual.widgets import Static
from PIL import Image
import httpx
from io import BytesIO
from rich.panel import Panel
from rich.text import Text
from textual.events import Enter

class ImageWidget(Widget):
    """A widget to display an image."""

    DEFAULT_CSS = """
    ImageWidget {
        height: auto;
    }
    """

    def __init__(self, url: str, renderer: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self.renderer = renderer
        self.image_loaded = False

    def compose(self):
        yield Static(Panel("Loading image...", style="dim"))

    def on_enter(self, event: Enter) -> None:
        """Load the image when it's about to be displayed."""
        if not self.image_loaded:
            self.run_worker(self.load_image, thread=True)
            self.image_loaded = True

    def load_image(self):
        """Loads the image from the URL."""
        try:
            # The width is the container width minus 4 for the panel border and padding
            self.image_width = self.size.width - 4
            with httpx.stream("GET", self.url, timeout=30) as response:
                response.raise_for_status()
                image_data = response.read()
            img = Image.open(BytesIO(image_data))
            self.app.call_from_thread(self.render_image, img)
        except Exception as e:
            self.app.call_from_thread(self.show_error_panel)

    def show_error_panel(self):
        """Displays an error panel when the image fails to load."""
        self.query_one(Static).update(Panel("[Image load failed]"))

    def render_image(self, img: Image):
        """Renders the image."""
        if self.renderer == "sixel":
            self.render_sixel(img)
        else:
            self.render_ansi(img)

    def render_ansi(self, img: Image):
        """Renders the image as ANSI art using full blocks."""
        img = img.convert("RGB")
        width, height = img.size
        aspect_ratio = height / width
        new_width = self.image_width
        new_height = int(aspect_ratio * new_width * 0.55) # Correction factor for character aspect ratio
        img = img.resize((new_width, new_height))
        
        pixels = img.load()
        
        ansi_str = ""
        for y in range(new_height):
            for x in range(new_width):
                pixel = pixels[x, y]
                # Set both background and foreground to the same color and use a full block
                ansi_str += f"\x1b[48;2;{pixel[0]};{pixel[1]};{pixel[2]}m"
                ansi_str += f"\x1b[38;2;{pixel[0]};{pixel[1]};{pixel[2]}m"
                ansi_str += "█"
            ansi_str += "\x1b[0m\n"
        
        ansi_str = ansi_str.strip()
        self.styles.height = ansi_str.count("\n") + 2 # +2 for panel border
        self.query_one(Static).update(Panel(Text.from_ansi(ansi_str)))

    def render_sixel(self, img: Image):
        """Renders the image as Sixel."""
        # Sixel rendering is more complex and requires a library.
        # For now, we'll just show a placeholder.
        self.query_one(Static).update(Panel("[Sixel image placeholder]"))
