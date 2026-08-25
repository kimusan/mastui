from pathlib import Path
import os
import sys

# Add repo root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_packages import get_version, normalize_tree_permissions


def test_get_version():
    version = get_version()
    assert version
    assert isinstance(version, str)
    assert len(version.split(".")) >= 3


def test_desktop_entry_exists_and_valid():
    desktop_file = ROOT / "packaging" / "mastui.desktop"
    assert desktop_file.exists()
    content = desktop_file.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in content
    assert "Type=Application" in content
    assert "Exec=mastui" in content
    assert "Terminal=true" in content


def test_rpm_spec_exists():
    spec_file = ROOT / "packaging" / "rpm" / "mastui.spec"
    assert spec_file.exists()
    content = spec_file.read_text(encoding="utf-8")
    assert "Name:           mastui" in content
    assert "%files" in content
    assert "%{_bindir}/mastui" in content


def test_arch_pkgbuild_exists():
    pkgbuild = ROOT / "packaging" / "arch" / "PKGBUILD"
    assert pkgbuild.exists()
    content = pkgbuild.read_text(encoding="utf-8")
    assert "pkgname=mastui-bin" in content
    assert "arch=('x86_64')" in content
    assert "package()" in content


def test_pyinstaller_spec_exists():
    spec_file = ROOT / "mastui.spec"
    assert spec_file.exists()
    content = spec_file.read_text(encoding="utf-8")
    assert "mastui/__main__.py" in content
    assert "Analysis" in content
    assert "EXE" in content


def test_normalize_tree_permissions(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    os.chmod(d, 0o777)
    
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe_file = bin_dir / "mastui"
    exe_file.write_text("dummy")
    os.chmod(exe_file, 0o600)
    
    data_file = d / "file.txt"
    data_file.write_text("data")
    os.chmod(data_file, 0o777)
    
    normalize_tree_permissions(tmp_path)
    
    assert oct(d.stat().st_mode & 0o777) == "0o755"
    assert oct(exe_file.stat().st_mode & 0o777) == "0o755"
    assert oct(data_file.stat().st_mode & 0o777) == "0o644"


def test_android_project_structure():
    android_dir = ROOT / "android"
    assert android_dir.exists()
    assert (android_dir / "build.gradle").exists()
    assert (android_dir / "settings.gradle").exists()
    assert (android_dir / "app" / "build.gradle").exists()
    assert (android_dir / "app" / "src" / "main" / "AndroidManifest.xml").exists()
    assert (android_dir / "app" / "src" / "main" / "java" / "dk" / "schulz" / "mastui" / "MainActivity.kt").exists()

