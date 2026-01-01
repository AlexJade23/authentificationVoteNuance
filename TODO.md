# TODO - Auth Service Decision Collective

## Configuration requise

- [x] **Configurer SMTP** - Infomaniak (mail.infomaniak.com:587)
- [ ] **Configurer le DNS** pour `app.decision-collective.fr` (frontend)

## Documentation

- [x] README.md avec instructions d'installation
- [x] Guide d'intégration pour développeurs (`INTEGRATION.md`)
- [x] Spécifications techniques (`authentificationVoteNuance.md`)

## Intégration frontend (hors scope)

> Le frontend est développé séparément dans le projet `app.decision-collective.fr`.
> Voir le guide d'intégration : [INTEGRATION.md](./INTEGRATION.md)

## Tests

- [x] Test envoi email magic link
- [ ] Tester le flow complet d'inscription (frontend)
- [ ] Tester le flow complet de connexion magic link (frontend)
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
| SMTP | ✅ Infomaniak |
| Documentation | ✅ Complète |

**URL Production** : https://auth.decision-collective.fr
**Swagger UI** : https://auth.decision-collective.fr/docs
