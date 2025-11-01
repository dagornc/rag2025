"""Adaptateur de configuration pour convertir 02_preprocessing.yaml vers format fallback."""

from typing import Any


def convert_parser_to_fallback_config(parser_config: dict[str, Any]) -> dict[str, Any]:
    """Convertit 02_preprocessing.yaml vers le format attendu par FallbackManager.

    02_preprocessing.yaml utilise une structure orientée types de fichiers:
        preprocessing -> file_categories -> pdf/office/etc -> fallback_chain

    FallbackManager attend une structure plate avec profile et extractors:
        fallback -> profile -> extractors[]

    Cette fonction fait la conversion en créant une liste d'extracteurs
    avec leurs configurations depuis les fallback_chain de chaque catégorie.

    Parameters
    ----------
    parser_config : dict[str, Any]
        Configuration complète depuis 02_preprocessing.yaml.

    Returns:
    -------
    dict[str, Any]
        Configuration adaptée au format attendu par FallbackManager.

    Examples:
    --------
    >>> parser_cfg = load_yaml_config(Path("config/02_preprocessing.yaml"))
    >>> fallback_cfg = convert_parser_to_fallback_config(parser_cfg)
    >>> manager = FallbackManager(fallback_cfg)
    """
    preprocessing = parser_config.get("preprocessing", {})

    # Pour le moment, on considère que VLM n'est pas activé
    # (02_preprocessing.yaml n'a pas de flag use_vlm explicite)
    use_vlm = False

    # Construction de la liste d'extracteurs depuis file_categories
    extractors: list[dict[str, Any]] = []

    file_categories = preprocessing.get("file_categories", {})

    # Mapping des noms de library dans 02_preprocessing.yaml vers les noms d'extracteurs
    # utilisés par FallbackManager
    library_to_extractor: dict[str, str] = {
        "marker": "marker",
        "docling": "docling",
        "pymupdf": "pymupdf",
        "unstructured": "docling",  # Unstructured → docling
        "pypdf": "pypdf2",
        "pdfplumber": "pdfplumber",
        "python-docx": "docx",
        "python-pptx": "pptx",
        "openpyxl": "pandas",
        "pandas": "pandas",
        "text": "text",
        "beautifulsoup4": "html",
        "lxml": "html",
        "markdown": "text",
        "striprtf": "text",
        "ebooklib": "text",
        # OCR engines
        "tesseract": "ocr",
        "easyocr": "ocr",
        "paddleocr": "ocr",
        "rapidocr": "ocr",
        "surya": "ocr",
    }

    # Parcourir chaque catégorie de fichiers
    for _category_name, category_config in file_categories.items():
        if not category_config.get("enabled", False):
            continue

        # Traiter fallback_chain si présent
        fallback_chain = category_config.get("fallback_chain", [])
        for parser_entry in fallback_chain:
            library = parser_entry.get("library", "")
            extractor_name = library_to_extractor.get(library, library)

            # Créer l'entrée extracteur au format FallbackManager
            extractor_entry = {
                "name": extractor_name,
                "enabled": True,
                "config": parser_entry.get("config", {}),
            }

            # Ajouter uniquement si pas déjà dans la liste (éviter doublons)
            if not any(e["name"] == extractor_name for e in extractors):
                extractors.append(extractor_entry)

        # Traiter ocr_fallback si présent
        ocr_fallback = category_config.get("ocr_fallback", {})
        if ocr_fallback.get("enabled", False):
            ocr_chain = ocr_fallback.get("chain", [])
            for ocr_entry in ocr_chain:
                engine = ocr_entry.get("engine", "")
                extractor_name = library_to_extractor.get(engine, "ocr")

                extractor_entry = {
                    "name": extractor_name,
                    "enabled": True,
                    "config": {
                        "lang": ocr_entry.get("language", "eng"),
                        "psm": 3,
                        "preprocess": True,
                        "min_confidence": 0.5,
                    },
                }

                if not any(e["name"] == extractor_name for e in extractors):
                    extractors.append(extractor_entry)

        # Traiter ocr_chain si présent (pour images)
        ocr_chain = category_config.get("ocr_chain", [])
        for ocr_entry in ocr_chain:
            engine = ocr_entry.get("engine", "")
            extractor_name = library_to_extractor.get(engine, "ocr")

            extractor_entry = {
                "name": extractor_name,
                "enabled": True,
                "config": {
                    "lang": ocr_entry.get("language", "eng"),
                    "psm": 3,
                    "preprocess": True,
                    "min_confidence": 0.5,
                },
            }

            if not any(e["name"] == extractor_name for e in extractors):
                extractors.append(extractor_entry)

    # Construction de la configuration finale au format FallbackManager
    fallback_config = {
        "fallback": {
            "enabled": True,
            "use_vlm": use_vlm,
            "profile": "custom",  # Toujours custom car config manuelle
            "extractors": extractors,
        }
    }

    return fallback_config
