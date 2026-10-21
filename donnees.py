# -*- coding: utf-8 -*-
"""Stockage des contenus de la bibliothèque (sans interface graphique).

Ce module est volontairement pur : il ne dépend pas de Kivy, ce qui permet de
le tester facilement. Il gère la lecture et l'écriture du fichier JSON.
"""

import json
import os
import time
import uuid
from pathlib import Path

TYPES = ["Série", "Article", "Vidéo"]
STATUTS = ["À voir", "En cours", "Terminé", "Abandonné"]


def normaliser_tags(texte):
    """Transforme « SF, cuisine, SF » en ["SF", "cuisine"] (sans doublon)."""
    vus = set()
    tags = []
    for morceau in texte.split(","):
        tag = " ".join(morceau.split())
        if tag and tag.casefold() not in vus:
            vus.add(tag.casefold())
            tags.append(tag)
    return tags


def element_normalise(brut):
    """Nettoie un contenu relu du fichier JSON (valeurs par défaut, bornes)."""
    if not isinstance(brut, dict):
        return None
    titre = str(brut.get("titre", "")).strip()
    if not titre:
        return None
    try:
        note = int(brut.get("note", 0) or 0)
    except (TypeError, ValueError):
        note = 0
    tags = brut.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    type_contenu = brut.get("type")
    statut = brut.get("statut")
    return {
        "id": str(brut.get("id") or uuid.uuid4().hex),
        "titre": titre,
        "type": type_contenu if type_contenu in TYPES else TYPES[0],
        "auteur": str(brut.get("auteur", "")).strip(),
        "statut": statut if statut in STATUTS else STATUTS[0],
        "note": max(0, min(5, note)),
        "tags": [str(tag).strip() for tag in tags if str(tag).strip()],
        "avis": str(brut.get("avis", "")).strip(),
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
