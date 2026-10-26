<!-- protection_enfance/_archives/LISEZMOI.md -->
# Archives de l'embryon « protection de l'enfance » (octobre 2026)

Rien n'a été supprimé : ces fichiers sont rangés ici en attendant la décision de Fred.
Ils ne sont pas chargés par Django (aucun import depuis l'application).

- `ase/`, `templates_ase/` : placements, familles d'accueil, adoption, mesures éducatives,
  tableau de bord ASE — base pour un futur module ASE.
- `embryon_ip/`, `templates_embryon_ip/` : première version des IP. Ce qui était réutilisable
  a été repris dans le nouveau module (`models/m_ip.py`, `views/v_ip.py`…) :
  numéro D13 atomique, binôme, MDS en partage, journal, fiche signalant,
  trame d'enquête sociale, délais réglementaires, niveaux d'urgence.
