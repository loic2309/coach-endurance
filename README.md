# 🏃 Coach Endurance — route vers 1h05 (20km) & sub-5h (70.3)

Plateforme de coaching personnelle : plan d'entrainement périodisé sur ~12 mois,
synchronisation automatique des données Garmin, conseils de coaching, et dashboard de suivi.

Interface **sombre premium** (style Whoop / Strava), responsive (utilisable au téléphone),
organisée en 5 sections : **Vue d'ensemble · Mon plan · Cette semaine · Charge · Conseils**.

## Objectifs

| Course | Actuel | Objectif principal | Stretch | Date |
|--------|--------|--------------------|---------|------|
| 20km de Bruxelles | 1h10 | **1h05** (3:15/km) | 1h02 | ~30 mai 2027 |
| Half-Ironman 70.3 | 5h15 | **sub-5h** | — | ~20 juin 2027 |

> Note de coach : avec 1h10 déjà au compteur, viser 1h05 (≈15 s/km de mieux) sur un an de
> prépa structurée est ambitieux mais crédible. Le sub-5h sur 70.3 est tout à fait atteignable.

## Périodisation (4 phases)

1. **Base aérobie & technique** (juin → mi-oct 2026) — volume facile en course, technique natation, endurance vélo.
2. **Force & bloc hivernal** (mi-oct 2026 → fév 2027) — Le Mix : Burn (force) + vélo en salle (sweet spot/FTP), seuil sur tapis.
3. **Spécifique course & triathlon** (fév → mi-mai 2027) — VO2max & allure 20km, enchaînements brick, retour eau libre.
4. **Affûtage & courses** (mi-mai → juin 2027) — pic 20km, récup, réactivation, pic 70.3.

Contraintes respectées : séances de semaine < 2h (sauf course à pied), Le Mix l'hiver,
préférence course > vélo > natation, 1 semaine d'allègement sur 4.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis édite .env (identifiants Garmin + objectifs)
```

## Lancer en local

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
# ouvre http://localhost:8000
```

## Synchroniser Garmin

Renseigne `GARMIN_EMAIL` / `GARMIN_PASSWORD` dans `.env`, puis clique **🔄 Synchroniser Garmin**
sur le dashboard (ou `POST /api/sync`). À la première connexion un token est sauvegardé dans
`data/garmin_tokens/` pour les fois suivantes. Les identifiants restent **en local**.

Si tu as la double authentification (MFA) sur Garmin, fais une première connexion en local
pour générer le token, puis déploie avec le dossier `data/garmin_tokens/`.

## Déploiement (app hébergée)

L'app est un service FastAPI standard. Pour la rendre accessible depuis ton téléphone :

- **Railway / Render / Fly.io** : déploie le repo, commande de démarrage
  `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, et configure les variables
  d'environnement (`.env`). Monte un volume persistant sur `DATA_DIR` pour garder SQLite + le token.

> ⚠️ En hébergé, protège l'accès (auth basique / réseau privé) : l'app contient ta session Garmin.

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/overview` | objectifs, allures cibles, statut Garmin, meilleurs efforts, avancement du plan |
| GET | `/api/plan` | plan complet (toutes les semaines) |
| GET | `/api/week?d=AAAA-MM-JJ` | semaine contenant la date (avec statut des séances) |
| GET | `/api/load?weeks=12` | charge réelle par sport (Garmin) |
| GET | `/api/coaching` | principes, guides de phase, stratégies de course |
| POST | `/api/sync` | importe les activités Garmin |
| POST | `/api/session-status` | marque une séance fait/sauté |

## Structure

```
backend/   FastAPI + plan_engine + garmin_sync + analytics + coaching + db (SQLite)
frontend/  dashboard SPA (HTML/CSS/JS + Chart.js), design sombre premium
data/      SQLite + token Garmin (gitignored)
```
