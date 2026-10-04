"""Las pruebas del panel importan sus módulos (auth, ui, cliente_java) y el script de usuarios."""
import sys
from pathlib import Path

PANEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PANEL))
sys.path.insert(0, str(PANEL.parent / "scripts"))
