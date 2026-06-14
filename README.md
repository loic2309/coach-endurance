# 🏃 Coach Endurance — route vers 1h05 (20km) & sub-5h (70.3)

Plateforme de coaching personnelle : plan d'entrainement périodisé sur ~12 mois,
synchronisation automatique des données Garmin, conseils de coaching, et dashboard de suivi.

Interface **sombre premium** (style Whoop / Strava), responsive (utilisable au téléphone),
organisée en 6 sections : **Vue d'ensemble · Mon plan · Cette semaine · Charge · Défis · Conseils**.

Fonctionnalités clés :
- 📈 Plan périodisé 12 mois (4 phases, deload 3:1) adapté aux contraintes de l'athlète
- ⌚ Synchro Garmin + **analyse coach** des allures réelles (`coach_report`)
- 🎯 Allures d'entraînement **crescendo**, ancrées sur les vraies données Garmin
- 🏆 **Gamification** : niveau, XP, série hebdomadaire, badges (calculés sur l'historique réel)
- 🔒 Auth optionnelle pour un déploiement en ligne sécurisé

## Objectifs

| Course | PR actuel (Garmin) | Palier 1 an (visé) | Rêve | Date |
|--------|--------------------|--------------------|------|------|
| 20km de Bruxelles | 1h21 (4:04/km) | **1h13** | 1h05 | ~30 mai 2027 |
| Half-Ironman 70.3 | 5h15 | **sub-5h** | — | ~20 juin 2027 |

> Note de coach : l'analyse Garmin montre un PR réel de 1h21 (couru en aisance, donc avec de la
> marge). Le palier crédible sur un an est ~1h13 ; 1h05 reste le rêve à 2-3 ans. Les allures
> d'entraînement visent le palier 1 an et montent crescendo depuis les allures Garmin réelles.

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

## Analyse coach des allures (Garmin)

Un outil analyse ton historique et calibre les allures sur tes vraies données :

```bash
python -m backend.coach_report --sync   # synchronise 12 mois puis analyse
```
Il calcule ta Z2 réelle, ton meilleur effort, ton volume, et une projection 20km (Riegel).
Ces repères sont stockés et utilisés par le moteur d'allures (crescendo depuis le réel).

## Déploiement (app hébergée, accessible au téléphone)

Le repo contient un **`Dockerfile`** et un **`render.yaml`** (blueprint).

**Render (le plus simple) :**
1. Sur [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** → choisis ce repo.
2. Render lit `render.yaml` (service Docker + disque persistant `/data`).
3. Renseigne les secrets dans le dashboard : `GARMIN_EMAIL`, `GARMIN_PASSWORD`, et **`APP_PASSWORD`** (le mot de passe d'accès à ton app).
4. Déploie → ton app est en ligne sur une URL `https://…onrender.com`, accessible au téléphone.

> 🔒 **Sécurité** : dès que `APP_PASSWORD` est défini, l'app exige un login HTTP (user `APP_USER`,
> défaut `coach`). Les identifiants Garmin ne sont **jamais** dans le repo — uniquement en variables
> d'environnement côté hébergeur. Le `.env` local est gitignored.

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/overview` | objectifs, allures cibles, statut Garmin, meilleurs efforts, avancement du plan |
| GET | `/api/plan` | plan complet (toutes les semaines) |
| GET | `/api/week?d=AAAA-MM-JJ` | semaine contenant la date (avec statut des séances) |
| GET | `/api/load?weeks=12` | charge réelle par sport (Garmin) |
| GET | `/api/coaching` | principes, guides de phase, stratégies de course |
| GET | `/api/gamification` | niveau, XP, série, badges |
| POST | `/api/sync` | importe les activités Garmin |
| POST | `/api/session-status` | marque une séance fait/sauté |

## Structure

```
backend/   FastAPI + plan_engine + garmin_sync + analytics + coaching + db (SQLite)
frontend/  dashboard SPA (HTML/CSS/JS + Chart.js), design sombre premium
data/      SQLite + token Garmin (gitignored)
```
