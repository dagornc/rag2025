"""Test pour valider le parsing JSON robuste de llm_guided chunking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag_framework.config import load_step_config
from rag_framework.steps.step_03_chunking import ChunkingStep


def test_json_parsing():
    """Teste le parsing JSON avec différents formats de réponse LLM."""
    print("\n" + "=" * 70)
    print("TEST DU PARSING JSON ROBUSTE - llm_guided")
    print("=" * 70)

    # Initialiser ChunkingStep
    config = load_step_config("03_chunking.yaml")
    config["strategy"] = "llm_guided"
    chunking_step = ChunkingStep(config)

    # Accéder à la méthode de parsing
    parse_func = chunking_step._parse_llm_boundaries

    # Tests de différents formats
    test_cases = [
        {
            "name": "JSON pur",
            "response": '{"boundaries": [500, 1200, 2400]}',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON dans code block markdown (```json)",
            "response": '```json\n{"boundaries": [500, 1200, 2400]}\n```',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON dans code block markdown (```)",
            "response": '```\n{"boundaries": [500, 1200, 2400]}\n```',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON avec texte avant/après",
            "response": '''Voici l'analyse du texte :
{"boundaries": [500, 1200, 2400]}
Bonne journée!''',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON avec commentaires //",
            "response": '''{
  // Points de découpage optimaux
  "boundaries": [500, 1200, 2400]
}''',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON avec trailing comma",
            "response": '{"boundaries": [500, 1200, 2400,]}',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON avec types mixtes (int, string, float)",
            "response": '{"boundaries": [500, "1200", 2400.0]}',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON avec espaces et newlines",
            "response": '''{
  "boundaries": [
    500,
    1200,
    2400
  ]
}''',
            "expected": [500, 1200, 2400],
        },
        {
            "name": "JSON vide (pas de boundaries)",
            "response": '{"boundaries": []}',
            "expected": [],
        },
        {
            "name": "Réponse sans JSON",
            "response": "Désolé, je ne peux pas analyser ce texte.",
            "expected": [],
        },
        {
            "name": "JSON avec valeurs invalides ignorées",
            "response": '{"boundaries": [500, "invalide", 1200, null, 2400]}',
            "expected": [500, 1200, 2400],
        },
    ]

    # Exécuter les tests
    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Test: {test['name']}")
        print(f"Réponse: {test['response'][:100]}...")

        try:
            result = parse_func(test["response"])
            expected = test["expected"]

            if result == expected:
                print(f"✅ PASS - Résultat: {result}")
                passed += 1
            else:
                print(f"❌ FAIL")
                print(f"   Attendu: {expected}")
                print(f"   Obtenu:  {result}")
                failed += 1

        except Exception as e:
            print(f"❌ FAIL - Exception: {e}")
            failed += 1

    # Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ DES TESTS")
    print("=" * 70)
    print(f"Tests passés: {passed}/{len(test_cases)}")
    print(f"Tests échoués: {failed}/{len(test_cases)}")

    if failed == 0:
        print("✅ TOUS LES TESTS PASSÉS - Parsing JSON robuste validé!")
    else:
        print(f"⚠️ {failed} test(s) échoué(s)")

    print("=" * 70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = test_json_parsing()
    sys.exit(0 if success else 1)
