"""
=====================================================================
INSTRUMENTATION D'ENTRAINEMENT — self-play (boucle AlphaZero)
=====================================================================
Ceci N'EST PAS un fichier du projet de base (comme Puissance4.py,
minmax.py, Ia.py, Alpha0bis.py) : c'est un script d'ORCHESTRATION que
Claude a ecrit pour piloter l'entrainement du reseau defini dans
Alpha0bis.py. Il importe les briques (noeud, perte_par_lots, etc.)
depuis une COPIE FIGEE de Alpha0bis.py (ici : alpha0_sp.py) plutot que
le fichier "vivant", pour qu'un run en cours ne casse pas si le fichier
original continue d'etre modifie pendant l'entrainement.

C'est une copie (le vrai run tourne dans ~/Puissance4/nuit_selfplay/) :
elle sert a montrer a quoi ressemble le code qui pilote l'entrainement.

PRINCIPE DU SELF-PLAY (rappel) :
  Le reseau joue des parties CONTRE LUI-MEME avec son propre MCTS.
  - la cible POLITIQUE = le nombre de visites MCTS de chaque colonne
    (une recherche "affinee" par rapport a la politique brute)
  - la cible VALEUR = qui a gagne CETTE partie precise
  C'est different de l'imitation (ou la cible venait du minimax) :
  ici le signal de valeur est coherent car il vient d'une partie que
  le reseau a reellement jouee.
=====================================================================
"""
import sys, time, json, os, random
import multiprocessing as mp

sys.path.insert(0, '/home/ethanbravard/Puissance4')
sys.path.insert(0, '/home/ethanbravard/Puissance4/nuit_selfplay')

# Dossier ou tout est sauvegarde. Volontairement DANS le projet
# (pas dans /tmp) : /tmp peut etre purge par le systeme a tout moment,
# ce qui est deja arrive deux fois pendant ce projet et a fait perdre
# des runs entiers.
SCRATCH = '/home/ethanbravard/Puissance4/nuit_selfplay/'
POIDS_WORKER = SCRATCH + 'poids_sp_worker.pt'   # poids partages avec les ouvriers

SIMS = 100                  # simulations MCTS par coup joue
COUPS_ALEATOIRES = 10       # nb de coups "temperature" en debut de partie (diversite)
CANNEAUX = 128               # largeur du reseau (doit matcher Alpha0bis.py)


# =====================================================================
# PARTIE 1 : L'OUVRIER — tourne dans un processus separe (un par coeur)
# =====================================================================
# multiprocessing.Pool lance cette fonction plusieurs fois EN PARALLELE,
# chacune dans son propre processus Python (donc sur son propre coeur).
# Chaque ouvrier joue N parties completes de bout en bout, tout seul.

def worker_selfplay(args):
    seed, n_parties = args

    # Chaque ouvrier reimporte torch/le reseau depuis zero : c'est le
    # cout du multiprocessing (pas de memoire partagee), mais c'est ce
    # qui permet un vrai parallelisme en Python (le GIL empeche les
    # threads de calculer en parallele, les process non).
    import torch
    torch.set_num_threads(1)          # 1 thread/process : 12 process sur
                                       # 12 coeurs > 12 process qui se
                                       # battent chacun pour plusieurs coeurs
    import Puissance4 as p
    from alpha0_sp import ReseauAlphaZero, noeud
    random.seed(seed); torch.manual_seed(seed)   # graine differente par ouvrier -> parties differentes

    reseau = ReseauAlphaZero(CANNEAUX)
    reseau.load_state_dict(torch.load(POIDS_WORKER, map_location='cpu'))
    reseau.eval()                     # IMPORTANT : la BatchNorm doit etre
                                       # en mode inference ici (pas de lot
                                       # a normaliser sur une seule partie)

    # --- FILET DE SECURITE : PUCT peut echouer a choisir un coup dans de
    # rares cas numeriques (scores tous egaux/NaN). On evite que ca fasse
    # planter tout le processus en repartant sur un coup legal au hasard.
    _orig = noeud.PUCT
    def _puct_ok(self, plateau, res):
        s, c = _orig(self, plateau, res)
        if c is None:
            c = random.choice(plateau.coup_legaux())
        return s, c
    noeud.PUCT = _puct_ok

    def copie(pl):
        q = p.plateau(); q.etatj1 = pl.etatj1; q.etatj2 = pl.etatj2; q.tour = pl.tour; return q

    sorties = []
    for _ in range(n_parties):
        racine = noeud(p.plateau(), 0)
        positions = []
        coups = 0
        while racine.etat.position_final() is None and coups < 42:
            racine.recherche(racine.etat, reseau, SIMS)

            # nombre de visites de chaque colonne apres la recherche MCTS
            # -> c'est CA la cible politique du self-play (pas juste "le
            # meilleur coup" comme en imitation, mais toute la distribution)
            visites = [0] * 7
            for cp, enf in racine.enfants.items():
                visites[cp[0]] = enf.visites
            if sum(visites) == 0:
                break

            joueur = 1 if racine.etat.tour % 2 == 1 else 2
            positions.append((racine.etat.etatj1, racine.etat.etatj2, racine.etat.tour, list(visites), joueur))

            # --- DIVERSITE : sans ca, le reseau jouerait TOUJOURS le meme
            # coup dans la meme position -> toutes les parties de self-play
            # seraient identiques, et le reseau n'apprendrait qu'une seule
            # ligne de jeu au lieu d'explorer.
            # Sur les COUPS_ALEATOIRES premiers coups, on TIRE le coup au
            # hasard, avec une probabilite proportionnelle a ses visites
            # (un coup tres visite a plus de chances d'etre choisi, mais
            # ce n'est jamais garanti). Apres, on prend le meilleur.
            if coups < COUPS_ALEATOIRES:
                total = sum(visites)
                r = random.random() * total
                cum = 0
                col = 0
                for c7 in range(7):
                    cum += visites[c7]
                    if r <= cum and visites[c7] > 0:
                        col = c7
                        break
                choix = None
                for cp in racine.enfants:
                    if cp[0] == col:
                        choix = cp
                        break
                if choix is None:
                    choix = racine.meilleur_coup_final()
            else:
                choix = racine.meilleur_coup_final()

            racine = racine.enfants[tuple(choix)]
            coups += 1

        res = racine.etat.position_final()
        sorties.append((positions, res))
    return sorties


# =====================================================================
# PARTIE 2 : LE PRINCIPAL — orchestre les ouvriers, entraine, evalue
# =====================================================================
if __name__ == "__main__":
    # Python 3.14 utilise "forkserver" par defaut, qui pose des soucis
    # avec ce script ; "fork" est plus simple et suffisant ici (tout
    # tourne sur CPU, pas de contexte CUDA a dupliquer entre process).
    mp.set_start_method('fork', force=True)

    import torch
    import Puissance4 as p
    import minmax as mm
    from alpha0_sp import ReseauAlphaZero, noeud, Alpha0bis, perte_par_lots, entrainer_par_lots

    print("=== SELF-PLAY conv+BN+residu ===", flush=True)

    N_WORKERS = 12               # nb de coeurs/ouvriers en parallele
    PARTIES_PAR_TOUR = 12        # 1 partie par ouvrier par tour
    TAILLE_LOT = 64               # taille des lots pour entrainer_par_lots (BatchNorm)
    EVAL_TOUS_LES = 4            # frequence des mesures ELO (en "tours")
    MAX_PARTIES = 1000

    # Roster de reference pour estimer l'ELO du reseau en cours.
    # Ce sont des ancres FIXES (leur propre ELO n'est jamais recalcule
    # ici) : minmax est independant du reseau, donc c'est un repere stable.
    ELO_REFERENCE = {"minmax_prof2": 1000.0, "minmax_prof4": 1104.4}

    # --- Fichiers de sauvegarde (tous dans SCRATCH, un dossier durable) ---
    PROGRESS = SCRATCH + 'sp_progress.json'      # compteurs (reprise apres coupure)
    ELO_JSON = SCRATCH + 'sp_elo.json'           # historique complet (pour tracer la courbe)
    POIDS_PARTIEL = SCRATCH + 'poids_sp_partiel.pt'   # reseau COURANT, ecrase a chaque eval
    POIDS_BEST = SCRATCH + 'poids_sp_best.pt'         # meilleur ELO JAMAIS atteint, jamais regresse

    # meme filet de securite PUCT que dans l'ouvrier (le processus
    # principal joue aussi des matchs d'evaluation contre minimax)
    _orig = noeud.PUCT
    def _puct_ok(self, plateau, res):
        s, c = _orig(self, plateau, res)
        if c is None:
            c = random.choice(plateau.coup_legaux())
        return s, c
    noeud.PUCT = _puct_ok

    def plateau_de(e1, e2, t):
        q = p.plateau(); q.etatj1 = e1; q.etatj2 = e2; q.tour = t; return q

    def copie(pl):
        q = p.plateau(); q.etatj1 = pl.etatj1; q.etatj2 = pl.etatj2; q.tour = pl.tour; return q

    def valeur_pour(j, res):
        # convention "point de vue du joueur au trait" (negamax) :
        # le meme res peut valoir +1 ou -1 selon qui regarde.
        if res == "match nul" or res is None:
            return 0
        return 1 if j == (1 if res == "victoire Joueur 1" else 2) else -1

    def coup_mm(pl, prof):
        b = mm.minmax(); b.plateau_actuel = pl; b.meilleur_coup(prof); c = b.coup
        leg = pl.coup_legaux()
        # le minimax peut renvoyer un coup invalide sur un cas limite (ligne None)
        if c is None or c[1] is None or list(c) not in [list(x) for x in leg]:
            c = random.choice(leg)
        return list(c)

    def coup_a0(pl, reseau, sims):
        r = noeud(copie(pl), 0)
        r.recherche(r.etat, reseau, sims)
        return list(r.meilleur_coup_final())

    def match_vs_mm(reseau, prof, commence):
        pl = p.plateau(); c = 0
        while pl.position_final() is None and c < 42:
            au_trait = (pl.tour % 2 == 1) == commence
            piece = coup_a0(pl, reseau, SIMS) if au_trait else coup_mm(pl, prof)
            pl.tour_joueur(piece); pl.avancer_le_tour(); c += 1
        j = 1 if commence else 2
        r = pl.position_final()
        return 0.5 if r == "match nul" else (1.0 if valeur_pour(j, r) == 1 else 0.0)

    def evaluer_elo(reseau, elo, b):
        # formule ELO standard : le reseau joue une fois contre chaque
        # ancre, en alternant qui commence pour ne pas biaiser
        K = 32
        for i, (nom, ea) in enumerate(ELO_REFERENCE.items()):
            prof = int(nom.split("prof")[1])
            s = match_vs_mm(reseau, prof, (b + i) % 2 == 0)
            att = 1 / (1 + 10 ** ((ea - elo) / 400))
            elo += K * (s - att)
        return elo

    def a_nan(r):
        return any(torch.isnan(x).any() or torch.isinf(x).any() for x in r.parameters())

    def charger(f, d):
        return json.load(open(f)) if os.path.exists(f) else d

    # --- REPRISE : si une progression existe deja, on repart de la ---
    prog = charger(PROGRESS, {"parties": 0, "tour": 0, "elo": 1000.0, "best_elo": -1})
    elo_hist = charger(ELO_JSON, {"historique": []})["historique"]

    reseau = ReseauAlphaZero(CANNEAUX)
    if os.path.exists(POIDS_PARTIEL) and prog["parties"] > 0:
        reseau.load_state_dict(torch.load(POIDS_PARTIEL, map_location='cpu'))
        print(f"[reprise] parties={prog['parties']}", flush=True)
    else:
        # premier lancement : on part d'un reseau deja entraine par
        # imitation (politique deja bonne), pas d'un reseau vierge
        depart = SCRATCH + 'poids_valeur_large.pt'
        if os.path.exists(depart):
            reseau.load_state_dict(torch.load(depart, map_location='cpu'))
            print("[depart] reprise du reseau imitation", flush=True)
        else:
            print("[depart] reseau neuf", flush=True)

    reseau.eval()
    opt = torch.optim.Adam(reseau.parameters(), lr=0.001)

    # --- FILET ANTI-NaN : on garde une copie des poids valides en
    # memoire, pour pouvoir y revenir si un entrainement produit des
    # NaN (division par zero, log(0), etc.)
    etat_ok = {k: v.clone() for k, v in reseau.state_dict().items()}

    t0 = time.time()
    depart_parties = prog["parties"]     # pour calculer le temps restant estime
    pool = mp.Pool(N_WORKERS)            # le pool d'ouvriers, cree UNE fois
    graine = prog["parties"] * 7 + 1

    def sauver():
        json.dump(prog, open(PROGRESS, 'w'), indent=2)
        json.dump({"historique": elo_hist}, open(ELO_JSON, 'w'), indent=2)

    # ===================== LA BOUCLE PRINCIPALE =====================
    while prog["parties"] < MAX_PARTIES:

        # 1) on ecrit les poids courants sur disque : c'est ainsi que les
        #    ouvriers (des process SEPARES) recuperent le reseau a jour
        torch.save(reseau.state_dict(), POIDS_WORKER)

        # 2) on lance les N_WORKERS ouvriers EN PARALLELE (pool.map bloque
        #    jusqu'a ce que TOUS aient fini)
        args = [(graine + i, 1) for i in range(N_WORKERS)]
        graine += N_WORKERS
        lots = pool.map(worker_selfplay, args)

        # 3) on aplati toutes les positions de toutes les parties de tous
        #    les ouvriers en une seule liste de donnees d'entrainement
        donnees = []
        for sorties in lots:
            for positions, res in sorties:
                for e1, e2, tour, visites, j in positions:
                    donnees.append([plateau_de(e1, e2, tour), [float(v) for v in visites], valeur_pour(j, res)])
                prog["parties"] += 1
        prog["tour"] += 1
        if not donnees:
            continue

        # 4) entrainement par lots (BatchNorm a besoin de vrais lots, pas
        #    d'exemples un par un -> c'est le levier qui a debloque tout
        #    l'entrainement, voir Alpha0bis.py / perte_par_lots)
        reseau.train()
        entrainer_par_lots(reseau, donnees, opt, TAILLE_LOT)
        reseau.eval()

        # --- FILET ANTI-NaN ---
        if a_nan(reseau):
            print("[NaN] retour a l'etat valide precedent", flush=True)
            reseau.load_state_dict(etat_ok)
            opt = torch.optim.Adam(reseau.parameters(), lr=0.001)
            continue
        etat_ok = {k: v.clone() for k, v in reseau.state_dict().items()}

        # 5) evaluation periodique (pas a chaque tour : ca coute cher en
        #    temps de calcul de jouer des matchs contre minimax)
        if prog["tour"] % EVAL_TOUS_LES == 0:
            with torch.no_grad():
                pm = perte_par_lots(donnees[:64], reseau).item()
            prog["elo"] = evaluer_elo(reseau, prog["elo"], prog["tour"])
            elo_hist.append({"parties": prog["parties"], "elo": round(prog["elo"], 1), "perte": round(pm, 3)})

            # --- SAUVEGARDES ---
            if prog["elo"] > prog["best_elo"]:
                prog["best_elo"] = prog["elo"]
                torch.save(reseau.state_dict(), POIDS_BEST)      # meilleur ELO jamais vu
            torch.save(reseau.state_dict(), POIDS_PARTIEL)        # reseau courant (toujours ecrase)
            if prog["parties"] % 500 < PARTIES_PAR_TOUR:
                torch.save(reseau.state_dict(), SCRATCH + f"poids_sp_snap_{prog['parties']}.pt")  # instantane fige
            sauver()

            # --- affichage de l'avancement ---
            pct = 100 * prog["parties"] / MAX_PARTIES
            ecoule = time.time() - t0
            reste = ecoule / max(prog["parties"] - depart_parties, 1) * (MAX_PARTIES - prog["parties"])
            barre = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
            print(f"[{barre}] {prog['parties']:4d}/{MAX_PARTIES} ({pct:4.1f}%) "
                  f"| perte={pm:.3f} ELO={prog['elo']:.0f} best={prog['best_elo']:.0f} "
                  f"| reste ~{reste/60:.0f} min", flush=True)

    pool.close(); pool.join()
    torch.save(reseau.state_dict(), SCRATCH + "poids_sp.pt")
    print(f"=== TERMINE - best ELO={prog['best_elo']:.0f} ===", flush=True)


# =====================================================================
# CE QUI MANQUE (garde-fou identifie mais pas encore implemente) :
# =====================================================================
# Le vrai AlphaZero n'accepte un nouveau reseau que s'il BAT l'ancien
# en match d'evaluation direct (souvent >55% de victoires). Ici, le
# reseau est ecrase en continu a chaque tour, sans jamais verifier que
# la mise a jour est une amelioration -> une regression (due au bruit
# d'un petit lot de parties) peut s'installer et durer, sans filet.
# C'est ce qu'on observe : l'ELO monte, atteint un pic, puis derive.
