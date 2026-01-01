# Spécification : Système d'Authentification Magic Link + TOTP

## 1. Contexte et objectifs

### 1.1 Contexte
Développement d'un système d'authentification pour un site à contenu politique sensible (type decision-collective.fr). Les utilisateurs doivent pouvoir s'authentifier sans dépendre des GAFAM, et leurs contributions doivent être dissociées de leur identité réelle (email) pour protéger leur anonymat.

### 1.2 Objectifs principaux
- Authentification sans mot de passe via Magic Link (envoi d'un lien par email)
- Option alternative : saisie d'un code au lieu de cliquer sur le lien
- MFA optionnel via TOTP (compatible FreeOTP, Aegis, Google Authenticator)
- Dissociation complète entre l'email de l'utilisateur et son identifiant applicatif
- Solution légère, maintenable par un développeur solo (ClaudeCode)
- Anti-GAFAM : aucune dépendance SSO Google/Microsoft

### 1.3 Contraintes
- Freelance solo, pas d'équipe de développement
- Budget minimal (pas de services payants obligatoires)
- Hébergement VPS standard (type OVH, Scaleway)
- RGPD : minimisation des données, droit à l'oubli

---

## 2. Architecture technique

### 2.1 Stack technique
| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| Backend | Python 3.11+ / FastAPI | Léger, moderne, excellente doc, ClaudeCode performant |
| Base de données | PostgreSQL | Robuste, chiffrement possible, JSON natif |
| TOTP | pyotp | Aucune CVE connue, standard RFC 6238 |
| Envoi emails | SMTP externe (Brevo, Postmark) | Délivrabilité, pas de gestion serveur mail |
| QR Code | qrcode (Python) | Génération QR pour provisioning TOTP |
| Tokens | secrets (stdlib Python) | Cryptographiquement sûr |

### 2.2 Architecture de séparation des données

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE AUTHENTIFICATION                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Table: auth_users                                       │    │
│  │  - id (UUID, PK)                                         │    │
│  │  - email (chiffré ou hashé)                              │    │
│  │  - email_hash (pour lookup, SHA256)                      │    │
│  │  - totp_secret (chiffré, nullable)                       │    │
│  │  - totp_enabled (boolean)                                │    │
│  │  - created_at                                            │    │
│  │  - last_login_at                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              │ Génère                            │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  public_id (UUID différent de id)                        │    │
│  │  = Identifiant transmis à l'application                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ JWT contenant uniquement public_id
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION PRINCIPALE                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Table: app_users                                        │    │
│  │  - public_id (UUID, PK) ← reçu du service auth           │    │
│  │  - display_name (choisi par l'utilisateur)               │    │
│  │  - preferences (JSON)                                    │    │
│  │  - created_at                                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Table: contributions                                    │    │
│  │  - id (UUID, PK)                                         │    │
│  │  - public_id (FK → app_users)                            │    │
│  │  - content                                               │    │
│  │  - created_at                                            │    │
│  │  ⚠️ JAMAIS d'email ici                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Principe** : Même en cas de fuite de la BDD applicative, impossible de relier les contributions aux emails.

---

## 3. Fonctionnalités détaillées

### 3.1 Inscription / Première connexion

**Flux utilisateur :**
1. L'utilisateur saisit son email
2. Le système vérifie si l'email existe (via hash)
3. Si nouveau : création du compte (auth_users + app_users)
4. Envoi du magic link par email
5. L'utilisateur clique ou saisit le code
6. Connexion établie, JWT généré

**Règles métier :**
- Un email = un compte unique
- Pas de validation de format email côté serveur (anti-typosquatting à la charge de l'utilisateur)
- Le code alternatif est affiché dans l'email en plus du lien

### 3.2 Connexion Magic Link

**Flux utilisateur :**
1. Saisie de l'email
2. Envoi du magic link + code
3. Option A : Clic sur le lien → connexion directe
4. Option B : Saisie du code sur la page d'attente → connexion

**Spécifications techniques :**
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| Longueur token | 32 bytes (64 hex) | Impossible à deviner |
| Expiration | 15 minutes | Compromis sécurité/UX |
| Usage | Unique | Invalidé après utilisation |
| Code alternatif | 6 caractères alphanumériques | Facile à saisir |

### 3.3 Authentification TOTP (optionnelle)

**Activation par l'utilisateur :**
1. Accès aux paramètres de sécurité
2. Génération d'un secret TOTP
3. Affichage QR code (scannable par FreeOTP/Aegis)
4. Saisie d'un code de vérification pour confirmer
5. Génération de codes de récupération (10 codes à usage unique)

**Connexion avec TOTP activé :**
1. Magic link validé
2. → Redirection vers page de saisie TOTP
3. Saisie du code 6 chiffres
4. Connexion établie

**Spécifications techniques :**
| Paramètre | Valeur |
|-----------|--------|
| Algorithme | TOTP (RFC 6238) |
| Période | 30 secondes |
| Digits | 6 |
| Fenêtre de tolérance | ±1 période (pour décalage horloge) |
| Codes de récupération | 10, usage unique, 16 caractères |

### 3.4 Gestion de session

**JWT (JSON Web Token) :**
| Claim | Valeur |
|-------|--------|
| sub | public_id (UUID) |
| iat | Timestamp création |
| exp | Timestamp expiration (7 jours) |
| mfa | true/false (TOTP validé) |

**Stockage côté client :**
- Cookie HttpOnly, Secure, SameSite=Strict
- Pas de localStorage (XSS)

**Refresh :**
- Token rafraîchi automatiquement si activité et < 24h avant expiration

### 3.5 Déconnexion et révocation

- Déconnexion : suppression du cookie
- Révocation globale : invalidation de tous les tokens (changement de secret JWT)
- Option "Déconnecter tous les appareils" dans les paramètres

---

## 4. Sécurité

### 4.1 Checklist sécurité obligatoire

- [ ] Tokens générés avec `secrets.token_urlsafe(32)`
- [ ] Tokens hashés (SHA256) avant stockage en BDD
- [ ] Rate limiting sur endpoints sensibles :
  - `/auth/request` : 5 requêtes / email / heure
  - `/auth/verify` : 10 tentatives / token / heure
  - `/auth/totp` : 5 tentatives / session / 15 min
- [ ] HTTPS obligatoire (redirect HTTP → HTTPS)
- [ ] Headers de sécurité (CSP, X-Frame-Options, etc.)
- [ ] Logs des tentatives de connexion (sans email en clair)
- [ ] Alertes en cas de connexion depuis nouveau device/IP

### 4.2 Protection contre les attaques

| Attaque | Protection |
|---------|------------|
| Brute force token | Token 256 bits + rate limiting |
| Timing attack | Comparaison en temps constant |
| Email enumeration | Réponse identique que l'email existe ou non |
| Session hijacking | Cookie HttpOnly + SameSite + Secure |
| CSRF | SameSite cookie + token CSRF si formulaires |
| Replay TOTP | Stockage du dernier code utilisé |

### 4.3 Chiffrement des données sensibles

| Donnée | Protection |
|--------|------------|
| Email | Hashé (SHA256) pour lookup + chiffré (AES-256) pour récupération |
| TOTP secret | Chiffré (AES-256) avec clé serveur |
| Magic link token | Hashé (SHA256) en BDD |
| Codes de récupération | Hashés (bcrypt) |

---

## 5. API Endpoints

### 5.1 Authentification

```
POST /auth/request
  Body: { "email": "user@example.com" }
  Response: { "message": "Si ce compte existe, un email a été envoyé" }
  
GET /auth/verify/{token}
  Response: 302 Redirect vers app (avec cookie) ou page TOTP

POST /auth/verify-code
  Body: { "email": "user@example.com", "code": "ABC123" }
  Response: { "requires_totp": true/false, "session_token": "..." }

POST /auth/totp
  Body: { "code": "123456" }
  Headers: Authorization: Bearer <session_token>
  Response: { "access_token": "...", "expires_in": 604800 }

POST /auth/logout
  Response: 200 (cookie supprimé)
```

### 5.2 Gestion TOTP

```
POST /auth/totp/setup
  Headers: Authorization: Bearer <access_token>
  Response: { "secret": "BASE32...", "qr_uri": "otpauth://...", "recovery_codes": [...] }

POST /auth/totp/confirm
  Body: { "code": "123456" }
  Headers: Authorization: Bearer <access_token>
  Response: { "enabled": true }

POST /auth/totp/disable
  Body: { "code": "123456" }  // ou recovery code
  Headers: Authorization: Bearer <access_token>
  Response: { "enabled": false }

POST /auth/totp/recovery
  Body: { "recovery_code": "XXXX-XXXX-XXXX-XXXX" }
  Headers: Authorization: Bearer <session_token>
  Response: { "access_token": "...", "remaining_codes": 9 }
```

### 5.3 Utilisateur

```
GET /me
  Headers: Authorization: Bearer <access_token>
  Response: { "public_id": "uuid", "display_name": "...", "totp_enabled": true/false }

PATCH /me
  Body: { "display_name": "Nouveau nom" }
  Headers: Authorization: Bearer <access_token>
  Response: { "public_id": "uuid", "display_name": "Nouveau nom" }

DELETE /me
  Headers: Authorization: Bearer <access_token>
  Response: 200 (compte supprimé, RGPD)
```

---

## 6. Base de données

### 6.1 Schéma SQL

```sql
-- Service Authentification
CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    email_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 pour lookup
    email_encrypted BYTEA,                    -- AES-256 pour récupération
    totp_secret_encrypted BYTEA,
    totp_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    login_count INTEGER DEFAULT 0
);

CREATE TABLE auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 du token
    code VARCHAR(6) NOT NULL,                 -- Code alternatif
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_recovery_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    code_hash VARCHAR(60) NOT NULL,  -- bcrypt
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    mfa_verified BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performances
CREATE INDEX idx_auth_users_email_hash ON auth_users(email_hash);
CREATE INDEX idx_auth_tokens_token_hash ON auth_tokens(token_hash);
CREATE INDEX idx_auth_tokens_expires ON auth_tokens(expires_at);
CREATE INDEX idx_auth_sessions_user ON auth_sessions(user_id);
```

### 6.2 Politique de rétention

| Donnée | Durée | Action |
|--------|-------|--------|
| Tokens expirés | 24h après expiration | Suppression automatique |
| Sessions inactives | 30 jours | Suppression automatique |
| Logs de connexion | 90 jours | Anonymisation |
| Compte inactif | 2 ans | Notification puis suppression |

---

## 7. Configuration

### 7.1 Variables d'environnement

```bash
# Base de données
DATABASE_URL=postgresql://user:pass@localhost:5432/authdb

# Sécurité
JWT_SECRET=<générer avec: openssl rand -hex 32>
ENCRYPTION_KEY=<générer avec: openssl rand -hex 32>
TOTP_ISSUER=MonApplication

# Email
SMTP_HOST=smtp.brevo.com
SMTP_PORT=587
SMTP_USER=<api_key>
SMTP_PASSWORD=<api_password>
SMTP_FROM=auth@mondomaine.fr

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_HOUR=5

# URLs
BASE_URL=https://mondomaine.fr
FRONTEND_URL=https://app.mondomaine.fr
```

---

## 8. Tests

### 8.1 Tests unitaires

- [ ] Génération de tokens (entropie suffisante)
- [ ] Hashage/chiffrement emails
- [ ] Validation TOTP (avec décalage temps)
- [ ] Expiration tokens
- [ ] Rate limiting

### 8.2 Tests d'intégration

- [ ] Flux complet inscription
- [ ] Flux complet connexion magic link
- [ ] Flux complet connexion avec TOTP
- [ ] Récupération via code de secours
- [ ] Suppression compte (RGPD)

### 8.3 Tests de sécurité

- [ ] Tentative brute force token
- [ ] Tentative brute force TOTP
- [ ] Timing attack sur comparaison token
- [ ] Enumération d'emails
- [ ] Injection SQL
- [ ] XSS sur paramètres

---

## 9. Déploiement

### 9.1 Prérequis serveur

- Ubuntu 22.04+ ou Debian 12+
- Python 3.11+
- PostgreSQL 15+
- Nginx (reverse proxy)
- Certbot (Let's Encrypt)

### 9.2 Structure des fichiers

```
auth-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── database.py          # SQLAlchemy setup
│   ├── models/
│   │   ├── __init__.py
│   │   └── auth.py          # Modèles SQLAlchemy
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py          # Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoints auth
│   │   └── user.py          # Endpoints user
│   ├── services/
│   │   ├── __init__.py
│   │   ├── token.py         # Génération tokens
│   │   ├── email.py         # Envoi emails
│   │   ├── totp.py          # Gestion TOTP
│   │   └── crypto.py        # Chiffrement
│   └── utils/
│       ├── __init__.py
│       └── security.py      # Helpers sécurité
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_totp.py
├── alembic/                  # Migrations BDD
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 10. Roadmap

### Phase 1 : MVP Magic Link (Semaine 1-2)
- [ ] Setup projet FastAPI
- [ ] Modèles BDD + migrations
- [ ] Endpoint demande magic link
- [ ] Envoi email
- [ ] Endpoint validation token
- [ ] Génération JWT
- [ ] Tests unitaires

### Phase 2 : Code alternatif (Semaine 3)
- [ ] Génération code 6 caractères
- [ ] Page de saisie code
- [ ] Validation code
- [ ] Tests

### Phase 3 : TOTP (Semaine 4-5)
- [ ] Setup TOTP (pyotp)
- [ ] Génération QR code
- [ ] Endpoints activation/validation
- [ ] Codes de récupération
- [ ] Tests

### Phase 4 : Sécurité (Semaine 6)
- [ ] Rate limiting
- [ ] Logging sécurisé
- [ ] Headers de sécurité
- [ ] Tests de sécurité
- [ ] Audit code

### Phase 5 : Production (Semaine 7)
- [ ] Docker + docker-compose
- [ ] Documentation déploiement
- [ ] Monitoring (health check)
- [ ] Déploiement

---

## 11. Références

- [RFC 6238 - TOTP](https://tools.ietf.org/html/rfc6238)
- [RFC 4226 - HOTP](https://tools.ietf.org/html/rfc4226)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST SP 800-63B - Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [pyotp Documentation](https://pyauth.github.io/pyotp/)
