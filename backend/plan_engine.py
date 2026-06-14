"""Moteur de plan d'entrainement périodisé.

Génère un plan semaine par semaine du `plan_start` jusqu'à la dernière course,
découpé en 4 phases, en respectant les contraintes de l'athlète :
- semaine = séances courtes (<2h), sauf la course à pied qui peut être plus longue
- hiver = Le Mix (cours "Burn" type cross-training + vélo en salle)
- préférence : course à pied > vélo > natation (la natation reste travaillée car
  c'est le point faible technique d'un triathlète)

Deux A-races rapprochées : 20km de Bruxelles (fin mai) puis 70.3 (~3 semaines après).
La forme de course se reporte ; le vélo/natation doivent déjà être prêts avant le 20km.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta

from .config import settings

WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

SPORT_EMOJI = {
    "run": "🏃",
    "bike": "🚴",
    "swim": "🏊",
    "strength": "🏋️",
    "brick": "🔁",
    "rest": "😴",
    "mobility": "🧘",
}


@dataclass
class Session:
    slug: str           # identifiant stable dans la journée (sport+type)
    sport: str
    type: str           # easy / long / threshold / vo2 / tempo / technique / sweetspot / burn / recovery / race
    title: str
    duration_min: int
    description: str
    zone: str           # zone d'intensité (Z1..Z5) ou texte

    def dict(self) -> dict:
        d = asdict(self)
        d["emoji"] = SPORT_EMOJI.get(self.sport, "•")
        return d


@dataclass
class Phase:
    key: str
    name: str
    color: str
    focus: str


PHASES = [
    Phase("base", "Phase 1 — Base aérobie & technique", "#2563eb",
          "Construire le moteur aérobie en course, poser la technique de natation, "
          "installer du volume vélo facile. Beaucoup de Z2, peu d'intensité."),
    Phase("build", "Phase 2 — Force & bloc hivernal (Le Mix)", "#7c3aed",
          "Gagner en force et en puissance via le Burn + vélo en salle (sweet spot / FTP). "
          "Maintenir la course avec du seuil sur tapis, natation technique 1–2x/sem."),
    Phase("specific", "Phase 3 — Spécifique course & triathlon", "#db2777",
          "Affûter la vitesse pour le 20km (VO2max, seuil, allure course) et installer "
          "les enchaînements vélo→course (brick) pour le 70.3. Retour eau libre."),
    Phase("peak", "Phase 4 — Affûtage & courses", "#ea580c",
          "Réduire le volume, garder l'intensité courte. Pic sur le 20km, "
          "récupération courte, réactivation 70.3, puis 2e pic."),
]


def phase_for(d: date) -> Phase:
    """Détermine la phase selon la date, en se calant sur les courses."""
    r20 = settings.race_20km_date
    r70 = settings.race_703_date
    # Affûtage : 12 jours avant le 20km jusqu'au 70.3.
    if d >= r20 - timedelta(days=12):
        return PHASES[3]
    # Spécifique : ~16 semaines avant le 20km.
    if d >= r20 - timedelta(weeks=16):
        return PHASES[2]
    # Build hivernal : ~18 sept -> spécifique.
    if d >= date(2026, 10, 19):
        return PHASES[1]
    return PHASES[0]


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def is_deload(week_index: int) -> bool:
    """1 semaine de récupération (allègement) toutes les 4 semaines."""
    return week_index % 4 == 3


# ---------------------------------------------------------------------------
# Gabarits de semaine par phase. Clé = index du jour (0=lundi .. 6=dimanche).
# Les durées sont des durées "semaine normale" ; le deload applique 0.7x.
# ---------------------------------------------------------------------------

def _base_week() -> dict[int, list[Session]]:
    return {
        0: [Session("mobility", "mobility", "mobility", "Mobilité & gainage", 25,
                    "Routine hanches/chevilles + gainage 3x. Récup active.", "Z1")],
        1: [Session("run-easy", "run", "easy", "Footing facile + lignes", 55,
                    "Z2 confortable, tu peux parler. Finir par 6×20\" lignes en accélération.", "Z2")],
        2: [Session("swim-tech", "swim", "technique", "Natation technique", 45,
                    "Éducatifs (rattrapé, poings fermés), 8×50m focus glisse. La technique avant le volume.", "Z2")],
        3: [Session("run-tempo", "run", "tempo", "Footing avec tempo", 50,
                    "20' Z2 + 15' allure tempo (confortablement dur) + 15' retour au calme.", "Z3")],
        4: [Session("bike-endu", "bike", "easy", "Vélo endurance", 75,
                    "Z2 régulier, cadence 85–95. Travail de l'aisance et de la position.", "Z2")],
        5: [Session("run-long", "run", "long", "Sortie longue course", 90,
                    "Z2 strict, allonge la durée de +5–10' chaque semaine. Le pilier de la base.", "Z2")],
        6: [Session("bike-long", "bike", "long", "Vélo long (ou brick léger)", 105,
                    "Z2. 1×/2 semaines : enchaîne 15' de course juste après (brick découverte).", "Z2")],
    }


def _build_week() -> dict[int, list[Session]]:
    return {
        0: [Session("rest", "rest", "recovery", "Repos", 0,
                    "Repos complet ou marche. La force fatigue : respecte la récup.", "Z1")],
        1: [Session("burn", "strength", "burn", "Le Mix — Burn (vitesse & force)", 60,
                    "Cours Burn : ton travail de vitesse/puissance de l'hiver + base force full-body pour les 3 disciplines.", "Z4")],
        2: [Session("bike-ss", "bike", "sweetspot", "Vélo salle — Sweet spot", 60,
                    "Échauff. 15' puis 3×10' à 88–93% FTP (sweet spot), récup 4'. Gagne ta puissance ici.", "Z3")],
        3: [Session("run-thr", "run", "threshold", "Course seuil (extérieur)", 55,
                    "Échauff. 15' + 4×6' au seuil (allure ~semi) DEHORS, récup 90\". Couvre-toi et échauffe-toi bien avant les fractions.", "Z4")],
        4: [Session("swim-css", "swim", "technique", "Natation technique + CSS", 45,
                    "Éducatifs puis 6×100m à allure CSS (seuil natation). Garde le contact avec l'eau.", "Z3")],
        5: [Session("run-long", "run", "long", "Sortie longue course", 95,
                    "Z2 en extérieur. Maintien du volume aérobie course tout l'hiver (tu cours dehors, pas sur tapis).", "Z2")],
        6: [Session("bike-long", "bike", "long", "Vélo salle long / Burn endu", 80,
                    "Z2 long sur home-trainer, ou 2e Burn plus cardio. Finir par 10' de course (brick).", "Z2")],
    }


def _specific_week() -> dict[int, list[Session]]:
    return {
        0: [Session("swim-rec", "swim", "recovery", "Natation récup / technique", 35,
                    "Nage souple, focus respiration bilatérale. Récup active des jambes.", "Z1")],
        1: [Session("run-vo2", "run", "vo2", "Course VO2max", 60,
                    "Échauff. 20' + 6×800m à allure 5km (~3:15–3:25/km), récup 2'30. Le moteur du 20km.", "Z5")],
        2: [Session("bike-thr", "bike", "threshold", "Vélo seuil / FTP", 75,
                    "Échauff. + 3×12' à 95–100% FTP, récup 5'. Prépare la partie vélo du 70.3.", "Z4")],
        3: [Session("run-rp", "run", "tempo", "Course allure 20km", 60,
                    "Échauff. 15' + 2×15' à allure objectif 20km, récup 3'. Ancre l'allure de course.", "Z4")],
        4: [Session("swim-ow", "swim", "threshold", "Natation CSS / eau libre", 55,
                    "8×100m CSS, ou eau libre dès que possible (sighting, départ groupé).", "Z3")],
        5: [Session("run-long", "run", "long", "Long avec bloc allure", 100,
                    "70' Z2 + 4×5' à allure 20km en fin de sortie. Fraîcheur sous fatigue.", "Z2-Z4")],
        6: [Session("brick", "brick", "long", "Brick vélo → course", 120,
                    "90' vélo Z2-Z3 avec 2×15' tempo, puis 25' course allure 70.3. Spécifique triathlon.", "Z3")],
    }


def _peak_week(d: date) -> dict[int, list[Session]]:
    """Affûtage + courses : logique spéciale selon proximité des courses."""
    r20 = settings.race_20km_date
    r70 = settings.race_703_date
    week_mon = _monday(d)

    # Semaine du 20km
    if week_mon <= r20 <= week_mon + timedelta(days=6):
        wk = {
            0: [Session("rest", "rest", "recovery", "Repos", 0, "Repos. Jambes fraîches.", "Z1")],
            1: [Session("run-sharp", "run", "vo2", "Réveil musculaire", 35,
                        "15' Z2 + 4×1' allure 20km, récup 2'. Court et vif.", "Z4")],
            2: [Session("swim-rec", "swim", "recovery", "Natation souple", 30, "Décrassage léger.", "Z1")],
            3: [Session("run-strides", "run", "easy", "Footing + lignes", 30,
                        "20' Z2 + 4×20\" lignes. Rien de fatigant.", "Z2")],
            4: [Session("rest", "rest", "recovery", "Repos / mobilité", 15, "Mobilité légère, hydratation.", "Z1")],
        }
        # Place la course le jour J.
        race_day = (r20 - week_mon).days
        wk[race_day] = [Session("race-20km", "run", "race", "🎯 COURSE — 20km de Bruxelles", 70,
                                "Jour J ! Pars sur ton allure objectif, négative split si possible.", "Z5")]
        return wk

    # Semaine du 70.3
    if week_mon <= r70 <= week_mon + timedelta(days=6):
        wk = {
            0: [Session("rest", "rest", "recovery", "Repos", 0, "Repos.", "Z1")],
            1: [Session("brick-sharp", "brick", "tempo", "Mini-brick d'activation", 45,
                        "30' vélo avec 3×3' tempo + 12' course allure 70.3. Vif et court.", "Z3")],
            2: [Session("swim-rec", "swim", "recovery", "Natation aisance", 30, "Sensations, sighting.", "Z2")],
            3: [Session("bike-open", "bike", "easy", "Vélo ouverture", 35,
                        "20' Z2 + 4×45\" allure course, récup 2'. Réveil des jambes.", "Z3")],
            4: [Session("rest", "rest", "recovery", "Repos / prépa matos", 15, "Check vélo, dossard, transitions.", "Z1")],
        }
        race_day = (r70 - week_mon).days
        wk[race_day] = [Session("race-703", "brick", "race", "🎯 COURSE — Half-Ironman 70.3", 300,
                                "Jour J ! Nage régulier, vélo maîtrisé (négative split), garde du jus pour courir.", "Z4")]
        return wk

    # Semaine intermédiaire (récup post-20km + réactivation 70.3)
    return {
        0: [Session("rest", "rest", "recovery", "Repos", 0, "Récup post-course.", "Z1")],
        1: [Session("swim-rec", "swim", "recovery", "Natation décrassage", 35, "Nage souple régénérative.", "Z1")],
        2: [Session("bike-z2", "bike", "easy", "Vélo Z2", 60, "Réactivation aérobie, jambes légères.", "Z2")],
        3: [Session("run-easy", "run", "easy", "Footing facile", 40, "Z2 sans forcer, vérifie les sensations.", "Z2")],
        4: [Session("swim-ow", "swim", "threshold", "Natation CSS courte", 40, "4×100m CSS, sighting.", "Z3")],
        5: [Session("brick", "brick", "tempo", "Brick spécifique 70.3", 110,
                    "75' vélo avec 2×12' allure 70.3 + 20' course allure 70.3. Dernier vrai rappel.", "Z3")],
        6: [Session("bike-long", "bike", "long", "Vélo long modéré", 90, "Z2, fluide, finir frais.", "Z2")],
    }


def _apply_load(week: dict[int, list[Session]], deload: bool, ramp: float) -> dict[int, list[Session]]:
    """Applique une montée de charge progressive (+ deload) sur les durées."""
    mult = 0.7 if deload else ramp
    out: dict[int, list[Session]] = {}
    for day, sessions in week.items():
        new = []
        for s in sessions:
            dur = s.duration_min
            # On ne réduit pas le repos / la course ; on n'allonge pas indéfiniment les <2h.
            if s.type not in ("race", "recovery") and s.sport != "rest":
                dur = round(s.duration_min * mult)
                if s.sport != "run":  # plafond 2h hors course à pied (contrainte semaine)
                    dur = min(dur, 120)
            new.append(Session(s.slug, s.sport, s.type, s.title, dur, s.description, s.zone))
        out[day] = new
    return out


def build_week(week_index: int, monday: date) -> dict:
    phase = phase_for(monday)
    deload = is_deload(week_index)

    if phase.key == "base":
        tmpl = _base_week()
    elif phase.key == "build":
        tmpl = _build_week()
    elif phase.key == "specific":
        tmpl = _specific_week()
    else:
        tmpl = _peak_week(monday)

    # Montée de charge douce à l'intérieur d'un bloc de 4 semaines (0.85 -> 1.0 -> 1.05).
    ramp = {0: 0.9, 1: 1.0, 2: 1.05, 3: 0.7}[week_index % 4]
    if phase.key != "peak":
        tmpl = _apply_load(tmpl, deload, ramp)

    days = []
    total_min = 0
    by_sport: dict[str, int] = {}
    for i in range(7):
        sessions = [s.dict() for s in tmpl.get(i, [])]
        for s in sessions:
            total_min += s["duration_min"]
            if s["sport"] not in ("rest", "mobility"):
                by_sport[s["sport"]] = by_sport.get(s["sport"], 0) + s["duration_min"]
        days.append({
            "weekday": WEEKDAYS[i],
            "date": (monday + timedelta(days=i)).isoformat(),
            "sessions": sessions,
        })

    return {
        "week_index": week_index,
        "monday": monday.isoformat(),
        "phase": asdict(phase),
        "deload": deload,
        "total_min": total_min,
        "total_hours": round(total_min / 60, 1),
        "by_sport_min": by_sport,
        "days": days,
    }


def full_plan() -> list[dict]:
    last_race = max(settings.race_20km_date, settings.race_703_date)
    monday = _monday(settings.plan_start)
    weeks = []
    idx = 0
    while monday <= _monday(last_race):
        weeks.append(build_week(idx, monday))
        monday += timedelta(days=7)
        idx += 1
    return weeks


def week_containing(d: date) -> dict:
    monday = _monday(d)
    start = _monday(settings.plan_start)
    idx = (monday - start).days // 7
    return build_week(max(idx, 0), monday)
