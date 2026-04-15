# Catégories comptables — Guide de l'agent

## Principe du système de catégories Dougs
Chaque dépense appartient soit à une catégorie **charge** (compte 6xxxx),
soit à une catégorie **immobilisation** (compte 2xxxx).
Lorsqu'une dépense doit être reclassée, l'agent doit utiliser
la catégorie immobilisation correspondante via le champ `immo_equivalente_id`.

## Table des catégories disponibles

| id | Libellé                                    | Compte PCG | Classe          | → Immo id |
|----|--------------------------------------------|------------|-----------------|-----------|
| 1  | Mobilier                                   | 6064       | charge          | → 11      |
| 11 | Mobilier immobilisé                        | 2184       | immobilisation  | —         |
| 2  | Matériel informatique                      | 6063       | charge          | → 12      |
| 12 | Matériel informatique immobilisé           | 2183       | immobilisation  | —         |
| 3  | Aménagement du local                       | 6135       | charge          | → 13      |
| 13 | Aménagement du local immobilisé            | 2315       | immobilisation  | —         |
| 4  | Immobilisation en cours                    | 2313       | immobilisation  | —         |
| 5  | Outillage et matériel professionnel        | 6061       | charge          | → 15      |
| 15 | Outillage et matériel professionnel immo.  | 2154       | immobilisation  | —         |
| 6  | Logiciels & Internet                       | 6226       | charge          | → 16      |
| 16 | Logiciels & licences acquises              | 2053       | immobilisation  | —         |
| 7  | Fournitures de bureau                      | 6064       | charge          | —         |
| 8  | Entretien et réparations                   | 6152       | charge          | —         |
| 9  | Électroménager                             | 6063       | charge          | → 11      |

## Règle de reclassification
Lors d'une décision `reclassification`, utiliser le `new_category_id`
correspondant à la colonne "→ Immo id" de la catégorie charge actuelle.
Exemple : opération en catégorie 2 (Matériel informatique) → new_category_id = 12

## Quand utiliser "Immobilisation en cours" (id: 4)
- Développement informatique livré partiellement ou projet non finalisé
- Travaux en cours sur un immeuble non encore mis en service
- Ne jamais créer de dotation d'amortissement pour cette catégorie

## Catégories sans équivalent immobilisation (jamais reclassables)
- id: 7 — Fournitures de bureau : consommables, toujours charge
- id: 8 — Entretien et réparations : maintenance courante, toujours charge
  (sauf remplacement complet d'un composant → arbitrage human_review)

## Note sur l'Électroménager (id: 9)
- En charge : compte 6063
- En immobilisation : reclasser vers id 11 (Mobilier immobilisé, compte 2184)
- Durée d'amortissement : 5 ans (différente du mobilier standard à 10 ans)
  → préciser "électroménager" dans le champ `reasoning` pour justifier la durée
