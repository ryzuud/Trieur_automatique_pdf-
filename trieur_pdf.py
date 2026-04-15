#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trieur Automatique de PDF
=========================
Surveille le dossier Téléchargements et classe automatiquement les PDF
en identifiant l'expéditeur via des mots-clés dans le contenu.

Renomme au format : AAAA-MM_Fournisseur.pdf
Déplace dans : Archives_PDF/{Fournisseur}/
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Forcer l'encodage UTF-8 sur Windows pour supporter les emojis et accents
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pdfplumber
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ─────────────────────────── Configuration du logging ───────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / "trieur_pdf.log", encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("TrieurPDF")


def sanitiser_log(message: str) -> str:
    """Nettoie une chaîne pour le logging en remplaçant les sauts de ligne."""
    return str(message).replace("\n", r"\n").replace("\r", r"\r")


# ─────────────────────────── Chargement de la config ────────────────────────────


def charger_config() -> dict:
    """Charge la configuration depuis config.json situé à côté du script."""
    chemin_config = Path(__file__).parent / "config.json"

    if not chemin_config.exists():
        logger.error("Fichier config.json introuvable : %s", chemin_config)
        sys.exit(1)

    with open(chemin_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Résoudre les chemins avec ~ (home directory)
    config["dossier_surveillance"] = Path(
        os.path.expanduser(config["dossier_surveillance"])
    ).resolve()
    config["dossier_archives"] = Path(
        os.path.expanduser(config["dossier_archives"])
    ).resolve()

    # Vérifier que le dossier de surveillance existe
    if not config["dossier_surveillance"].exists():
        logger.error(
            "Le dossier de surveillance n'existe pas : %s",
            config["dossier_surveillance"],
        )
        sys.exit(1)

    # Créer le dossier d'archives + sous-dossiers si nécessaire
    config["dossier_archives"].mkdir(parents=True, exist_ok=True)
    for fournisseur_data in config["fournisseurs"].values():
        dossier = config["dossier_archives"] / fournisseur_data.get(
            "dossier", fournisseur_data["nom"]
        )
        dossier.mkdir(parents=True, exist_ok=True)

    # Créer aussi le dossier "Non_classé" pour les PDF non identifiés
    (config["dossier_archives"] / "Non_classe").mkdir(parents=True, exist_ok=True)

    logger.info("Configuration chargée avec succès")
    logger.info("  Surveillance  : %s", config["dossier_surveillance"])
    logger.info("  Archives      : %s", config["dossier_archives"])
    logger.info(
        "  Fournisseurs  : %d configurés", len(config["fournisseurs"])
    )

    return config


# ─────────────────────────── Extraction de texte ────────────────────────────────


def extraire_texte(chemin_pdf: Path) -> str:
    """Extrait le texte de toutes les pages d'un PDF avec pdfplumber."""
    texte_complet = ""
    try:
        with pdfplumber.open(chemin_pdf) as pdf:
            for page in pdf.pages:
                texte_page = page.extract_text()
                if texte_page:
                    texte_complet += texte_page + "\n"
    except Exception as e:
        logger.error(
            "Erreur lors de la lecture du PDF '%s' : %s",
            sanitiser_log(chemin_pdf.name),
            e,
        )
        return ""

    if not texte_complet.strip():
        logger.warning(
            "Aucun texte extractible dans '%s' (PDF scanné ou protégé ?)",
            sanitiser_log(chemin_pdf.name),
        )

    return texte_complet


# ─────────────────────────── Identification du fournisseur ──────────────────────


def identifier_fournisseur(texte: str, fournisseurs: dict) -> dict | None:
    """
    Recherche les mots-clés de chaque fournisseur dans le texte extrait.
    Retourne les infos du premier fournisseur trouvé, ou None.

    La recherche se fait en case-insensitive.
    On privilégie les mots-clés les plus longs d'abord pour éviter les faux positifs
    (ex: "free" pourrait matcher dans d'autres contextes).
    """
    texte_lower = texte.lower()

    # Trier les fournisseurs par longueur de leur mot-clé le plus long (desc)
    # pour favoriser les matches les plus spécifiques
    fournisseurs_tries = sorted(
        fournisseurs.items(),
        key=lambda item: max(len(kw) for kw in item[1]["mots_cles"]),
        reverse=True,
    )

    for _cle, infos in fournisseurs_tries:
        for mot_cle in sorted(infos["mots_cles"], key=len, reverse=True):
            if mot_cle.lower() in texte_lower:
                logger.info(
                    "  ✔ Fournisseur identifié : %s (mot-clé : '%s')",
                    infos["nom"],
                    mot_cle,
                )
                return infos

    return None


# ─────────────────────────── Extraction de la date ──────────────────────────────

# Mois français → numéro
MOIS_FR = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
    "avril": "04", "mai": "05", "juin": "06", "juillet": "07",
    "août": "08", "aout": "08", "septembre": "09", "octobre": "10",
    "novembre": "11", "décembre": "12", "decembre": "12",
}

# Patterns de dates courants dans les documents français
PATTERNS_DATE = [
    # "15 avril 2026", "3 mars 2025"
    re.compile(
        r"(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|"
        r"août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})",
        re.IGNORECASE,
    ),
    # "15/04/2026", "03/03/2025"
    re.compile(r"(\d{2})[/\-.](\d{2})[/\-.](\d{4})"),
    # "2026-04-15" (ISO)
    re.compile(r"(\d{4})[/\-.](\d{2})[/\-.](\d{2})"),
]


def extraire_date(texte: str, chemin_pdf: Path) -> tuple[str, str]:
    """
    Tente d'extraire une date du contenu du PDF.
    Retourne (année, mois) sous forme de strings.
    En cas d'échec, utilise la date de modification du fichier.
    """
    for i, pattern in enumerate(PATTERNS_DATE):
        match = pattern.search(texte)
        if match:
            groups = match.groups()

            if i == 0:
                # Format texte : "15 avril 2026"
                mois_texte = groups[1].lower()
                annee = groups[2]
                mois = MOIS_FR.get(mois_texte, "01")
                logger.info("  📅 Date trouvée dans le texte : %s/%s", mois, annee)
                return annee, mois

            elif i == 1:
                # Format JJ/MM/AAAA
                annee = groups[2]
                mois = groups[1]
                logger.info("  📅 Date trouvée dans le texte : %s/%s", mois, annee)
                return annee, mois

            elif i == 2:
                # Format AAAA-MM-JJ (ISO)
                annee = groups[0]
                mois = groups[1]
                logger.info("  📅 Date trouvée dans le texte : %s/%s", mois, annee)
                return annee, mois

    # Fallback : date de modification du fichier
    timestamp = os.path.getmtime(chemin_pdf)
    dt = datetime.fromtimestamp(timestamp)
    logger.info(
        "  📅 Aucune date dans le texte, utilisation de la date du fichier : %s",
        dt.strftime("%m/%Y"),
    )
    return dt.strftime("%Y"), dt.strftime("%m")


# ─────────────────────────── Traitement d'un PDF ───────────────────────────────


def generer_nom_unique(dossier: Path, nom_base: str) -> Path:
    """Génère un nom de fichier unique en ajoutant un suffixe si nécessaire."""
    destination = dossier / nom_base
    if not destination.exists():
        return destination

    # Ajouter un suffixe _2, _3, etc.
    stem = Path(nom_base).stem
    suffix = Path(nom_base).suffix
    compteur = 2
    while True:
        nouveau_nom = f"{stem}_{compteur}{suffix}"
        destination = dossier / nouveau_nom
        if not destination.exists():
            return destination
        compteur += 1


def traiter_pdf(chemin_pdf: Path, config: dict) -> bool:
    """
    Traite un fichier PDF :
    1. Extraction du texte
    2. Identification du fournisseur
    3. Extraction de la date
    4. Renommage et déplacement

    Retourne True si le traitement a réussi, False sinon.
    """
    logger.info("━" * 60)
    logger.info("📄 Nouveau PDF détecté : %s", sanitiser_log(chemin_pdf.name))

    # Vérifier que le fichier existe toujours
    if not chemin_pdf.exists():
        logger.warning("  Le fichier a disparu avant le traitement.")
        return False

    # Vérifier que c'est bien un PDF
    if chemin_pdf.suffix.lower() != ".pdf":
        return False

    # 1. Extraction du texte
    texte = extraire_texte(chemin_pdf)

    # 2. Identification du fournisseur
    fournisseur = identifier_fournisseur(texte, config["fournisseurs"])

    if fournisseur:
        nom_fournisseur = fournisseur["nom"]
        dossier_dest = config["dossier_archives"] / fournisseur.get(
            "dossier", nom_fournisseur
        )
    else:
        nom_fournisseur = "Non_classe"
        dossier_dest = config["dossier_archives"] / "Non_classe"
        logger.warning("  ⚠ Fournisseur non identifié, classé dans 'Non_classe'")

    # 3. Extraction de la date
    annee, mois = extraire_date(texte, chemin_pdf)

    # 4. Construction du nouveau nom
    # Nettoyer le nom du fournisseur pour le nom de fichier
    nom_propre = nom_fournisseur.replace(" ", "_")
    nouveau_nom = f"{annee}-{mois}_{nom_propre}.pdf"

    # 5. Déplacement
    dossier_dest.mkdir(parents=True, exist_ok=True)
    destination = generer_nom_unique(dossier_dest, nouveau_nom)

    try:
        shutil.move(str(chemin_pdf), str(destination))
        logger.info("  ✅ Renommé et déplacé vers : %s", destination)
        return True
    except Exception as e:
        logger.error("  ❌ Erreur lors du déplacement : %s", e)
        return False


# ─────────────────────────── Handler Watchdog ───────────────────────────────────


class GestionnairePDF(FileSystemEventHandler):
    """Gestionnaire d'événements filesystem pour les nouveaux PDF."""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.delai = config.get("delai_traitement_secondes", 3)

    def on_created(self, event):
        """Appelé lorsqu'un nouveau fichier est créé dans le dossier surveillé."""
        if event.is_directory:
            return

        chemin = Path(event.src_path)

        # Ne traiter que les PDF et ignorer les fichiers temporaires
        if (
            chemin.suffix.lower() != ".pdf"
            or chemin.name.startswith(".")
            or chemin.name.endswith((".tmp", ".crdownload", ".part"))
        ):
            return

        logger.info("⏳ Fichier détecté, attente de %d secondes...", self.delai)

        # Attendre que le téléchargement soit terminé
        time.sleep(self.delai)

        # Vérifier la stabilité du fichier (taille ne change plus)
        if not self._fichier_stable(chemin):
            logger.warning("  Le fichier est encore en cours de modification, nouvel essai...")
            time.sleep(self.delai)
            if not self._fichier_stable(chemin):
                logger.error("  Le fichier n'est toujours pas stable, abandon.")
                return

        traiter_pdf(chemin, self.config)

    def _fichier_stable(self, chemin: Path, intervalle: float = 1.0) -> bool:
        """Vérifie que la taille du fichier ne change plus."""
        if not chemin.exists():
            return False
        try:
            taille1 = chemin.stat().st_size
            time.sleep(intervalle)
            taille2 = chemin.stat().st_size
            return taille1 == taille2 and taille1 > 0
        except OSError:
            return False


# ─────────────────────────── Traitement initial ─────────────────────────────────


def traiter_fichiers_existants(config: dict):
    """Traite les PDF déjà présents dans le dossier de surveillance."""
    dossier = config["dossier_surveillance"]
    pdfs = list(dossier.glob("*.pdf"))

    if not pdfs:
        logger.info("Aucun PDF existant à traiter dans le dossier de surveillance.")
        return

    logger.info("📂 %d PDF existant(s) trouvé(s), traitement en cours...", len(pdfs))
    for pdf in pdfs:
        traiter_pdf(pdf, config)


# ─────────────────────────── Automatisation Git ─────────────────────────────────

NOM_PROJET = "Trieur_automatique_pdf"
GITHUB_URL = "https://github.com/ryzuud/Trieur_automatique_pdf-.git"


def executer_commande_git(*args: str) -> tuple[bool, str]:
    """
    Exécute une commande git et retourne (succès, sortie).
    """
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(Path(__file__).parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        sortie = (result.stdout + result.stderr).strip()
        return result.returncode == 0, sortie
    except FileNotFoundError:
        return False, "Git n'est pas installé ou introuvable dans le PATH."
    except subprocess.TimeoutExpired:
        return False, "Timeout : la commande git a pris trop de temps."
    except Exception as e:
        return False, f"Erreur inattendue : {e}"


def git_auto_push():
    """
    Automatisation Git :
    1. Vérifie/initialise le dépôt Git
    2. Vérifie/ajoute le remote origin vers GitHub
    3. git add . → git commit → git push origin main
    """
    logger.info("━" * 60)
    logger.info("🔄 Automatisation Git en cours...")

    dossier_projet = Path(__file__).parent

    # ── 1. Vérifier si un dépôt Git existe, sinon l'initialiser ──
    dossier_git = dossier_projet / ".git"
    if not dossier_git.exists():
        logger.info("  Aucun dépôt Git trouvé, initialisation...")
        ok, msg = executer_commande_git("init")
        if not ok:
            logger.error("  ❌ Échec de git init : %s", msg)
            return False
        logger.info("  ✅ Dépôt Git initialisé.")

        # Créer la branche main par défaut
        executer_commande_git("branch", "-M", "main")
    else:
        logger.info("  ✅ Dépôt Git existant détecté.")

    # ── 2. Vérifier le remote origin ──
    ok, remote_url = executer_commande_git("remote", "get-url", "origin")

    if not ok:
        # Pas de remote origin, on l'ajoute
        logger.info("  Aucun remote 'origin' trouvé, ajout de %s", GITHUB_URL)
        ok, msg = executer_commande_git("remote", "add", "origin", GITHUB_URL)
        if not ok:
            logger.error("  ❌ Échec de l'ajout du remote : %s", msg)
            return False
        logger.info("  ✅ Remote 'origin' ajouté.")
    elif GITHUB_URL not in remote_url and "ryzuud" not in remote_url:
        # Remote existe mais ne pointe pas vers le bon GitHub
        logger.info("  Remote actuel : %s", remote_url.strip())
        logger.info("  Mise à jour vers : %s", GITHUB_URL)
        ok, msg = executer_commande_git("remote", "set-url", "origin", GITHUB_URL)
        if not ok:
            logger.error("  ❌ Échec de la mise à jour du remote : %s", msg)
            return False
        logger.info("  ✅ Remote 'origin' mis à jour.")
    else:
        logger.info("  ✅ Remote 'origin' correctement configuré : %s", remote_url.strip())

    # ── 3. git add . ──
    ok, msg = executer_commande_git("add", ".")
    if not ok:
        logger.error("  ❌ Échec de git add : %s", msg)
        return False
    logger.info("  ✅ Fichiers ajoutés au staging (git add .)")

    # ── 4. git commit ──
    message_commit = f"Mise à jour automatique - {NOM_PROJET}"
    ok, msg = executer_commande_git("commit", "-m", message_commit)
    if not ok:
        if "nothing to commit" in msg:
            logger.info("  ℹ️  Rien à commiter, le dépôt est déjà à jour.")
            return True
        logger.error("  ❌ Échec de git commit : %s", msg)
        return False
    logger.info("  ✅ Commit créé : '%s'", message_commit)

    # ── 5. git push origin main ──
    ok, msg = executer_commande_git("push", "origin", "main")
    if not ok:
        # Tenter un push avec --set-upstream si c'est le premier push
        if "has no upstream" in msg or "set-upstream" in msg:
            logger.info("  Premier push, configuration de l'upstream...")
            ok, msg = executer_commande_git("push", "--set-upstream", "origin", "main")

        if not ok:
            logger.error("  ❌ Échec de git push : %s", msg)
            logger.error("  💡 Vérifiez votre connexion et vos identifiants GitHub.")
            return False

    logger.info("  ✅ Push réussi vers %s", GITHUB_URL)
    logger.info("━" * 60)
    return True


# ─────────────────────────── Point d'entrée ─────────────────────────────────────


def main():
    """Point d'entrée principal du trieur de PDF."""
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              🗂️  TRIEUR AUTOMATIQUE DE PDF                  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Charger la configuration
    config = charger_config()

    # Traiter les PDF déjà présents
    traiter_fichiers_existants(config)

    # Lancer la surveillance
    gestionnaire = GestionnairePDF(config)
    observer = Observer()
    observer.schedule(
        gestionnaire,
        str(config["dossier_surveillance"]),
        recursive=False,
    )
    observer.start()

    logger.info("👁️  Surveillance active sur : %s", config["dossier_surveillance"])
    logger.info("Appuyez sur Ctrl+C pour arrêter.")
    print()

    # Automatisation Git après démarrage réussi
    git_auto_push()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur.")
        observer.stop()

    observer.join()
    logger.info("Programme terminé.")


if __name__ == "__main__":
    main()
