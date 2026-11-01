# =============================================================================
# © AGPL3 - CID - Developpeur : Frederic COTTA
# Assistance technique: l'IA
# Interdiction de réutilisation commerciale
# =============================================================================
# docs/aide/outils/generer_fiches.py
"""Génère les fiches d'aide HTML (docs/aide/*.html) à partir du contenu ci-dessous : python docs/aide/outils/generer_fiches.py"""
import html
from pathlib import Path
OUT = str(Path(__file__).resolve().parent.parent)

ORDRE = ['connexion', 'beneficiaire-chercher', 'beneficiaire-creer', 'beneficiaire-famille',
         'beneficiaire-modifier', 'beneficiaire-transferer', 'beneficiaire-sortie']
TITRES = {
    'connexion': ("Se connecter à CID", "Ouvrir sa session"),
    'beneficiaire-chercher': ("Chercher un bénéficiaire", "Retrouver un dossier"),
    'beneficiaire-creer': ("Créer un bénéficiaire", "Ouvrir un nouveau dossier"),
    'beneficiaire-famille': ("Ajouter un membre de la famille", "Relier les personnes d'un foyer"),
    'beneficiaire-modifier': ("Modifier un bénéficiaire", "Mettre à jour l'identité et les coordonnées"),
    'beneficiaire-transferer': ("Transférer un bénéficiaire vers sa MDS", "Quand un usager déménage"),
    'beneficiaire-sortie': ("Enregistrer la sortie d'un bénéficiaire", "Clore un suivi"),
}


def lien(slug):
    t, d = TITRES[slug]
    return f'<a href="{slug}.html"><b>{html.escape(t)}</b><span>{html.escape(d)}</span></a>'


def fig(fiche, n, legende, alt=None, petite=False):
    return (f'<figure{" class=\"petite\"" if petite else ""}><img src="img/{fiche}/{n}.jpg" alt="{html.escape(alt or legende)}" loading="lazy">'
            f'<figcaption>{legende}</figcaption></figure>')


def page(slug, *, qui, ou, duree, intro, avant=(), etapes=(), savoir=(), ensuite=()):
    titre, sous = TITRES[slug]
    i = ORDRE.index(slug)
    prec = ORDRE[i - 1] if i > 0 else None
    suiv = ORDRE[i + 1] if i + 1 < len(ORDRE) else None
    corps = []
    if avant:
        corps.append('<div class="bloc"><h2>Avant de commencer</h2><ul>' + ''.join(f'<li>{a}</li>' for a in avant) + '</ul></div>')
    for k, (t, figs, pas, encarts) in enumerate(etapes, 1):
        corps.append(
            f'<section class="etape" id="e{k}"><h2><span class="num">{k}</span>{t}</h2>'
            + (f'<div class="vignettes{" une" if len(figs) == 1 else ""}">' + ''.join(figs) + '</div>' if figs else '')
            + '<ol class="pas">' + ''.join(f'<li>{p}</li>' for p in pas) + '</ol>'
            + ''.join(f'<div class="encart {c}">{x}</div>' for c, x in encarts) + '</section>')
    if savoir:
        corps.append('<div class="bloc"><h2>Bon à savoir</h2><ul>' + ''.join(f'<li>{s}</li>' for s in savoir) + '</ul></div>')
    if ensuite:
        corps.append('<div class="bloc"><h2>Et ensuite ?</h2><div class="liens">' + ''.join(
            lien(e) if e in TITRES else f'<a class="avenir"><b>{html.escape(e)}</b><span>Fiche à venir</span></a>' for e in ensuite) + '</div></div>')
    nav = (f'<a href="{prec}.html">← {html.escape(TITRES[prec][0])}</a>' if prec else '<span></span>') + \
          (f'<a href="{suiv}.html">{html.escape(TITRES[suiv][0])} →</a>' if suiv else '<span></span>')
    doc = f'''<!DOCTYPE html>
<!-- docs/aide/{slug}.html -->
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titre)} – Aide CID</title>
<link rel="stylesheet" href="aide.css">
</head>
<body>
<header><div class="in">
  <div class="fil"><a href="index.html">Aide CID</a> › {"Premiers pas" if slug == "connexion" else "Bénéficiaires"}</div>
  <h1>{html.escape(titre)}</h1>
  <p>{intro}</p>
  <div class="meta"><span>👤 {qui}</span><span>📍 {ou}</span><span>⏱ {duree}</span></div>
</div></header>
<main>
{chr(10).join(corps)}
<p class="note">Cliquez sur une image pour l'agrandir. Le cadre <span class="clic">rouge</span> montre où cliquer ou quoi remplir. Toutes les données affichées sont fictives.</p>
</main>
<nav class="pied">{nav}</nav>
<footer>CID – Aide utilisateur · <a href="index.html">Toutes les fiches</a></footer>
<script src="aide.js"></script>
</body>
</html>
'''
    open(f'{OUT}/{slug}.html', 'w').write(doc)


# =============================================================================
page('connexion', qui="Tous les agents", ou="Page d'accueil de CID", duree="1 minute",
     intro="Votre identifiant et votre mot de passe vous sont donnés par le gestionnaire des accès.",
     etapes=[
         ("Saisir ses identifiants", [fig('connexion', '01', "La page de connexion.")],
          ["Ouvrez CID dans votre navigateur.",
           "Tapez votre <b>nom d'utilisateur</b> puis votre <b>mot de passe</b>.",
           "Cliquez sur <b>Se connecter</b>. La page d'accueil et le menu de CID s'affichent."], []),
         ("Mot de passe oublié", [fig('connexion', '02', "Indiquer son identifiant."), fig('connexion', '03', "La demande est transmise.")],
          ["Sur la page de connexion, cliquez sur <b>Mot de passe oublié ?</b>.",
           "Tapez votre <b>nom d'utilisateur</b> et cliquez sur <span class=\"clic\">Prévenir l'administration</span>.",
           "L'administration de CID reçoit un message (votre nom, la date et l'heure) et vous communique un <b>mot de passe provisoire</b> : vos initiales en majuscules suivies de la date du jour (par exemple <code>AS01112026</code>)."], []),
         ("Choisir son nouveau mot de passe", [fig('connexion', '04', "Changement obligatoire après une réinitialisation.")],
          ["Connectez-vous avec le mot de passe provisoire : CID vous demande aussitôt d'en choisir un nouveau.",
           "Saisissez l'ancien mot de passe (le provisoire), puis deux fois le nouveau, et enregistrez.",
           "Vous pouvez aussi changer votre mot de passe à tout moment : cliquez sur votre nom, en haut à droite, puis <b>Changer mon mot de passe</b>."], []),
     ],
     savoir=["Le menu en haut de l'écran dépend de votre profil : un travailleur social, un cadre ou un agent de la CRIP ne voient pas les mêmes rubriques.",
             "Pensez à vous déconnecter (bouton <b>Déconnexion</b>, en haut à droite) si vous quittez un poste partagé."],
     ensuite=['beneficiaire-chercher', 'beneficiaire-creer'])

page('beneficiaire-chercher', qui="Tous les agents de la MDS", ou="Menu « Bénéficiaires »", duree="1 minute",
     intro="Avant toute démarche, retrouvez la fiche de la personne. Chercher d'abord évite de créer des doublons.",
     etapes=[
         ("Ouvrir la recherche", [fig('chercher', '01', "Menu Bénéficiaires → Liste complète.")],
          ["Dans le menu, cliquez sur <b>Bénéficiaires</b>.", "Choisissez <span class=\"clic\">Liste complète</span>."], []),
         ("Saisir ce que l'on sait", [fig('chercher', '02', "Le nom suffit dans la plupart des cas.")],
          ["Tapez le <b>nom</b> de la personne.",
           "Vous pouvez affiner avec le <b>prénom</b>, la <b>date de naissance</b>, ou un numéro : NIR, n° CAF, n° France Travail, téléphone.",
           "Cliquez sur <b>Rechercher</b> (ou appuyez sur <kbd>Entrée</kbd>)."], []),
         ("Ouvrir la fiche", [fig('chercher', '03', "Les résultats : une ligne par personne."),
                              fig('chercher', '04', "La fiche du bénéficiaire.")],
          ["Les personnes trouvées s'affichent avec leur code, leur date de naissance et leur ville.",
           "Cliquez sur la ligne de la personne : sa <b>fiche</b> s'ouvre.",
           "<b>Aucun résultat ?</b> Vérifiez l'orthographe ou essayez avec moins de critères avant de <a href=\"beneficiaire-creer.html\">créer la personne</a>."],
          [("astuce", "Chaque bénéficiaire a un <b>code interne</b> (par exemple <code>FAM9-CEL</code> ou <code>BEN-B4DDZQ</code>), affiché sous son nom. C'est le repère le plus sûr entre collègues.")]),
     ],
     savoir=["Vous pouvez consulter la fiche d'un usager suivi par une autre MDS : l'identité, les coordonnées, le référent et la famille. Ses documents et ses aides restent réservés à sa MDS (voir <a href=\"beneficiaire-transferer.html\">Transférer un bénéficiaire</a>).",
             "Les enfants et les conjoints ont aussi leur propre fiche : ils apparaissent dans la recherche."],
     ensuite=['beneficiaire-creer', 'beneficiaire-famille', 'beneficiaire-modifier'])

page('beneficiaire-creer', qui="Tous les agents de la MDS", ou="Menu « Bénéficiaires »", duree="3 minutes",
     intro="Créez la fiche d'une personne que CID ne connaît pas encore.",
     avant=["<a href=\"beneficiaire-chercher.html\">Cherchez la personne</a> : si elle existe déjà, ne la recréez pas."],
     etapes=[
         ("Ouvrir le formulaire", [fig('creer', '01', "Aucun résultat : bouton « Nouveau bénéficiaire ».")],
          ["Après une recherche sans résultat, cliquez sur <span class=\"clic\">+ Nouveau bénéficiaire</span>.",
           "Autre chemin : menu <b>Bénéficiaires</b> → <b>Ajouter un usager</b>."], []),
         ("Remplir l'identité et l'adresse", [fig('creer', '02', "L'identité."), fig('creer', '03', "L'adresse et la MDS de rattachement.")],
          ["Les champs marqués d'une <b>*</b> sont obligatoires : civilité, nom, prénom, date de naissance, adresse, code postal, ville, MDS de rattachement.",
           "Date de naissance : <kbd>14/03/1991</kbd>, ou plus vite <kbd>140391</kbd>.",
           "Code postal : CID propose la commune correspondante.",
           "Le <b>référent MDS</b> est facultatif : il peut être choisi plus tard.",
           "Cliquez sur <span class=\"clic\">Enregistrer le bénéficiaire</span>."], []),
         ("Vérifier la fiche créée", [fig('creer', '04', "La fiche, juste après sa création.")],
          ["Un message vert confirme la création.",
           "CID a attribué un <b>code interne</b>, affiché sous le nom (ici <code>BEN-NAO714</code>).",
           "Les boutons du haut servent ensuite au quotidien : <b>Ajouter un lien</b>, <b>Modifier</b>, <b>Document</b>, <b>Message</b>, <b>Prendre rendez-vous</b>, puis <b>Aides financières</b> et <b>CER</b>."], []),
     ],
     savoir=["Les numéros (NIR, CAF, France Travail…) se complètent ensuite avec <a href=\"beneficiaire-modifier.html\">Modifier</a>.",
             "Les enfants et le conjoint se créent depuis la fiche, avec <a href=\"beneficiaire-famille.html\">Ajouter un membre de la famille</a> : ils reprennent alors l'adresse et la MDS."],
     ensuite=['beneficiaire-famille', 'beneficiaire-modifier', "Prendre un rendez-vous"])

page('beneficiaire-famille', qui="Tous les agents de la MDS", ou="Fiche du bénéficiaire", duree="2 minutes par personne",
     intro="Reliez à la fiche les enfants, le conjoint, un parent ou un tiers. La composition du foyer sert ensuite aux aides financières et aux IP.",
     avant=["Ouvrez la fiche du bénéficiaire (<a href=\"beneficiaire-chercher.html\">Chercher un bénéficiaire</a>)."],
     etapes=[
         ("Ouvrir « Ajouter un lien »", [fig('famille', '01', "Bouton « Ajouter un lien » de la fiche.")],
          ["Sur la fiche, cliquez sur <span class=\"clic\">Ajouter un lien</span> (en haut, ou dans le cadre <i>Réseau familial</i>)."], []),
         ("Choisir le lien et la personne", [fig('famille', '02', "Le type de lien."), fig('famille', '03', "Une nouvelle personne, ici un enfant.")],
          ["Choisissez le <b>type de lien</b> : Parent, Enfant, Conjoint, Placement, Tuteur ou Tiers.",
           "<b>La personne est déjà connue de CID ?</b> Tapez au moins 3 lettres de son nom dans <b>Bénéficiaire cible</b> et choisissez-la dans la liste.",
           "<b>Sinon</b>, remplissez « <b>Ou créez un nouveau bénéficiaire</b> » : civilité, nom, prénom, date de naissance.",
           "Cochez <b>Vit au foyer</b> si la personne vit sous le même toit, et <b>Responsable légal</b> si c'est le cas.",
           "Cliquez sur <b>Créer le lien</b>."],
          [("attention", "Cherchez toujours la personne avant d'en créer une nouvelle : un enfant déjà suivi par la MDS ne doit pas avoir deux fiches.")]),
         ("Vérifier le réseau familial", [fig('famille', '04', "Les messages de confirmation."), fig('famille', '05', "Le cadre « Réseau familial ».", petite=True)],
          ["Deux messages confirment la création de la personne et du lien.",
           "Elle apparaît dans le cadre <b>Réseau familial</b>, avec son lien et la mention <b>Foyer</b> si elle vit sous le même toit.",
           "Cliquez sur son nom pour ouvrir sa propre fiche."], []),
     ],
     savoir=["Le lien est enregistré <b>dans les deux sens</b> : sur la fiche de l'enfant, la mère apparaît comme parent.",
             "Une personne créée ici reprend <b>l'adresse et la MDS</b> du bénéficiaire. Si elle vit ailleurs, corrigez sa fiche avec <a href=\"beneficiaire-modifier.html\">Modifier</a>.",
             "Les personnes cochées <b>Vit au foyer</b> donnent le nombre de personnes au foyer proposé dans une demande d'AFASE."],
     ensuite=['beneficiaire-modifier', "Demander une AFASE"])

page('beneficiaire-modifier', qui="Tous les agents de la MDS", ou="Fiche du bénéficiaire", duree="2 minutes",
     intro="Corrigez l'identité, l'adresse, les téléphones ou les numéros administratifs d'un bénéficiaire.",
     avant=["Ouvrez la fiche du bénéficiaire (<a href=\"beneficiaire-chercher.html\">Chercher un bénéficiaire</a>)."],
     etapes=[
         ("Ouvrir la modification", [fig('modifier', '01', "Bouton « Modifier » de la fiche.")],
          ["Sur la fiche, cliquez sur <span class=\"clic\">Modifier</span>."], []),
         ("Corriger les informations", [fig('modifier', '02', "Les coordonnées."), fig('modifier', '03', "Les informations administratives.")],
          ["Le formulaire a trois parties : <b>1. État civil et situation</b>, <b>2. Coordonnées</b>, <b>3. Informations administratives</b>.",
           "Les informations administratives regroupent le <b>NIR</b>, le <b>numéro CAF</b>, le <b>n° France Travail</b>, le <b>numéro fiscal</b> et le <b>référent social</b>.",
           "Cliquez sur <b>Enregistrer les modifications</b>, en bas du formulaire."], []),
         ("Vérifier", [fig('modifier', '04', "Message « Mise à jour effectuée ».")],
          ["Un message vert confirme la mise à jour ; les nouvelles informations s'affichent sur la fiche."], []),
     ],
     savoir=["Le <b>nom de naissance</b> (si différent du nom d'usage) se saisit ici : il est repris dans les formulaires officiels.",
             "La MDS de rattachement ne se change pas ici : voir <a href=\"beneficiaire-transferer.html\">Transférer un bénéficiaire</a>."],
     ensuite=['beneficiaire-transferer', 'beneficiaire-sortie'])

page('beneficiaire-transferer', qui="Agents de la MDS qui reprend le suivi", ou="Fiche du bénéficiaire", duree="2 minutes",
     intro="Un usager suivi par une autre MDS vient d'emménager dans votre secteur : rapatriez son dossier dans votre MDS.",
     avant=["<a href=\"beneficiaire-chercher.html\">Cherchez l'usager</a> : sa fiche s'ouvre en consultation limitée, avec un bandeau orange."],
     etapes=[
         ("Demander le transfert", [fig('transferer', '01', "Bandeau orange : usager suivi par une autre MDS.")],
          ["Le bandeau indique la MDS qui suit l'usager. Vous voyez son identité, ses coordonnées, son référent et sa famille ; ses documents et ses aides seront accessibles après le transfert.",
           "Cliquez sur <span class=\"clic\">Transférer vers ma MDS</span>."], []),
         ("Choisir la MDS et la famille", [fig('transferer', '02', "MDS de destination et membres de la famille."),
                                         fig('transferer', '03', "Ce qui va se passer, puis « Confirmer le transfert ».")],
          ["Vérifiez la <b>MDS de destination</b> (si vous travaillez dans plusieurs MDS, choisissez la bonne).",
           "Cochez les <b>membres de la famille</b> qui déménagent avec l'usager. Par défaut, CID coche ceux qui vivent au foyer et sont suivis par la même MDS. Décochez par exemple un conjoint en cas de séparation.",
           "Lisez l'encadré : il rappelle ce qui va suivre l'usager et qui sera prévenu.",
           "Cliquez sur <span class=\"clic\">Confirmer le transfert</span>."], []),
         ("Vérifier", [fig('transferer', '04', "La fiche, désormais dans votre MDS.")],
          ["Un message indique le nombre de personnes transférées. La fiche est maintenant complète, rattachée à votre MDS."], []),
     ],
     savoir=["Les <b>documents et les aides</b> suivent automatiquement les personnes transférées ; les aides en cours seront traitées par votre MDS.",
             "Le <b>référent</b> est remis à zéro : pensez à en désigner un (<a href=\"beneficiaire-modifier.html\">Modifier</a>).",
             "Un <b>message CID</b> prévient le référent sortant et le responsable de l'ancienne MDS."],
     ensuite=['beneficiaire-modifier', 'beneficiaire-famille'])

page('beneficiaire-sortie', qui="Tous les agents de la MDS", ou="Fiche du bénéficiaire", duree="1 minute",
     intro="Enregistrez la fin du suivi (déménagement hors du département, fin de droits, majorité, placement…) ou un décès, et remettez actif un usager sorti par erreur.",
     avant=["Ouvrez la fiche du bénéficiaire (<a href=\"beneficiaire-chercher.html\">Chercher un bénéficiaire</a>).",
            "Un usager qui déménage <b>dans le département</b> ne sort pas : la nouvelle MDS le <a href=\"beneficiaire-transferer.html\">transfère</a>."],
     etapes=[
         ("Ouvrir la sortie", [fig('sortie', '01', "Bouton rouge « Sortie » de la fiche.")],
          ["Sur la fiche, cliquez sur le bouton rouge <span class=\"clic\">Sortie</span>."], []),
         ("Indiquer la date et le motif", [fig('sortie', '02', "Date, motif et observations.")],
          ["Si des <b>suivis sont encore ouverts</b> (aide en cours, rendez-vous à venir, IP), un encadré orange les liste : la sortie ne les annule pas, prévenez les collègues ou traitez-les avant.",
           "Saisissez la <b>date de sortie</b> (<kbd>31/10/2026</kbd> ou <kbd>311026</kbd>).",
           "Choisissez le <b>motif</b> : séparation, divorce, décès, déménagement, placement, majorité, fin de droits.",
           "Précisez les circonstances dans <b>Détails ou observations</b> si nécessaire.",
           "Cliquez sur <b>Confirmer la fin de prise en charge</b>."],
          [("attention", "CID ne clôture pas les prestations : s'il est concerné, signalez la fin de droits RSA par le circuit habituel.")]),
         ("Vérifier", [fig('sortie', '03', "Message « Sortie enregistrée », statut « Sorti ».")],
          ["Un message confirme la sortie ; le bénéficiaire passe au statut <b>Sorti</b> (ou <b>Décédé</b> si le motif est le décès).",
           "Sa fiche reste consultable : elle n'est pas supprimée."], []),
         ("Déclarer un décès", [fig('sortie', '04', "Bouton « Déclarer un décès ».")],
          ["Sur la fiche, cliquez sur <span class=\"clic\">Déclarer un décès</span>.",
           "Saisissez la <b>date du décès</b> et, si besoin, une observation, puis validez : le statut passe à <b>Décédé</b>."], []),
         ("Remettre actif (erreur ou retour de l'usager)", [fig('sortie', '05', "Bouton « Remettre actif » d'une fiche sortie."), fig('sortie', '06', "Confirmation.")],
          ["Sur la fiche d'un usager sorti ou déclaré décédé, cliquez sur <span class=\"clic\">Remettre actif</span>.",
           "Indiquez le motif si vous le souhaitez (par exemple « sortie enregistrée par erreur »), puis confirmez.",
           "La date et le motif de sortie sont effacés ; une trace de la remise en activité est gardée dans les observations."], []),
     ],
     savoir=["Une personne sortie n'apparaît plus dans le réseau familial des autres membres du foyer.",
             "Les observations de sortie s'ajoutent les unes aux autres : rien n'est effacé."],
     ensuite=['beneficiaire-chercher'])

# =============================================================================
# Sommaire
fiches = ''.join(lien(s) for s in ORDRE[1:])
a_venir = ''.join(f'<a class="avenir"><b>{t}</b><span>Fiche à venir</span></a>' for t in
                  ["Demander une AFASE", "Décider une AFASE (cadre)", "Recours contre un refus", "Chèques service et régie",
                   "Saisir une IP (CRIP)", "Évaluer une IP (binôme)", "Messagerie", "Documents (GED)", "Prendre un rendez-vous"])
open(f'{OUT}/index.html', 'w').write(f'''<!DOCTYPE html>
<!-- docs/aide/index.html -->
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aide CID</title>
<link rel="stylesheet" href="aide.css">
</head>
<body>
<header><div class="in">
  <h1>Aide CID</h1>
  <p>Les fiches pas à pas pour travailler avec CID au quotidien. Une fiche = une fonction ; chaque fiche renvoie aux fiches voisines.</p>
</div></header>
<main>
  <div class="bloc"><h2>Premiers pas</h2><div class="liens">{lien('connexion')}</div></div>
  <div class="bloc"><h2>Bénéficiaires</h2><div class="liens">{fiches}</div></div>
  <div class="bloc"><h2>Prochainement</h2><div class="liens">{a_venir}</div></div>
  <div class="bloc"><h2>Aide-mémoire</h2><p>Pour les habitués : chaque procédure résumée en une page, sans images (fichiers Markdown du dossier <code>memo/</code>).</p>
    <ul>''' + ''.join(f'<li><a href="memo/{s}.md">{html.escape(TITRES[s][0])}</a></li>' for s in ORDRE) + '''</ul></div>
  <p class="note">Les captures d'écran sont réalisées avec des données fictives.</p>
</main>
<footer>CID – Aide utilisateur</footer>
</body>
</html>
''')
print('fiches générées')
