from textual.widgets import Static

class LogoWidget(Static):
    """A widget to display the Mastui ASCII art logo."""

    def on_mount(self):
        """Render the logo."""
        logo = r"""
            [bold cyan]
            
 888b     d888                   888             d8b 
 8888b   d8888                   888             Y8P 
 88888b.d88888                   888                 
 888Y88888P888  8888b.  .d8888b  888888 888  888 888 
 888 Y888P 888     "88b 88K      888    888  888 8K8 
 888  Y8P  888 .d888888 "Y8888b. 888    888  888 8I8 
 888   "   888 888  888      X88 Y88b.  Y88b 888 8M8 
 888       888 "Y888888  88888P'  "Y888  "Y88888 888 
            [/bold cyan]
            """
        self.update(logo)
