# Règles spécifiques — SARL

## Régime fiscal
- Soumise à l'Impôt sur les Sociétés (IS)
- Une charge passée par erreur à la place d'une immo
  réduit artificiellement le bénéfice → risque de redressement fiscal

## TVA
- SARL assujettie à la TVA : récupère la TVA sur achats
  (charges ET immobilisations)
- Le seuil de 500€ s'applique sur le montant HT
- L'immobilisation est enregistrée pour sa valeur HT
- Calcul : montant_ht = montant_ttc / 1.20

## Activité non immobilière
- Pas de terrain, pas d'immeuble à immobiliser
- Les aménagements de bureau restent immobilisables (compte 2315)
- Exclure les catégories : fonds de commerce, terrains, constructions

## Biens immobilisables typiques en SARL de conseil
- Mobilier de bureau >= 500€ HT → compte 2184
- Matériel informatique >= 500€ HT → compte 2183
- Aménagement du local >= 500€ HT → compte 2315
- Logiciels acquis >= 500€ HT, usage > 1 an → compte 2053
- Développement informatique interne durable → compte 2053

## Cas particulier logiciels et développements IT
- Abonnement SaaS annuel → toujours charge (compte 6226)
- Logiciel acquis sur étagère usage > 1 an >= 500€ HT → immo (compte 2053)
- Développement sur commande par prestataire externe :
  - La capitalisation exige la vérification des critères PCG 311-3 :
    faisabilité technique, intention d'utilisation durable, ressources disponibles,
    coûts identifiables et mesurables
  - Ces critères ne sont PAS vérifiables sur une facture seule
  - → toujours escalader en human_review avec note "split possible si critères PCG 311-3 confirmés"
  - Phase analyse/conception → charge (compte 6226)
  - Phase développement livré et fonctionnel → immo possible (compte 2053) si critères confirmés
  - Projet abandonné ou en cours → charge ou immo en cours (compte 232)
