# TODO - Auth Service Decision Collective

## Configuration requise

- [ ] **Configurer SMTP** dans `.env` pour l'envoi des magic links
  ```bash
  SMTP_USER=votre-api-key-brevo
  SMTP_PASSWORD=votre-password-brevo
  ```
  Puis redémarrer : `sudo systemctl restart auth-service`

- [ ] **Configurer le DNS** pour `app.decision-collective.fr` (frontend)

## Intégration frontend

- [ ] Créer la page de login (formulaire email)
- [ ] Créer la page d'attente magic link (avec champ code)
- [ ] Créer la page de saisie TOTP
- [ ] Créer le callback `/auth/callback` pour récupérer le token
- [ ] Implémenter le stockage du JWT (cookie HttpOnly recommandé)
- [ ] Créer la page paramètres sécurité (activation TOTP)

## Tests

- [ ] Tester le flow complet d'inscription
- [ ] Tester le flow complet de connexion magic link
- [ ] Tester le flow connexion avec TOTP activé
- [ ] Tester les codes de récupération TOTP
- [ ] Tester la suppression de compte (RGPD)
- [ ] Tester le rate limiting

## Sécurité (optionnel mais recommandé)

- [ ] Ajouter des alertes email lors de connexion depuis nouvelle IP
- [ ] Implémenter la révocation de tokens (blacklist JWT)
- [ ] Ajouter logs de sécurité (tentatives échouées)
- [ ] Configurer fail2ban pour les tentatives de brute force
- [ ] Audit de sécurité du code

## Production

- [ ] Configurer le monitoring (health checks)
- [ ] Configurer les backups PostgreSQL
- [ ] Configurer la rotation des logs
- [ ] Documenter la procédure de restauration
- [ ] Configurer les alertes (service down, erreurs)

## Améliorations futures

- [ ] Support WebAuthn/Passkeys (alternative au TOTP)
- [ ] Historique des connexions visible par l'utilisateur
- [ ] Notifications push pour les connexions suspectes
- [ ] API pour l'application principale (vérification tokens)
- [ ] Dashboard admin (stats, utilisateurs)

---

## Statut actuel

| Composant | Statut |
|-----------|--------|
| API Backend | ✅ Déployé |
| PostgreSQL | ✅ Configuré |
| Nginx | ✅ Configuré |
| SSL/HTTPS | ✅ Let's Encrypt |
| SMTP | ⏳ À configurer |
| Frontend | ⏳ À développer |

**URL Production** : https://auth.decision-collective.fr
