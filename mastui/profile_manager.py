import os
from pathlib import Path
import shutil
import logging

log = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "mastui"
        self.profiles_dir = self.config_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.last_profile_file = self.config_dir / "last_profile.txt"

    def get_last_profile(self) -> str | None:
        """Reads the name of the last used profile."""
        try:
            if self.last_profile_file.exists():
                return self.last_profile_file.read_text().strip()
        except (IOError, OSError) as e:
            log.error(f"Failed to read last profile file: {e}", exc_info=True)
            return None
        return None

    def set_last_profile(self, profile_name: str):
        """Saves the name of the last used profile."""
        try:
            self.last_profile_file.write_text(profile_name)
        except (IOError, OSError) as e:
            log.error(f"Failed to write last profile file: {e}", exc_info=True)


    def get_profiles(self) -> list[str]:
        """Returns a list of available profile names."""
        return [d.name for d in self.profiles_dir.iterdir() if d.is_dir()]

    def get_profile_path(self, profile_name: str) -> Path:
        """Returns the path to a specific profile directory."""
        return self.profiles_dir / profile_name

    def create_profile(self, profile_name: str, env_content: str):
        """Creates a new profile directory and .env file."""
        profile_path = self.get_profile_path(profile_name)
        profile_path.mkdir(exist_ok=True)
        (profile_path / ".env").write_text(env_content)

    def delete_profile(self, profile_name: str):
        """Deletes a profile directory."""
        profile_path = self.get_profile_path(profile_name)
        if profile_path.exists():
            shutil.rmtree(profile_path)

    def migrate_old_profile(self) -> bool:
        """Migrates the old single-profile setup to the new profiles directory."""
        old_env_file = self.profiles_dir.parent / ".env"
        old_cache_db = self.profiles_dir.parent / "cache.db"
        
        if old_env_file.exists():
            default_profile_path = self.get_profile_path("default")
            default_profile_path.mkdir(exist_ok=True)
            
            # Move the old .env file
            shutil.move(str(old_env_file), str(default_profile_path / ".env"))
            
            # Move the old cache.db if it exists
            if old_cache_db.exists():
                shutil.move(str(old_cache_db), str(default_profile_path / "cache.db"))
            
            return True
        return False

profile_manager = ProfileManager()
