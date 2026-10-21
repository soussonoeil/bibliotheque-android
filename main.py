# -*- coding: utf-8 -*-
"""Ma bibliothèque — version Android (Kivy).

Mêmes champs que la version pour ordinateur : titre, type, auteur/plateforme,
statut, note (curseur de 0 à 5), tags et petit avis.

Les données sont enregistrées dans un fichier JSON privé de l'application
(dossier « user_data_dir »). Aucune connexion Internet n'est nécessaire.

Pour tester sur un ordinateur : python main.py
Pour construire l'APK Android : voir LISEZMOI.md.
"""

import uuid
from pathlib import Path

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from donnees import STATUTS, TYPES, charger, normaliser_tags, sauvegarder

FOND = (0.09, 0.10, 0.13, 1)
CARTE = (0.15, 0.17, 0.22, 1)
CHAMP = (0.17, 0.19, 0.24, 1)
TEXTE = (0.95, 0.96, 0.98, 1)
GRIS = (0.63, 0.66, 0.72, 1)
ACCENT = (0.30, 0.55, 1.0, 1)
ROUGE = (0.88, 0.30, 0.30, 1)


def note_texte(note):
    """Renvoie « 4/5 » ou « non noté »."""
    note = int(note or 0)
    return f"{note}/5" if note else "non noté"


def etiquette(contenu, taille, couleur, hauteur, centree=False, couper=False):
    """Label à hauteur fixe, aligné à gauche (ou centré) et tronqué au besoin."""
    label = Label(
        text=contenu,
        font_size=taille,
        color=couleur,
        halign="center" if centree else "left",
        valign="middle",
        size_hint_y=None,
        height=hauteur,
        shorten=couper,
    )

    def ajuster(*_args):
        label.text_size = (max(dp(1), label.width), label.height)

    label.bind(size=ajuster)
    ajuster()
    return label


class Carte(BoxLayout):
    """Une ligne de la bibliothèque : texte à gauche, bouton « Modifier »."""

    def __init__(self, contenu, ouvrir, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(96),
            padding=[dp(10), dp(8)],
            spacing=dp(6),
            **kwargs,
        )
        self.contenu = contenu
        with self.canvas.before:
            Color(*CARTE)
            self.fond = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._placer, size=self._placer)

        colonne = BoxLayout(orientation="vertical", spacing=dp(1))
        colonne.add_widget(
            etiquette(contenu["titre"], sp(15), TEXTE, dp(28), couper=True)
        )
        colonne.add_widget(
            etiquette(
                f"{contenu['type']} · {contenu['statut']} · "
                f"Note {note_texte(contenu['note'])}",
                sp(12),
                GRIS,
                dp(20),
                couper=True,
            )
        )
        colonne.add_widget(
            etiquette(
                f"{contenu['auteur'] or '—'} · "
                f"{', '.join(contenu['tags']) or '—'}",
                sp(12),
                GRIS,
                dp(20),
                couper=True,
            )
        )
        self.add_widget(colonne)

        bouton = Button(
            text="Modifier",
            size_hint=(None, 1),
            width=dp(84),
            background_normal="",
            background_down="",
            background_color=ACCENT,
            color=(1, 1, 1, 1),
            font_size=sp(12),
        )
        bouton.bind(on_release=lambda _bouton: ouvrir(contenu))
        self.add_widget(bouton)

    def _placer(self, *_args):
        self.fond.pos = self.pos
        self.fond.size = self.size


class Confirmation(Popup):
    """Petite fenêtre « Oui / Non » avant une suppression."""

    def __init__(self, message, action, **kwargs):
        super().__init__(
            title="Supprimer ?",
            size_hint=(0.85, 0.4),
            background_color=FOND,
            separator_color=ROUGE,
            **kwargs,
        )
        racine = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(12), dp(8), dp(12), dp(8)],
        )
        racine.add_widget(etiquette(message, sp(14), TEXTE, dp(64), centree=True))

        boutons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8)
        )
        annuler = Button(
            text="Annuler",
            background_normal="",
            background_down="",
            background_color=CARTE,
            font_size=sp(14),
        )
        annuler.bind(on_release=lambda _bouton: self.dismiss())
        supprimer = Button(
            text="Supprimer",
            background_normal="",
            background_down="",
            background_color=ROUGE,
            font_size=sp(14),
        )
        supprimer.bind(on_release=lambda _bouton: (self.dismiss(), action()))
        boutons.add_widget(annuler)
        boutons.add_widget(supprimer)
        racine.add_widget(boutons)
        self.content = racine


class Formulaire(Popup):
    """Fenêtre de saisie : ajout d'un contenu ou modification d'un existant."""

    def __init__(self, application, contenu=None, **kwargs):
        super().__init__(
            title="Modifier le contenu" if contenu else "Nouveau contenu",
            size_hint=(0.95, 0.92),
            auto_dismiss=False,
            background_color=FOND,
            separator_color=ACCENT,
            title_size=sp(16),
            **kwargs,
        )
        self.application = application
        self.contenu = contenu

        note_initiale = int(contenu["note"]) if contenu else 0
        type_initial = contenu["type"] if contenu else TYPES[0]
        statut_initial = contenu["statut"] if contenu else STATUTS[0]

        racine = BoxLayout(orientation="vertical", spacing=dp(2))
        scroll = ScrollView(bar_width=dp(3), bar_color=ACCENT)
        champs = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
            padding=[dp(12), dp(6), dp(12), dp(6)],
        )
        champs.bind(minimum_height=champs.setter("height"))

        champs.add_widget(etiquette("Titre", sp(12), GRIS, dp(18)))
        self.champ_titre = self._entree(contenu["titre"] if contenu else "")
        champs.add_widget(self.champ_titre)

        ligne = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(64), spacing=dp(8)
        )
        colonne_type = BoxLayout(orientation="vertical", spacing=dp(1))
        colonne_type.add_widget(etiquette("Type", sp(12), GRIS, dp(16)))
        self.champ_type = Spinner(
            text=type_initial,
            values=TYPES,
            size_hint_y=None,
            height=dp(44),
            font_size=sp(14),
        )
        colonne_type.add_widget(self.champ_type)
        colonne_statut = BoxLayout(orientation="vertical", spacing=dp(1))
        colonne_statut.add_widget(etiquette("Statut", sp(12), GRIS, dp(16)))
        self.champ_statut = Spinner(
            text=statut_initial,
            values=STATUTS,
            size_hint_y=None,
            height=dp(44),
            font_size=sp(14),
        )
        colonne_statut.add_widget(self.champ_statut)
        ligne.add_widget(colonne_type)
        ligne.add_widget(colonne_statut)
        champs.add_widget(ligne)

        champs.add_widget(etiquette("Auteur / chaîne / plateforme", sp(12), GRIS, dp(18)))
        self.champ_auteur = self._entree(contenu["auteur"] if contenu else "")
        champs.add_widget(self.champ_auteur)

        champs.add_widget(etiquette("Note", sp(12), GRIS, dp(18)))
        self.texte_note = etiquette(
            f"Note : {note_texte(note_initiale)}", sp(13), TEXTE, dp(20)
        )
        champs.add_widget(self.texte_note)
        self.curseur = Slider(
            min=0, max=5, step=1, value=note_initiale, size_hint_y=None, height=dp(38)
        )
        self.curseur.bind(value=self._changer_note)
        champs.add_widget(self.curseur)

        champs.add_widget(etiquette("Tags", sp(12), GRIS, dp(18)))
        tags_texte = ", ".join(contenu["tags"]) if contenu else ""
        self.champ_tags = self._entree(tags_texte)
        champs.add_widget(self.champ_tags)

        champs.add_widget(etiquette("Avis", sp(12), GRIS, dp(18)))
        self.champ_avis = TextInput(
            text=(contenu["avis"] if contenu else ""),
            multiline=True,
            size_hint_y=None,
            height=dp(96),
            font_size=sp(14),
            background_color=CHAMP,
            foreground_color=TEXTE,
            cursor_color=ACCENT,
            padding=[dp(8), dp(8)],
        )
        champs.add_widget(self.champ_avis)

        self.erreur = etiquette("", sp(12), ROUGE, dp(20))
        champs.add_widget(self.erreur)

        scroll.add_widget(champs)

        barre = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(54),
            spacing=dp(8),
            padding=[dp(10), dp(4), dp(10), dp(8)],
        )
        annuler = Button(
            text="Annuler",
            background_normal="",
            background_down="",
            background_color=CARTE,
            font_size=sp(14),
        )
        annuler.bind(on_release=lambda _bouton: self.dismiss())
        barre.add_widget(annuler)
        if contenu:
            supprimer = Button(
                text="Supprimer",
                background_normal="",
                background_down="",
                background_color=ROUGE,
                font_size=sp(14),
            )
            supprimer.bind(on_release=lambda _bouton: self._demander_suppression())
            barre.add_widget(supprimer)
        enregistrer = Button(
            text="Enregistrer",
            background_normal="",
            background_down="",
            background_color=ACCENT,
            font_size=sp(14),
        )
        enregistrer.bind(on_release=self._enregistrer)
        barre.add_widget(enregistrer)

        racine.add_widget(scroll)
        racine.add_widget(barre)
        self.content = racine

    def _entree(self, texte):
        return TextInput(
            text=texte,
            multiline=False,
            size_hint_y=None,
            height=dp(44),
            font_size=sp(14),
            background_color=CHAMP,
            foreground_color=TEXTE,
            cursor_color=ACCENT,
            padding=[dp(8), dp(10)],
        )

    def _changer_note(self, _curseur, valeur):
        self.texte_note.text = f"Note : {note_texte(int(valeur))}"

    def _enregistrer(self, *_args):
        titre = self.champ_titre.text.strip()
        if not titre:
            self.erreur.text = "Le titre est obligatoire : écris au moins un mot."
            return
        type_choisi = self.champ_type.text
        statut_choisi = self.champ_statut.text
        donnees = {
            "titre": titre,
            "type": type_choisi if type_choisi in TYPES else TYPES[0],
            "auteur": self.champ_auteur.text.strip(),
            "statut": statut_choisi if statut_choisi in STATUTS else STATUTS[0],
            "note": int(self.curseur.value),
            "tags": normaliser_tags(self.champ_tags.text),
            "avis": self.champ_avis.text.strip(),
        }
        self.dismiss()
        self.application.enregistrer(donnees, self.contenu)

    def _demander_suppression(self):
        def confirmer():
            self.dismiss()
            self.application.supprimer(self.contenu)

        Confirmation(f"Supprimer « {self.contenu['titre']} » ?", confirmer).open()


class Bibliotheque(App):
    """Application principale."""

    def build(self):
        self.title = "Ma bibliothèque"
        Window.clearcolor = FOND
        try:
            Window.softinput_mode = "below_target"
        except Exception:  # pas grave si le système ne gère pas l'option
            pass

        base = self.user_data_dir or str(Path.home())
        self.chemin = Path(base) / "bibliotheque.json"
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.contenus = charger(self.chemin)
        self.filtre_type = "Tous"
        self.filtre_statut = "Tous"

        self.racine = BoxLayout(
            orientation="vertical",
            padding=[dp(12), dp(10), dp(12), dp(8)],
            spacing=dp(6),
        )

        entete = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(44))
        entete.add_widget(etiquette("Ma bibliothèque", sp(22), TEXTE, dp(30)))
        entete.add_widget(etiquette("séries · articles · vidéos", sp(11), GRIS, dp(16)))
        self.racine.add_widget(entete)

        self.champ_recherche = TextInput(
            hint_text="Rechercher (titre, auteur, tag, avis)",
            multiline=False,
            size_hint_y=None,
            height=dp(46),
            font_size=sp(14),
            background_color=CHAMP,
            foreground_color=TEXTE,
            cursor_color=ACCENT,
            padding=[dp(10), dp(12)],
        )
        self.champ_recherche.bind(text=lambda *_args: self._rafraichir())
        self.racine.add_widget(self.champ_recherche)

        filtres = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(60), spacing=dp(8)
        )
        colonne_type = BoxLayout(orientation="vertical", spacing=dp(1))
        colonne_type.add_widget(etiquette("Type", sp(11), GRIS, dp(16)))
        self.spinner_type = Spinner(
            text="Tous",
            values=["Tous"] + TYPES,
            size_hint_y=None,
            height=dp(42),
            font_size=sp(13),
        )
        self.spinner_type.bind(text=self._sur_type)
        colonne_type.add_widget(self.spinner_type)
        colonne_statut = BoxLayout(orientation="vertical", spacing=dp(1))
        colonne_statut.add_widget(etiquette("Statut", sp(11), GRIS, dp(16)))
        self.spinner_statut = Spinner(
            text="Tous",
            values=["Tous"] + STATUTS,
            size_hint_y=None,
            height=dp(42),
            font_size=sp(13),
        )
        self.spinner_statut.bind(text=self._sur_statut)
        colonne_statut.add_widget(self.spinner_statut)
        filtres.add_widget(colonne_type)
        filtres.add_widget(colonne_statut)
        self.racine.add_widget(filtres)

        self.liste = ScrollView(
            size_hint=(1, 1), do_scroll_x=False, bar_width=dp(3), bar_color=ACCENT
        )
        self.conteneur = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.conteneur.bind(minimum_height=self.conteneur.setter("height"))
        self.liste.add_widget(self.conteneur)
        self.racine.add_widget(self.liste)

        self.barre_stats = etiquette("", sp(11.5), GRIS, dp(20))
        self.racine.add_widget(self.barre_stats)

        self.bouton_ajouter = Button(
            text="+ Ajouter un contenu",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_down="",
            background_color=ACCENT,
            color=(1, 1, 1, 1),
            font_size=sp(16),
        )
        self.bouton_ajouter.bind(on_release=lambda _bouton: Formulaire(self).open())
        self.racine.add_widget(self.bouton_ajouter)

        self._rafraichir()
        return self.racine

    # -- filtres -----------------------------------------------------------

    def _sur_type(self, _spinner, valeur):
        self.filtre_type = valeur
        self._rafraichir()

    def _sur_statut(self, _spinner, valeur):
        self.filtre_statut = valeur
        self._rafraichir()

    # -- données -----------------------------------------------------------

    def _rafraichir(self, *_args):
        requete = self.champ_recherche.text.strip().casefold()
        affiches = []
        for contenu in self.contenus:
            if self.filtre_type != "Tous" and contenu["type"] != self.filtre_type:
                continue
            if self.filtre_statut != "Tous" and contenu["statut"] != self.filtre_statut:
                continue
            if requete:
                texte = " ".join(
                    (
                        contenu["titre"],
                        contenu["auteur"],
                        " ".join(contenu["tags"]),
                        contenu["avis"],
                        contenu["type"],
                        contenu["statut"],
                    )
                ).casefold()
                if requete not in texte:
                    continue
            affiches.append(contenu)

        affiches.sort(key=lambda element: element["titre"].casefold())

        self.conteneur.clear_widgets()
        if affiches:
            for contenu in affiches:
                self.conteneur.add_widget(Carte(contenu, self._ouvrir))
        else:
            if self.contenus:
                message = (
                    "Aucun résultat avec ces filtres.\n"
                    "Change la recherche ou choisis « Tous »."
                )
            else:
                message = (
                    "Aucun contenu pour le moment.\n"
                    "Appuie sur « + Ajouter un contenu »."
                )
            self.conteneur.add_widget(etiquette(message, sp(14), GRIS, dp(120), centree=True))

        self._maj_stats()

    def _maj_stats(self):
        total = len(self.contenus)
        termines = sum(1 for contenu in self.contenus if contenu["statut"] == "Terminé")
        notes = [contenu["note"] for contenu in self.contenus if contenu["note"] > 0]
        if notes:
            moyenne = f"{sum(notes) / len(notes):.1f}".replace(".", ",")
        else:
            moyenne = "—"
        self.barre_stats.text = (
            f"{total} contenu{'s' if total != 1 else ''} · "
            f"{termines} terminé{'s' if termines != 1 else ''} · "
            f"note moyenne {moyenne}"
        )

    def _ouvrir(self, contenu):
        Formulaire(self, contenu).open()

    def enregistrer(self, donnees, contenu=None):
        if contenu is None:
            donnees = dict(donnees)
            donnees["id"] = uuid.uuid4().hex
            self.contenus.append(donnees)
        else:
            contenu.update(donnees)
        self._sauvegarder()

    def supprimer(self, contenu):
        self.contenus = [
            element for element in self.contenus if element["id"] != contenu["id"]
        ]
        self._sauvegarder()

    def _sauvegarder(self):
        try:
            sauvegarder(self.contenus, self.chemin)
        except OSError as erreur:
            Popup(
                title="Enregistrement impossible",
                content=etiquette(
                    f"Tes données n'ont pas pu être enregistrées :\n{erreur}",
                    sp(13),
                    TEXTE,
                    dp(90),
                    centree=True,
                ),
                size_hint=(0.85, 0.38),
                background_color=FOND,
                separator_color=ROUGE,
            ).open()
        self._rafraichir()


if __name__ == "__main__":
    Bibliotheque().run()
