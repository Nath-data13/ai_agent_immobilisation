# Règles spécifiques — LMNP

## Régime fiscal
- Loueur en Meublé Non Professionnel, imposition à l'IR (BIC réel)
- Pas d'Impôt sur les Sociétés : le résultat s'intègre au revenu du foyer fiscal
- L'amortissement est le levier principal de déduction : il permet de réduire
  le résultat BIC, idéalement à zéro
- Une charge passée par erreur à la place d'une immo déduit deux fois
  la même dépense → risque de redressement fiscal

## TVA
- LMNP non assujetti à la TVA (cas général, hors para-hôtelier)
- Aucune récupération de TVA sur les achats
- Le seuil de 500€ s'applique sur le montant TTC
- L'immobilisation est enregistrée pour sa valeur TTC
- Calcul : base_amortissement = montant_ttc (pas de division par 1.20)

## Activité immobilière
- L'immeuble (hors terrain) est le principal actif à immobiliser → compte 2131
- Le terrain n'est JAMAIS amortissable → à exclure systématiquement
- Les travaux d'amélioration augmentant la valeur ou prolongeant la durée de vie
  sont immobilisables (compte 2315)
- Les frais d'acquisition de l'immeuble (notaire, agence) sont immobilisables

## Biens immobilisables typiques en LMNP
- Immeuble (hors terrain) >= 500€ TTC → compte 2131, durée 20 ans
- Mobilier >= 500€ TTC → compte 2184, durée 10 ans
- Électroménager >= 500€ TTC → compte 2184, durée 5 ans
- Aménagement / travaux du logement >= 500€ TTC → compte 2315, durée 10 ans

## Cas particulier entretien vs amélioration
- Entretien courant, réparation simple → charge (compte 6152)
- Remplacement complet d'un composant durable (chaudière, chauffe-eau) :
  - Si prolonge la durée de vie du bien → immobilisation (compte 2315)
  - Si simple remise en état → charge (compte 6152)
- Attention : une facture peut mixer charge et immobilisation
  (ex : main-d'œuvre en charge + pièce de remplacement majeure en immo)

## RÈGLES SPÉCIFIQUES LMNP — Réparation vs Amélioration
- Les charges d'entretien et réparation sont déductibles immédiatement,
  y compris les remplacements à l'identique.
- La méthode des composants s'applique uniquement aux remplacements
  qui améliorent ou prolongent significativement la durée de vie du bien.
- En cas de doute sur la nature du remplacement (identique vs amélioration),
  toujours escalader en human_review avec la question précise à poser au client.
