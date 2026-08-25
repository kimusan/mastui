#!/usr/bin/env python3
"""
scripts/build_packages.py

Unified build and packaging script for mastui.
Supports building:
  - Standalone binary (PyInstaller)
  - Debian/Ubuntu package (.deb)
  - RedHat/Fedora/openSUSE package (.rpm)
  - AppImage (.AppImage)
  - Arch Linux package (.pkg.tar.zst)
  - Windows standalone zip (.zip)
  - SHA256 checksums (SHA256SUMS.txt)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess  # nosec B404
import sys
import tarfile
import time
import zipfile
from pathlib import Path
from typing import List, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
PACKAGING_DIR = ROOT_DIR / "packaging"
ASSETS_DIR = ROOT_DIR / "assets"


def run_cmd(cmd: List[str], *, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess command with clear logging."""
    cwd_path = cwd or ROOT_DIR
    print(f"==> Running: {' '.join(str(c) for c in cmd)} (in {cwd_path})")
    result = subprocess.run(cmd, cwd=str(cwd_path), check=False)  # nosec B603
    if check and result.returncode != 0:
        print(f"Error: command failed with return code {result.returncode}: {' '.join(str(c) for c in cmd)}", file=sys.stderr)
        sys.exit(result.returncode)
    return result


def get_version() -> str:
    """Read version from pyproject.toml."""
    pyproject = ROOT_DIR / "pyproject.toml"
    if not pyproject.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("version ="):
            # version = "1.11.0"
            parts = line.split("=", 1)
            return parts[1].strip().strip('"').strip("'")
    
    raise ValueError("Could not find version in pyproject.toml")


def ensure_dirs() -> None:
    """Ensure dist and build directories exist."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def build_binary() -> Path:
    """Build standalone executable using PyInstaller."""
    print("\n--- Building Standalone Binary with PyInstaller ---")
    ensure_dirs()
    spec_file = ROOT_DIR / "mastui.spec"
    if not spec_file.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_file}")
    
    # Run PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_file)]
    run_cmd(cmd)
    
    ext = ".exe" if platform.system() == "Windows" else ""
    binary_path = DIST_DIR / f"mastui{ext}"
    if not binary_path.exists():
        raise FileNotFoundError(f"Expected built binary at {binary_path}, but it does not exist.")
    
    print(f"Successfully built binary: {binary_path}")
    return binary_path


def normalize_tree_permissions(root: Path) -> None:
    """Normalize file and directory permissions in a build tree for packaging."""
    if not root.exists():
        return
    for item in root.rglob("*"):
        if item.is_dir():
            os.chmod(item, 0o755)
        elif item.is_file():
            if item.parent.name == "bin" or item.name == "AppRun":
                os.chmod(item, 0o755)
            else:
                os.chmod(item, 0o644)
    if root.is_dir():
        os.chmod(root, 0o755)


def build_deb(version: str) -> Path:
    """Build Debian/Ubuntu .deb package."""
    print(f"\n--- Building Debian Package (.deb) for v{version} ---")
    binary = DIST_DIR / "mastui"
    if not binary.exists():
        binary = build_binary()
    
    pkg_name = f"mastui_{version}_amd64"
    deb_root = BUILD_DIR / "deb" / pkg_name
    if deb_root.exists():
        shutil.rmtree(deb_root)
    
    # Create directory layout
    debian_dir = deb_root / "DEBIAN"
    bin_dir = deb_root / "usr" / "bin"
    apps_dir = deb_root / "usr" / "share" / "applications"
    icons_dir = deb_root / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    licenses_dir = deb_root / "usr" / "share" / "licenses" / "mastui"
    
    debian_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    apps_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)
    licenses_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy files
    shutil.copy2(binary, bin_dir / "mastui")
    
    desktop_src = PACKAGING_DIR / "mastui.desktop"
    if desktop_src.exists():
        shutil.copy2(desktop_src, apps_dir / "mastui.desktop")
    
    icon_src = ASSETS_DIR / "mastui-logo.png"
    if icon_src.exists():
        shutil.copy2(icon_src, icons_dir / "mastui.png")
    
    license_src = ROOT_DIR / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, licenses_dir / "LICENSE")
    
    # Write control file
    control_content = f"""Package: mastui
Version: {version}
Section: net
Priority: optional
Architecture: amd64
Maintainer: Kim Schulz
Homepage: https://github.com/kimusan/mastui
Description: A Mastodon TUI client
 Mastui is a modern, terminal user interface (TUI) client for Mastodon
 built with Textual and Python.
"""
    (debian_dir / "control").write_text(control_content, encoding="utf-8")
    
    # Normalize permissions so dpkg-deb is satisfied
    normalize_tree_permissions(deb_root)
    
    out_deb = DIST_DIR / f"{pkg_name}.deb"
    if out_deb.exists():
        out_deb.unlink()
        
    dpkg_deb = shutil.which("dpkg-deb")
    if dpkg_deb:
        run_cmd([dpkg_deb, "--build", "--root-owner-group", str(deb_root), str(out_deb)])
    else:
        print("Warning: dpkg-deb not found on system. Skipping .deb build.", file=sys.stderr)
        return out_deb
    
    print(f"Successfully built Debian package: {out_deb}")
    return out_deb


def build_rpm(version: str) -> Path:
    """Build RedHat/Fedora/openSUSE .rpm package."""
    print(f"\n--- Building RPM Package (.rpm) for v{version} ---")
    binary = DIST_DIR / "mastui"
    if not binary.exists():
        binary = build_binary()
    
    rpmbuild = shutil.which("rpmbuild")
    if not rpmbuild:
        print("Warning: rpmbuild not found on system. Skipping .rpm build.", file=sys.stderr)
        return DIST_DIR / f"mastui-{version}-1.x86_64.rpm"
    
    rpm_topdir = BUILD_DIR / "rpm"
    if rpm_topdir.exists():
        shutil.rmtree(rpm_topdir)
    
    for d in ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS", "tmp", "db"]:
        (rpm_topdir / d).mkdir(parents=True, exist_ok=True)
    
    # Copy sources into SOURCES
    sources_dir = rpm_topdir / "SOURCES"
    shutil.copy2(binary, sources_dir / "mastui")
    
    desktop_src = PACKAGING_DIR / "mastui.desktop"
    if desktop_src.exists():
        shutil.copy2(desktop_src, sources_dir / "mastui.desktop")
    
    icon_src = ASSETS_DIR / "mastui-logo.png"
    if icon_src.exists():
        shutil.copy2(icon_src, sources_dir / "mastui.png")
    
    license_src = ROOT_DIR / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, sources_dir / "LICENSE")
    
    spec_src = PACKAGING_DIR / "rpm" / "mastui.spec"
    spec_dest = rpm_topdir / "SPECS" / "mastui.spec"
    shutil.copy2(spec_src, spec_dest)
    
    # Execute rpmbuild
    run_cmd([
        rpmbuild,
        "-bb",
        "--define", f"_topdir {rpm_topdir}",
        "--define", f"_tmppath {rpm_topdir}/tmp",
        "--define", f"_dbpath {rpm_topdir}/db",
        "--define", f"_version {version}",
        str(spec_dest),
    ])
    
    # Find generated rpm
    rpms = list((rpm_topdir / "RPMS").glob("**/*.rpm"))
    if not rpms:
        raise FileNotFoundError("rpmbuild completed but no .rpm file was found in RPMS/")
    
    out_rpm = DIST_DIR / rpms[0].name
    shutil.copy2(rpms[0], out_rpm)
    print(f"Successfully built RPM package: {out_rpm}")
    return out_rpm


def build_appimage(version: str) -> Path:
    """Build standalone AppImage."""
    print(f"\n--- Building AppImage for v{version} ---")
    binary = DIST_DIR / "mastui"
    if not binary.exists():
        binary = build_binary()
    
    appdir = BUILD_DIR / "appimage" / "AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    
    usr_bin = appdir / "usr" / "bin"
    usr_apps = appdir / "usr" / "share" / "applications"
    usr_icons = appdir / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    
    usr_bin.mkdir(parents=True, exist_ok=True)
    usr_apps.mkdir(parents=True, exist_ok=True)
    usr_icons.mkdir(parents=True, exist_ok=True)
    
    # Copy binary
    shutil.copy2(binary, usr_bin / "mastui")
    os.chmod(usr_bin / "mastui", 0o755)
    
    # Desktop and icon inside usr/share
    desktop_src = PACKAGING_DIR / "mastui.desktop"
    if desktop_src.exists():
        shutil.copy2(desktop_src, usr_apps / "mastui.desktop")
        shutil.copy2(desktop_src, appdir / "mastui.desktop")
    
    icon_src = ASSETS_DIR / "mastui-logo.png"
    if icon_src.exists():
        shutil.copy2(icon_src, usr_icons / "mastui.png")
        shutil.copy2(icon_src, appdir / "mastui.png")
        shutil.copy2(icon_src, appdir / ".DirIcon")
    
    # Create AppRun script
    apprun = appdir / "AppRun"
    apprun_content = """#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/mastui" "$@"
"""
    apprun.write_text(apprun_content, encoding="utf-8")
    
    normalize_tree_permissions(appdir)
    
    appimagetool = shutil.which("appimagetool")
    out_appimage = DIST_DIR / f"mastui-{version}-x86_64.AppImage"
    
    if not appimagetool:
        # Check if appimagetool exists in build dir
        local_tool = BUILD_DIR / "appimagetool"
        if local_tool.exists() and os.access(local_tool, os.X_OK):
            appimagetool = str(local_tool)
    
    if not appimagetool:
        print("Warning: appimagetool not found on system. Skipping AppImage bundle generation.", file=sys.stderr)
        print(f"AppDir prepared at: {appdir}")
        return out_appimage
    
    env = os.environ.copy()
    env["ARCH"] = "x86_64"
    if "APPIMAGE_EXTRACT_AND_RUN" not in env:
        env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        
    appimage_cmd = [appimagetool]
    runtime_file = BUILD_DIR / "runtime-x86_64"
    if runtime_file.exists():
        appimage_cmd.extend(["--runtime-file", str(runtime_file)])
        
    appimage_cmd.extend([str(appdir), str(out_appimage)])
    print(f"Running {' '.join(appimage_cmd)}...")
    proc = subprocess.run(appimage_cmd, env=env, check=False)  # nosec B603
    if proc.returncode != 0:
        print(f"Warning: appimagetool exited with code {proc.returncode}", file=sys.stderr)
    else:
        print(f"Successfully built AppImage: {out_appimage}")
    return out_appimage


def build_arch(version: str) -> Path:
    """Build Arch Linux package (.pkg.tar.zst)."""
    print(f"\n--- Building Arch Linux Package (.pkg.tar.zst) for v{version} ---")
    binary = DIST_DIR / "mastui"
    if not binary.exists():
        binary = build_binary()
    
    arch_root = BUILD_DIR / "arch" / "pkg"
    if arch_root.exists():
        shutil.rmtree(arch_root)
    
    bin_dir = arch_root / "usr" / "bin"
    apps_dir = arch_root / "usr" / "share" / "applications"
    icons_dir = arch_root / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    licenses_dir = arch_root / "usr" / "share" / "licenses" / "mastui"
    
    bin_dir.mkdir(parents=True, exist_ok=True)
    apps_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)
    licenses_dir.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(binary, bin_dir / "mastui")
    
    desktop_src = PACKAGING_DIR / "mastui.desktop"
    if desktop_src.exists():
        shutil.copy2(desktop_src, apps_dir / "mastui.desktop")
    
    icon_src = ASSETS_DIR / "mastui-logo.png"
    if icon_src.exists():
        shutil.copy2(icon_src, icons_dir / "mastui.png")
    
    license_src = ROOT_DIR / "LICENSE"
    if license_src.exists():
        shutil.copy2(license_src, licenses_dir / "LICENSE")
    
    normalize_tree_permissions(arch_root)
    
    # Calculate installed size in bytes
    installed_size = sum(f.stat().st_size for f in arch_root.glob("**/*") if f.is_file())
    
    # Write .PKGINFO
    pkginfo_file = arch_root / ".PKGINFO"
    pkginfo_content = f"""# Generated by mastui build system
pkgname = mastui
pkgver = {version}-1
pkgdesc = A Textual-based terminal user interface client for Mastodon
url = https://github.com/kimusan/mastui
builddate = {int(time.time())}
packager = Kim Schulz
size = {installed_size}
arch = x86_64
license = MIT
"""
    pkginfo_file.write_text(pkginfo_content, encoding="utf-8")
    os.chmod(pkginfo_file, 0o644)
    
    out_pkg = DIST_DIR / f"mastui-{version}-1-x86_64.pkg.tar.zst"
    if out_pkg.exists():
        out_pkg.unlink()
        
    # Check if tar with zstd is available
    tar_cmd = [
        "tar",
        "--zstd",
        "--owner=0",
        "--group=0",
        "--numeric-owner",
        "-cf",
        str(out_pkg),
        "-C",
        str(arch_root),
        ".PKGINFO",
        "usr",
    ]
    result = subprocess.run(tar_cmd, check=False)  # nosec B603
    if result.returncode != 0:
        # Fallback: create .tar then zstd
        tar_temp = BUILD_DIR / "arch" / "temp.tar"
        with tarfile.open(tar_temp, "w") as tf:
            tf.add(arch_root / ".PKGINFO", arcname=".PKGINFO")
            tf.add(arch_root / "usr", arcname="usr")
        zstd_tool = shutil.which("zstd")
        if zstd_tool:
            run_cmd([zstd_tool, "-f", "-q", "-19", str(tar_temp), "-o", str(out_pkg)])
            if tar_temp.exists():
                tar_temp.unlink()
        else:
            print("Warning: neither 'tar --zstd' nor 'zstd' found. Creating .pkg.tar.gz instead.", file=sys.stderr)
            out_pkg = DIST_DIR / f"mastui-{version}-1-x86_64.pkg.tar.gz"
            with tarfile.open(out_pkg, "w:gz") as tf:
                tf.add(arch_root / ".PKGINFO", arcname=".PKGINFO")
                tf.add(arch_root / "usr", arcname="usr")
    
    print(f"Successfully built Arch Linux package: {out_pkg}")
    return out_pkg


def build_windows(version: str) -> Path:
    """Build Windows standalone binary and zip archive."""
    print(f"\n--- Building Windows Executable and Zip for v{version} ---")
    binary = DIST_DIR / "mastui.exe"
    if not binary.exists():
        binary = build_binary()
    
    out_zip = DIST_DIR / f"mastui-{version}-windows-x86_64.zip"
    if out_zip.exists():
        out_zip.unlink()
    
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(binary, arcname="mastui.exe")
        for extra in ["README.md", "LICENSE", "CHANGELOG.md"]:
            extra_path = ROOT_DIR / extra
            if extra_path.exists():
                zf.write(extra_path, arcname=extra)
    
    print(f"Successfully built Windows zip package: {out_zip}")
    return out_zip


def generate_checksums() -> Path:
    """Generate SHA256SUMS.txt for all files in dist/."""
    print("\n--- Generating SHA256 Checksums ---")
    checksums_file = DIST_DIR / "SHA256SUMS.txt"
    lines = []
    
    for item in sorted(DIST_DIR.iterdir()):
        if item.is_file() and item.name != "SHA256SUMS.txt":
            sha256 = hashlib.sha256(item.read_bytes()).hexdigest()
            lines.append(f"{sha256}  {item.name}")
    
    checksums_content = "\n".join(lines) + "\n"
    checksums_file.write_text(checksums_content, encoding="utf-8")
    print(f"Wrote SHA256 sums to: {checksums_file}")
    for line in lines:
        print(f"  {line}")
    return checksums_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mastui binary and distribution packages.")
    parser.add_argument(
        "--target",
        choices=["binary", "deb", "rpm", "appimage", "arch", "windows", "checksums", "all-linux"],
        default="all-linux",
        help="Target package to build (default: all-linux)",
    )
    parser.add_argument(
        "--all-linux",
        action="store_true",
        help="Build all Linux packages (binary, deb, rpm, appimage, arch, checksums)",
    )
    parser.add_argument(
        "--version",
        help="Override version string (defaults to version in pyproject.toml)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    version = args.version or get_version()
    target = "all-linux" if args.all_linux else args.target
    print(f"Starting mastui packaging for v{version} (Target: {target})")
    
    if target == "binary":
        build_binary()
    elif target == "deb":
        build_deb(version)
    elif target == "rpm":
        build_rpm(version)
    elif target == "appimage":
        build_appimage(version)
    elif target == "arch":
        build_arch(version)
    elif target == "windows":
        build_windows(version)
    elif target == "checksums":
        generate_checksums()
    elif target == "all-linux":
        build_binary()
        build_deb(version)
        build_rpm(version)
        build_appimage(version)
        build_arch(version)
        generate_checksums()
    
    print("\nPackage build process completed successfully!")


if __name__ == "__main__":
    main()
