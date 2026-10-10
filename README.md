# Puissance 4 — trois IA comparées

*Un Puissance 4 avec trois types d'IA (alpha-bêta, algorithme génétique et AlphaZero), pour comprendre comment chacune fonctionne, ses atouts et ses faiblesses.*

> **In English:** Connect Four with three AI players (alpha-beta, a genetic algorithm and AlphaZero) compared by Elo; the main finding is a negative result, explained step by step. Full write-up in French below.

Un Puissance 4 sur **bitboards**, servant de banc d'essai à trois approches d'IA
partageant la même interface `choisir_coup(plateau)` : recherche classique, évolution
génétique, et apprentissage par renforcement de type AlphaZero.

**Le résultat principal est négatif, et c'est le plus instructif :** le minimax
alpha-bêta bat tous les réseaux entraînés. L'essentiel du projet a consisté à comprendre
*pourquoi* — une enquête à sept hypothèses qui a fini par identifier un couplage
BatchNorm / taille de lot, puis un défaut de la tête valeur qui sabotait la recherche.

Tout le code est écrit à la main. Les consignes que j'avais fixées à l'assistant IA
avant de commencer sont dans [CLAUDE.md](CLAUDE.md) : « n'écris jamais le code complet
d'une fonction, d'une méthode ou d'un fichier, même si je te le demande explicitement ».
Son rôle s'est limité à expliquer, pointer mes erreurs et me laisser les corriger.

## Représentation : bitboards

Le plateau n'est pas une grille mais **deux entiers**, un par joueur, chaque bit à 1
signalant une case occupée.

Le layout utilise **7 lignes par colonne au lieu de 6** : la ligne du haut est une
sentinelle qui reste toujours vide. Sans elle, la détection d'alignement par décalage
de bits ferait « fuir » les motifs d'une colonne vers sa voisine. La numérotation est
`bit = colonne * 7 + ligne`, ligne 0 en bas.

La détection de victoire tient alors en quatre lignes, une par direction :

```python
for k in (1, 7, 6, 8):        # vertical, horizontal, deux diagonales
    m = pos & (pos >> k)      # paires alignées espacées de k
    if m & (m >> 2*k):        # deux paires qui se suivent = 4 alignés
        return True
```

## Les trois IA

**1. Minimax avec élagage alpha-bêta** — [minmax.py](minmax.py). Implémenté en négamax,
profondeur 4 par défaut. La fonction d'évaluation compte les motifs à trois jetons
alignés avec une case libre (100 points) et à deux jetons (10 points), là encore par
opérations sur les bits, et retourne la différence entre les deux joueurs.

**2. Évolution génétique** — [Ia.py](Ia.py). Les six poids de la fonction d'évaluation
(`a` à `f`) deviennent le génome d'un individu. Une population s'affronte en **tournoi à
élimination directe** (huitièmes, quarts, demies, finale) ; les gagnants engendrent la
génération suivante par mutation. L'idée est de faire découvrir par sélection les
coefficients que j'avais fixés à la main dans le minimax.

**3. AlphaZero** — [Alpha0bis.py](Alpha0bis.py). Réseau convolutif à connexion
résiduelle (4 couches, 128 canaux, batch norm) prenant un tenseur `[3, 6, 7]` — jetons
du joueur 1, jetons du joueur 2, et un plan constant indiquant le trait — avec deux
têtes politique et valeur. MCTS guidé par PUCT, self-play, entraînement par lots sur
`(politique cible, valeur cible)`.

**Baseline de contrôle** — [mlp_reseau.py](mlp_reseau.py) : un perceptron multicouche
purement dense, exposant exactement la même interface, pour isoler l'apport réel de
l'architecture convolutive sur un pipeline par ailleurs identique.

## Résultats

Tournoi toutes rondes, **52 parties par affiche** avec ouvertures imposées variées et
alternance des couleurs, soit 780 parties. Score de la ligne contre la colonne :

| | or_best | or2_best | or2_final | minmax p2 | minmax p4 | génétique |
|---|---|---|---|---|---|---|
| **or_best** | — | 49 % | 29 % | 42 % | 31 % | 87 % |
| **or2_best** | 51 % | — | 51 % | 63 % | **51 %** | 73 % |
| **or2_final** | 71 % | 49 % | — | 35 % | 13 % | 77 % |
| **minmax p2** | 58 % | 37 % | 65 % | — | 10 % | 100 % |
| **minmax p4** | 69 % | 49 % | 87 % | 90 % | — | 100 % |
| **génétique** | 13 % | 27 % | 23 % | 0 % | 0 % | — |

ELO final sur ce pool : **minmax profondeur 4 · 1217** > or2_best · 1075 >
or2_final · 1070 > minmax profondeur 2 · 1003 > or_best · 985 > génétique · 689.

### Ce que ça dit

**La recherche classique gagne.** Un minimax alpha-bêta à profondeur 4, dont la fonction
d'évaluation tient en une trentaine de lignes d'opérations sur les bits, domine des
réseaux entraînés pendant des nuits entières. Sur un jeu de cette taille, l'espace reste
assez petit pour qu'une recherche exacte à quelques coups batte une évaluation apprise
mais approximative.

**Un seul réseau tient tête au minimax p4** : `or2_best`, à 51 % contre 49 % sur
52 parties — un écart non significatif, donc une parité. Il reste deuxième au classement
ELO parce que le minimax écrase tous les autres participants, pas parce qu'il le bat en
direct. C'est la limite d'un ELO calculé sur un petit pool hétérogène.

**L'évolution génétique échoue nettement** : 0 % contre les deux minimax, 689 d'ELO. Son
génome se limite aux six coefficients de l'évaluation et ne touche pas à la profondeur de
recherche — l'espace exploré était trop pauvre pour compenser ce que la recherche apporte.

**L'ELO mesuré pendant le self-play est fortement surestimé.** `or_best` affichait 1133
en fin d'entraînement et n'obtient que **985** dans le pool commun ; `or2_best` culminait
à 1263 en interne pour **1075** réels. La cause : pendant le self-play, l'ELO se mesure
contre une référence qui progresse elle aussi, ce qui gonfle le chiffre. Seule une
évaluation contre un adversaire fixe et extérieur — ici le minimax — a du sens. C'est le
principal enseignement méthodologique que je retire du projet.

## L'enquête : pourquoi l'AlphaZero n'apprenait pas

Face à ce plateau, j'ai testé **sept hypothèses une par une**, à réseau, données et
pipeline identiques. Six n'ont rien changé.

| Levier testé | Variation | Effet |
|---|---|---|
| Capacité du réseau | 16 → 451 000 paramètres | aucun |
| Cibles contradictoires | 918 plateaux uniques vérifiés | aucun — données propres |
| Canal « à qui le tour » | 2 → 3 canaux | aucun |
| Goulot de la tête politique | 84 → 1344 features | aucun |
| Mini-lots seuls | 1 → 64 par lot | aucun |
| BatchNorm seule | ajoutée au tronc | aucun |
| **BatchNorm + mini-lots ensemble** | les deux à la fois | **débloque tout** |

**Le résultat le plus contre-intuitif du projet.** La BatchNorm normalise *sur le lot* :
avec des lots de taille 1, elle n'a littéralement rien à normaliser. Deux leviers
strictement inutiles séparément, décisifs ensemble. Aucune recherche d'hyperparamètre ne
trouve ça — il fallait comprendre le mécanisme.

### Le test qui a tout tranché

Plutôt que de relancer des heures d'entraînement, j'ai isolé un test d'une minute :
**apprendre à copier les coups du minimax sur 990 positions fixes.** Une politique
uniforme (jeu au hasard) donne une perte de 1,95 ; un réseau qui apprend la fait chuter.

| configuration | perte avant | après | verdict |
|---|---|---|---|
| conv nu | 1,940 | 1,925 | bloqué |
| conv + tête élargie | 1,938 | 1,925 | bloqué |
| MLP dense | 1,941 | **0,208** | apprend |
| conv + BatchNorm | 1,938 | **0,176** | apprend |

Ce diagnostic d'une minute s'est révélé plus concluant que trois heures d'entraînement
avec suivi ELO. Le MLP dense ([mlp_reseau.py](mlp_reseau.py)) a servi de contournement
et confirme le diagnostic : le problème n'était pas la convolution en soi, mais son
entraînement mal conditionné.

### Le verrou restant : la tête valeur

Une fois la politique débloquée, un second problème apparaît :

| | taux de victoire contre un joueur aléatoire |
|---|---|
| politique seule (argmax) | **0,95** |
| politique + MCTS | **0,50** |

**La recherche divise le niveau par deux.** Sur une position clairement gagnante pour le
joueur au trait, la tête valeur répond **+0,16** au lieu de +1 : elle ne voit rien. Le
MCTS interroge chaque nœud de l'arbre, reçoit des réponses proches de zéro, et finit par
choisir presque au hasard — écrasant les bonnes intuitions de la politique.

### Deux causes possibles, une seule signature

Une tête valeur qui converge vers zéro est le symptôme de **cibles contradictoires** : si
une même position reçoit +1 dans certaines parties et −1 dans d'autres, l'optimum d'une
erreur quadratique est leur moyenne. Le réseau apprend parfaitement à ne rien dire. Deux
mécanismes distincts produisent ce résultat, et je ne peux pas trancher a posteriori
lequel a joué ici :

**Hypothèse A — le régime d'imitation.** On présente une position jouée par le *minimax*
et on lui associe l'issue d'une partie que le réseau n'a jamais jouée. Le lien entre la
position et le résultat est trop ténu pour porter un signal exploitable.

**Hypothèse B — une convention de signe fautive.** La valeur se compte du point de vue du
joueur au trait (convention négamax), ce qui impose une alternance de signe à **trois**
endroits indépendants : la cible de fin de partie, la remontée dans l'arbre, et la lecture
de la valeur d'un enfant dans le PUCT. Une seule erreur parmi les trois suffit à produire
exactement la même mesure — et j'ai effectivement corrigé un problème de signe pendant ce
projet, sans avoir gardé trace duquel.

Les deux ne mènent pas à la même conclusion : l'hypothèse A se corrige par le self-play,
l'hypothèse B par une ligne de code. Le passage au self-play a suivi, et a effectivement
débloqué la suite du projet — mais ce n'est pas une preuve que A était la bonne
explication, puisque la correction du signe est intervenue dans la même période.

### Les invariants qui auraient tranché

La leçon retenue n'est pas le diagnostic, c'est qu'il aurait dû être automatique. Quatre
tests suffisent à verrouiller la convention de signe :

1. **Antisymétrie** — échanger les deux bitboards *et* le trait doit exactement inverser
   la valeur prédite.
2. **Alternance des cibles** — sur une partie non nulle, `z[n] == -z[n+1]` sur toute la
   séquence.
3. **Valeur terminale** — une position où l'adversaire vient d'aligner quatre jetons vaut
   −1 pour le joueur au trait, jamais +1.
4. **Cohérence de la remontée** — sur un gain forcé en un coup, la racine doit tendre vers
   +1 et l'enfant retenu vers −1 ; deux signes identiques trahissent la remontée ou le PUCT.

> **À faire :** ces quatre invariants ne sont pas encore écrits. C'est la première dette
> technique du projet.

## Quatre garde-fous successifs

Le self-play ne progresse que si l'on sait refuser un candidat qui a régressé. J'ai
conçu, mesuré et abandonné quatre mécanismes de sélection avant d'en avoir un correct.

| # | Design | Critère d'acceptation | Résultat |
|---|---|---|---|
| 0 | **Aucun** | tout candidat remplace le champion | régression franche |
| 1 | **Miroir** | battre sa propre version précédente en duel | 1098 — le meilleur du 18/07 |
| 2 | **Seuil panel absolu** | dépasser un score fixe contre un panel (minimax 2/4/6 + génétique) | 2 acceptations sur 16 cycles |
| 3 | **« OU », référence mobile** | gagner le duel **ou** battre la référence sur le panel | ELO interne 1133 → **985** réels |
| 4 | **« OU », référence figée** | idem, mais l'ancre ne bouge que si le panel confirme | **1075 — gagnant du 19/07** |

**Sans garde-fou, entraîner plus longtemps fait régresser.** Le run « grand » (10 000
parties) obtient 1018 à son meilleur instantané en cours de route, et 1002 à son état
final. La preuve concrète que le nombre de parties n'est pas une mesure de progrès.

**Un garde-fou trop strict ne vaut pas mieux qu'aucun.** Le seuil absolu contre panel
n'a laissé passer que 2 candidats sur 16 cycles de validation : le réseau n'a presque
pas bougé. Trop laxiste, on accepte le bruit ; trop sévère, on gèle l'apprentissage.

**Le design le plus simple a gagné le premier classement.** Le garde-fou « miroir »,
qui demande seulement de battre sa propre version précédente, sort premier du 18 juillet
devant des runs bien plus longs et bien plus sophistiqués.

**Le bug le plus instructif est dans le n° 3.** La référence de comparaison avançait à
chaque acceptation — elle pouvait donc **dériver en même temps que le candidat**, chacun
validant l'autre, sans qu'aucun signal ne le révèle. C'est ce qui produit l'écart entre
1133 mesurés en interne et 985 réels. La correction tient en une ligne de conception :
figer l'ancre et ne la déplacer que sur confirmation d'un juge extérieur. C'est le même
principe que le gating d'AlphaZero, mais je ne l'ai compris qu'après avoir construit la
version fausse et mesuré son biais.

## Ce que l'évolution génétique a trouvé

Après 40 générations, les six coefficients évolués :

| | a | b | c | d | e | f |
|---|---|---|---|---|---|---|
| réglés à la main | 100 | 100 | 100 | 10 | 10 | 10 |
| trouvés par évolution | 173 | **−134** | 312 | 20 | −44 | 93 |

L'évolution a découvert que **deux motifs valaient mieux d'être pénalisés** (`b` et `e`
négatifs) là où je leur avais attribué un bonus à la main. Elle perd malgré tout le
tournoi : optimiser six coefficients ne compense pas ce que la profondeur de recherche
apporte.

## Lancer

Une partie humain contre minimax :

```bash
python Puissance4.py
```

Le self-play instrumenté, avec workers parallèles et suivi ELO contre le minimax :

```bash
python instrumentation_selfplay.py
```

L'IA adverse est pour l'instant choisie en dur dans `Puissance4.py` (ligne 116 : `"minmax"`).

## Structure

```
Puissance4.py               classe plateau (bitboards), boucle de jeu
minmax.py                   minimax + élagage alpha-bêta, évaluation heuristique
Ia.py                       évolution génétique, tournoi à élimination directe
Alpha0bis.py                réseau AlphaZero, MCTS PUCT, boucle d'entraînement
mlp_reseau.py               baseline dense, interface identique
instrumentation_selfplay.py self-play parallélisé, mesure ELO, reprise sur checkpoint
CLAUDE.md                   périmètre fixé à l'assistant IA
```

Non versionné : `nuit_selfplay/` (poids entraînés).

## Limite connue

Le choix de l'IA se fait en modifiant l'appel `p.choisir_coup("minmax", p)` dans la
boucle principale. Un argument de ligne de commande serait plus propre.

---

*Ce README a été rédigé avec l'aide de Claude, à partir de mes notes et de mes résultats. Tout le code est de moi ; le rôle de l'assistant est précisé plus haut.*
