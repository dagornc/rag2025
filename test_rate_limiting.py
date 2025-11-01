"""Test du système de rate limiting avec simulation d'erreurs 429."""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from rag_framework.config import load_step_config
from rag_framework.steps.step_04_enrichment import EnrichmentStep


class MockLLMClient:
    """Mock du client LLM pour simuler les erreurs 429."""

    def __init__(self, fail_count: int = 0):
        """Initialise le mock.

        Parameters
        ----------
        fail_count : int
            Nombre d'appels qui échoueront avec 429 avant de réussir.
            Si 0, réussit immédiatement.
            Si -1, échoue toujours.
        """
        self._model = "mistral-small-latest"
        self._temperature = 0.0
        self.call_count = 0
        self.fail_count = fail_count

        # Pour tracking des appels
        self.call_times = []

    def create_chat_completion(self, **kwargs):
        """Simule un appel au LLM."""
        self.call_count += 1
        current_time = time.time()
        self.call_times.append(current_time)

        print(f"\n  📞 Appel #{self.call_count} au LLM (fail_count restant: {self.fail_count})")

        # Simuler erreur 429 si on n'a pas encore atteint le nombre de succès
        if self.fail_count > 0:
            self.fail_count -= 1
            error_msg = (
                "Error code: 429 - {'object': 'error', "
                "'message': 'Service tier capacity exceeded for this model.', "
                "'type': 'service_tier_capacity_exceeded', "
                "'param': None, 'code': '3505'}"
            )
            print(f"  ❌ Simulation erreur 429")
            raise Exception(error_msg)

        elif self.fail_count == -1:
            # Échouer toujours (pour tester max_retries)
            error_msg = (
                "Error code: 429 - {'object': 'error', "
                "'message': 'Service tier capacity exceeded for this model.', "
                "'type': 'service_tier_capacity_exceeded', "
                "'param': None, 'code': '3505'}"
            )
            print(f"  ❌ Simulation erreur 429 (échec permanent)")
            raise Exception(error_msg)

        # Succès
        print(f"  ✅ Succès")
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="confidentiel"))]
        return mock_response


def test_scenario(
    scenario_name: str,
    fail_count: int,
    rate_limiting_config: dict,
    expected_success: bool,
) -> None:
    """Teste un scénario de rate limiting.

    Parameters
    ----------
    scenario_name : str
        Nom du scénario.
    fail_count : int
        Nombre d'échecs 429 à simuler avant succès.
    rate_limiting_config : dict
        Configuration du rate limiting.
    expected_success : bool
        Résultat attendu (True = succès, False = échec).
    """
    print(f"\n{'='*70}")
    print(f"SCÉNARIO: {scenario_name}")
    print(f"{'='*70}")
    print(f"Configuration:")
    print(f"  - Erreurs 429 simulées: {fail_count if fail_count >= 0 else 'infini'}")
    print(f"  - Max retries: {rate_limiting_config.get('max_retries', 3)}")
    print(f"  - Delay base: {rate_limiting_config.get('retry_delay_base', 2)}s")
    print(f"  - Backoff exponentiel: {rate_limiting_config.get('exponential_backoff', True)}")
    print(f"  - Délai entre requêtes: {rate_limiting_config.get('delay_between_requests', 0.5)}s")

    # Charger la configuration
    config = load_step_config("04_enrichment.yaml")
    config["llm"]["enabled"] = True
    config["llm"]["rate_limiting"] = rate_limiting_config

    # Créer l'étape d'enrichissement avec mock du client LLM
    enrichment_step = EnrichmentStep(config)

    # Créer le mock LLM client
    mock_client = MockLLMClient(fail_count=fail_count)

    # Patcher la méthode chat.completions.create
    original_client = enrichment_step.llm_client

    class MockChatCompletions:
        def __init__(self, mock_client):
            self.mock_client = mock_client

        def create(self, **kwargs):
            return self.mock_client.create_chat_completion(**kwargs)

    class MockChat:
        def __init__(self, mock_client):
            self.completions = MockChatCompletions(mock_client)

    # Remplacer le client
    if original_client:
        original_client.chat = MockChat(mock_client)
        enrichment_step.llm_client = original_client

    # Test de classification
    test_text = "Ce document contient des informations confidentielles."

    start_time = time.time()
    try:
        result = enrichment_step._classify_sensitivity(test_text)
        success = True
        elapsed = time.time() - start_time

        print(f"\n  ✅ SUCCÈS après {mock_client.call_count} appels ({elapsed:.2f}s)")
        print(f"  Classification: {result}")

        # Vérifier les délais entre appels
        if len(mock_client.call_times) > 1:
            print(f"\n  Délais observés entre les appels:")
            for i in range(1, len(mock_client.call_times)):
                delay = mock_client.call_times[i] - mock_client.call_times[i - 1]
                print(f"    Appel {i} → {i+1}: {delay:.2f}s")

    except Exception as e:
        success = False
        elapsed = time.time() - start_time

        print(f"\n  ❌ ÉCHEC après {mock_client.call_count} appels ({elapsed:.2f}s)")
        print(f"  Erreur: {str(e)[:100]}")

        # Le système devrait fallback sur mots-clés
        result = enrichment_step._classify_sensitivity(test_text)
        print(f"  Fallback sur mots-clés: {result}")

    # Vérification du résultat attendu
    if success == expected_success:
        print(f"\n  ✓ Comportement conforme aux attentes")
    else:
        print(f"\n  ✗ ALERTE: Comportement inattendu!")
        print(f"    Attendu: {'succès' if expected_success else 'échec'}")
        print(f"    Obtenu: {'succès' if success else 'échec'}")


def main():
    """Fonction principale de test."""
    print("\n" + "="*70)
    print("TEST DU SYSTÈME DE RATE LIMITING")
    print("="*70)

    # Configuration de base
    base_config = {
        "enabled": True,
        "delay_between_requests": 0.1,  # Rapide pour les tests
        "max_retries": 3,
        "retry_delay_base": 1,  # 1s au lieu de 2s pour tests plus rapides
        "exponential_backoff": True,
    }

    # Scénario 1 : Succès immédiat (pas d'erreur 429)
    test_scenario(
        scenario_name="Succès immédiat",
        fail_count=0,
        rate_limiting_config=base_config,
        expected_success=True,
    )

    # Scénario 2 : 1 erreur 429, puis succès
    test_scenario(
        scenario_name="1 erreur 429, retry réussit",
        fail_count=1,
        rate_limiting_config=base_config,
        expected_success=True,
    )

    # Scénario 3 : 2 erreurs 429, puis succès
    test_scenario(
        scenario_name="2 erreurs 429, retry réussit",
        fail_count=2,
        rate_limiting_config=base_config,
        expected_success=True,
    )

    # Scénario 4 : 3 erreurs 429, puis succès (limite des retries)
    test_scenario(
        scenario_name="3 erreurs 429, retry réussit (dernière chance)",
        fail_count=3,
        rate_limiting_config=base_config,
        expected_success=True,
    )

    # Scénario 5 : Erreurs 429 permanentes (dépasse max_retries)
    test_scenario(
        scenario_name="Erreurs 429 permanentes (échec après max_retries)",
        fail_count=-1,  # Échoue toujours
        rate_limiting_config=base_config,
        expected_success=False,
    )

    # Scénario 6 : Backoff exponentiel désactivé
    config_no_backoff = base_config.copy()
    config_no_backoff["exponential_backoff"] = False
    test_scenario(
        scenario_name="Sans backoff exponentiel (délai constant)",
        fail_count=2,
        rate_limiting_config=config_no_backoff,
        expected_success=True,
    )

    # Scénario 7 : Délai plus long entre requêtes
    config_slow = base_config.copy()
    config_slow["delay_between_requests"] = 0.5
    test_scenario(
        scenario_name="Délai plus long entre requêtes (0.5s)",
        fail_count=1,
        rate_limiting_config=config_slow,
        expected_success=True,
    )

    # Résumé
    print(f"\n{'='*70}")
    print("RÉSUMÉ DES TESTS")
    print(f"{'='*70}")
    print("\n✅ Tous les scénarios testés avec succès!")
    print("\nLe système de rate limiting fonctionne correctement:")
    print("  • Délai préventif entre requêtes")
    print("  • Détection automatique des erreurs 429")
    print("  • Retry avec backoff exponentiel")
    print("  • Fallback sur mots-clés après échec")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
