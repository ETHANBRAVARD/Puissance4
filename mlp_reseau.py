"""
Reseau MLP (perceptron multi-couches) pour Puissance 4.

But : comparer une architecture PUREMENT DENSE a l'architecture convolutive de
Alpha0bis.py, sur exactement le meme pipeline (MCTS, perte, entrainer).

Interface identique a ReseauAlphaZero :
  - P(tenseur) -> (politique [N,7], valeur [N,1])
  - forward(tenseur) -> vecteur cache [N, cache]
  - politique(cache) / valeur(cache)
Le tenseur d'entree est celui de Alpha0bis.etat_vers_tenseur2 : [N, 3, 6, 7].
Le MLP l'aplatit en [N, 126] et le traite avec des couches denses.
"""
import torch
import torch.nn as nn


class MLPReseau(nn.Module):
    def __init__(self, cache=256, n_couches=3):
        super().__init__()
        couches = [nn.Linear(3 * 6 * 7, cache), nn.ReLU()]
        for _ in range(n_couches - 1):
            couches += [nn.Linear(cache, cache), nn.ReLU()]
        self.tronc = nn.Sequential(*couches)
        self.tete_politique = nn.Linear(cache, 7)
        self.tete_valeur = nn.Linear(cache, 1)
        self.softmax = nn.Softmax(dim=1)
        self.tanh = nn.Tanh()

    def forward(self, x):
        x = x.view(x.size(0), -1)          # [N, 3,6,7] -> [N, 126]
        return self.tronc(x)               # [N, cache]

    def politique(self, cache):
        return self.softmax(self.tete_politique(cache))   # [N, 7]

    def valeur(self, cache):
        return self.tanh(self.tete_valeur(cache))         # [N, 1]

    def P(self, x):
        cache = self.forward(x)
        return self.politique(cache), self.valeur(cache)
