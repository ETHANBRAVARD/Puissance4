import math
import random
import Puissance4 as p

class self_play :

    def __init__(self):
        self.coup=[0,0]
        self.plateau_actuel = p.plateau()
        self.a=0
        self.b=0
        self.c=0
        self.d=0
        self.e=0
        self.f=0
        self.generation=0


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
                score += self.a
            if m & (vide >> 2*k) & pos >> 3*k :        #  3 alligné et 1 libre
                score += self.b
            if vide & (m >> k) & m >> 2*k :        #  3 alligné et 1 libre
                score += self.c
        for k in (1, 7, 6, 8):      # les 4 directions
            m = pos & (pos >> k)    # paires alignées espacées de k
            if m & vide >> 2*k & vide >>3*k:                  
                score += self.d
            if vide & m >> k & vide >>3*k:                  
                score += self.e
            if vide & vide >> k & m >>2*k:
                score += self.f
        return score
    

    def meilleur_coup(self):
        meilleur_score = -math.inf
        meilleur_coup = None
        for colonne in range(7):
            ligne = self.plateau_actuel.premiere_ligne_libre(colonne)
            if ligne is not None:
                piece = [colonne, ligne]
                self.plateau_actuel.tour_joueur(piece)
                score = self.bon_coup(self.plateau_actuel.etatj1 if self.plateau_actuel.tour % 2 == 1 else self.plateau_actuel.etatj2)
                self.plateau_actuel.retirer_un_jeton(piece)
                if score > meilleur_score:
                    meilleur_score = score
                    meilleur_coup = piece
        return meilleur_coup
    

    def copie(self):
        copie_ia = self_play()
        copie_ia.a = self.a
        copie_ia.b = self.b
        copie_ia.c = self.c
        copie_ia.d = self.d
        copie_ia.e = self.e
        copie_ia.f = self.f
        copie_ia.generation = self.generation
        new_ia(copie_ia)
        return copie_ia

def huitieme (IA,Classement):
    random.shuffle(IA)
    for i in range(8):
        plateau = p.plateau()
        m = IA[i*2]
        n = IA[i*2+1]
        m.plateau_actuel=plateau
        n.plateau_actuel=plateau
        nb_coup = 0
        while not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1) and not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2) and nb_coup<42:
            if plateau.tour%2==1:
                piece = m.meilleur_coup()
            else:
                piece = n.meilleur_coup()
            if piece is None:
                continue                         
            nb_coup += 1
            plateau.tour_joueur(piece)
            plateau.tour+=1                    
        if m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1):
            print("Joueur 1 gagne")
            Classement[i]=IA[i*2]
        elif m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2):
            print("Joueur 2 gagne")
            Classement[i]=IA[i*2+1]
        else:
            print("Match nul")
            a=random.choice([IA[i*2],IA[i*2+1]])
            Classement[i]=a
    return (IA,Classement)


def quart (Classement):
    classementquart=[]
    for i in range(4):
        plateau = p.plateau()
        m = Classement[i*2]
        n = Classement[i*2+1]
        m.plateau_actuel=plateau
        n.plateau_actuel=plateau
        nb_coup = 0
        while not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1) and not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2) and nb_coup<42:
            if plateau.tour%2==1:
                piece = m.meilleur_coup()
            else:
                piece = n.meilleur_coup()
            if piece is None:
                continue                         
            nb_coup += 1
            plateau.tour_joueur(piece)
            plateau.tour+=1                    
        if m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1):
            print("Joueur 1 gagne")
            classementquart.append(Classement[i*2])
        elif m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2):
            print("Joueur 2 gagne")
            classementquart.append(Classement[i*2+1])
        else:
            print("Match nul")
            a=random.choice([Classement[i*2],Classement[i*2+1]])
            classementquart.append(a)
    for ia in Classement:
        if not (ia in classementquart):
            classementquart.append(ia)
    return(classementquart)
    

def demi (Classement):
    classementdemi=[]
    for i in range(2):
        plateau = p.plateau()
        m = Classement[i*2]
        n = Classement[i*2+1]
        m.plateau_actuel=plateau
        n.plateau_actuel=plateau
        nb_coup = 0
        while not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1) and not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2) and nb_coup<42:
            if plateau.tour%2==1:
                piece = m.meilleur_coup()
            else:
                piece = n.meilleur_coup()
            if piece is None:
                continue                         
            nb_coup += 1
            plateau.tour_joueur(piece)
            plateau.tour+=1                    
        if m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1):
            print("Joueur 1 gagne")
            classementdemi.append(Classement[i*2])
        elif m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2):
            print("Joueur 2 gagne")
            classementdemi.append(Classement[i*2+1])
        else:
            print("Match nul")
            a=random.choice([Classement[i*2],Classement[i*2+1]])
            classementdemi.append(a)
    for ia in Classement:
        if not (ia in classementdemi):
            classementdemi.append(ia)
    return(classementdemi)

def final (Classement):
    classementfinal=[]
    for i in range(2):
        plateau = p.plateau()
        m = Classement[i*2]
        n = Classement[i*2+1]
        m.plateau_actuel=plateau
        n.plateau_actuel=plateau
        nb_coup = 0
        while not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1) and not m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2) and nb_coup<42:
            if plateau.tour%2==1:
                piece = m.meilleur_coup()
            else:
                piece = n.meilleur_coup()
            if piece is None:
                continue                         
            nb_coup += 1
            plateau.tour_joueur(piece)
            plateau.tour+=1                    
        if m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj1):
            print("Joueur 1 gagne")
            classementfinal.append(Classement[i*2])
        elif m.plateau_actuel.Etat_partie(m.plateau_actuel.etatj2):
            print("Joueur 2 gagne")
            classementfinal.append(Classement[i*2+1])
        else:
            print("Match nul")
            a=random.choice([Classement[i*2],Classement[i*2+1]])
            classementfinal.append(a)
    for ia in Classement:
        if not (ia in classementfinal):
            classementfinal.append(ia)
    return(classementfinal)


def tournoi(IA):
    classement=[0 for _ in range(16)]
    IA,classement=huitieme(IA,classement)
    classement=quart(classement)
    classement=demi(classement)
    classement=final(classement)
    return(classement)
    
def new_ia (ia):
        if ia.generation<1000:
            ia.a+=random.uniform(-100,100)
            ia.b+=random.uniform(-100,100)
            ia.c+=random.uniform(-100,100)
            ia.d+=random.uniform(-100,100)
            ia.e+=random.uniform(-100,100)
            ia.f+=random.uniform(-100,100)
        elif ia.generation < 2000:
            ia.a+=random.uniform(-10,10)
            ia.b+=random.uniform(-10,10)
            ia.c+=random.uniform(-10,10)
            ia.d+=random.uniform(-10,10)
            ia.e+=random.uniform(-10,10)
            ia.f+=random.uniform(-10,10)
        else :
            ia.a+=random.uniform(-1,1)
            ia.b+=random.uniform(-1,1)
            ia.c+=random.uniform(-1,1)
            ia.d+=random.uniform(-1,1)
            ia.e+=random.uniform(-1,1)
            ia.f+=random.uniform(-1,1)
        ia.generation+=1
        return(ia)

def nouvelle_gen(Classement):
    Ia=[0 for _ in range(16)]
    Ia[0]=Classement[0]
    Ia[1]=Classement[1]
    Ia[2]=Classement[2]
    Ia[3]=Classement[3]
    Ia[4]=Classement[4]
    Ia[5]=Classement[5]
    Ia[6]=Classement[6]
    Ia[7]=Classement[7]
    Ia[8]=Classement[3].copie()
    Ia[9]=Classement[0].copie()
    Ia[10]=Classement[0].copie()
    Ia[11]=Classement[0].copie()
    Ia[12]=Classement[1].copie()
    Ia[13]=Classement[1].copie()
    Ia[14]=Classement[2].copie()
    Ia[15]=Classement[2].copie()
    return(Ia)

if __name__ == "__main__":
    Ia= [self_play() for _ in range(16)]
    for i in range (210):
        Classement=tournoi(Ia)
        Ia=nouvelle_gen(Classement)
    for i in range(4):
        print(Classement[i].a,Classement[i].b,Classement[i].c,Classement[i].d,Classement[i].e,Classement[i].f)
    
