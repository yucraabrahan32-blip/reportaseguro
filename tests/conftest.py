"""Configuracion de pytest: pone la raiz del proyecto en el path de importacion.

Asi, al correr `pytest`, las pruebas pueden hacer `from backend...` e `import database`
sin importar desde que carpeta se ejecute.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
