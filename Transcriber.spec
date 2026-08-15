# -*- mode: python ; coding: utf-8 -*-
"""Cross-platform PyInstaller build.

    pyinstaller Transcriber.spec

One spec for the three targets, because PyInstaller never cross-compiles: each
operating system builds its own artifact on its own machine (or CI runner).

  macOS    -> dist/Transcriber.app   (folder bundle, fast start)
  Linux    -> dist/Transcriber/      (folder, shipped as a tarball)
  Windows  -> dist/Transcriber.exe   (single file)

Collects what PyInstaller cannot discover on its own:
  - CTranslate2 native libraries (the faster-whisper backend);
  - the FFmpeg binaries bundled inside PyAV;
  - the VAD ONNX model that lives inside the faster_whisper package;
  - the onnxruntime runtime used by the VAD;
  - metadata required at run time (tokenizers, huggingface-hub);
  - the brand fonts under assets/fonts, registered at startup.

Whisper weights are NOT bundled: they are downloaded on first use into the
user cache, exactly like the source version.
"""

import pathlib
import re
import sys

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

APP_NAME = "Transcriber"

# Single source of truth for the version: the package. Reading it here keeps the
# bundle metadata and the released tag from drifting apart.
VERSION = re.search(
    r'__version__ = "([^"]+)"',
    pathlib.Path("transcriber/__init__.py").read_text(encoding="utf-8"),
).group(1)
IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

PACKAGES = ("faster_whisper", "ctranslate2", "av", "onnxruntime", "tokenizers")
METADATA = ("faster-whisper", "ctranslate2", "tokenizers", "huggingface-hub", "onnxruntime")

binaries = []
datas = [("assets/fonts/*.ttf", "assets/fonts")]
hiddenimports = []

for package in PACKAGES:
    binaries += collect_dynamic_libs(package)
    datas += collect_data_files(package)
    hiddenimports += collect_submodules(package)

for distribution in METADATA:
    try:
        datas += copy_metadata(distribution)
    except Exception:
        # Optional metadata missing in this environment: not a build blocker.
        pass


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Heavy libraries nothing here uses.
    excludes=["matplotlib", "PyQt5", "PySide6", "IPython", "notebook", "pandas", "scipy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

common = dict(
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed application, no terminal behind it
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if IS_WINDOWS:
    # Single file: what Windows users expect to double-click.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **common)
else:
    # Folder build: starts in a fraction of the time a one-file build takes,
    # because nothing has to be unpacked into a temporary directory.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    collected = COLLECT(
        exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name=APP_NAME
    )

if IS_MACOS:
    app = BUNDLE(
        collected,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="studio.nzila.transcriber",
        info_plist={
            "CFBundleName": "Transcriber",
            "CFBundleDisplayName": "Transcriber",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            # Microphone is never used: the app only reads files the user picks.
            "LSApplicationCategoryType": "public.app-category.productivity",
            "NSHumanReadableCopyright": "MIT licensed. Model weights fetched on first use.",
        },
    )
