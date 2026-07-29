"""Regression test for the project's English-only language policy."""

from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".in", ".md", ".py", ".sh", ".ui", ".xml"}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "pkg",
}

# Keep these markers focused on words that cannot reasonably occur in English
# prose. This test complements the accented-character check without requiring a
# language-detection dependency.
PORTUGUESE_MARKERS = re.compile(
    r"[À-ÿ]"
    r"|\b(?:"
    r"agora|ainda|arquivo|arquivos|baixe|baixando|carregando|conceder|"
    r"configuração|continuar|credenciais|diretório|escolha|executável|"
    r"fechar|funcionalidades|gerenciador|instalação|instalador|instale|"
    r"nenhum|obrigatório|"
    r"pacote|pacotes|permissão|preparando|remover|revogar|selecionar|"
    r"projeto|recursos|resumo|servidor|sessão|usuário|verifica|verificando|"
    r"você|corrigido|desabilitado|habilitado|identificado|perfeitamente|"
    r"totalmente"
    r")\b",
    re.IGNORECASE,
)


class EnglishOnlyTest(unittest.TestCase):
    def test_project_text_is_english_only(self):
        violations = []

        for path in PROJECT_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if path == Path(__file__).resolve():
                continue
            if any(part in EXCLUDED_DIRECTORIES for part in path.parts):
                continue

            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                match = PORTUGUESE_MARKERS.search(line)
                if match:
                    relative_path = path.relative_to(PROJECT_ROOT)
                    violations.append(
                        f"{relative_path}:{line_number}: {match.group(0)!r}"
                    )

        self.assertFalse(
            violations,
            "Portuguese text found in English-only project files:\n"
            + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
