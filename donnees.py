# -*- coding: utf-8 -*-
"""Stockage des contenus de la bibliothèque (sans interface graphique).

Nouveau schéma : titre, type, statut, informations, resume.
Les anciennes fiches (auteur, note, tags, avis) restent lisibles :
les tags deviennent le texte d'« informations », l'avis devient le « résumé ».
"""

import json
import os
import time
import uuid
from pathlib import Path

TYPES = ["Série", "Article", "Vidéo"]
STATUTS = ["À voir", "En cours", "Terminé", "Abandonné"]


def element_normalise(brut):
    """Nettoie un contenu relu du fichier JSON (valeurs par défaut, migration)."""
    if not isinstance(brut, dict):
        return None
    titre = str(brut.get("titre", "")).strip()
    if not titre:
        return None

    type_contenu = brut.get("type")
    statut = brut.get("statut")

    informations = brut.get("informations")
    if informations is None:
        anciens_tags = brut.get("tags", [])
        if isinstance(anciens_tags, list):
            informations = ", ".join(
                str(tag).strip() for tag in anciens_tags if str(tag).strip()
            )
        else:
            informations = str(anciens_tags)
    informations = str(informations).strip()

    resume = brut.get("resume")
    if resume is None:
        resume = brut.get("avis", "")
    resume = str(resume).strip()

    return {
        "id": str(brut.get("id") or uuid.uuid4().hex),
        "titre": titre,
        "type": type_contenu if type_contenu in TYPES else TYPES[0],
        "statut": statut if statut in STATUTS else STATUTS[0],
        "informations": informations,
        "resume": resume,
    }


def charger(chemin):
    """Lit le fichier JSON. Renvoie la liste des contenus (vide si absent)."""
    chemin = Path(chemin)
    if not chemin.exists():
        return []
    try:
        # « utf-8-sig » accepte aussi un fichier enregistré avec un BOM.
        with open(chemin, encoding="utf-8-sig") as fichier:
            brut = json.load(fichier)
    except (OSError, ValueError):
        # Fichier illisible : on le met de côté pour ne rien perdre.
        sauvegarde = chemin.with_name(f"bibliotheque_corrompue_{int(time.time())}.json")
        try:
            os.replace(chemin, sauvegarde)
        except OSError:
            return []
        return []
    if isinstance(brut, dict):
        brut = brut.get("contenus", [])
    if not isinstance(brut, list):
        return []
    contenus = [element_normalise(element) for element in brut]
    return [contenu for contenu in contenus if contenu]


def sauvegarder(contenus, chemin):
    """Écrit les contenus dans le fichier JSON de façon sûre."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_name(chemin.name + ".tmp")
    with open(temporaire, "w", encoding="utf-8") as fichier:
        json.dump(contenus, fichier, ensure_ascii=False, indent=2)
    os.replace(temporaire, chemin)
