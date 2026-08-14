import minmax as m
import Ia as ia

class plateau:


    def __init__(self):
        self.etatj1=0
        self.etatj2=0
        self.tour=1


    def affichage_plateau(self)  :
        grille=[[0]*7 for i in range (6)]
        self.poser_jetons(grille,1)
        self.poser_jetons(grille,2)
        for i in range(6):
            print(f'{grille[len(grille)-1-i]}\n')


    def poser_jetons(self,grille, valeur):
        if valeur==1:
            etat=self.etatj1
        else:
            etat=self.etatj2
        while etat > 0:
            k = 0
            while etat - 2**k >= 0:
                k = k + 1
            bit = k - 1
            etat = etat - 2**bit
            r = bit % 7        # ligne
            i = bit // 7       # colonne
            if r < 6:
                grille[r][i] = valeur
    

    def retirer_un_jeton(self,piece):
        if self.tour%2 == 1:
            self.etatj1 -= 2**(piece[0]*7+piece[1])
        else:
            self.etatj2 -= 2**(piece[0]*7+piece[1])

        
    def tour_joueur(self,piece):
        if self.tour%2 == 1:
            self.etatj1 += 2**(piece[0]*7+piece[1])    #[colone,ligne]
        else:
            self.etatj2 += 2**(piece[0]*7+piece[1])  #[colone,ligne]


    def Etat_partie(self,pos):
        for k in (1, 7, 6, 8):      # les 4 directions
            m = pos & (pos >> k)    # paires alignées espacées de k
            if m & (m >> 2*k):      # deux paires qui se suivent = 4 alignés
                return True
        return False
    

    def premiere_ligne_libre(self ,colonne):
        for r in range(6):                     # lignes 0 à 5 seulement
            bit = colonne*7 + r
            occupe = (self.etatj1 >> bit & 1) or (self.etatj2 >> bit & 1)
            if not occupe:
                return r                       # première case vide trouvée
        return None                            # colonne pleine
    

    def avancer_le_tour(self):
        self.tour += 1


    def position_final(self):
        if self.Etat_partie(self.etatj1) :
            return("victoire Joueur 1")
        if self.Etat_partie(self.etatj2):
            return("victoire Joueur 2")
        if self.coup_legaux()==[]:
            return("match nul")
        else:
            return(None)
        
    
    def coup_legaux(self):
        L=[]
        for i in range (7):
            lignelibre=self.premiere_ligne_libre(i)
            if lignelibre != None:
                L.append([i,lignelibre])
        return(L)   
    

    def choisir_coup(self,QUI,plateau):
        piece = [0,0]
        if QUI == "ia":
            bot=ia.self_play()
            piece = bot.choisir_coup(self)
        elif QUI =="minmax":
            bot=m.minmax()
            piece = bot.choisir_coup(self)
        else:
            piece[0] = int(input('Quelle colonne ? '))-1
            piece[1] = self.premiere_ligne_libre(piece[0])
        if piece[0] > 6 or piece[0] <0:
            return("mauvaise entrée")
        return(piece)
            

    
if __name__ == "__main__":
    p=plateau()
    piece=[0,0]
    nb_coup = 0
    while not p.Etat_partie(p.etatj1) and not p.Etat_partie(p.etatj2) and nb_coup<42:
        if p.tour%2==1:
            piece = p.choisir_coup("minmax",p)
        else:
            piece = p.choisir_coup("",p)
        if piece is None or piece =="mauvaise entrée":
            continue
        p.tour_joueur(piece)                           # pas de réaffectation
        nb_coup += 1
        p.affichage_plateau()                          # rien
        if p.tour==1:
            p.tour=2
        else:
            p.tour=1
    if p.Etat_partie(p.etatj1):
        print("Joueur 1 gagne")
    elif p.Etat_partie(p.etatj2):
        print("Joueur 2 gagne")
    else:
        print("Match nul")

