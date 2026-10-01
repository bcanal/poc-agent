"""
Traduz evals/dataset/golden_set.yaml (schema próprio do projeto: id, pergunta,
gabarito, fonte) para o formato de tests que o promptfoo espera (vars).

O golden_set.yaml continua sendo a fonte única de verdade — este script só
gera uma vista derivada, descartável, pro promptfoo consumir. Não editar
evals/tests.generated.yaml na mão.

Rode: uv run python evals/build_tests.py
"""

from pathlib import Path

import yaml

GOLDEN_SET_PATH = Path(__file__).parent / "dataset" / "golden_set.yaml"
OUTPUT_PATH = Path(__file__).parent / "tests.generated.yaml"


def main() -> None:
    with open(GOLDEN_SET_PATH) as f:
        casos = yaml.safe_load(f)

    tests = [
        {
            "description": caso["id"],
            "vars": {
                "pergunta": caso["pergunta"],
                "gabarito": caso["gabarito"],
            },
        }
        for caso in casos
    ]

    with open(OUTPUT_PATH, "w") as f:
        yaml.dump(tests, f, allow_unicode=True, sort_keys=False)

    print(f"{len(tests)} casos traduzidos para {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
