# 🗂️ Trieur Automatique de PDF

Script Python qui surveille votre dossier **Téléchargements** et classe automatiquement vos documents PDF.

## ✨ Fonctionnalités

- **Surveillance en temps réel** du dossier Téléchargements
- **Extraction de texte** des PDF pour identifier l'expéditeur
- **Renommage automatique** au format `AAAA-MM_Fournisseur.pdf`
- **Classement dans des sous-dossiers** par fournisseur
- **Traitement des PDF existants** au lancement
- **Gestion des conflits** de noms (suffixe `_2`, `_3`, etc.)

## 📋 Fournisseurs pré-configurés

| Fournisseur | Exemples de mots-clés |
|---|---|
| EDF | edf, électricité de france, enedis |
| Engie | engie, gaz de france, grdf |
| Free | free, free mobile, freebox, iliad |
| Orange | orange, sosh |
| SFR | sfr, altice, red by sfr |
| Bouygues Telecom | bouygues telecom, b&you, bbox |
| Impôts | dgfip, trésor public, avis d'imposition |
| Assurance Maladie | ameli, cpam, sécurité sociale |
| CAF | caf, allocations familiales |
| Banque | relevé de compte, crédit agricole, bnp paribas, ... |
| Amazon | amazon, amazon.fr |
| Eau | veolia eau, suez eau |

## 🚀 Installation

### 1. Installer Python

Assurez-vous d'avoir **Python 3.10+** installé sur votre machine.

### 2. Installer les dépendances

```bash
cd Trieur_automatique_pdf
pip install -r requirements.txt
```

### 3. Configurer (optionnel)

Éditez `config.json` pour personnaliser :

- **`dossier_surveillance`** : le dossier à surveiller (par défaut `~/Downloads`)
- **`dossier_archives`** : le dossier de destination (par défaut `~/Documents/Archives_PDF`)
- **`fournisseurs`** : ajoutez vos propres fournisseurs avec leurs mots-clés

### 4. Lancer le script

```bash
python trieur_pdf.py
```

Le script va :
1. Traiter les PDF déjà présents dans le dossier Téléchargements
2. Rester actif et surveiller le dossier en permanence
3. Pour arrêter : appuyez sur `Ctrl+C`

## 📁 Structure des archives

```
Archives_PDF/
├── EDF/
│   ├── 2026-01_EDF.pdf
│   └── 2026-04_EDF.pdf
├── Free/
│   └── 2026-03_Free.pdf
├── Impots/
│   └── 2025-09_Impots.pdf
├── Banque/
│   └── 2026-04_Banque.pdf
└── Non_classe/
    └── 2026-04_Non_classe.pdf
```

## ➕ Ajouter un fournisseur

Éditez `config.json` et ajoutez une entrée dans `fournisseurs` :

```json
"Mon_Fournisseur": {
    "nom": "Mon Fournisseur",
    "mots_cles": ["mot-clé 1", "mot-clé 2", "identifiant unique"],
    "dossier": "Mon_Fournisseur"
}
```

> **Astuce** : Ouvrez un PDF du fournisseur en question et cherchez des mots ou phrases
> uniques (nom de société, numéro SIRET, formule type) pour les utiliser comme mots-clés.

## 📝 Logs

Le script génère un fichier `trieur_pdf.log` dans son dossier pour garder un historique
de tous les fichiers traités.

## ⚠️ Limitations

- Les **PDF scannés** (images) ne contiennent pas de texte extractible et seront classés dans `Non_classe`.
  Pour les traiter, il faudrait ajouter un OCR (ex: Tesseract).
- Les **PDF protégés par mot de passe** ne peuvent pas être lus.
