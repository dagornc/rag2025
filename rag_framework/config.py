"""Gestion de la configuration du framework RAG."""

import os
from pathlib import Path
from typing import Any, Union

import yaml
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from rag_framework.exceptions import ConfigurationError

# Type pour les valeurs de configuration (peut être récursif)
ConfigValue = Union[str, int, float, bool, dict[str, Any], list[Any], None]


class RegulatoryFramework(BaseModel):
    """Configuration d'un framework réglementaire."""

    enabled: bool = False
    full_name: str = ""
    description: str = ""
    scope: str = ""
    region: str = ""
    articles: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    notification_delay_hours: int = 0


class PerformanceConfig(BaseModel):
    """Configuration de performance."""

    batch_size: int = 10
    max_workers: int = 4
    timeout_seconds: int = 300


class GlobalConfig(BaseModel):
    """Configuration globale du framework."""

    vlm_providers: dict[str, Any] = Field(default_factory=dict)
    llm_config: dict[str, Any] = Field(default_factory=dict)
    # Nouveau: providers LLM transverses (infrastructure)
    llm_providers: dict[str, Any] = Field(default_factory=dict)
    # Nouveau: activation centralisée des étapes du pipeline
    steps: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    logging: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    # Nouveau: frameworks réglementaires (RGPD, SOC2, ISO27001, etc.)
    regulatory_frameworks: dict[str, RegulatoryFramework] = Field(default_factory=dict)


class StepConfig(BaseModel):
    """Configuration d'une étape du pipeline."""

    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


def substitute_env_vars(value: ConfigValue) -> ConfigValue:
    """Remplace les variables d'environnement dans les valeurs de configuration.

    Les variables d'environnement doivent être au format ${VAR_NAME}.

    Parameters
    ----------
    value : ConfigValue
        Valeur à traiter (peut être str, dict, list, etc.).

    Returns:
    -------
    ConfigValue
        Valeur avec les variables d'environnement substituées.

    Examples:
    --------
    >>> os.environ["API_KEY"] = "secret123"
    >>> substitute_env_vars("${API_KEY}")
    'secret123'
    """
    # Traitement des chaînes de caractères
    if isinstance(value, str):
        # Détection du pattern ${VAR_NAME} pour substitution
        # Exemple: "${OPENAI_API_KEY}" → valeur depuis os.environ
        if value.startswith("${") and value.endswith("}"):
            # Extraction du nom de variable (sans les délimiteurs ${ })
            var_name = value[2:-1]

            # Récupération depuis l'environnement système
            env_value = os.getenv(var_name)

            # Validation : la variable DOIT être définie
            # SAUF pour les clés API optionnelles (finissent par _API_KEY ou _TOKEN)
            if env_value is None:
                if var_name.endswith("_API_KEY") or var_name.endswith("_TOKEN"):
                    # Pour les clés API, retourner une valeur placeholder
                    # Le code utilisateur devra vérifier si la clé est valide
                    return f"{var_name}_NOT_SET"
                else:
                    # Pour les autres variables, lever une erreur
                    raise ConfigurationError(
                        f"Variable d'environnement non définie: {var_name}",
                        details={"variable": var_name},
                    )
            return env_value

        # Chaîne normale sans substitution
        return value

    # Traitement récursif des dictionnaires
    # Substitue les variables dans toutes les valeurs du dict
    elif isinstance(value, dict):
        return {k: substitute_env_vars(v) for k, v in value.items()}

    # Traitement récursif des listes
    # Substitue les variables dans tous les éléments
    elif isinstance(value, list):
        return [substitute_env_vars(item) for item in value]

    # Types primitifs (int, float, bool, None) : retour direct
    else:
        return value


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """Charge un fichier YAML de configuration.

    Parameters
    ----------
    config_path : Path
        Chemin vers le fichier YAML.

    Returns:
    -------
    dict[str, Any]
        Dictionnaire de configuration.

    Raises:
    ------
    ConfigurationError
        Si le fichier n'existe pas ou est invalide.
    """
    # Validation de l'existence du fichier AVANT tentative de lecture
    # Échec rapide si le fichier n'existe pas
    if not config_path.exists():
        raise ConfigurationError(
            f"Fichier de configuration introuvable: {config_path}",
            details={"path": str(config_path)},
        )

    try:
        # Ouverture en mode lecture avec encoding UTF-8 (standard universel)
        # Contexte manager (with) assure la fermeture automatique du fichier
        with open(config_path, encoding="utf-8") as f:
            # Parsing YAML safe (n'exécute pas de code Python arbitraire)
            # safe_load est OBLIGATOIRE pour la sécurité
            config_data = yaml.safe_load(f)

        # Fichier vide ou contenant uniquement des commentaires → dict vide
        if config_data is None:
            return {}

        # Substitution récursive des variables d'environnement
        # Exemple: "${API_KEY}" → valeur depuis os.environ["API_KEY"]
        result = substitute_env_vars(config_data)

        # Assertion de type : on s'attend toujours à un dictionnaire
        # Les fichiers YAML de config doivent avoir une structure de mapping
        assert isinstance(result, dict), "Config data must be a dictionary"
        return result

    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Erreur de parsing YAML: {config_path}",
            details={"path": str(config_path), "error": str(e)},
        ) from e
    except Exception as e:
        raise ConfigurationError(
            f"Erreur lors du chargement de la configuration: {config_path}",
            details={"path": str(config_path), "error": str(e)},
        ) from e


def load_config(config_dir: Path = Path("config")) -> GlobalConfig:
    """Charge la configuration globale du framework.

    Parameters
    ----------
    config_dir : Path, optional
        Répertoire contenant les fichiers de configuration (default: Path("config")).

    Returns:
    -------
    GlobalConfig
        Instance de GlobalConfig validée.

    Raises:
    ------
    ConfigurationError
        Si la configuration est invalide.
    """
    global_config_path = config_dir / "global.yaml"
    config_data = load_yaml_config(global_config_path)

    try:
        return GlobalConfig(**config_data)
    except PydanticValidationError as e:
        raise ConfigurationError(
            "Configuration globale invalide",
            details={"errors": e.errors()},
        ) from e


def load_step_config(
    config_path: Union[Path, str],
    config_dir: Path = Path("config"),
) -> dict[str, Any]:
    """Charge la configuration d'une étape spécifique.

    Parameters
    ----------
    config_path : Union[Path, str]
        Nom ou chemin du fichier de configuration de l'étape.
    config_dir : Path, optional
        Répertoire contenant les fichiers de configuration (default: Path("config")).

    Returns:
    -------
    dict[str, Any]
        Dictionnaire de configuration de l'étape.

    Raises:
    ------
    ConfigurationError
        Si la configuration est invalide.
    """
    if isinstance(config_path, str):
        config_path = config_dir / config_path

    return load_yaml_config(Path(config_path))


def get_llm_client(
    provider_name: str,
    model: str,
    temperature: float,
    global_config: GlobalConfig,
) -> Any:  # noqa: ANN401
    """Crée un client LLM à partir de la configuration globale.

    Cette fonction récupère les paramètres de connexion du provider depuis
    global.yaml (base_url, api_key, access_method) et crée un client
    compatible OpenAI avec les paramètres fonctionnels spécifiés.

    Parameters
    ----------
    provider_name : str
        Nom du provider LLM (ex: "ollama", "lm_studio", "mistral_ai").
    model : str
        Nom du modèle à utiliser (ex: "llama3", "mistral-large-latest").
    temperature : float
        Température pour la génération (0.0 = déterministe, 1.0 = créatif).
    global_config : GlobalConfig
        Configuration globale contenant les providers LLM.

    Returns:
    -------
    Any
        Client LLM configuré (compatible OpenAI API).

    Raises:
    ------
    ConfigurationError
        Si le provider est introuvable ou mal configuré.

    Examples:
    --------
    >>> global_config = load_config()
    >>> client = get_llm_client("ollama", "llama3", 0.0, global_config)
    >>> response = client.chat.completions.create(...)
    """
    # Récupération de la configuration du provider depuis global.yaml
    provider_config = global_config.llm_providers.get(provider_name)

    # Validation: le provider DOIT être configuré dans global.yaml
    if not provider_config:
        available_providers = list(global_config.llm_providers.keys())
        raise ConfigurationError(
            f"Provider LLM '{provider_name}' introuvable dans global.yaml",
            details={
                "provider": provider_name,
                "available_providers": available_providers,
            },
        )

    # Extraction de la méthode d'accès
    access_method = provider_config.get("access_method", "openai_compatible")

    # Création du client selon la méthode d'accès
    try:
        # === PROVIDERS LOCAUX (sentence-transformers) ===
        if access_method == "local":
            library = provider_config.get("library")
            if library == "sentence-transformers":
                # Import tardif pour éviter dépendances inutiles
                from sentence_transformers import SentenceTransformer

                # Création du modèle sentence-transformers
                # Le modèle est téléchargé automatiquement si nécessaire
                client = SentenceTransformer(model)

                # Stockage des paramètres fonctionnels
                client._model = model  # type: ignore[attr-defined]
                client._temperature = temperature  # type: ignore[attr-defined]

                return client
            else:
                raise ConfigurationError(
                    f"Library non supportée pour access_method='local': {library}",
                    details={
                        "provider": provider_name,
                        "library": library,
                        "supported_libraries": ["sentence-transformers"],
                    },
                )

        # === PROVIDERS API (OpenAI-compatible, HuggingFace) ===
        elif access_method in ("openai_compatible", "huggingface_inference_api"):
            # Extraction des paramètres de connexion
            base_url = provider_config.get("base_url")
            api_key = provider_config.get("api_key")

            # Validation des paramètres obligatoires pour les providers API
            if not base_url or not api_key:
                raise ConfigurationError(
                    f"Configuration incomplète pour le provider '{provider_name}'",
                    details={
                        "provider": provider_name,
                        "missing_fields": [
                            f
                            for f in ["base_url", "api_key"]
                            if not provider_config.get(f)
                        ],
                    },
                )

            # Import tardif pour éviter dépendances inutiles
            from openai import OpenAI

            # Création du client OpenAI compatible
            client = OpenAI(
                base_url=base_url,
                api_key=api_key,
            )

            # Stockage des paramètres fonctionnels
            client._model = model  # type: ignore[attr-defined]
            client._temperature = temperature  # type: ignore[attr-defined]

            return client

        else:
            raise ConfigurationError(
                f"Méthode d'accès non supportée: {access_method}",
                details={
                    "provider": provider_name,
                    "access_method": access_method,
                    "supported_methods": [
                        "local",
                        "openai_compatible",
                        "huggingface_inference_api",
                    ],
                },
            )

    except ImportError as e:
        raise ConfigurationError(
            f"Librairie manquante pour '{provider_name}'. "
            f"Installez avec: rye add {access_method}",
            details={"error": str(e)},
        ) from e


def get_enabled_regulatory_frameworks(global_config: GlobalConfig) -> list[str]:
    """Retourne la liste des noms de frameworks réglementaires activés.

    Parameters
    ----------
    global_config : GlobalConfig
        Configuration globale contenant les frameworks réglementaires.

    Returns:
    -------
    list[str]
        Liste des noms de frameworks activés (ex: ["RGPD", "SOC2"]).

    Examples:
    --------
    >>> global_config = load_config()
    >>> frameworks = get_enabled_regulatory_frameworks(global_config)
    >>> print(frameworks)
    ['RGPD', 'ISO27001']
    """
    return [
        name
        for name, framework in global_config.regulatory_frameworks.items()
        if framework.enabled
    ]


def get_regulatory_framework(
    global_config: GlobalConfig,
    framework_name: str,
) -> RegulatoryFramework:
    """Récupère la configuration d'un framework réglementaire spécifique.

    Parameters
    ----------
    global_config : GlobalConfig
        Configuration globale contenant les frameworks réglementaires.
    framework_name : str
        Nom du framework (ex: "RGPD", "SOC2", "ISO27001").

    Returns:
    -------
    RegulatoryFramework
        Configuration du framework réglementaire.

    Raises:
    ------
    ConfigurationError
        Si le framework n'existe pas ou n'est pas activé.

    Examples:
    --------
    >>> global_config = load_config()
    >>> rgpd = get_regulatory_framework(global_config, "RGPD")
    >>> print(rgpd.notification_delay_hours)
    72
    """
    # Vérification de l'existence du framework
    framework = global_config.regulatory_frameworks.get(framework_name)

    if framework is None:
        available = list(global_config.regulatory_frameworks.keys())
        raise ConfigurationError(
            f"Framework réglementaire '{framework_name}' introuvable",
            details={
                "framework": framework_name,
                "available_frameworks": available,
            },
        )

    # Vérification de l'activation du framework
    if not framework.enabled:
        raise ConfigurationError(
            f"Framework réglementaire '{framework_name}' désactivé",
            details={"framework": framework_name, "enabled": False},
        )

    return framework


def validate_regulatory_compliance(
    global_config: GlobalConfig,
    required_frameworks: list[str],
) -> dict[str, bool]:
    """Valide que les frameworks réglementaires requis sont activés.

    Cette fonction vérifie qu'un ensemble de frameworks réglementaires
    requis sont bien configurés et activés. Utile pour valider la conformité
    d'un document ou d'un processus.

    Parameters
    ----------
    global_config : GlobalConfig
        Configuration globale contenant les frameworks réglementaires.
    required_frameworks : list[str]
        Liste des noms de frameworks requis (ex: ["RGPD", "SOC2"]).

    Returns:
    -------
    dict[str, bool]
        Dictionnaire indiquant pour chaque framework s'il est activé.
        Exemple: {"RGPD": True, "SOC2": False}

    Examples:
    --------
    >>> global_config = load_config()
    >>> compliance = validate_regulatory_compliance(global_config, ["RGPD", "SOC2"])
    >>> if all(compliance.values()):
    ...     print("Tous les frameworks requis sont activés")
    """
    result = {}

    for framework_name in required_frameworks:
        framework = global_config.regulatory_frameworks.get(framework_name)
        result[framework_name] = framework is not None and framework.enabled

    return result


def get_framework_requirements(
    global_config: GlobalConfig,
    framework_name: str,
) -> list[str]:
    """Retourne les exigences d'un framework réglementaire.

    Parameters
    ----------
    global_config : GlobalConfig
        Configuration globale contenant les frameworks réglementaires.
    framework_name : str
        Nom du framework (ex: "RGPD", "SOC2").

    Returns:
    -------
    list[str]
        Liste des exigences/requirements du framework.
        Pour RGPD: ["lawfulness_fairness", "purpose_limitation", ...]
        Pour SOC2: ["CC6.1", "CC6.6", "CC7.2", ...]

    Raises:
    ------
    ConfigurationError
        Si le framework n'existe pas ou n'est pas activé.

    Examples:
    --------
    >>> global_config = load_config()
    >>> requirements = get_framework_requirements(global_config, "RGPD")
    >>> print(len(requirements))
    8
    """
    framework = get_regulatory_framework(global_config, framework_name)

    # RGPD utilise 'requirements', SOC2 utilise 'controls', ISO27001 utilise 'controls'
    if framework.requirements:
        return framework.requirements
    elif framework.controls:
        return framework.controls
    elif framework.articles:
        return framework.articles
    else:
        return []
