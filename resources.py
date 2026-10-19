"""同梱リソース(images/など)の場所を解決するヘルパー。

通常のPythonスクリプトとして実行する場合と、PyInstallerで.exeに固めた場合とで
リソースの置き場所が変わる
"""

import sys
from pathlib import Path

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

IMAGES_DIR = BASE_DIR / "images"
