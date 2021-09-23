import os
import yaml
import click
import subprocess
from typing import Optional
from xdg import xdg_config_home
from dataclasses import dataclass, asdict, fields


@dataclass
class Theme:
    """A base theme container, uses pyserde for (de)serialization"""

    wallpaper: str = None
    rofi_theme: str = None
    polybar_theme: str = None
    gtk_theme: str = None
    alacritty_theme: str = None

    def _apply_wallpaper(self):
        """Use feh to apply the current wallpaper"""
        subprocess.call(["feh", "--bg-fill", self.wallpaper])

    def _apply_rofi(self):
        """Modify the config.rasi to use the selected theme"""
        confpath = os.path.join(xdg_config_home(), "rofi", "config.rasi")
        with open(confpath, "w") as file:
            file.write(
                f"""
                @import "layout.rasi"
                @import "themes/{self.rofi_theme}.rasi"
                """
            )

    def _apply_polybar(self):
        """Modify the polybar conffile to use what's needed"""
        confpath = os.path.join(xdg_config_home(), "polybar", "colors")
        with open(confpath, "w") as file:
            file.write(f"include-file='~/.config/polybar/themes/{self.polybar_theme}'")

    def _apply_alacritty(self):
        """Apply the alacritty theme"""
        confpath = os.path.join(xdg_config_home(), "alacritty", "alacritty.yml")
        original = open(confpath, "r").read()
        lines = original.split("\n")
        while not lines[-1]:
            lines.pop()
        lines[-1] = f"colors: *{self.alacritty_theme}-theme"
        lines.append("")
        result = "\n".join(lines)
        with open(confpath, "w") as file:
            file.write(result)

    def apply(self):
        """Apply this theme"""
        if self.wallpaper:
            self._apply_wallpaper()
        if self.rofi_theme:
            self._apply_rofi()
        if self.polybar_theme:
            self._apply_polybar()
        if self.alacritty_theme:
            self._apply_alacritty()


class Manager:
    """A class that loads and saves the themes"""

    def __init__(self, config: Optional[str] = None):
        """Initialize the manager

        Args:
            config: (optional) the path of a config directory to use
        """
        self.generate_paths(config)
        self.load_themes()
        self.select_theme()

    def generate_paths(self, config: Optional[str] = None):
        """Generate the paths to every config file

        Args:
            config: (optional) the path of a config directory to use
        """
        if config is None:
            config = xdg_config_home()
        self.config = config
        self.confdir = os.path.join(self.config, "tiny-theme-switcher")
        if not os.path.exists(self.confdir):
            os.mkdir(self.confdir)
        self.conffile = os.path.join(self.confdir, "theme")
        self.themesfile = os.path.join(self.confdir, "themes.yaml")

    def load_themes(self):
        """Load the themes from a provided config file"""
        if os.path.exists(self.themesfile):
            self.rawthemes = yaml.safe_load(open(self.themesfile))
            if not isinstance(self.rawthemes, dict):
                self.rawthemes = {}
        else:
            self.rawthemes = {}
        self.themes = {name: Theme(**data) for name, data in self.rawthemes.items()}

    def use_default_theme(self):
        """Load the default theme to use

        The first one alphabetically, an empty one if the conffile is empty
        """
        self.themename = sorted(self.themes.keys())[0] if self.themes else None
        if self.themename is None:
            self.theme = Theme()

    def select_theme(self, theme: Optional[str] = None):
        """Select a theme

        Will read the name from the config file if not specified.
        Will use the first one alphabetically if it does not exist.
        Will automatically save the changes.

        Args:
            theme: (optional) the theme to select
        """
        if theme:
            self.themename = theme
        elif os.path.exists(self.conffile):
            self.themename = open(self.conffile, "r").read().strip()
        else:
            self.use_default_theme()
        if self.themename not in self.themes.keys():
            self.use_default_theme()
            if self.themename is not None:
                with open(self.conffile, "w") as conffile:
                    conffile.write(self.themename)
        elif theme is not None:
            with open(self.conffile, "w") as conffile:
                conffile.write(self.themename)
        if self.themename is not None:
            self.theme = self.themes[self.themename]

    def apply(self):
        """Apply the currently selected theme"""
        self.theme.apply()

    def append(self, name: str):
        """Add an empty theme

        Args:
            name: the name of a theme to save
        """
        self.themes[name] = Theme()
        self.dump()

    def remove(self, name: str):
        """Remove a theme from the config file

        Args:
            name: the name of the theme to remove
        """
        del self.themes[name]
        self.dump()
        if self.themename == name:
            self.use_default_theme()

    def dump(self):
        """Dump all changes into the conffile"""
        self.rawthemes = {name: asdict(theme) for name, theme in self.themes.items()}
        yaml.safe_dump(self.rawthemes, open(self.themesfile, "w"))


@click.group(help="A little script that lets me switch themes on-the-fly")
def main():
    pass


@main.command(help="Apply a selected theme")
@click.option(
    "--name",
    help="Theme name to use, will reapply the previous one if unspecified",
    type=str,
    default=None,
)
@click.option(
    "--config",
    help="Path to the directory where all configs are saved",
    type=click.Path(exists=True),
    default=None,
)
def apply(name: Optional[str] = None, config: Optional[str] = None):
    manager = Manager(config=config)
    if name is not None:
        manager.select_theme(name)
    manager.apply()


@main.group(help="Create, destroy or modify themes")
def theme():
    pass


@theme.command(help="Create a new theme")
@click.option(
    "--name", help="The name for the newly created theme", type=str, required=True
)
@click.option(
    "--config",
    help="Path to the directory where all configs are saved",
    type=click.Path(exists=True),
    default=None,
)
def create(name: str, config: Optional[str] = None):
    manager = Manager(config=config)
    manager.append(name)


@theme.command(help="Delete a theme")
@click.option("--name", help="The name of the deleted theme", type=str, required=True)
@click.option(
    "--config",
    help="Path to the directory where all configs are saved",
    type=click.Path(exists=True),
    default=None,
)
def delete(name: str, config: Optional[str] = None):
    manager = Manager(config=config)
    manager.remove(name)


@theme.command(help="List all themes")
@click.option(
    "--config",
    help="Path to the directory where all configs are saved",
    type=click.Path(exists=True),
    default=None,
)
def list(config: Optional[str] = None):
    manager = Manager(config=config)
    for name in manager.themes.keys():
        click.echo(name)


@theme.command(help="Set acurrent theme's attribute")
@click.option(
    "--config",
    help="Path to the directory where all configs are saved",
    type=click.Path(exists=True),
    default=None,
)
@click.option(
    "--field",
    help="The field to be modified",
    type=click.Choice([field.name for field in fields(Theme)], False),
    required=True,
)
@click.option("--value", help="The target value", type=str, required=True)
def set(config, field, value):
    manager = Manager(config=config)
    setattr(manager.theme, field, value)
    manager.dump()


@theme.command(help="Get a current theme's attribute")
@click.option(
    "--config",
    help="Path to the directory where all configs are saved",
    type=click.Path(exists=True),
    default=None,
)
@click.option(
    "--field",
    help="The field to be retrieved",
    type=click.Choice([field.name for field in fields(Theme)], False),
    required=True,
)
def get(config, field):
    manager = Manager(config=config)
    click.echo(getattr(manager.theme, field))


if __name__ == "__main__":
    main()
