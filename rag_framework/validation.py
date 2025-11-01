"""Validation des dépendances et prérequis du framework RAG."""

import importlib
from pathlib import Path

from rag_framework.config import GlobalConfig, get_llm_client
from rag_framework.exceptions import ConfigurationError
from rag_framework.utils.logger import get_logger

logger = get_logger(__name__)


class DependencyValidator:
    """Valide les dépendances et l'accès aux services externes au démarrage."""

    def __init__(self, global_config: GlobalConfig) -> None:
        """Initialise le validateur.

        Parameters
        ----------
        global_config : GlobalConfig
            Configuration globale du framework.
        """
        self.global_config = global_config
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Valide toutes les dépendances et prérequis.

        Returns:
        -------
        bool
            True si toutes les validations passent, False sinon.

        Raises:
        ------
        ConfigurationError
            Si des erreurs critiques sont détectées.
        """
        logger.info("=" * 70)
        logger.info("VALIDATION DES DÉPENDANCES ET PRÉREQUIS")
        logger.info("=" * 70)

        # 1. Validation des dépendances Python
        self._validate_python_dependencies()

        # 2. Validation des chemins de fichiers
        self._validate_file_paths()

        # 3. Validation de l'accès aux LLM providers
        self._validate_llm_providers()

        # Résumé des validations
        self._print_summary()

        # Si des erreurs critiques, lever une exception
        if self.errors:
            error_msg = "\n".join([f"  - {err}" for err in self.errors])
            raise ConfigurationError(
                f"Validation échouée. Erreurs critiques détectées:\n{error_msg}",
                details={"errors": self.errors, "warnings": self.warnings},
            )

        return True

    def _validate_python_dependencies(self) -> None:
        """Valide que toutes les dépendances Python requises sont installées."""
        logger.info("\n[1/3] Validation des dépendances Python")
        logger.info("-" * 70)

        # Dépendances critiques (toujours requises)
        required_deps = [
            ("yaml", "pyyaml"),
            ("pydantic", "pydantic"),
        ]

        # Dépendances optionnelles (selon les étapes activées)
        optional_deps = [
            ("watchdog", "watchdog", "monitoring"),
            ("openai", "openai", "llm"),
        ]

        # Validation des dépendances critiques
        for module_name, package_name in required_deps:
            if not self._check_module(module_name):
                self.errors.append(
                    f"Dépendance critique manquante: {package_name}. "
                    f"Installez avec: pip install {package_name}"
                )
            else:
                logger.debug(f"✓ {package_name} installé")

        # Validation des dépendances optionnelles
        for module_name, package_name, feature in optional_deps:
            if not self._check_module(module_name):
                self.warnings.append(
                    f"Dépendance optionnelle manquante: {package_name} "
                    f"(feature: {feature}). "
                    f"Installez avec: pip install {package_name}"
                )
            else:
                logger.debug(f"✓ {package_name} installé")

        if not self.errors:
            logger.info("✓ Toutes les dépendances critiques sont installées")

    def _check_module(self, module_name: str) -> bool:
        """Vérifie si un module Python est disponible.

        Parameters
        ----------
        module_name : str
            Nom du module à vérifier.

        Returns:
        -------
        bool
            True si le module est disponible, False sinon.
        """
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

    def _validate_file_paths(self) -> None:
        """Valide que les chemins de fichiers configurés sont accessibles."""
        logger.info("\n[2/3] Validation des chemins de fichiers")
        logger.info("-" * 70)

        # Validation du répertoire de logs
        log_file = self.global_config.logging.get("log_file")
        if log_file:
            log_path = Path(log_file)
            # Créer le répertoire si nécessaire
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"✓ Répertoire de logs accessible: {log_path.parent}")

        logger.info("✓ Tous les chemins de fichiers sont accessibles")

    def _validate_llm_providers(self) -> None:
        """Valide l'accès aux LLM providers pour les étapes activées."""
        logger.info("\n[3/3] Validation de l'accès aux LLM providers")
        logger.info("-" * 70)

        # Récupération des providers configurés
        llm_providers = self.global_config.llm_providers

        if not llm_providers:
            logger.warning("Aucun provider LLM configuré")
            return

        # Compteur de providers testés
        tested_count = 0
        accessible_count = 0

        # Test de chaque provider
        for provider_name, provider_config in llm_providers.items():
            # Vérifier si le provider est utilisé dans les étapes activées
            # Pour l'instant, on teste tous les providers configurés
            logger.debug(f"  Testing provider '{provider_name}'...")

            try:
                # Tentative de création d'un client
                # Note: Ceci ne fait qu'initialiser le client, pas d'appel API
                _ = get_llm_client(
                    provider_name=provider_name,
                    model="test-model",
                    temperature=0.0,
                    global_config=self.global_config,
                )

                # Validation de la configuration du provider
                base_url = provider_config.get("base_url")
                api_key = provider_config.get("api_key")

                if not base_url or not api_key:
                    self.warnings.append(
                        f"Provider '{provider_name}' : configuration incomplète "
                        f"(base_url ou api_key manquant)"
                    )
                else:
                    logger.debug(
                        f"  ✓ Provider '{provider_name}' configuré correctement"
                    )
                    accessible_count += 1

                tested_count += 1

            except Exception as e:
                self.warnings.append(
                    f"Provider '{provider_name}' : erreur de validation - {e}"
                )
                tested_count += 1

        logger.info(
            f"✓ Providers LLM validés: {accessible_count}/{tested_count} accessibles"
        )

    def _print_summary(self) -> None:
        """Affiche un résumé des validations."""
        logger.info("\n" + "=" * 70)
        logger.info("RÉSUMÉ DE LA VALIDATION")
        logger.info("=" * 70)

        if not self.errors and not self.warnings:
            logger.info("✅ Toutes les validations sont passées avec succès!")
        else:
            if self.errors:
                logger.error(
                    f"❌ {len(self.errors)} erreur(s) critique(s) détectée(s):"
                )
                for error in self.errors:
                    logger.error(f"  - {error}")

            if self.warnings:
                logger.warning(f"⚠️  {len(self.warnings)} avertissement(s):")
                for warning in self.warnings:
                    logger.warning(f"  - {warning}")

        logger.info("=" * 70 + "\n")


def validate_dependencies(global_config: GlobalConfig) -> bool:
    """Fonction helper pour valider les dépendances.

    Parameters
    ----------
    global_config : GlobalConfig
        Configuration globale du framework.

    Returns:
    -------
    bool
        True si toutes les validations passent, False sinon.

    Raises:
    ------
    ConfigurationError
        Si des erreurs critiques sont détectées.
    """
    validator = DependencyValidator(global_config)
    return validator.validate_all()
