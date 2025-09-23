import os
import subprocess


def get_exec_dir():
    return os.path.dirname(__file__)


def run_script(script_path: str, *args: str) -> str:
    """Run a shell script and return its output as a string."""

    path = os.path.join(get_exec_dir(), script_path)

    result = subprocess.run([path, *args], capture_output=True, text=True, check=True)
    return result.stdout
