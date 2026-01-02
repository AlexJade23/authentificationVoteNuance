# Guide d'intégration - Auth Service Decision Collective

Documentation pour intégrer l'authentification dans l'application frontend.

## Informations de connexion

| Élément | Valeur |
|---------|--------|
| **URL API** | `https://auth.decision-collective.fr` |
| **Documentation Swagger** | https://auth.decision-collective.fr/docs |
| **Méthode d'auth** | Magic Link (email) + TOTP optionnel |

---

## Flow d'authentification

### 1. Connexion simple (sans TOTP)

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend   │      │  Auth API    │      │    Email     │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       │ POST /auth/request  │                     │
       │ {email: "..."}      │                     │
       │────────────────────>│                     │
       │                     │   Magic Link        │
       │                     │────────────────────>│
       │  "email envoyé"     │                     │
       │<────────────────────│                     │
       │                     │                     │
       │   (user clique)     │                     │
       │   GET /auth/verify/{token}                │
       │────────────────────>│                     │
       │                     │                     │
       │  Si OK: Redirect    │                     │
       │  /auth/callback?token=JWT                 │
       │<────────────────────│                     │
       │                     │                     │
       │  Si expiré: Redirect│                     │
       │  /auth/error?reason=token_expired         │
       │<────────────────────│                     │
       │                     │                     │
       │  Stocke le JWT      │                     │
       └─────────────────────┴─────────────────────┘
```

### 2. Connexion avec TOTP activé

```
┌──────────────┐      ┌──────────────┐
│   Frontend   │      │  Auth API    │
└──────┬───────┘      └──────┬───────┘
       │                     │
       │ POST /auth/request  │
       │────────────────────>│
       │                     │
       │ (après clic email)  │
       │ Redirect vers       │
       │ /auth/totp?session=TOKEN_SESSION
       │<────────────────────│
       │                     │
       │ POST /auth/totp     │
       │ {code: "123456"}    │
       │ Header: Bearer TOKEN_SESSION
       │────────────────────>│
       │                     │
       │ {access_token: JWT} │
       │<────────────────────│
       └─────────────────────┘
```

---

## Endpoints à implémenter côté frontend

### Pages requises

| Page | Route suggérée | Description |
|------|----------------|-------------|
| Login | `/login` | Formulaire email |
| Attente | `/login/pending` | "Vérifiez votre email" + champ code |
| TOTP | `/login/totp` | Saisie code 6 chiffres |
| Callback | `/auth/callback` | Récupère le token, redirige |
| **Erreur auth** | `/auth/error` | **Affiche les erreurs d'authentification** |
| Paramètres | `/settings/security` | Activer/désactiver TOTP |

### Page d'erreur `/auth/error`

Quand un magic link est invalide ou expiré, l'API redirige vers `/auth/error` avec un paramètre `reason`.

**URL de redirection :**
```
https://app.decision-collective.fr/auth/error?reason=token_expired
```

**Paramètres query string :**

| Paramètre | Valeurs possibles | Description |
|-----------|-------------------|-------------|
| `reason` | `token_expired` | Le magic link a expiré (durée de vie : 15 min) |

**Exemple d'implémentation (React) :**

```jsx
// pages/auth/error.jsx
import { useSearchParams, Link } from 'react-router-dom';

const ERROR_MESSAGES = {
  token_expired: {
    title: 'Lien expiré',
    message: 'Ce lien de connexion a expiré. Les liens sont valables 15 minutes.',
    action: 'Demander un nouveau lien'
  }
};

export default function AuthError() {
  const [params] = useSearchParams();
  const reason = params.get('reason') || 'unknown';
  const error = ERROR_MESSAGES[reason] || {
    title: 'Erreur',
    message: 'Une erreur est survenue lors de la connexion.',
    action: 'Réessayer'
  };

  return (
    <div className="auth-error">
      <h1>{error.title}</h1>
      <p>{error.message}</p>
      <Link to="/login">{error.action}</Link>
    </div>
  );
}
```

---

## API Reference

### Demander un magic link

```http
POST https://auth.decision-collective.fr/auth/request
Content-Type: application/json

{
  "email": "utilisateur@example.com"
}
```

**Réponse :**
```json
{
  "message": "Si ce compte existe, un email a été envoyé"
}
```

> Note : La réponse est identique que l'email existe ou non (anti-énumération).

---

### Vérifier avec le code (alternative au clic)

```http
POST https://auth.decision-collective.fr/auth/verify-code
Content-Type: application/json

{
  "email": "utilisateur@example.com",
  "code": "ABC123"
}
```

**Réponse (sans TOTP) :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "requires_totp": false
}
```

**Réponse (avec TOTP activé) :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "requires_totp": true
}
```

> Si `requires_totp: true`, le token est temporaire (15 min) et doit être utilisé pour `/auth/totp`.

---

### Vérifier le code TOTP

```http
POST https://auth.decision-collective.fr/auth/totp
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "code": "123456"
}
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "requires_totp": false
}
```

---

### Obtenir les infos utilisateur

```http
GET https://auth.decision-collective.fr/me
Authorization: Bearer <access_token>
```

**Réponse :**
```json
{
  "public_id": "f5284bf9-3718-4248-b31b-dd291a5c9164",
  "display_name": null,
  "totp_enabled": false
}
```

> `public_id` est l'identifiant unique de l'utilisateur à utiliser dans l'application.

---

### Activer le TOTP (2FA)

**Étape 1 : Générer le secret**

```http
POST https://auth.decision-collective.fr/auth/totp/setup
Authorization: Bearer <access_token>
```

**Réponse :**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_uri": "otpauth://totp/DecisionCollective:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=DecisionCollective",
  "recovery_codes": [
    "XXXX-XXXX-XXXX-XXXX",
    "YYYY-YYYY-YYYY-YYYY",
    ...
  ]
}
```

> Afficher le QR code généré depuis `qr_uri` et demander à l'utilisateur de sauvegarder les `recovery_codes`.

**Étape 2 : Confirmer avec un code**

```http
POST https://auth.decision-collective.fr/auth/totp/confirm
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "123456"
}
```

---

### Désactiver le TOTP

```http
POST https://auth.decision-collective.fr/auth/totp/disable
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "123456"
}
```

---

### Supprimer le compte (RGPD)

```http
DELETE https://auth.decision-collective.fr/me
Authorization: Bearer <access_token>
```

---

## Gestion du JWT

### Structure du token

```json
{
  "sub": "f5284bf9-3718-4248-b31b-dd291a5c9164",
  "mfa": false,
  "iat": 1704067200,
  "exp": 1704672000
}
```

| Claim | Description |
|-------|-------------|
| `sub` | `public_id` de l'utilisateur |
| `mfa` | `true` si TOTP validé |
| `iat` | Timestamp de création |
| `exp` | Timestamp d'expiration (7 jours) |

### Stockage recommandé

- **Cookie HttpOnly** (recommandé) : Protection XSS
- **localStorage** : Plus simple mais vulnérable XSS

### Exemple avec cookie (backend-for-frontend)

```javascript
// Après récupération du token
document.cookie = `auth_token=${token}; path=/; secure; samesite=strict; max-age=604800`;
```

---

## Codes d'erreur

| Code HTTP | Signification |
|-----------|---------------|
| 400 | Requête invalide (code expiré, email invalide, etc.) |
| 401 | Non authentifié (token manquant ou expiré) |
| 429 | Rate limit atteint |
| 500 | Erreur serveur |

### Exemple d'erreur

```json
{
  "detail": "Token invalide ou expiré"
}
```

---

## Rate Limiting

| Endpoint | Limite |
|----------|--------|
| `/auth/request` | 5 requêtes / email / heure |
| `/auth/verify-code` | 10 tentatives / heure |
| `/auth/totp` | 5 tentatives / 15 min |

---

## Exemple d'implémentation (React)

```jsx
// hooks/useAuth.js
import { useState } from 'react';

const API_URL = 'https://auth.decision-collective.fr';

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const requestMagicLink = async (email) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/auth/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      return res.ok;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (email, code) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/auth/verify-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      });
      if (!res.ok) throw new Error('Code invalide');
      return await res.json();
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const verifyTotp = async (sessionToken, code) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/auth/totp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`,
        },
        body: JSON.stringify({ code }),
      });
      if (!res.ok) throw new Error('Code TOTP invalide');
      return await res.json();
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { requestMagicLink, verifyCode, verifyTotp, loading, error };
}
```

---

## Contact

- **Swagger UI** : https://auth.decision-collective.fr/docs
- **Spécifications** : voir `authentificationVoteNuance.md` dans le repo
