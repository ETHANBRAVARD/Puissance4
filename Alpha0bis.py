import Puissance4 as p
import torch.nn as nn
import torch
import math

class Alpha0bis:

    def __init__(self):
        self.etatj1=0
        self.etatj2=0
        self.tour=0
        self.tenseur=[[[0 for i in range (7)]for k in range (6)]for m in range (2)]


    def etat_vers_tenseur(self):
        for i in range (7):
            for k in range (6):
                bit = i*7 + k
                valeurj1 = (self.etatj1 >> bit) & 1
                valeurj2 = (self.etatj2 >> bit) & 1
                self.tenseur[0][k][i]=valeurj1
                self.tenseur[1][k][i]=valeurj2

    @staticmethod
    def etat_vers_tenseur2 ( plateau ):
            tens=[[[0 for i in range (7)]for k in range (6)]for m in range (3)]
            t=plateau.tour%2
            for i in range (7):
                for k in range (6):
                    tens[2][k][i]=t
                    bit = i*7 + k
                    valeurj1 = (plateau.etatj1 >> bit) & 1
                    valeurj2 = (plateau.etatj2 >> bit) & 1
                    tens[0][k][i]=valeurj1
                    tens[1][k][i]=valeurj2
            tens = torch.tensor(tens, dtype=torch.float32)
            tens = tens.unsqueeze(0)
            return (tens)





class ReseauAlphaZero(nn.Module):

    def __init__(self,canneaux=128):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=canneaux, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=canneaux, out_channels=canneaux, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(in_channels=canneaux, out_channels=canneaux, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(in_channels=canneaux, out_channels=canneaux, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.appl = nn.Conv2d(in_channels=canneaux, out_channels=3, kernel_size=1)
        self.lin1 = nn.Linear(in_features=42*3, out_features=32)
        self.lin2 = nn.Linear(in_features=32, out_features=1)
        self.tanh = nn.Tanh()
        self.softmax = nn.Softmax(dim=1)
        self.appl2 = nn.Conv2d(in_channels=canneaux, out_channels=32, kernel_size=1)
        self.lin3 = nn.Linear(in_features=42*32, out_features=32)
        self.lin4 = nn.Linear(in_features=32, out_features=7)
        self.bn1 = nn.BatchNorm2d(num_features=canneaux)
        self.bn2 = nn.BatchNorm2d(num_features=canneaux)
        self.bn3 = nn.BatchNorm2d(num_features=canneaux)
        self.bn4 = nn.BatchNorm2d(num_features=canneaux)
        


    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        a = x.clone()
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        x = self.conv3(x)
        x = self.bn3(x)
        x = self.relu(x)
        x = self.conv4(x)
        x = a +self.bn4(x)
        x = self.relu(x)
        return x


    def valeur(self,x):
        x=self.appl(x)
        x = x.view(x.size(0), -1)
        x = self.relu(x)
        x=self.lin1(x)
        x = self.relu(x)
        x = self.lin2(x)
        x = self.tanh(x)
        return(x)
    
    def politique(self,x):
        x=self.appl2(x)
        x = x.view(x.size(0), -1)
        x = self.relu(x)
        x=self.lin3(x)
        x = self.relu(x)
        x = self.lin4(x)
        x=self.softmax(x)
        return(x)
    

    def P(self , x):
        P=self.forward(x)
        v=self.valeur(P)
        P=self.politique(P)
        return(P,v)

class noeud:

    c=1.4

    def __init__(self,etat,profondeur):
        self.etat=etat
        self.profondeur=profondeur
        self.enfants={}
        self.visites=0
        self.valeur_moyenne=0


    def trouver_enfant(self, coup):
        n=self.enfants.get(tuple(coup))    # cherche dans self.enfants le noeud qui correspond à ce coup
        return(n)                   # renvoie ce noeud s'il existe, sinon None
    

    def PUCT(self , p , reseau):
        coup_final=None
        score_puct = - math.inf
        COUP = p.coup_legaux()
        Pol=reseau.P(Alpha0bis.etat_vers_tenseur2(p))[0]
        for coup in COUP:
            enfant=self.trouver_enfant(coup)
            if enfant != None :
                a = - enfant.valeur_moyenne + self.c * Pol[0][coup[0]] * math.sqrt(self.visites) / (1 + enfant.visites)
                if score_puct < a :
                    score_puct = a
                    coup_final=coup
            else:
                a = self.c * Pol[0][coup[0]] * math.sqrt(self.visites) / 1
                if score_puct < a: 
                    score_puct = a 
                    coup_final=coup
        return(score_puct,coup_final)
    

    def expansion(self, coup):
        plateau=p.plateau()
        plateau.etatj1=self.etat.etatj1
        plateau.etatj2=self.etat.etatj2
        plateau.tour=self.etat.tour
        plateau.tour_joueur(coup)
        plateau.avancer_le_tour()
        self.enfants[tuple(coup)]=noeud(plateau, self.profondeur+1)
        return(self.enfants[tuple(coup)])
    

    def recherche(self,plateau_depart, reseau, nombre_de_simulations):
        coup=[]
        for i in range (nombre_de_simulations):
            noeud_courant = self
            coup = noeud_courant.PUCT( plateau_depart , reseau)[1]
            k=0
            chemin = [self]
            while k==0 :
                if noeud_courant.etat.position_final() == None :
                    coup = noeud_courant.PUCT( noeud_courant.etat , reseau)[1]
                    if noeud_courant.trouver_enfant(coup) != None :
                        cet_enfant=noeud_courant.trouver_enfant(coup)
                    else:
                        cet_enfant=noeud_courant.expansion(coup)
                        valeur=reseau.P(Alpha0bis.etat_vers_tenseur2(cet_enfant.etat))[1]
                        k=1
                    noeud_courant=cet_enfant
                    chemin.append(noeud_courant)
                elif noeud_courant.etat.position_final() == "match nul" :
                    valeur=0
                    k=1
                else:
                    valeur=-1
                    k=1
            for noeud in chemin[::-1] :
                noeud.valeur_moyenne=(noeud.valeur_moyenne* noeud.visites + valeur)/(noeud.visites+1)
                noeud.visites+=1
                valeur=-valeur


    def meilleur_coup_final (self):
        meilleur_coup = None
        visite_max=-math.inf
        for coup , enfant in self.enfants.items() :
            if visite_max < enfant.visites :
                meilleur_coup = coup
                visite_max = enfant.visites
        return(meilleur_coup)

def jouer_partie(reseau):
    coups=0
    L=[]
    plateau_de_depart = p.plateau()
    racine = noeud(plateau_de_depart, 0)
    while racine.etat.position_final() is None and coups < 42 :
        racine.recherche(racine.etat, reseau, 30)
        coup = racine.meilleur_coup_final()
        visite=[0,0,0,0,0,0,0]
        for coup_possible ,enfant in racine.enfants.items() :
            visite[coup_possible[0]] = enfant.visites
        L.append([racine.etat,visite,0])
        racine = racine.enfants[tuple(coup)]
        coups += 1
    if racine.etat.position_final() == "victoire Joueur 1" :
        n=0
        for t in L :
            t[2] = 1*(-1)**n
            n+=1
    elif racine.etat.position_final() == "victoire Joueur 2" :
        n=0
        for t in L :
            t[2] = -1*(-1)**n
            n+=1
    return(L)

def perte(t,reseau):
    politique,valeur_actuelle=reseau.P(Alpha0bis.etat_vers_tenseur2(t[0]))
    cible = t[1]
    prédiction = politique
    somme=0
    for p in cible :
        somme+=p
    for i in range (len(cible)):
        cible[i]=cible[i]/somme
    perte_politique=0
    for i in range (len(cible)):
        perte_politique -= (cible[i] * torch.log(prédiction[0][i]+1E-10))
    perte_valeur = (valeur_actuelle - t[2])**2
    return(perte_politique + perte_valeur)


def perte_par_lots(lots, reseau):
    X = torch.cat([Alpha0bis.etat_vers_tenseur2(p[0]) for p in lots], 0)               # [B, 3, 6, 7]  ← empile les tenseurs du lot
    politique, valeur = reseau.P(X)            # UNE seule passe -> [B,7] et [B,1]
    perte_totale = 0
    for i, t in enumerate(lots):
        cible = t[1]
        prédiction = politique[i]
        somme=0
        for k in cible :
            somme+=k
        for j in range (len(cible)):
            cible[j]=cible[j]/somme
        perte_politique=0
        for j in range (len(cible)):
            perte_politique -= (cible[j] * torch.log(prédiction[j]+1E-10))
        perte_valeur = (valeur[i] - t[2])**2
        perte_totale += (perte_politique + perte_valeur)
    return perte_totale/len(lots)



def entrainer(reseau, donnees, optimiseur):
    for t in donnees:
        optimiseur.zero_grad()
        loss = perte(t, reseau)
        loss.backward()
        optimiseur.step()

def entrainer_par_lots(reseau, donnees, optimiseur, taille_lot):
    for i in range(0, len(donnees), taille_lot):
        lot = donnees[i:i+taille_lot]
        optimiseur.zero_grad()
        loss = perte_par_lots(lot, reseau)
        loss.backward()
        optimiseur.step()
    
if __name__=="__main__":
    reseau = ReseauAlphaZero()
    optimiseur = torch.optim.Adam(reseau.parameters(), lr=0.001)
    for i in range(1000):
        donnees=[]
        for j in range(10):
            partie=jouer_partie(reseau)
            for t in partie:
                donnees.append(t)
        entrainer(reseau,donnees,optimiseur)