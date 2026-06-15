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

def _pick(opts: list[Session], i: int) -> Session:
    """Choisit une variante selon l'index de semaine → casse la répétitivité."""
    return opts[i % len(opts)]


# Variantes par créneau (on tourne d'une semaine à l'autre). Slug stable par créneau.
_VAR = {
    # ---- BASE ----
    "base-q": [  # mardi : qualité légère course
        Session("run-easy", "run", "easy", "Footing + lignes", 55, "Z2 conversationnel + 6×20\" lignes en accélération (relâché, pas en force).", "Z2"),
        Session("run-easy", "run", "tempo", "Footing + fartlek", 55, "Z2 puis 8×1' soutenu / 1' récup. Jeu d'allures au feeling, ludique.", "Z3"),
        Session("run-easy", "run", "tempo", "Footing + côtes", 55, "Z2 puis 8×30\" en côte (force/puissance), retour en trottinant. Gainage des appuis.", "Z4"),
        Session("run-easy", "run", "easy", "Footing progressif", 55, "Z2 qui accélère doucement : les 10 dernières minutes en allure tempo. Finir frais.", "Z2-Z3"),
    ],
    "base-swim": [
        Session("swim-tech", "swim", "technique", "Natation — glisse & appuis", 45, "Éducatifs rattrapé/poings fermés, 8×50m focus glisse. La technique avant le volume.", "Z2"),
        Session("swim-tech", "swim", "technique", "Natation — battements & gainage", 45, "Battements avec planche, 10×50m, focus alignement et jambes. Respiration tous les 3.", "Z2"),
        Session("swim-tech", "swim", "technique", "Natation — respiration bilatérale", 45, "Éducatifs respiration, 8×75m souple en respirant des 2 côtés. Confort aquatique.", "Z2"),
        Session("swim-tech", "swim", "technique", "Natation — appui/catch (pull)", 45, "Pull-buoy + plaquettes légères, 8×50m focus prise d'appui avant. Sens de l'eau.", "Z2"),
    ],
    "base-tempo": [
        Session("run-tempo", "run", "tempo", "Course tempo continu", 50, "20' Z2 + 15' allure tempo (confortablement dur) + 15' retour au calme.", "Z3"),
        Session("run-tempo", "run", "tempo", "Course tempo fractionné", 50, "Échauff. + 3×6' tempo, récup 2'. Plus facile à tenir, même bénéfice.", "Z3"),
        Session("run-tempo", "run", "tempo", "Course 2×10' cruise", 50, "Échauff. + 2×10' à allure seuil douce, récup 3'. Habitue le corps à durer.", "Z3-Z4"),
        Session("run-tempo", "run", "tempo", "Course progressive", 50, "Négative split : démarre Z2 et finis en tempo sur les 12 dernières minutes.", "Z2-Z3"),
    ],
    "base-bike": [
        Session("bike-endu", "bike", "easy", "Vélo endurance", 75, "Z2 régulier, cadence 85–95. Travail de l'aisance et de la position.", "Z2"),
        Session("bike-endu", "bike", "easy", "Vélo endurance vallonné", 75, "Z2 sur parcours vallonné, monte en souplesse. Renforce sans casser.", "Z2"),
        Session("bike-endu", "bike", "easy", "Vélo cadence", 75, "Z2 + 3×5' à cadence élevée (100+ rpm). Fluidité du coup de pédale.", "Z2"),
        Session("bike-endu", "bike", "tempo", "Vélo force", 75, "Z2 + 4×4' gros braquet en côte à basse cadence (force). Récup en roulant.", "Z3"),
    ],
    "base-long": [
        Session("run-long", "run", "long", "Sortie longue Z2", 90, "Z2 strict, allonge +5–10' vs la dernière. Le pilier de la base aérobie.", "Z2"),
        Session("run-long", "run", "long", "Longue + lignes", 90, "Z2 puis 5×20\" lignes relâchées en fin de sortie. Garde du jus de jambes.", "Z2"),
        Session("run-long", "run", "long", "Longue progressive", 90, "Z2 et finis les 15 dernières minutes en allure tempo (sous fatigue).", "Z2-Z3"),
        Session("run-long", "run", "long", "Longue vallonnée", 90, "Z2 sur parcours avec du relief. Renforce les jambes en douceur.", "Z2"),
    ],
    "base-bikelong": [
        Session("bike-long", "bike", "long", "Vélo long Z2", 105, "Z2, fluide. Endurance fondamentale et économie.", "Z2"),
        Session("bike-long", "bike", "long", "Vélo long + brick", 105, "Z2 puis enchaîne 15' de course juste après (brick découverte 70.3).", "Z2"),
        Session("bike-long", "bike", "long", "Vélo long vallonné", 105, "Z2 sur du relief, gère l'effort dans les bosses. Endurance + force.", "Z2"),
        Session("bike-long", "bike", "tempo", "Vélo long + tempo", 105, "Z2 avec 3×8' en tempo au milieu, récup 5'. Premier travail de soutien.", "Z3"),
    ],
    # ---- BUILD ----
    "build-burn": [
        Session("burn", "strength", "burn", "Le Mix — Burn (force)", 60, "Cours Burn orienté force : squats, fentes, tirage. Base de puissance triathlon.", "Z4"),
        Session("burn", "strength", "burn", "Le Mix — Burn (pliométrie)", 60, "Burn explosif : sauts, bondissements, gainage dynamique. Vitesse & réactivité.", "Z4"),
        Session("burn", "strength", "burn", "Le Mix — Burn (circuit cardio)", 60, "Burn cardio-renfo en circuit. Tape dans le seuil tout en renforçant.", "Z4"),
        Session("burn", "strength", "burn", "Le Mix — Burn (puissance)", 60, "Burn charges + vitesse d'exécution. Recrutement musculaire pour la vitesse pure.", "Z4"),
    ],
    "build-bike": [
        Session("bike-ss", "bike", "sweetspot", "Vélo — Sweet spot 3×10'", 60, "Échauff. 15' + 3×10' à 88–93% FTP, récup 4'. Construit ta puissance.", "Z3"),
        Session("bike-ss", "bike", "sweetspot", "Vélo — Sweet spot 2×20'", 60, "Échauff. + 2×20' à 88–92% FTP, récup 6'. Endurance de puissance.", "Z3"),
        Session("bike-ss", "bike", "threshold", "Vélo — Over-unders", 60, "4×(3' à 95% + 1' à 105% FTP), récup 4'. Tolérance au seuil.", "Z4"),
        Session("bike-ss", "bike", "threshold", "Vélo — Seuil 4×8'", 60, "Échauff. + 4×8' à 95–100% FTP, récup 4'. Monte ta FTP.", "Z4"),
    ],
    "build-thr": [
        Session("run-thr", "run", "threshold", "Course seuil 4×6'", 55, "Échauff. 15' + 4×6' au seuil (allure ~semi) DEHORS, récup 90\". Bien s'échauffer par froid.", "Z4"),
        Session("run-thr", "run", "threshold", "Course seuil 5×5'", 55, "Échauff. + 5×5' au seuil, récup 75\". Volume de qualité au seuil.", "Z4"),
        Session("run-thr", "run", "threshold", "Course seuil 3×10'", 55, "Échauff. + 3×10' légèrement sous le seuil, récup 2'30. Endurance de seuil.", "Z4"),
        Session("run-thr", "run", "threshold", "Course cruise 6×4'", 55, "Échauff. + 6×4' au seuil, récup 1'. Densité d'allure soutenue.", "Z4"),
    ],
    "build-swim": [
        Session("swim-css", "swim", "technique", "Natation — technique + CSS", 45, "Éducatifs puis 6×100m à allure CSS (seuil natation), récup 20\".", "Z3"),
        Session("swim-css", "swim", "threshold", "Natation — CSS 8×100m", 45, "Échauff. + 8×100m à allure CSS, récup 15\". Seuil natation.", "Z3"),
        Session("swim-css", "swim", "technique", "Natation — pyramide", 45, "50-100-150-100-50m en montée d'allure, technique soignée. Varié et ludique.", "Z3"),
        Session("swim-css", "swim", "threshold", "Natation — 4×200m", 45, "Échauff. + 4×200m réguliers à allure soutenue, récup 30\". Endurance.", "Z3"),
    ],
    "build-long": [
        Session("run-long", "run", "long", "Sortie longue Z2", 95, "Z2 en extérieur. Maintien du volume aérobie tout l'hiver (dehors, pas tapis).", "Z2"),
        Session("run-long", "run", "long", "Longue + finish tempo", 95, "Z2 puis 10' tempo en fin. Courir vite sur jambes fatiguées.", "Z2-Z3"),
        Session("run-long", "run", "long", "Longue vallonnée", 95, "Z2 sur du relief. Force spécifique et variété de terrain.", "Z2"),
        Session("run-long", "run", "long", "Longue avec surges", 95, "Z2 + 6×1' soutenu disséminés dans la sortie. Casse la monotonie.", "Z2-Z3"),
    ],
    "build-bikelong": [
        Session("bike-long", "bike", "long", "Vélo salle long", 80, "Z2 long sur home-trainer. Finis par 10' de course (brick).", "Z2"),
        Session("bike-long", "bike", "tempo", "Vélo long + tempo", 80, "Z2 + 3×10' tempo, récup 5'. Soutien aérobie + brick 10'.", "Z3"),
        Session("burn", "strength", "burn", "2e Burn (cardio-endu)", 75, "2e cours Burn plus cardio cette semaine, ou home-trainer Z2 long si fatigue.", "Z3"),
    ],
    # ---- SPECIFIC ----
    "spec-swimrec": [
        Session("swim-rec", "swim", "recovery", "Natation récup", 35, "Nage souple, respiration bilatérale. Récup active des jambes.", "Z1"),
        Session("swim-rec", "swim", "recovery", "Natation technique souple", 35, "Éducatifs + nage facile. Sensations et relâchement.", "Z1"),
    ],
    "spec-vo2": [
        Session("run-vo2", "run", "vo2", "VO2max 6×800m", 60, "Échauff. 20' + 6×800m à allure 5km, récup 2'30. Le moteur du 20km.", "Z5"),
        Session("run-vo2", "run", "vo2", "VO2max 10×400m", 60, "Échauff. + 10×400m vifs, récup 1'30. Vitesse pure et VO2.", "Z5"),
        Session("run-vo2", "run", "vo2", "VO2max 5×1000m", 60, "Échauff. + 5×1000m à allure 5km, récup 3'. Soutien du VO2max.", "Z5"),
        Session("run-vo2", "run", "vo2", "VO2max 12×300m", 60, "Échauff. + 12×300m rapides, récup 1'. Fréquence et relâchement à vitesse.", "Z5"),
        Session("run-vo2", "run", "vo2", "VO2max 4×1200m", 60, "Échauff. + 4×1200m proches allure 5km, récup 3'. Endurance de VO2.", "Z5"),
    ],
    "spec-bike": [
        Session("bike-thr", "bike", "threshold", "Vélo FTP 3×12'", 75, "Échauff. + 3×12' à 95–100% FTP, récup 5'. Vélo du 70.3.", "Z4"),
        Session("bike-thr", "bike", "threshold", "Vélo over-unders 4×8'", 75, "4×8' (alternance 95%/105% par minute), récup 5'. Tolérance au seuil.", "Z4"),
        Session("bike-thr", "bike", "threshold", "Vélo 2×20' seuil", 75, "Échauff. + 2×20' à 95% FTP, récup 8'. Endurance de puissance 70.3.", "Z4"),
        Session("bike-thr", "bike", "vo2", "Vélo VO2 5×4'", 75, "Échauff. + 5×4' à 110–115% FTP, récup 4'. Relève le plafond.", "Z5"),
    ],
    "spec-rp": [
        Session("run-rp", "run", "tempo", "Allure 20km 2×15'", 60, "Échauff. 15' + 2×15' à allure objectif 20km, récup 3'. Ancre l'allure.", "Z4"),
        Session("run-rp", "run", "tempo", "Allure 20km 4×8'", 60, "Échauff. + 4×8' à allure objectif, récup 2'. Densité à l'allure cible.", "Z4"),
        Session("run-rp", "run", "tempo", "Allure 20km 20' continu", 60, "Échauff. + 20' continus à allure objectif. Test de tenue mentale.", "Z4"),
        Session("run-rp", "run", "tempo", "Allure 20km en escalier", 60, "Échauff. + 10'-8'-6'-4' à allure objectif, récup 2'. Varié et stimulant.", "Z4"),
    ],
    "spec-swimow": [
        Session("swim-ow", "swim", "threshold", "Natation CSS 8×100m", 55, "8×100m à allure CSS, récup 15\". Seuil natation.", "Z3"),
        Session("swim-ow", "swim", "threshold", "Eau libre / sighting", 55, "Eau libre si possible : sighting tous les 6 mvts, départ groupé. Sinon 6×150m CSS.", "Z3"),
        Session("swim-ow", "swim", "threshold", "Natation 3×300m", 55, "Échauff. + 3×300m réguliers à allure 70.3, récup 30\". Endurance spécifique.", "Z3"),
    ],
    "spec-long": [
        Session("run-long", "run", "long", "Long + bloc allure", 100, "70' Z2 + 4×5' à allure 20km en fin. Fraîcheur sous fatigue.", "Z2-Z4"),
        Session("run-long", "run", "long", "Long progressif", 100, "Z2 et finis les 20 dernières minutes en allure semi. Mental + physiologie.", "Z2-Z3"),
        Session("run-long", "run", "long", "Long + surges", 100, "Z2 avec 8×1' à allure 10km disséminés. Casse la routine du long.", "Z2-Z4"),
    ],
    "spec-brick": [
        Session("brick", "brick", "long", "Brick 90' vélo → 25' course", 120, "90' vélo Z2-Z3 (2×15' tempo) puis 25' course allure 70.3. Le geste spécifique.", "Z3"),
        Session("brick", "brick", "long", "Brick court & intense", 110, "60' vélo avec 3×8' au seuil + 20' course allure 70.3. Transition sous intensité.", "Z3-Z4"),
        Session("brick", "brick", "long", "Brick long endurance", 120, "2h vélo Z2 régulier + 15' course souple. Endurance et habitude des jambes.", "Z2"),
    ],
}


def _base_week(i: int) -> dict[int, list[Session]]:
    return {
        0: [Session("mobility", "mobility", "mobility", "Mobilité & gainage", 25,
                    "Routine hanches/chevilles + gainage 3x. Récup active.", "Z1")],
        1: [_pick(_VAR["base-q"], i)],
        2: [_pick(_VAR["base-swim"], i)],
        3: [_pick(_VAR["base-tempo"], i)],
        4: [_pick(_VAR["base-bike"], i)],
        5: [_pick(_VAR["base-long"], i)],
        6: [_pick(_VAR["base-bikelong"], i)],
    }


def _build_week(i: int) -> dict[int, list[Session]]:
    return {
        0: [Session("rest", "rest", "recovery", "Repos", 0,
                    "Repos complet ou marche. La force fatigue : respecte la récup.", "Z1")],
        1: [_pick(_VAR["build-burn"], i)],
        2: [_pick(_VAR["build-bike"], i)],
        3: [_pick(_VAR["build-thr"], i)],
        4: [_pick(_VAR["build-swim"], i)],
        5: [_pick(_VAR["build-long"], i)],
        6: [_pick(_VAR["build-bikelong"], i)],
    }


def _specific_week(i: int) -> dict[int, list[Session]]:
    return {
        0: [_pick(_VAR["spec-swimrec"], i)],
        1: [_pick(_VAR["spec-vo2"], i)],
        2: [_pick(_VAR["spec-bike"], i)],
        3: [_pick(_VAR["spec-rp"], i)],
        4: [_pick(_VAR["spec-swimow"], i)],
        5: [_pick(_VAR["spec-long"], i)],
        6: [_pick(_VAR["spec-brick"], i)],
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
        tmpl = _base_week(week_index)
    elif phase.key == "build":
        tmpl = _build_week(week_index)
    elif phase.key == "specific":
        tmpl = _specific_week(week_index)
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
