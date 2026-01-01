# Auth Service - Decision Collective

Service d'authentification sans mot de passe pour la plateforme [app.decision-collective.fr](https://app.decision-collective.fr).

Alternative aux SSO GAFAM, respectueuse de la vie privée.

## Fonctionnalités

- **Magic Link** : Authentification par email (lien + code)
- **TOTP (2FA)** : Authentification à deux facteurs (FreeOTP, Aegis, Google Authenticator)
- **Anonymat** : Dissociation complète entre email et identifiant public
- **RGPD** : Droit à l'oubli, minimisation des données

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11+ / FastAPI |
| Base de données | PostgreSQL |
| TOTP | pyotp (RFC 6238) |
| Chiffrement | AES-256 (Fernet) |
| Tokens | JWT (python-jose) |

## Installation

### Prérequis

- Python 3.11+
- PostgreSQL 15+
- Serveur SMTP (Brevo, Postmark, etc.)

### Configuration

1. Cloner le dépôt :
```bash
git clone git@github.com:AlexJade23/authentificationVoteNuance.git
cd authentificationVoteNuance
```

2. Créer l'environnement virtuel :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Créer la base de données PostgreSQL :
```sql
CREATE USER authuser WITH PASSWORD 'votre-mot-de-passe';
CREATE DATABASE authdb OWNER authuser;
```

4. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

Variables requises :
```bash
DATABASE_URL=postgresql://authuser:password@localhost:5432/authdb
JWT_SECRET=<générer avec: openssl rand -hex 32>
ENCRYPTION_KEY=<générer avec: openssl rand -hex 32>
```

5. Lancer le service :
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## API Endpoints

### Authentification

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/auth/request` | POST | Demande un magic link |
| `/auth/verify/{token}` | GET | Valide un magic link |
| `/auth/verify-code` | POST | Valide un code |
| `/auth/totp` | POST | Valide un code TOTP |
| `/auth/logout` | POST | Déconnexion |

### TOTP (2FA)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/auth/totp/setup` | POST | Configure le TOTP |
| `/auth/totp/confirm` | POST | Active le TOTP |
| `/auth/totp/disable` | POST | Désactive le TOTP |
| `/auth/totp/recovery` | POST | Utilise un code de récupération |

### Utilisateur

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/me` | GET | Informations utilisateur |
| `/me` | PATCH | Mise à jour profil |
| `/me` | DELETE | Suppression compte (RGPD) |
| `/me/sessions` | GET | Liste des sessions |
| `/me/sessions` | DELETE | Révoque toutes les sessions |

## Architecture

```
app/
├── main.py              # Application FastAPI
├── config.py            # Configuration (via .env)
├── database.py          # Connexion PostgreSQL
├── models/
│   └── auth.py          # Modèles SQLAlchemy
├── schemas/
│   └── auth.py          # Schémas Pydantic
├── routers/
│   ├── auth.py          # Endpoints authentification
│   └── user.py          # Endpoints utilisateur
├── services/
│   ├── crypto.py        # Chiffrement AES-256, hachage SHA-256
│   ├── email.py         # Envoi emails SMTP
│   ├── token.py         # Génération/validation JWT
│   └── totp.py          # Gestion TOTP
└── utils/
    └── security.py      # Rate limiting, middlewares
```

## Sécurité

- Emails hashés (SHA-256) pour le lookup, chiffrés (AES-256) pour la récupération
- Tokens magic link à usage unique, expiration 15 minutes
- Rate limiting sur les endpoints sensibles
- Headers de sécurité (X-Frame-Options, CSP, etc.)
- Comparaison en temps constant (anti timing attack)

## Documentation

- [Spécifications complètes](./authentificationVoteNuance.md)
- [Swagger UI](https://auth.decision-collective.fr/docs) (en production)

## Licence

Voir [LICENSE](./LICENSE)
