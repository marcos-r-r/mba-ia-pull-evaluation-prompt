"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

V2_PATH = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    """Carrega o prompt otimizado v2 uma única vez para todos os testes."""
    data = load_prompts(str(V2_PATH))
    assert data is not None, "Não foi possível carregar o YAML do prompt v2."
    # Suporta YAML plano (campos na raiz) ou aninhado sob uma única chave.
    if "system_prompt" not in data and len(data) == 1:
        inner = next(iter(data.values()))
        if isinstance(inner, dict):
            return inner
    return data


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt, "Campo 'system_prompt' ausente no YAML."
        system_prompt = prompt["system_prompt"]
        assert isinstance(system_prompt, str), "'system_prompt' deve ser uma string."
        assert system_prompt.strip() != "", "'system_prompt' não pode estar vazio."

    def test_prompt_has_role_definition(self, prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt.get("system_prompt", "").lower()
        # Procura por uma definição de persona/role.
        pattern = r"(você é|voce é|atue como|aja como|assuma o papel|product manager)"
        assert re.search(pattern, system_prompt), (
            "O system_prompt deve definir uma persona/role "
            "(ex.: 'Você é um Product Manager...')."
        )

    def test_prompt_mentions_format(self, prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = (
            prompt.get("system_prompt", "") + "\n" + prompt.get("user_prompt", "")
        ).lower()
        keywords = ["markdown", "user story", "user stories", "como um", "como <papel>",
                    "critérios de aceitação", "criterios de aceitacao", "dado que"]
        assert any(k in text for k in keywords), (
            "O prompt deve exigir formato Markdown e/ou User Story padrão "
            "(Como <papel>... / Critérios de Aceitação / Dado-Quando-Então)."
        )

    def test_prompt_has_few_shot_examples(self, prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt.get("system_prompt", "").lower()
        has_example_marker = "exemplo" in system_prompt or "few-shot" in system_prompt
        has_io_pair = "entrada:" in system_prompt and "saída:" in system_prompt
        assert has_example_marker and has_io_pair, (
            "O prompt deve conter exemplos few-shot com pares de Entrada/Saída."
        )

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        blob = "\n".join(str(v) for v in prompt.values() if isinstance(v, str))
        # Marcador de placeholder [TODO] ou a palavra isolada TODO (com fronteiras),
        # sem pegar substrings legítimas como "meTODOlogias".
        assert "[TODO]" not in blob.upper(), "Há um marcador [TODO] pendente no prompt."
        assert not re.search(r"\bTODO\b", blob, re.IGNORECASE), (
            "Há um TODO pendente no prompt."
        )

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list), "'techniques_applied' deve ser uma lista."
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas exigido; encontradas: {len(techniques)}."
        )

    def test_structure_is_valid(self, prompt):
        """Sanidade extra: valida a estrutura usando o utilitário do projeto."""
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, f"Estrutura inválida: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
