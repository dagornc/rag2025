
Dossier d'Architecture Technique - Sécurisation d'une Application Nginx

Date: 12/10/2025
Version: 1.0
Auteur: Gemini

-------------------------------------------------------------------

**1. Introduction**

Ce document décrit l'architecture technique et les mesures recommandées pour sécuriser une application web servie par le serveur HTTP Nginx. L'objectif est de mettre en place une défense en profondeur pour protéger l'application contre les menaces courantes, garantir la confidentialité, l'intégrité et la disponibilité des données.

**2. Principes de Sécurité**

L'architecture proposée repose sur les principes fondamentaux suivants :
- **Défense en profondeur** : Mettre en place plusieurs couches de sécurité. Si une couche est compromise, les autres peuvent encore protéger le système.
- **Principe de moindre privilège** : Chaque composant du système ne doit avoir que les permissions strictement nécessaires à son fonctionnement.
- **Sécurité par défaut** : La configuration de base doit être la plus sécurisée possible.
- **Surface d'attaque minimale** : Exposer le moins de services et de ports possible à l'extérieur.

**3. Architecture de Sécurité Proposée**

L'architecture se décompose en plusieurs couches de protection :

**3.1. Couche Réseau**

- **Pare-feu (Firewall)** : Un pare-feu (ex: UFW sur Ubuntu, iptables) sera configuré sur le serveur hébergeant Nginx.
    - Règle par défaut : Tout refuser (`DENY ALL`).
    - Règle d'autorisation : N'autoriser le trafic entrant que sur les ports 80 (HTTP, pour redirection) et 443 (HTTPS).
    - Le trafic sortant sera également limité aux besoins stricts de l'application.

**3.2. Couche Transport (TLS/SSL)**

- **Certificats TLS** : Utilisation systématique de certificats TLS pour chiffrer les communications entre le client et le serveur.
    - Recommandation : Utiliser Let's Encrypt pour des certificats gratuits et un renouvellement automatisé (via `certbot`).
- **Configuration TLS robuste** :
    - Désactivation des protocoles obsolètes et vulnérables : SSLv2, SSLv3, TLSv1.0, TLSv1.1.
    - Seuls TLS 1.2 et TLS 1.3 seront activés.
    - Utilisation de suites de chiffrement (ciphers) modernes et fortes.
    - Implémentation de HSTS (HTTP Strict Transport Security) pour forcer les navigateurs à utiliser HTTPS.

**3.3. Durcissement du Serveur Nginx**

La configuration de Nginx sera optimisée pour la sécurité :

- **Masquer la version de Nginx** : La directive `server_tokens off;` sera utilisée pour ne pas divulguer la version de Nginx dans les en-têtes de réponse.
- **En-têtes de sécurité HTTP** : Ajout des en-têtes suivants pour protéger contre les attaques côté client :
    - `X-Frame-Options 'SAMEORIGIN';` : Protection contre le Clickjacking.
    - `X-Content-Type-Options 'nosniff';` : Prévention du MIME-sniffing.
    - `X-XSS-Protection '1; mode=block';` : Protection basique contre les attaques XSS (Cross-Site Scripting).
    - `Content-Security-Policy (CSP)` : Définition d'une politique stricte pour contrôler les ressources que le navigateur est autorisé à charger.
- **Limitation du débit (Rate Limiting)** : Configuration de `limit_req_zone` et `limit_req` pour prévenir les attaques par force brute (ex: sur une page de login) et les dénis de service (DoS) simples.
- **Contrôle d'accès par IP** : Utilisation des directives `allow` et `deny` pour restreindre l'accès à certaines parties de l'application (ex: un panneau d'administration) à des adresses IP spécifiques.
- **Désactivation des méthodes HTTP non utilisées** : Si l'application n'utilise que GET, POST et HEAD, les autres méthodes (DELETE, PUT, etc.) peuvent être bloquées.

**3.4. Sécurité du Système d'Exploitation sous-jacent**

- **Utilisateur non-privilégié** : Le processus Nginx s'exécutera avec un utilisateur dédié sans privilèges (ex: `www-data`), et non en tant que `root`.
- **Mises à jour régulières** : Le système d'exploitation et tous ses paquets, y compris Nginx, seront maintenus à jour pour corriger les failles de sécurité connues.
- **Permissions de fichiers restrictives** :
    - Les fichiers de configuration de Nginx ne seront lisibles que par l'utilisateur `root`.
    - Les fichiers de l'application web appartiendront à l'utilisateur de l'application et auront des permissions restrictives (ex: `750` pour les dossiers, `640` pour les fichiers).

**3.5. Journalisation et Surveillance (Logging & Monitoring)**

- **Logs d'accès et d'erreur Nginx** : Les logs seront activés et configurés dans un format détaillé pour faciliter l'analyse.
- **Surveillance d'intégrité des fichiers** : Un outil comme `fail2ban` sera configuré pour surveiller les logs d'erreurs et bannir automatiquement les adresses IP qui montrent un comportement malveillant (ex: tentatives de scan, erreurs 404 répétées).
- **Centralisation des logs (Optionnel)** : Pour une meilleure visibilité, les logs peuvent être envoyés vers un système centralisé (ex: ELK Stack, Graylog) pour l'analyse et la corrélation d'événements.

**4. Plan de Mise en Œuvre (Résumé)**

1.  **Phase 1 (Configuration initiale)** : Installation de Nginx, configuration du pare-feu, obtention et installation du certificat TLS.
2.  **Phase 2 (Durcissement)** : Application des configurations de sécurité Nginx (en-têtes, rate limiting), configuration des permissions de fichiers et de l'utilisateur Nginx.
3.  **Phase 3 (Surveillance)** : Configuration de `fail2ban`, mise en place d'une routine de revue des logs et de mise à jour du système.

-------------------------------------------------------------------

**Annexe A : Exemple de bloc de configuration Nginx sécurisé**

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name your_domain.com;
    root /path/to/your/webroot;

    # --- Configuration SSL/TLS ---
    ssl_certificate /etc/letsencrypt/live/your_domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your_domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH';
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # --- En-têtes de sécurité ---
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    # add_header Content-Security-Policy "default-src 'self'; ..."; # À adapter précisément

    # --- Masquer la version ---
    server_tokens off;

    # --- Protection contre les bots/scans ---
    location = /robots.txt {
        log_not_found off;
        access_log off;
    }

    location / {
        try_files $uri $uri/ /index.php?$query_string;
        limit_req zone=mylimit burst=5 nodelay; # Exemple de rate limiting
    }

    # ... autres configurations (PHP-FPM, etc.)
}

# Redirection de HTTP vers HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name your_domain.com;
    return 301 https://$server_name$request_uri;
}
```
