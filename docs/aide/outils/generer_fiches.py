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
         'beneficiaire-modifier', 'beneficiaire-transferer', 'beneficiaire-sortie',
         'afase-demander', 'afase-ajournement', 'afase-decider', 'afase-transmettre', 'afase-uagaf',
         'afase-recours', 'afase-inspecteur',
         'cap-demander', 'cap-decider', 'cap-coffre', 'regie-demander', 'regie-decider']
RUBRIQUES = [("Premiers pas", ['connexion']),
             ("Bénéficiaires", ['beneficiaire-chercher', 'beneficiaire-creer', 'beneficiaire-famille',
                                'beneficiaire-modifier', 'beneficiaire-transferer', 'beneficiaire-sortie']),
             ("Aides financières – AFASE", ['afase-demander', 'afase-ajournement', 'afase-decider', 'afase-transmettre',
                                            'afase-uagaf', 'afase-recours', 'afase-inspecteur']),
             ("Chèques service (CAP) et régie d'urgence", ['cap-demander', 'cap-decider', 'cap-coffre',
                                                           'regie-demander', 'regie-decider'])]


def rubrique(slug):
    return next(r for r, fiches in RUBRIQUES if slug in fiches)
TITRES = {
    'connexion': ("Se connecter à CID", "Ouvrir sa session"),
    'beneficiaire-chercher': ("Chercher un bénéficiaire", "Retrouver un dossier"),
    'beneficiaire-creer': ("Créer un bénéficiaire", "Ouvrir un nouveau dossier"),
    'beneficiaire-famille': ("Ajouter un membre de la famille", "Relier les personnes d'un foyer"),
    'beneficiaire-modifier': ("Modifier un bénéficiaire", "Mettre à jour l'identité et les coordonnées"),
    'beneficiaire-transferer': ("Transférer un bénéficiaire vers sa MDS", "Quand un usager déménage"),
    'beneficiaire-sortie': ("Enregistrer la sortie d'un bénéficiaire", "Clore un suivi, décès, remise en activité"),
    'afase-demander': ("Demander une AFASE", "Travailleur social : saisir et déposer la demande"),
    'afase-ajournement': ("Répondre à un ajournement", "Travailleur social : compléter et redéposer"),
    'afase-decider': ("Décider une AFASE", "Cadre : accord, refus ou ajournement"),
    'afase-transmettre': ("Notifier et transmettre à l'UAGAF", "Cadre : courrier à l'usager, dossier complet"),
    'afase-uagaf': ("Contrôler et payer une AFASE", "UAGAF : contrôle, renvoi, paiement"),
    'afase-recours': ("Enregistrer un recours", "Cadre : recours contre un refus"),
    'afase-inspecteur': ("AFASE des familles avec une mesure ASE", "Inspecteur enfance-famille"),
    'cap-demander': ("Demander des chèques service", "Travailleur social : alimentation, hygiène"),
    'cap-decider': ("Décider et remettre des chèques service", "Cadre : décision, remise, feuille signée"),
    'cap-coffre': ("Gérer le coffre de chèques service", "Régisseur de la MDS : réception, incidents, inventaire"),
    'regie-demander': ("Demander une régie d'urgence", "Travailleur social : espèces ou paiement à un tiers"),
    'regie-decider': ("Décider et verser une régie d'urgence", "Cadre, puis régie centrale sous 24 heures"),
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
  <div class="fil"><a href="index.html">Aide CID</a> › {rubrique(slug)}</div>
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
     ensuite=['beneficiaire-modifier', 'afase-demander'])

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
# AFASE
DELAIS = ("La demande est réputée refusée <b>2 mois</b> après la date de signature du demandeur : les échéances "
          "s'affichent sur la fiche et sur le tableau du cadre, et CID envoie des rappels.")

page('afase-demander', qui="Travailleur social", ou="Fiche de l'usager → Aides financières", duree="15 minutes",
     intro="Saisissez la demande d'allocation financière de l'aide sociale à l'enfance, joignez les pièces, puis déposez-la au cadre.",
     avant=["Ouvrez la fiche du demandeur (<a href=\"beneficiaire-chercher.html\">Chercher un bénéficiaire</a>) et vérifiez son "
            "<a href=\"beneficiaire-famille.html\">réseau familial</a> : les enfants et les personnes « au foyer » sont repris automatiquement.",
            "Ayez sous la main la date de signature du demandeur, son budget et les justificatifs scannés."],
     etapes=[
         ("Ouvrir une nouvelle AFASE", [fig('afase-demander', '01', "Fiche de l'usager : « Aides financières »."),
                                       fig('afase-demander', '02', "Ses aides : « Nouvelle AFASE ».")],
          ["Sur la fiche, cliquez sur <span class=\"clic\">Aides financières</span> : la liste de ses aides s'affiche.",
           "Cliquez sur <span class=\"clic\">Nouvelle AFASE</span>. Le formulaire compte quatre onglets : Contexte, Demande, Évaluation, Budget."], []),
         ("Onglet « Contexte » : le demandeur et les enfants", [fig('afase-demander', '03', "Le demandeur et le contexte."),
                                                               fig('afase-demander', '04', "Les enfants, repris de la famille.")],
          ["Choisissez la <b>personne qui fait la demande</b> et son <b>lien avec l'enfant</b> (mère, père, tuteur, femme enceinte, jeune majeur…).",
           "Saisissez la <b>date de signature du demandeur</b> : elle est indispensable, le délai de 2 mois court à partir de cette date.",
           "Complétez l'avis du travailleur social, votre qualité, l'allocataire CAF et les situations professionnelles.",
           "Dans le tableau des <b>enfants</b>, cochez ceux qui sont concernés. Un enfant à naître se déclare avec la case « à naître » et la date prévue d'accouchement."], []),
         ("Onglet « Demande » : montant et objet", [fig('afase-demander', '05', "Montant, durée, objet de la demande.")],
          ["Indiquez le <b>montant mensuel</b> et la <b>durée</b> (en mois).",
           "Choisissez l'<b>objet de la demande</b> : le référentiel de la note de service s'affiche (conditions, aides de droit commun à mobiliser avant).",
           "Cochez les <b>aides de droit commun déjà sollicitées</b>, et renseignez une éventuelle <b>mesure ASE</b> dans la fratrie : enfant confié ou assistance éducative, la décision revient alors à l'inspecteur enfance-famille.",
           "L'historique des aides des 12 derniers mois est repris automatiquement de CID ; complétez-le si besoin."], []),
         ("Onglet « Évaluation » : la situation", [fig('afase-demander', '06', "Le code de la demande et l'évaluation sociale.")],
          ["Choisissez le <b>code de la demande</b> et décrivez la situation familiale, l'analyse, la justification et le <b>plan d'action</b> élaboré avec la famille.",
           "Indiquez le degré d'adhésion de la famille et, si besoin, l'affectation ciblée de l'aide."], []),
         ("Onglet « Budget » : ressources et charges", [fig('afase-demander', '07', "Le budget et le reste à vivre.")],
          ["Saisissez les <b>ressources mensuelles</b> (demandeur, conjoint, autres) et les <b>charges</b>, en distinguant payées et non payées ; ajoutez les dettes.",
           "Vérifiez le <b>nombre de personnes au foyer</b> (proposé d'après la famille) : CID calcule le <b>reste à vivre</b> par jour et par personne.",
           "Cliquez sur <b>Enregistrer la demande</b> : elle est créée en brouillon."], []),
         ("Joindre les pièces", [fig('afase-demander', '08', "La demande enregistrée : « Ajouter un document »."),
                                fig('afase-demander', '09', "Le type de pièce, le fichier, puis « Uploader et lier ».")],
          ["Sur la demande, cliquez sur <span class=\"clic\">Ajouter un document</span>.",
           "Choisissez le <b>type de pièce</b> (RIB, identité, livret de famille, domicile, facture ou devis…), le type de document, un titre, puis le fichier, et cliquez sur <b>Uploader et lier</b>.",
           "Recommencez pour chaque pièce : pièces d'identité du demandeur et des enfants, livret de famille (ou attestation CAF/MSA), RIB au nom du destinataire, justificatif de domicile de moins de 3 mois, justificatif lié à l'objet de la demande."],
          [("astuce", "Pour corriger la demande avant de la déposer : bouton <b>Modifier la demande</b>.")]),
         ("Finaliser et déposer au cadre", [fig('afase-demander', '10', "« Instruire / Finaliser la demande AFASE »."),
                                           fig('afase-demander', '11', "Dernière relecture, puis « Finaliser et transmettre au Cadre »."),
                                           fig('afase-demander', '12', "La demande est déposée au cadre.")],
          ["Cliquez sur <span class=\"clic\">Instruire / Finaliser la demande AFASE</span>.",
           "Relisez l'analyse et la justification, ajoutez le commentaire de la famille, puis cliquez sur <b>Finaliser et transmettre au Cadre</b>.",
           "La demande passe au statut <b>Déposée au cadre</b> ; le cadre (ou l'inspecteur, en cas de mesure ASE) reçoit un message CID."], []),
     ],
     savoir=[DELAIS,
             "Les encadrés bleus et orange de la fiche sont des <b>points de vigilance</b> (autre AFASE ce mois-ci, demandeur hors Bouches-du-Rhône, renouvellement…) : ils n'empêchent rien, le cadre décide.",
             "La demande est nominative : le RIB doit être au nom du demandeur, sauf versement à un tiers avec son autorisation signée."],
     ensuite=['afase-ajournement', 'afase-decider'])

page('afase-ajournement', qui="Travailleur social", ou="Messagerie, ou fiche de la demande", duree="5 minutes",
     intro="Le cadre a ajourné la demande : il manque une pièce ou une information. Vous avez 15 jours pour compléter et redéposer.",
     etapes=[
         ("Voir ce qui manque", [fig('afase-ajournement', '01', "L'encadré de l'ajournement, avec ce qu'il faut compléter.")],
          ["Vous recevez un message CID quand le cadre ajourne. Ouvrez la demande : un encadré orange indique <b>qui</b> a ajourné, <b>quand</b>, et <b>ce qu'il faut compléter</b>.",
           "En haut de la fiche, l'échéance des 15 jours est rappelée."], []),
         ("Compléter et redéposer", [fig('afase-ajournement', '02', "« Compléter l'évaluation et redéposer au cadre »."),
                                    fig('afase-ajournement', '03', "La demande est de nouveau déposée.")],
          ["Ajoutez les pièces manquantes (<b>Ajouter un document</b>) ou corrigez la demande (<b>Modifier la demande</b>).",
           "Cliquez sur <span class=\"clic\">Compléter l'évaluation et redéposer au cadre</span>, relisez, puis <b>Finaliser et transmettre au Cadre</b>.",
           "La demande repasse au statut <b>Déposée au cadre</b> : le délai de 15 jours s'arrête."], []),
     ],
     savoir=["CID vous envoie un rappel <b>10 jours</b> après l'ajournement.",
             "Sans réponse au bout de <b>15 jours</b>, le cadre est prévenu : la demande est à refuser pour absence de justificatifs.",
             DELAIS],
     ensuite=['afase-demander', 'afase-decider'])

page('afase-decider', qui="Cadre de la MDS (inspecteur enfance-famille en cas de mesure ASE)", ou="Menu « Cadre » → AFASE et CAP à traiter", duree="5 minutes",
     intro="Accordez, refusez ou ajournez une demande déposée, avec l'aide à la décision de CID.",
     etapes=[
         ("Ouvrir les demandes à traiter", [fig('afase-decider', '01', "Menu Cadre → « AFASE et CAP à traiter »."),
                                           fig('afase-decider', '02', "Le tableau du cadre : échéances et bouton « Décider ».")],
          ["Menu <b>Cadre</b> → <span class=\"clic\">AFASE et CAP à traiter</span>.",
           "Chaque demande indique sa date limite (2 mois après la signature) ; les demandes <b>réputées refusées</b> sont en rouge. Les AFASE ajournées sont listées en bas.",
           "Cliquez sur <b>Décider</b> (ou <b>Consulter</b> pour lire d'abord le dossier)."], []),
         ("Lire l'aide à la décision", [fig('afase-decider', '03', "L'aide à la décision.")],
          ["Le cadre « Aide à la décision » rassemble le <b>reste à vivre</b> (et ce qu'il permet pour un soutien alimentaire), le montant demandé, les enfants concernés et les <b>AFASE accordées sur 12 mois</b>.",
           "Il rappelle l'objet de la demande, les aides de droit commun sollicitées et le référentiel du motif (conditions, montant indicatif).",
           "<b>Prévisualiser le dossier</b> ouvre le formulaire complet en PDF."], []),
         ("Choisir la décision", [fig('afase-decider', '04', "Type de décision, motif, montant et durée."),
                                 fig('afase-decider', '05', "Refus : le motif et la précision pour le courrier."),
                                 fig('afase-decider', '06', "Ajournement : le bouton l'indique.")],
          ["Cochez <b>Accord</b>, <b>Refus</b> ou <b>Ajournement</b> : la liste des motifs s'adapte.",
           "<b>Accord</b> : choisissez le motif, ajustez le montant mensuel et la durée.",
           "<b>Refus</b> : choisissez le code de refus. Pour les codes 3 et 7, remplissez la <b>précision pour le courrier</b> (le dispositif à solliciter, la date de l'aide déjà attribuée) : elle est reprise dans la lettre à l'usager.",
           "<b>Ajournement</b> : écrivez dans le motif ce qu'il faut compléter ; le travailleur social a 15 jours.",
           "Le <b>motif</b> (zone de texte) est votre motivation interne : il n'apparaît pas dans le courrier à l'usager."], []),
         ("Enregistrer", [fig('afase-decider', '07', "Le bouton reprend la décision choisie."),
                         fig('afase-decider', '08', "La décision est enregistrée.")],
          ["Vérifiez le libellé du bouton (« Enregistrer l'accord », « … le refus », « … l'ajournement ») et cliquez.",
           "Le travailleur social reçoit un message CID ; le formulaire de la demande est rangé dans la GED.",
           "Besoin de rendre la main sans décider ? <b>Renvoyer au travailleur social sans décision</b> remet la demande en instruction (sans délai d'ajournement)."], []),
     ],
     savoir=[DELAIS,
             "Une demande ajournée depuis plus de 15 jours peut être tranchée directement : le refus code 1 (absence de justificatifs) est proposé.",
             "Famille avec un enfant confié ou une mesure d'assistance éducative : la décision revient à l'inspecteur enfance-famille (<a href=\"afase-inspecteur.html\">voir la fiche</a>)."],
     ensuite=['afase-transmettre', 'afase-recours'])

page('afase-transmettre', qui="Cadre de la MDS", ou="Fiche de l'AFASE accordée", duree="5 minutes",
     intro="Après la décision : éditez le courrier de notification à l'usager, complétez les pièces et transmettez le dossier à l'UAGAF pour le paiement.",
     etapes=[
         ("Éditer le courrier de notification", [fig('afase-transmettre', '01', "Bouton « Courrier de notification à l'usager »."),
                                                fig('afase-transmettre', '02', "Le courrier (PDF).", petite=True)],
          ["Sur la fiche de l'AFASE, cliquez sur <span class=\"clic\">Courrier de notification à l'usager</span> : un PDF prêt à signer est téléchargé.",
           "<b>Accord</b> : montant, durée, total et destinataire du versement. <b>Refus</b> : le texte du code de refus, avec la précision saisie.",
           "Le courrier comporte le fondement juridique, les voies et délais de recours et la signature « par délégation »."],
          [("astuce", "Les textes des refus, le fondement juridique et les voies de recours se règlent dans l'administration (référentiel AFASE).")]),
         ("Compléter le dossier et transmettre", [fig('afase-transmettre', '03', "Pièces exigées, destinataire du paiement, confirmation."),
                                                 fig('afase-transmettre', '04', "Le dossier est transmis à l'UAGAF.")],
          ["Dans « Circuit du paiement », la liste des <b>pièces exigées</b> doit être entièrement cochée : le lien <b>ajouter</b> ouvre le dépôt de la pièce manquante.",
           "Choisissez à qui l'aide est versée : <b>la famille</b> (son RIB) ou <b>un organisme</b> (cantine, centre de loisirs… : son nom et son RIB).",
           "Cochez la confirmation des pièces d'identité, puis cliquez sur <span class=\"clic\">Transmettre à l'UAGAF</span>.",
           "Le dossier passe au statut <b>Transmise à l'UAGAF</b>."],
          [("attention", "Tant qu'une pièce manque, le bouton reste grisé avec la mention « Transmission impossible : dossier incomplet ».")]),
     ],
     savoir=["Si l'UAGAF renvoie le dossier (pièce illisible, RIB…), il revient à la MDS avec le motif du renvoi : corrigez puis transmettez à nouveau.",
             "« Correction manuelle (cadre) » sert uniquement aux anciens dossiers payés hors du circuit."],
     ensuite=['afase-uagaf', 'afase-recours'])

page('afase-uagaf', qui="Agents de l'UAGAF", ou="Menu « UAGAF (AFASE) »", duree="5 minutes",
     intro="Contrôlez la conformité des dossiers transmis par les MDS, enregistrez la demande de paiement, puis le paiement.",
     etapes=[
         ("Ouvrir les dossiers transmis", [fig('afase-uagaf', '01', "La liste des AFASE transmises.")],
          ["Menu <span class=\"clic\">UAGAF (AFASE)</span> : les dossiers transmis par les MDS, avec la date, la MDS, le montant, le destinataire du paiement et l'état.",
           "Cliquez sur <b>Ouvrir</b> : vous voyez le dossier et ses pièces."], []),
         ("Demander le paiement, ou renvoyer", [fig('afase-uagaf', '02', "Demande de paiement saisie dans le logiciel comptable."),
                                               fig('afase-uagaf', '03', "Ou renvoi à la MDS, avec le motif.")],
          ["Après contrôle, saisissez la demande de paiement dans le logiciel comptable (nom, RIB, somme), puis dans CID : la <b>date</b> et, si vous le souhaitez, le <b>n° d'enregistrement comptable</b> → <b>Paiement demandé</b>.",
           "Dossier non conforme : indiquez le <b>motif</b> (pièce illisible, RIB au mauvais nom…) et cliquez sur <b>Renvoyer à la MDS</b>. Le cadre est prévenu et le dossier revient à la MDS."], []),
         ("Enregistrer le paiement", [fig('afase-uagaf', '04', "Le paiement effectué par la paierie."),
                                     fig('afase-uagaf', '05', "Le circuit du paiement est complet.")],
          ["Quand la paierie a payé : indiquez la <b>date</b> et le <b>montant payé</b> (vide : le montant accordé ; un paiement partiel est possible).",
           "Cliquez sur <span class=\"clic\">Payé : clôturer le dossier</span>. La MDS est prévenue ; le dossier est <b>Clôturé</b>."], []),
     ],
     savoir=["Vous ne voyez que les dossiers transmis à l'UAGAF, et leurs pièces : pas le reste des dossiers des usagers.",
             "Les étapes (transmission, demande de paiement, paiement) alimentent les statistiques des aides de chaque MDS."],
     ensuite=['afase-transmettre'])

page('afase-recours', qui="Cadre de la MDS (ou inspecteur)", ou="Fiche de l'AFASE refusée", duree="3 minutes",
     intro="L'usager conteste un refus auprès du Président du Département ou du tribunal administratif : gardez-en la trace et appliquez la décision du recours.",
     etapes=[
         ("Enregistrer le recours", [fig('afase-recours', '01', "Sur l'AFASE refusée : « Enregistrer un recours ».")],
          ["Ouvrez l'AFASE refusée : le cadre <b>Recours de l'usager</b> s'affiche.",
           "Choisissez le type (<b>gracieux</b> : Président du Département ; <b>contentieux</b> : tribunal administratif), la date du recours et, si besoin, un commentaire.",
           "Cliquez sur <span class=\"clic\">Enregistrer un recours</span> : le recours est « en cours »."], []),
         ("Enregistrer l'issue", [fig('afase-recours', '02', "L'issue et sa date."),
                                 fig('afase-recours', '03', "Refus réformé : la nouvelle AFASE est déposée.")],
          ["Quand la décision sur le recours est connue : choisissez l'issue (<b>refus réformé</b>, <b>refus confirmé</b>, <b>désistement</b>) et sa date, puis <b>Enregistrer l'issue</b>.",
           "<b>Refus réformé</b> : CID crée une <b>nouvelle AFASE</b> reprise de la demande refusée (enfants, budget, évaluation, pièces), déposée pour décision. Le premier refus et son courrier ne changent pas.",
           "Décidez la nouvelle AFASE comme d'habitude (<a href=\"afase-decider.html\">Décider une AFASE</a>) : le délai de 2 mois ne s'applique pas, et le courrier mentionne le recours.",
           "Vous pouvez joindre la <b>décision sur le recours</b> (pièce facultative) à la nouvelle AFASE, ou à l'AFASE refusée si le refus est confirmé."], []),
         ("Suivre les recours", [fig('afase-recours', '04', "Statistiques : recours contre les refus d'AFASE.")],
          ["La page des <b>statistiques des aides</b> présente les recours de l'année : nombre, gracieux ou contentieux, taux de recours, refus réformés, délai moyen et la liste des dossiers (aussi dans l'export Excel)."], []),
     ],
     savoir=["Le recours se traite hors de CID : CID n'en garde que la trace, pour le suivi et la transparence en cas de contrôle."],
     ensuite=['afase-decider', 'afase-transmettre'])

page('afase-inspecteur', qui="Inspecteur enfance-famille", ou="Menu « AFASE (inspecteur) »", duree="5 minutes",
     intro="Quand un enfant de la fratrie est confié à l'ASE ou suivi en assistance éducative, la décision sur l'AFASE vous revient.",
     etapes=[
         ("Ouvrir les AFASE à décider", [fig('afase-inspecteur', '01', "Les AFASE des familles avec une mesure ASE.")],
          ["Menu <span class=\"clic\">AFASE (inspecteur)</span> : les demandes à décider, toutes MDS confondues, puis celles déjà traitées.",
           "Vous recevez aussi un message CID à chaque dépôt."], []),
         ("Décider", [fig('afase-inspecteur', '02', "La demande : bouton « Décider ».")],
          ["Ouvrez la demande et cliquez sur <span class=\"clic\">Décider</span> : la page est celle du cadre (<a href=\"afase-decider.html\">Décider une AFASE</a>).",
           "Après un accord, vous pouvez aussi transmettre le dossier à l'UAGAF (<a href=\"afase-transmettre.html\">Notifier et transmettre</a>)."], []),
     ],
     savoir=["Le cadre de la MDS ne peut pas décider ces demandes ; il les voit sans pouvoir les trancher.",
             "Une mesure de TISF seule ne suffit pas : la décision reste à la MDS."],
     ensuite=['afase-decider', 'afase-transmettre'])


# =============================================================================
# CHÈQUES SERVICE ET RÉGIE
page('cap-demander', qui="Travailleur social", ou="Fiche de l'usager → Aides financières", duree="2 minutes",
     intro="Les chèques d'accompagnement personnalisé (CAP) répondent à un besoin immédiat d'alimentation ou d'hygiène.",
     etapes=[
         ("Ouvrir la demande", [fig('cap-demander', '01', "Les aides de l'usager : « Chèques service (CAP) ».")],
          ["Fiche de l'usager → <b>Aides financières</b> → <span class=\"clic\">Chèques service (CAP)</span>."], []),
         ("Remplir et transmettre", [fig('cap-demander', '02', "Montant et motivation."),
                                    fig('cap-demander', '03', "La demande est transmise au cadre.")],
          ["Indiquez le <b>montant demandé</b> et la <b>situation</b> qui le motive.",
           "Cochez la <b>remise exceptionnelle par la paierie départementale</b> seulement dans un cas exceptionnel : le dossier ira au régisseur central après la décision.",
           "Cliquez sur <b>Transmettre au cadre</b> : la demande est « Déposée au cadre »."],
          [("attention", "Les CAP couvrent uniquement l'alimentation et l'hygiène (nourriture, couches, protections périodiques, savon…). Pour un autre besoin, faites une <a href=\"afase-demander.html\">AFASE</a>.")]),
     ],
     savoir=["Les chèques existent en 10, 20 et 30 € : demandez un montant qui se compose avec ces valeurs.",
             "Après l'accord, le cadre vous remet les chèques pour l'usager : vous signez tous les trois la feuille de remise."],
     ensuite=['cap-decider', 'regie-demander'])

page('cap-decider', qui="Cadre de la MDS", ou="Menu « Cadre » → AFASE et CAP à traiter", duree="5 minutes",
     intro="Décidez la demande, remettez les chèques sortis du coffre, puis archivez la feuille de remise signée.",
     etapes=[
         ("Décider", [fig('cap-decider', '01', "Le tableau du cadre : CAP à décider et à remettre."),
                     fig('cap-decider', '02', "La décision.")],
          ["Menu <b>Cadre</b> → <b>AFASE et CAP à traiter</b> : la partie <b>Chèques service (CAP)</b> liste les demandes à décider et celles accordées, à remettre.",
           "Ouvrez la demande, choisissez <b>Accorder</b> (montant accordé) ou <b>Refuser</b> (motif), puis <b>Enregistrer la décision</b>.",
           "Le cadre de droite montre le contenu du coffre : ce qui est disponible, par valeur."], []),
         ("Remettre les chèques", [fig('cap-decider', '03', "Les numéros des chèques remis.")],
          ["Sortez les chèques du coffre et <b>scannez-les à la douchette</b> (un numéro par ligne), ou cliquez sur <b>Utiliser cette proposition</b> : CID propose des chèques disponibles pour le montant.",
           "Choisissez l'agent à qui les chèques sont <b>remis</b>, puis <b>Enregistrer la remise</b>."],
          [("attention", "Si le coffre ne permet pas de composer le montant, CID l'indique : prévenez le régisseur.")]),
         ("Faire signer et clôturer", [fig('cap-decider', '04', "« Imprimer la feuille à signer »."),
                                      fig('cap-decider', '05', "La feuille de remise.", petite=True),
                                      fig('cap-decider', '06', "Déposer la feuille signée, puis clôturer."),
                                      fig('cap-decider', '07', "Le dossier est clôturé.")],
          ["Cliquez sur <span class=\"clic\">Imprimer la feuille à signer</span> : cadre, travailleur social et usager la signent.",
           "Scannez ou photographiez la feuille signée, déposez-la (PDF ou photo) et cliquez sur <b>Archiver et clôturer le dossier</b>.",
           "La feuille est rangée dans la GED et le dossier est <b>Clôturé</b>."], []),
     ],
     savoir=["Chaque chèque garde sa traçabilité : qui l'a remis, à qui, pour quelle demande.",
             "Remise exceptionnelle par la paierie : après votre accord, le dossier part au régisseur central, qui saisit les numéros remis."],
     ensuite=['cap-coffre', 'cap-demander'])

page('cap-coffre', qui="Régisseur de la MDS (désigné par la direction)", ou="Menu « Coffre CAP »", duree="Variable",
     intro="Enregistrez les chèques reçus, signalez les incidents et faites l'inventaire du coffre.",
     etapes=[
         ("Le coffre", [fig('cap-coffre', '01', "Le coffre : stock par valeur, chèques, réceptions, inventaires.")],
          ["Menu <span class=\"clic\">Coffre CAP</span> : le nombre de chèques par valeur et le montant disponible, la liste des chèques avec leur statut, les CAP accordées à remettre, les réceptions et les inventaires.",
           "Recherchez un chèque par son numéro ou filtrez par statut (au coffre, remis, perdu, volé, retourné)."], []),
         ("Enregistrer une réception", [fig('cap-coffre', '02', "Nouvelle réception : validité et bordereau."),
                                       fig('cap-coffre', '03', "Saisie à la douchette.")],
          ["Cliquez sur <b>Nouvelle réception</b> : date de réception, <b>date de fin de validité</b> imprimée sur les titres, n° du bordereau.",
           "<b>Commencer la saisie à la douchette</b> : choisissez la valeur (10, 20 ou 30 €), puis scannez chaque chèque ; la liste et le total se mettent à jour.",
           "Cliquez sur <b>Terminer la saisie</b> : plus aucun chèque ne pourra être ajouté à cette réception. Le bordereau est disponible en PDF."], []),
         ("Signaler un incident", [fig('cap-coffre', '04', "« Signaler… » sur la ligne du chèque.")],
          ["Sur la ligne du chèque, <b>Signaler…</b> : perdu, volé, ou retourné (périmé, annulé), avec un commentaire."], []),
         ("Faire l'inventaire", [fig('cap-coffre', '05', "L'inventaire : scans et écarts.")],
          ["Cliquez sur <b>Inventaire</b>, puis scannez tous les chèques présents dans le coffre.",
           "CID compare au stock théorique (reçus − remis − perdus/volés − retournés) et affiche les écarts par valeur.",
           "<b>Terminer l'inventaire</b> : le procès-verbal est disponible en PDF."], []),
     ],
     savoir=["Le régisseur est désigné sur la page du coffre (« Régisseur (délégation de la direction) »)."],
     ensuite=['cap-decider'])

page('regie-demander', qui="Travailleur social", ou="Fiche de l'usager → Aides financières", duree="3 minutes",
     intro="Une aide d'urgence versée par la régie centrale dans les 24 heures après l'accord du cadre : en espèces, ou directement à un tiers (hôtel, fournisseur…).",
     etapes=[
         ("Ouvrir la demande", [fig('regie-demander', '01', "Les aides de l'usager : « Régie urgence ».")],
          ["Fiche de l'usager → <b>Aides financières</b> → <span class=\"clic\">Régie urgence</span>."], []),
         ("Remplir et transmettre", [fig('regie-demander', '02', "Montant, motif, mode de paiement, pièces du tiers."),
                                    fig('regie-demander', '03', "La demande est transmise au cadre.")],
          ["Indiquez le <b>montant</b> et le <b>motif de l'urgence</b>.",
           "<b>En espèces</b> : l'usager viendra avec une pièce d'identité avec photo en cours de validité. <b>À un tiers</b> : nom du tiers, référence de la facture, et joignez la <b>facture</b> et le <b>RIB du tiers</b>.",
           "Cliquez sur <b>Transmettre au cadre</b>."],
          [("attention", "Montant : se conformer au maximum prévu par la note de service en vigueur. Pour une urgence alimentaire, privilégiez les <a href=\"cap-demander.html\">chèques service</a>.")]),
     ],
     savoir=["L'aide d'urgence n'est pas déduite d'une AFASE à venir.",
             "Absence totale de ressources ou baisse importante et soudaine : joignez un avis motivé et un justificatif (attestation CAF…)."],
     ensuite=['regie-decider', 'cap-demander'])

page('regie-decider', qui="Cadre de la MDS, puis régisseur central", ou="Fiche de la régie ; menu « Régie centrale »", duree="2 minutes",
     intro="Le cadre décide ; en cas d'accord, le dossier part aussitôt à la régie centrale, qui verse dans les 24 heures.",
     etapes=[
         ("Décider (cadre)", [fig('regie-decider', '01', "La décision du cadre."),
                             fig('regie-decider', '02', "Accordée : transmise à la paierie.")],
          ["Ouvrez la demande (tableau du cadre ou message CID) : <b>Accorder</b> avec le montant, ou <b>Refuser</b> avec le motif, puis <b>Enregistrer la décision</b>.",
           "En cas d'accord, le dossier est <b>transmis à la paierie</b> : le régisseur central est prévenu."],
          [("attention", "Se conformer au montant maximum prévu par la note de service en vigueur : CID avertit s'il est dépassé.")]),
         ("Verser (régisseur central)", [fig('regie-decider', '03', "Régie centrale : les régies à verser, avec le délai."),
                                        fig('regie-decider', '04', "Le versement."),
                                        fig('regie-decider', '05', "Versement enregistré : dossier clôturé.")],
          ["Menu <span class=\"clic\">Régie centrale</span> : les régies à verser, avec le temps écoulé depuis l'accord (24 heures au plus), et les chèques service à remettre en paierie.",
           "Ouvrez la régie : facture et RIB du tiers sont à droite. Indiquez la date et l'heure du versement (vide : maintenant), le <b>montant versé</b> (partiel possible, jamais supérieur à l'accord) et le n° d'enregistrement comptable.",
           "Cliquez sur <b>Versement fait : clôturer le dossier</b> : le travailleur social et le cadre sont prévenus par message CID."], []),
     ],
     savoir=["Les étapes (décision, versement) alimentent les statistiques des aides de la MDS."],
     ensuite=['regie-demander', 'cap-decider'])

# =============================================================================
# Sommaire
a_venir = ''.join(f'<a class="avenir"><b>{t}</b><span>Fiche à venir</span></a>' for t in
                  [                   "Saisir une IP (CRIP)", "Évaluer une IP (binôme)", "Messagerie", "Documents (GED)", "Prendre un rendez-vous"])
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
  {''.join(f'<div class="bloc"><h2>{html.escape(r)}</h2><div class="liens">' + ''.join(lien(f) for f in fiches) + '</div></div>' for r, fiches in RUBRIQUES)}
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
