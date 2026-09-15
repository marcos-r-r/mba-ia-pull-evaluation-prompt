"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

V2_PATH = "prompts/bug_to_user_story_v2.yml"


def _normalize(prompt_data: dict) -> dict:
    """
    Aceita YAML plano (campos na raiz) ou aninhado sob uma única chave
    (ex.: 'bug_to_user_story_v2:') e retorna sempre o dict plano dos campos.
    """
    if "system_prompt" not in prompt_data and len(prompt_data) == 1:
        inner = next(iter(prompt_data.values()))
        if isinstance(inner, dict):
            return inner
    return prompt_data


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    return validate_prompt_structure(_normalize(prompt_data))


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt (ex.: '{username}/bug_to_user_story_v2')
        prompt_data: Dados do prompt (dict lido do YAML)

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        data = _normalize(prompt_data)

        system_prompt = data.get("system_prompt", "").strip()
        user_prompt = data.get("user_prompt", "{bug_report}").strip() or "{bug_report}"

        # Monta o ChatPromptTemplate (System + User) que será servido no Hub.
        # A única variável de entrada deve ser {bug_report}, pois o evaluate.py
        # invoca a chain com inputs = {"bug_report": ...}.
        template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("user", user_prompt),
            ]
        )

        description = data.get("description", "Conversor de bug report em User Story (otimizado)")
        techniques = data.get("techniques_applied", [])
        tags = list(data.get("tags", [])) + [f"tecnica:{t}" for t in techniques]

        print(f"Fazendo push PÚBLICO de: {prompt_name}")
        print(f"   Técnicas aplicadas: {', '.join(techniques) if techniques else '—'}")

        url = _push(prompt_name, template, description=description, tags=tags)

        print("   ✓ Push concluído com sucesso!")
        if url:
            print(f"   🔗 {url}")
        return True

    except Exception as e:
        print(f"\n❌ Erro ao fazer push do prompt '{prompt_name}': {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY está configurada corretamente no .env")
        print("- USERNAME_LANGSMITH_HUB corresponde ao seu handle no LangSmith Hub")
        return False


def _push(prompt_name, template, description, tags):
    """
    Chama hub.push de forma resiliente às diferenças de assinatura entre versões
    do langchain (nem toda versão aceita 'tags'/'new_repo_description').
    """
    attempts = [
        dict(new_repo_is_public=True, new_repo_description=description, tags=tags),
        dict(new_repo_is_public=True, new_repo_description=description),
        dict(new_repo_is_public=True),
        dict(),
    ]
    last_error = None
    for kwargs in attempts:
        try:
            return hub.push(prompt_name, template, **kwargs)
        except TypeError as e:
            last_error = e  # assinatura incompatível; tenta com menos kwargs
            continue
    if last_error:
        raise last_error


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS AO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")

    prompt_data = load_yaml(V2_PATH)
    if not prompt_data:
        print(f"❌ Não foi possível carregar {V2_PATH}")
        return 1

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido. Corrija os erros abaixo antes do push:")
        for err in errors:
            print(f"   - {err}")
        return 1

    print("✓ Estrutura do prompt validada.\n")

    prompt_name = f"{username}/bug_to_user_story_v2"
    success = push_prompt_to_langsmith(prompt_name, prompt_data)

    if success:
        print("\n✅ Push concluído!")
        print("\nPróximos passos:")
        print("1. Confirme no dashboard que o prompt está PÚBLICO:")
        print(f"   https://smith.langchain.com/hub/{prompt_name}")
        print("2. Execute a avaliação: python src/evaluate.py")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
