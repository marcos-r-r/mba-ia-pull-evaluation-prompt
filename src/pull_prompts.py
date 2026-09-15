"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

# Prompt de baixa qualidade publicado no repositório base do desafio.
SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = "prompts/bug_to_user_story_v1.yml"


def _extract_messages(prompt_template) -> dict:
    """
    Extrai os templates de system e user de um ChatPromptTemplate retornado
    pelo LangSmith Hub, de forma resiliente a variações de estrutura.

    Returns:
        dict com as chaves 'system_prompt' e 'user_prompt' (strings).
    """
    system_prompt = ""
    user_prompt = ""

    # ChatPromptTemplate expõe a lista de mensagens em .messages
    messages = getattr(prompt_template, "messages", [])

    for message in messages:
        # Cada mensagem-template tem .prompt.template com o texto cru
        prompt_attr = getattr(message, "prompt", None)
        template_text = getattr(prompt_attr, "template", None)
        if template_text is None:
            continue

        # O tipo da mensagem indica o papel (System/Human/AI)
        role = type(message).__name__.lower()
        if "system" in role:
            system_prompt = template_text
        elif "human" in role or "user" in role:
            user_prompt = template_text

    # Fallback: prompt de mensagem única (sem papéis explícitos)
    if not system_prompt and not user_prompt:
        template_text = getattr(prompt_template, "template", None)
        if template_text:
            system_prompt = template_text

    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt de baixa qualidade do LangSmith Hub e salva em YAML local.

    Returns:
        True se o pull e a gravação foram bem-sucedidos, False caso contrário.
    """
    try:
        print(f"Puxando prompt do LangSmith Hub: {SOURCE_PROMPT}")
        prompt_template = hub.pull(SOURCE_PROMPT)
        print("   ✓ Prompt carregado com sucesso")

        messages = _extract_messages(prompt_template)

        prompt_data = {
            "description": "Prompt para converter relatos de bugs em User Stories (versão inicial de baixa qualidade)",
            "system_prompt": messages["system_prompt"],
            "user_prompt": messages["user_prompt"] or "{bug_report}",
            "version": "v1",
            "source": SOURCE_PROMPT,
            "tags": ["bug-analysis", "user-story", "product-management"],
        }

        if save_yaml(prompt_data, OUTPUT_PATH):
            print(f"   ✓ Prompt salvo localmente em: {OUTPUT_PATH}")
            return True

        print("   ❌ Falha ao salvar o prompt localmente.")
        return False

    except Exception as e:
        print(f"\n❌ Erro ao fazer pull do prompt '{SOURCE_PROMPT}': {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY está configurada corretamente no .env")
        print("- Você tem acesso ao workspace do LangSmith")
        print("- Sua conexão com a internet está funcionando")
        return False


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    success = pull_prompts_from_langsmith()

    if success:
        print("\n✅ Pull concluído com sucesso!")
        print("\nPróximos passos:")
        print(f"1. Analise o prompt inicial em {OUTPUT_PATH}")
        print("2. Otimize-o criando prompts/bug_to_user_story_v2.yml")
        print("3. Faça push com: python src/push_prompts.py")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
