"""Contenu de coaching : principes méthodologiques, guides de phase, stratégies de course.

Rédigé selon les principes d'entraînement endurance reconnus (polarisation 80/20,
surcharge progressive, spécificité, périodisation, primauté de la récupération).
"""
from __future__ import annotations


PRINCIPLES = [
    {
        "icon": "polarized",
        "title": "Polarisation 80/20",
        "body": "≈80% de ton volume en endurance facile (Z1–Z2, tu peux tenir une conversation), "
                "≈20% en intensité réellement dure (seuil, VO2max). L'erreur n°1 de l'amateur motivé : "
                "courir trop vite les jours faciles et pas assez fort les jours durs. Le facile doit être "
                "VRAIMENT facile — c'est lui qui construit le moteur aérobie.",
    },
    {
        "icon": "progressive",
        "title": "Surcharge progressive & 3:1",
        "body": "On augmente la charge d'environ 5–10% par semaine sur 3 semaines, puis 1 semaine "
                "d'allègement (−30%) pour absorber le travail. C'est pendant la récupération que tu "
                "progresses, pas pendant l'effort. Ne saute jamais une semaine de décharge.",
    },
    {
        "icon": "specificity",
        "title": "Spécificité croissante",
        "body": "Plus la course approche, plus l'entraînement lui ressemble : allure cible, terrain, "
                "enchaînements vélo→course (brick) pour le triathlon, et nutrition de course testée. "
                "L'hiver on bâtit les qualités générales ; au printemps on les rend spécifiques.",
    },
    {
        "icon": "recovery",
        "title": "La récupération est un entraînement",
        "body": "Sommeil (7–9h), jours faciles respectés, et écoute des signaux (FC de repos élevée, "
                "VFC basse, jambes lourdes = on lève le pied). Mieux vaut arriver à la course "
                "légèrement sous-entraîné et frais que parfaitement entraîné et cramé.",
    },
    {
        "icon": "consistency",
        "title": "Régularité > héroïsme",
        "body": "Trois mois de séances régulières et modérées battent deux semaines de surentraînement "
                "suivies d'une blessure. Avec un emploi du temps chargé, la séance \"assez bonne\" que tu "
                "fais vaut mieux que la séance parfaite que tu sautes.",
    },
    {
        "icon": "strength",
        "title": "Force = vitesse + prévention",
        "body": "Le travail de force (Le Mix / Burn) améliore l'économie de course, la puissance vélo et "
                "réduit le risque de blessure. À garder toute l'année, allégé en phase d'affûtage.",
    },
]


PHASE_GUIDES = {
    "base": {
        "subtitle": "Construire le moteur — juin → mi-octobre 2026",
        "summary": "Le socle de toute la saison. On développe le système aérobie (mitochondries, "
                   "capillarisation, endurance) avec beaucoup de volume facile, et on règle la technique "
                   "de natation tant qu'il n'y a pas de pression de chrono.",
        "objectives": [
            "Augmenter progressivement le volume hebdomadaire en course (Z2).",
            "Poser une technique de natation propre (glisse, position, respiration bilatérale).",
            "Installer 2–3h de vélo facile par semaine pour l'endurance de base.",
            "Habituer le corps à 5–6 séances/semaine sans casse.",
        ],
        "key_sessions": ["Sortie longue course (le pilier)", "Footing avec lignes", "Natation technique"],
        "watch_outs": [
            "Ne pas transformer les footings faciles en tempo : reste en Z2.",
            "La natation se joue sur la technique, pas sur les longueurs avalées en force.",
        ],
        "metrics": ["Volume hebdo course (km/min)", "VO2max estimé Garmin", "FC en Z2 à allure donnée (doit baisser)"],
    },
    "build": {
        "subtitle": "Force & bloc hivernal — mi-octobre 2026 → février 2027",
        "summary": "Le vélo passe en salle (home-trainer) pour gagner force et puissance, mais la course "
                   "reste DEHORS — le seuil se court en extérieur. Le travail de vitesse/puissance vient "
                   "surtout des cours de Burn. C'est la phase où l'on construit la puissance vélo du sub-5h.",
        "objectives": [
            "Augmenter la FTP vélo via le sweet spot et le seuil en salle.",
            "Maintenir le volume course dehors et introduire du seuil (en extérieur).",
            "Développer vitesse et puissance via le Burn (explosivité transférable aux 3 disciplines).",
            "Garder un contact technique avec l'eau (1–2 séances/sem).",
        ],
        "key_sessions": ["Vélo sweet spot 3×10'", "Course seuil 4×6' (extérieur)", "Burn (vitesse & force)"],
        "watch_outs": [
            "Le Burn est intense : ne l'empile pas la veille d'une grosse séance de seuil.",
            "Habille-toi en couches pour le seuil hivernal en extérieur ; échauffe-toi bien avant les fractions.",
        ],
        "metrics": ["FTP vélo (W)", "Allure au seuil course", "Charge d'entraînement Garmin (équilibrée)"],
    },
    "specific": {
        "subtitle": "Spécifique course & triathlon — février → mi-mai 2027",
        "summary": "On transforme la forme générale en performance spécifique. Pour le 20km : VO2max et "
                   "allure cible. Pour le 70.3 : enchaînements vélo→course (brick) et retour à l'eau libre. "
                   "C'est ici qu'on apprend à courir vite ET à courir fatigué après le vélo.",
        "objectives": [
            "Développer la VO2max (le plafond de vitesse pour le 20km).",
            "Ancrer l'allure objectif 20km pour qu'elle devienne automatique.",
            "Maîtriser le brick : courir bien dès les premières foulées après le vélo.",
            "Retrouver l'eau libre : sighting, départ groupé, gestion de l'allure.",
        ],
        "key_sessions": ["VO2max 6×800m", "Allure 20km 2×15'", "Brick vélo→course"],
        "watch_outs": [
            "Les séances VO2max sont coûteuses : 1 à 2 par semaine maximum, jamais enchaînées.",
            "Teste ta nutrition de course longue PENDANT les bricks, pas le jour J.",
        ],
        "metrics": ["Allure sur 800m/1km", "Dérive cardiaque sur sortie longue", "Allure course post-vélo (brick)"],
    },
    "peak": {
        "subtitle": "Affûtage & courses — mi-mai → juin 2027",
        "summary": "On réduit nettement le volume (−40 à −60%) en gardant un peu d'intensité courte pour "
                   "rester affûté. La fatigue tombe, la forme remonte. Deux pics : le 20km, puis une "
                   "réactivation et le 70.3 ~3 semaines plus tard.",
        "objectives": [
            "Arriver frais et confiant sur le 20km (jambes légères > jambes entraînées).",
            "Récupérer vite après le 20km puis réactiver les spécificités 70.3.",
            "Verrouiller la logistique : matériel, transitions, plan nutrition de course.",
        ],
        "key_sessions": ["Réveils musculaires courts", "Mini-brick d'activation", "COURSES 🎯"],
        "watch_outs": [
            "Pendant l'affûtage on ne gagne plus de forme — on ne fait que la révéler. Résiste à l'envie d'en rajouter.",
            "Entre le 20km et le 70.3 : récup réelle d'abord, le maintien suffit, ne re-construis pas.",
        ],
        "metrics": ["Fraîcheur (VFC, FC repos)", "Sensations à l'allure cible", "Sommeil"],
    },
}


RACE_STRATEGIES = {
    "20km": {
        "title": "20km de Bruxelles — plan de course",
        "goal_line": "Objectif 1h05 (3:15/km) — ton 1h21 était couru en aisance, la marge est là : on va la chercher",
        "pacing": [
            "Pars délibérément 3–5 s/km plus lent que ta cible sur les 3 premiers km : l'adrénaline trompe.",
            "Verrouille l'allure cible du km 4 au km 15, en restant relâché (épaules, mâchoire).",
            "Du km 15 à l'arrivée : c'est là que tu donnes. Négative split = la 2e moitié plus vite que la 1re.",
        ],
        "pre_race": [
            "Derniers gros entraînements terminés 10–12 jours avant.",
            "Reconnais le profil (la montée de la rue de la Loi / bois de la Cambre selon le tracé).",
            "Petit-déjeuner testé à l'entraînement, 3h avant. Échauffement 15' + 4 lignes.",
        ],
        "mental": "Découpe la course en blocs de 5 km. Une seule consigne par bloc. Le mal commence "
                  "vers le 15e — c'est prévu, c'est normal, c'est là que se joue le chrono.",
    },
    "703": {
        "title": "Half-Ironman 70.3 — plan de course",
        "goal_line": "Cible sub-5h · le gain vient surtout du vélo et des transitions",
        "pacing": [
            "Natation (1,9 km) : régulier, ne pars pas en sprint. Économise — c'est le plus court en temps.",
            "Vélo (90 km) : reste en deçà de ta sensation \"je pourrais pousser plus\". Négative split. "
            "Mange et bois dès les premiers km (c'est sur le vélo qu'on s'alimente).",
            "Course (21 km) : les 3 premiers km semblent faciles malgré les jambes \"de bois\" — tiens "
            "l'allure prévue, ça revient. Puis gère au mental jusqu'au bout.",
        ],
        "pre_race": [
            "Transitions répétées à l'entraînement (T1/T2) : elles valent des minutes gratuites.",
            "Plan nutrition chiffré : ~60–90g de glucides/h sur le vélo, testé en brick.",
            "Check matériel la veille : vélo, pneus, dossards, combinaison, ravitos.",
        ],
        "mental": "Trois courses en une : ne juge jamais ta journée sur la natation. La course se "
                  "gagne en restant patient sur le vélo pour pouvoir courir le semi.",
    },
}


def coaching_payload() -> dict:
    return {
        "principles": PRINCIPLES,
        "phase_guides": PHASE_GUIDES,
        "race_strategies": RACE_STRATEGIES,
    }
