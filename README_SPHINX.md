# Documentation Sphinx - RAG Framework

## Documentation Générée

La documentation complète du projet a été générée avec Sphinx et l'extension Napoleon.

### Localisation

- **Documentation HTML** : `docs/build/html/`
- **Fichier principal** : `docs/build/html/index.html`

### Ouvrir la Documentation

```bash
open docs/build/html/index.html
```

Ou avec un serveur HTTP simple :

```bash
cd docs/build/html
python -m http.server 8000
# Ouvrir http://localhost:8000 dans votre navigateur
```

## Génération de la Documentation

### Prérequis

```bash
pip install sphinx sphinx-rtd-theme
```

### Générer la Documentation

```bash
cd docs
make html
```

### Nettoyer et Regénérer

```bash
cd docs
make clean
make html
```

## Format des Docstrings : NumPy Style

Le projet utilise le style NumPy pour les docstrings, qui est plus lisible que le style Google pour les projets scientifiques.

### Exemple de Docstring NumPy

```python
def substitute_env_vars(value: ConfigValue) -> ConfigValue:
    """Remplace les variables d'environnement dans les valeurs de configuration.

    Les variables d'environnement doivent être au format ${VAR_NAME}.

    Parameters
    ----------
    value : ConfigValue
        Valeur à traiter (peut être str, dict, list, etc.).

    Returns
    -------
    ConfigValue
        Valeur avec les variables d'environnement substituées.

    Raises
    ------
    ConfigurationError
        Si une variable d'environnement est non définie.

    Examples
    --------
    >>> os.environ["API_KEY"] = "secret123"
    >>> substitute_env_vars("${API_KEY}")
    'secret123'
    """
```

## Configuration Sphinx

Le fichier `docs/source/conf.py` est configuré avec :

- **Extension Napoleon** : Convertit les docstrings NumPy en RST
- **Extension autodoc** : Génère automatiquement la doc depuis le code
- **Extension viewcode** : Ajoute des liens vers le code source
- **Thème** : Read the Docs (sphinx_rtd_theme)

### Configuration Napoleon

```python
napoleon_google_docstring = False  # Désactivé
napoleon_numpy_docstring = True    # Activé
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True
```

## Structure de la Documentation

```
docs/
├── build/              # Documentation générée (HTML)
│   └── html/
│       ├── index.html
│       ├── modules.html
│       └── ...
├── source/             # Sources RST
│   ├── conf.py        # Configuration Sphinx
│   ├── index.rst      # Page d'accueil
│   └── modules.rst    # Documentation des modules
├── Makefile           # Commandes make
└── make.bat           # Pour Windows
```

## Statistiques

- **22 pages HTML** générées
- **Tous les modules** documentés automatiquement
- **Format NumPy** pour les docstrings
- **Thème Read the Docs** professionnel

## Modules Documentés

1. `rag_framework.config` - Configuration
2. `rag_framework.pipeline` - Pipeline principal
3. `rag_framework.exceptions` - Exceptions
4. `rag_framework.types` - Type aliases
5. `rag_framework.steps.*` - 8 étapes du pipeline
6. `rag_framework.utils.*` - Utilitaires (logger, secrets, validators)

## Regénération Automatique

Pour regénérer la documentation après modification du code :

```bash
cd docs
make clean html
```

La documentation se met à jour automatiquement en lisant les docstrings du code source.
