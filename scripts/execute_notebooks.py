"""Execute research notebooks with the active environment's Python kernel."""
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

for path in sorted(Path("notebooks").glob("*.ipynb")):
    notebook = nbformat.read(path, as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    NotebookClient(notebook, km=manager, timeout=180, resources={"metadata": {"path": str(Path.cwd())}}).execute()
    nbformat.write(notebook, path)
    print(f"Executed {path.name}", flush=True)
