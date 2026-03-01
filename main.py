import runpy
from pathlib import Path

APP_MAIN = Path(__file__).resolve().parent / "app" / "main.py"
runpy.run_path(str(APP_MAIN), run_name="__main__")
