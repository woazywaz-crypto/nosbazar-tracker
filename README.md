# Suivi des prix NosBazar (EU-Undercity)

Relève automatiquement, toutes les 3 heures, le prix des objets de ton choix sur le bazar de NosTale, grâce à l'API de [nosbazar.com](https://nosbazar.com). L'historique est stocké dans `docs/data/prices.csv` et affiché sur une page avec graphique.

Tout tourne sur GitHub : ton PC n'a pas besoin d'être allumé.

## Contenu

| Fichier | Rôle |
|---|---|
| `items.json` | Serveur et liste des objets à suivre |
| `tracker.py` | Script qui interroge NosBazar et ajoute une ligne par objet au CSV |
| `.github/workflows/track.yml` | Lance le script toutes les 3 h et enregistre le CSV |
| `docs/data/prices.csv` | L'historique des prix |
| `docs/index.html` | Page avec graphique et tableau (GitHub Pages) |

Colonnes du CSV : date (UTC), serveur, vnum, objet, prix mini, moyenne des 10 offres les moins chères, nombre d'offres vues, quantité totale visible sur ces offres.

## Mise en place (5 minutes)

1. **Crée un dépôt** sur GitHub (bouton *New repository*). Public ou privé, au choix.
   - Public : GitHub Actions est illimité et GitHub Pages est gratuit.
   - Privé : 2 000 minutes d'Actions par mois offertes (ce suivi en consomme environ 250), mais GitHub Pages sur dépôt privé demande un abonnement payant.
2. **Envoie les fichiers** : décompresse l'archive puis, sur la page du dépôt, *Add file → Upload files* et glisse tout le contenu du dossier (y compris le dossier `.github`).
   - Si le dossier `.github` ne passe pas par glisser-déposer (dossier caché), crée le fichier à la main : *Add file → Create new file*, nom `.github/workflows/track.yml`, et colle son contenu.
3. **Autorise l'écriture** : *Settings → Actions → General → Workflow permissions* → coche *Read and write permissions* → *Save*.
4. **Teste** : onglet *Actions* → *Relevé des prix NosBazar* → *Run workflow*. Au bout d'une minute, une nouvelle ligne apparaît dans `docs/data/prices.csv`.
5. **Active la page** (facultatif) : *Settings → Pages* → *Source : Deploy from a branch* → branche `main`, dossier `/docs` → *Save*. La page sera disponible à l'adresse `https://<ton-pseudo>.github.io/<nom-du-depot>/`.

Ensuite, c'est automatique : un relevé toutes les 3 heures.

## Ajouter un objet

Il faut son **vnum** (numéro d'objet). Pour le trouver, ouvre dans ton navigateur :

```
https://nosbazar.com/api/items/name-search?q=NOM_EN_ANGLAIS&lang=UK
```

Par exemple `q=Angel's Feather` renvoie `"vnum":2282`. Ajoute ensuite une ligne dans `items.json` (directement sur GitHub avec l'icône crayon) :

```json
{
  "server": 11,
  "server_name": "EU-Undercity",
  "items": [
    { "vnum": 2282, "name": "Plume d'ange" },
    { "vnum": 1234, "name": "Autre objet" }
  ]
}
```

Le nom est libre, c'est celui affiché sur la page. Pour changer de serveur : `1` = EU-Dragonveil, `11` = EU-Undercity.

## Bon à savoir

- **Heures** : GitHub travaille en UTC (le CSV aussi). La page convertit en heure française. Les lancements planifiés peuvent être décalés de quelques minutes à une demi-heure quand GitHub est chargé.
- **Inactivité** : sur un dépôt public, GitHub suspend les tâches planifiées après 60 jours sans activité. Les commits du robot ne comptent pas toujours ; si ça s'arrête, relance-le depuis l'onglet *Actions*.
- **Première page seulement** : le script lit les 10 offres les moins chères, c'est-à-dire ce que montre la première page du bazar. C'est ce qui compte pour suivre le prix, mais la colonne quantité ne représente pas tout le stock en vente.
- **Respect du site** : NosBazar est un projet de fan gratuit qui fait les recherches avec un vrai personnage en jeu. Le script fait une seule requête par objet, avec 5 secondes de pause entre objets. Garde une fréquence raisonnable (pas plus d'une fois par heure) et une liste d'objets courte.
- **Si le site change** son API ou ferme, le workflow échouera (GitHub t'envoie alors un e-mail). L'historique déjà collecté reste dans le CSV.
