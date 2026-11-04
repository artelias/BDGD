"""Diagnóstico interno do Motor V2 (--internal-dir): o valor contínuo fica fora das raízes públicas e não altera o produto publicado."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cenarios as C  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


class DiagnosticoInterno(unittest.TestCase):
    def test_recusa_gravar_sob_raiz_publica(self):
        for publica in (RAIZ / "web" / "public" / "data" / "x", RAIZ / "motor_cenarios" / "saida", RAIZ / "output-publicavel" / "y", RAIZ / "output-historico"):
            with self.assertRaises(ValueError, msg=str(publica)):
                C.main("contrato", "internas", "raw", tempfile.gettempdir(), None, internal_dir=str(publica))


if __name__ == "__main__":
    unittest.main()
