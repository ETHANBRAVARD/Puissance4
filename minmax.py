import Puissance4 as p
import math
class minmax:
     

    def __init__(self):
        self.coup=[0,0]
        self.plateau_actuel = p.plateau()
             


    def ajouter_un_jeton(self,piece):
        self.plateau_actuel.tour_joueur(piece)
    

    def retirer_un_jeton(self,piece):
        if self.plateau_actuel.tour%2 == 1:
            self.plateau_actuel.etatj1 -= 2**(piece[0]*7+piece[1])
        else:
            self.plateau_actuel.etatj2 -= 2**(piece[0]*7+piece[1])
    

    def valider_tour(self,piece):
        self.ajouter_un_jeton(piece)
        self.plateau_actuel.avancer_le_tour()


    def roll_back(self,piece):
        self.plateau_actuel.tour -= 1
        self.retirer_un_jeton(piece)

    def bon_coup(self,pos):
        MASQUE_JOUABLE=0
        score=0
        for i in range (7):
            for j in range (6):
                MASQUE_JOUABLE += 2**(7*i+j)
        vide = MASQUE_JOUABLE & ~(self.plateau_actuel.etatj1 | self.plateau_actuel.etatj2)
        if self.plateau_actuel.Etat_partie(pos):      # deux paires qui se suivent = 4 alignés
                return math.inf
        for k in (1, 7, 6, 8):      # les 4 directions
            m = pos & (pos >> k)    # paires alignées espacées de k
            if m & (m >> k) & vide >> 3*k :        #  3 alligné et 1 libre
                score += 100
            if m & (vide >> 2*k) & pos >> 3*k :        #  3 alligné et 1 libre
                score += 100
            if vide & (m >> k) & m >> 2*k :        #  3 alligné et 1 libre
                score += 100
        for k in (1, 7, 6, 8):      # les 4 directions
            m = pos & (pos >> k)    # paires alignées espacées de k
            if m & vide >> 2*k & vide >>3*k:                  
                score += 10
            if vide & m >> k & vide >>3*k:                  
                score += 10
            if vide & vide >> k & m >>2*k:
                score += 10
        return score

    def evaluation(self):
        if self.plateau_actuel.tour%2==1:
            return(self.bon_coup(self.plateau_actuel.etatj1)-self.bon_coup(self.plateau_actuel.etatj2))
        else:
            return(self.bon_coup(self.plateau_actuel.etatj2)-self.bon_coup(self.plateau_actuel.etatj1))
        
    def meilleur_coup(self,n,alpha=-math.inf,beta=math.inf):
        meilleur_score=[[0,0],-math.inf]
        T=self.plateau_actuel.coup_legaux()
        if self.plateau_actuel.position_final() or n<=0:
            return self.evaluation()
        else :
            for t in T:
                eval=0
                self.valider_tour(t)
                eval -= self.meilleur_coup(n-1,-beta,-alpha)
                if meilleur_score[1] < eval:
                    meilleur_score = [t, eval]
                if alpha < meilleur_score[1] :
                    alpha=meilleur_score[1]
                if alpha > beta :
                    self.roll_back(t)
                    return(meilleur_score[1])
                self.roll_back(t)
        self.coup=meilleur_score[0]
        return (meilleur_score[1])
    
    def choisir_coup ( self , p ):
        self.plateau_actuel = p
        self.meilleur_coup(4)
        return(self.coup)



if __name__=="__main__":
    m=minmax()
    piece=[0,0]
    nb_coup = 0
    while not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1) and not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2) and nb_coup<42:
        print(m.bon_coup(m.plateau_actuel.etatj1))
        entree = int(input('Quelle colonne ? '))-1
        if entree > 6 or entree < 0:
            print("mauvaise entrée")
            continue
        piece[1] = m.plateau_actuel.premiere_ligne_libre(entree)     # une seule colonne
        piece[0] = entree
        if piece[1] is None:
            continue
        m.plateau_actuel.tour_joueur(piece)                           # pas de réaffectation
        nb_coup += 1
        m.plateau_actuel.affichage_plateau()                          # rien
        if m.plateau_actuel.tour==1:
            m.plateau_actuel.tour=2
        else:
            m.plateau_actuel.tour=1
    if m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1):
        print("Joueur 1 gagne")
    elif m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2):
        print("Joueur 2 gagne")
    else:
        print("Match nul")
