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
         'cap-demander', 'cap-decider', 'cap-coffre', 'regie-demander', 'regie-decider',
         'ip-saisir', 'ip-binome', 'ip-evaluer', 'ip-synthese', 'ip-inspecteur', 'ip-saisine',
         'messagerie', 'ged-deposer', 'rdv-prendre', 'rdv-issue',
         'journal-accompagnement', 'budget-foyer', 'ateliers-collectifs', 'statistiques-accompagnement',
         'fsl-acces', 'copp', 'insertion-actions', 'insertion-action-locale', 'insertion-import',
         'contrat-rediger', 'contrat-pole', 'contrat-sante', 'contrat-renouveler',
         'prescription-rediger', 'prescription-pole', 'prescription-suivi', 'action-questions',
         'reorientation-demander', 'commission-reorientation', 'organismes-reorientation',
         'file-active', 'statistiques-rsa', 'journal-activite', 'archivage-rgpd', 'mds-organisation']
RUBRIQUES = [("Premiers pas", ['connexion']),
             ("Bénéficiaires", ['beneficiaire-chercher', 'beneficiaire-creer', 'beneficiaire-famille',
                                'beneficiaire-modifier', 'beneficiaire-transferer', 'beneficiaire-sortie']),
             ("Aides financières – AFASE", ['afase-demander', 'afase-ajournement', 'afase-decider', 'afase-transmettre',
                                            'afase-uagaf', 'afase-recours', 'afase-inspecteur']),
             ("Chèques service (CAP) et régie d'urgence", ['cap-demander', 'cap-decider', 'cap-coffre',
                                                           'regie-demander', 'regie-decider']),
             ("Informations préoccupantes", ['ip-saisir', 'ip-binome', 'ip-evaluer', 'ip-synthese', 'ip-inspecteur', 'ip-saisine']),
             ("Au quotidien", ['messagerie', 'ged-deposer', 'rdv-prendre', 'rdv-issue']),
             ("Accompagnement", ['journal-accompagnement', 'budget-foyer', 'ateliers-collectifs', 'statistiques-accompagnement']),
             ("Logement", ['fsl-acces', 'copp']),
             ("Protection des données", ['journal-activite', 'archivage-rgpd']),
             ("Encadrement de la MDS", ['mds-organisation']),
             ("RSA – Insertion", ['insertion-actions', 'insertion-action-locale', 'insertion-import',
                                  'contrat-rediger', 'contrat-pole', 'contrat-sante', 'contrat-renouveler',
                                  'prescription-rediger', 'prescription-pole', 'prescription-suivi',
                                  'action-questions', 'reorientation-demander', 'commission-reorientation',
                                  'organismes-reorientation', 'file-active', 'statistiques-rsa'])]


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
    'ip-saisir': ("Enregistrer et transmettre une IP", "CRIP"),
    'ip-binome': ("Réunion IP et désignation du binôme", "Cadre de la MDS"),
    'ip-evaluer': ("Évaluer une IP", "Binôme : convocations, démarches, rapport"),
    'ip-synthese': ("Synthèse et visas du rapport", "Cadre et binôme"),
    'ip-inspecteur': ("Avis de l'inspecteur sur une IP", "Inspecteur enfance-famille"),
    'ip-saisine': ("Saisine du procureur", "Binôme, cadre, inspecteur"),
    'messagerie': ("Envoyer et lire un message", "La messagerie interne de CID"),
    'ged-deposer': ("Déposer et consulter un document", "La GED du bénéficiaire"),
    'rdv-prendre': ("Prendre un rendez-vous", "Permanence, VAD ou autre rendez-vous"),
    'rdv-issue': ("Noter l'issue d'un rendez-vous", "Venu, absent, annulé, reporté…"),
    'insertion-actions': ("Consulter les actions d'insertion", "Le référentiel commun à toutes les MDS"),
    'insertion-action-locale': ("Créer une action d'insertion locale", "Cadre de MDS"),
    'insertion-import': ("Importer et exporter les actions (CSV)", "Pôle insertion"),
    'contrat-rediger': ("Rédiger et transmettre un contrat RSA", "Référent de MDS"),
    'contrat-pole': ("Réceptionner et valider un contrat", "Pôle insertion : administratif et cadre"),
    'contrat-sante': ("Contrat santé : certificat et avis médical", "Référent et médecin du pôle"),
    'contrat-renouveler': ("Suivre la file active et renouveler", "Référent de MDS"),
    'prescription-rediger': ("Prescrire une action d'insertion", "Référent de MDS"),
    'prescription-pole': ("Valider une prescription, noter le retour du porteur", "Pôle insertion"),
    'prescription-suivi': ("Suivre les prescriptions et le tableau des actions", "Référent de MDS"),
    'action-questions': ("Questions propres à une action", "Pôle insertion, cadre de MDS"),
    'reorientation-demander': ("Demander une réorientation", "Référent de MDS"),
    'commission-reorientation': ("Préparer et tenir la commission de réorientation", "Pôle insertion : administratif et cadre"),
    'organismes-reorientation': ("Organismes de réorientation", "Pôle insertion"),
    'file-active': ("La file active RSA", "Référents, cadres, pôles insertion"),
    'statistiques-rsa': ("Les statistiques RSA", "Référents, cadres, pôles insertion"),
    'journal-activite': ("Le journal d'activité : qui a consulté un dossier", "Cadres de MDS, administrateurs"),
    'archivage-rgpd': ("Archiver les dossiers inactifs (RGPD)", "Cadres de MDS, administrateurs"),
    'mds-organisation': ("Organiser la MDS : fonctions, équipe IP, MDS de proximité", "Cadres de MDS"),
    'journal-accompagnement': ("Le journal de l'accompagnement : entretiens et suites", "Travailleurs sociaux, agents de MDS"),
    'budget-foyer': ("Établir le budget du foyer", "Travailleurs sociaux, agents de MDS"),
    'copp': ("Demande de logement et commission des publics prioritaires", "Travailleurs sociaux de la MDS"),
    'fsl-acces': ("FSL : accès, maintien, énergie, eau", "Travailleurs sociaux, agents administratifs, cadres de MDS"),
    'ateliers-collectifs': ("Organiser un atelier collectif", "Agents de MDS, animateurs"),
    'statistiques-accompagnement': ("Les statistiques de l'accompagnement", "Cadres de MDS, direction"),
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
# INFORMATIONS PRÉOCCUPANTES
DELAIS_IP = ("L'évaluation dure <b>3 mois</b> à compter de la réception par la CRIP, avec un <b>point intermédiaire</b> : "
             "les dates s'affichent en haut de l'IP, et CID envoie des rappels au cadre.")
ACCES_IP = ("Une IP n'est visible que par la CRIP, les inspecteurs, les cadres de la MDS en charge et le binôme d'évaluation. "
            "L'identité du déclarant n'est visible que par la CRIP et les inspecteurs.")

page('ip-saisir', qui="Agents de la CRIP", ou="Menu « Accompagnement » → Informations préoccupantes", duree="10 minutes",
     intro="Enregistrez l'information préoccupante reçue, vérifiez la composition familiale, puis transmettez-la à la MDS en charge.",
     etapes=[
         ("Ouvrir une nouvelle IP", [fig('ip-saisir', '01', "La liste des IP : « Enregistrer une IP ».")],
          ["Ouvrez la liste des <b>informations préoccupantes</b> et cliquez sur <span class=\"clic\">Enregistrer une IP</span>.",
           "La liste se filtre par statut ; les IP dont le point intermédiaire est passé sont en orange, celles qui ont dépassé 3 mois en rouge."], []),
         ("Décrire l'information reçue", [fig('ip-saisir', '02', "Réception, origine, urgence, faits et dangers signalés."),
                                         fig('ip-saisir', '03', "Déclarant, famille et MDS en charge.")],
          ["<b>Réception</b> : la date de réception par la CRIP (le délai de 3 mois court à partir de cette date), l'origine et le niveau d'urgence.",
           "<b>Faits rapportés</b> et <b>dangers signalés</b> ; une <b>situation particulière</b> (grossesse, handicap…) conduira CID à proposer un professionnel de PMI dans le binôme.",
           "<b>Déclarant</b> : nom, qualité, structure, coordonnées, confidentialité demandée.",
           "<b>Famille</b> : saisissez le <b>code du dossier famille</b> dans CID (les enfants sont repris automatiquement) ; sinon le nom et l'adresse de la famille. Choisissez la <b>MDS en charge</b> (et les MDS associées en cas d'enquête conjointe).",
           "Enregistrez."],
          [("attention", "Le déclarant n'apparaît jamais à la MDS, ni dans les courriers, ni dans le rapport.")]),
         ("Vérifier la composition familiale", [fig('ip-saisir', '04', "Adultes concernés et enfants.")],
          ["CID ouvre la <b>composition familiale</b> : pour chaque adulte, sa qualité, son adresse, sa MDS, l'autorité parentale et s'il héberge les enfants.",
           "Les titulaires de l'autorité parentale et l'adulte qui héberge les enfants sont <b>convoqués d'office</b> (décochable). Parents séparés, autre MDS, autre département : chacun reçoit ses propres courriers.",
           "Indiquez <b>chez qui vivent les enfants</b> : leur convocation sera adressée à cet adulte."], []),
         ("Transmettre à la MDS", [fig('ip-saisir', '05', "« Transmettre à la MDS »."),
                                  fig('ip-saisir', '06', "IP transmise : le cadre est prévenu.")],
          ["Sur l'IP, cliquez sur <span class=\"clic\">Transmettre à la MDS</span> : le cadre de la MDS reçoit un message CID.",
           "La CRIP peut encore corriger la saisie (<b>Modifier</b>) jusqu'à la désignation du binôme."], []),
     ],
     savoir=[DELAIS_IP, ACCES_IP],
     ensuite=['ip-binome'])

page('ip-binome', qui="Cadre de la MDS", ou="IP transmise à la MDS", duree="5 minutes",
     intro="Présentez l'IP en réunion, puis désignez les deux professionnels qui l'évalueront.",
     etapes=[
         ("Enregistrer la réunion IP", [fig('ip-binome', '01', "Programmer la réunion IP.")],
          ["Ouvrez l'IP (message CID ou liste des IP). Dans <b>Démarches et réunions</b>, cliquez sur <span class=\"clic\">Réunion IP</span>.",
           "Indiquez la date, le résultat, les personnes et professionnels présents et le compte rendu, puis enregistrez. La réunion peut s'inscrire dans l'agenda.",
           "Tout est daté et compte dans les délais et les statistiques."], []),
         ("Désigner le binôme", [fig('ip-binome', '02', "La proposition de CID et le choix du binôme."),
                                fig('ip-binome', '03', "Le binôme est désigné.")],
          ["CID propose un binôme : l'<b>équipe IP</b> de la MDS d'abord (mention « équipe IP »), puis les moins chargés, et un professionnel de <b>PMI</b> quand il est conseillé (enfant de 5 ans ou moins, situation particulière).",
           "Un professionnel qui <b>suit déjà la famille</b> (référent, aide instruite, entretiens…) n'est pas proposé. Vous pouvez le désigner quand même : ouvrez « Désigner quand même… » et confirmez ; c'est tracé.",
           "Choisissez les deux professionnels et cliquez sur <span class=\"clic\">Valider le binôme</span>.",
           "Les deux professionnels reçoivent un message ; l'IP passe en <b>Évaluation en cours</b>. Le binôme reste modifiable."], []),
     ],
     savoir=[DELAIS_IP,
             "Le cadre peut aussi enregistrer les points d'étape et les réunions de synthèse dans les démarches."],
     ensuite=['ip-evaluer', 'ip-synthese'])

page('ip-evaluer', qui="Binôme d'évaluation (travailleur social, PMI)", ou="IP en évaluation", duree="Tout au long de l'évaluation",
     intro="Convoquez la famille, enregistrez chaque démarche, puis rédigez le rapport et soumettez-le pour la synthèse.",
     etapes=[
         ("Programmer une audition", [fig('ip-evaluer', '01', "Programmer une audition."),
                                     fig('ip-evaluer', '02', "La démarche et le courrier de convocation."),
                                     fig('ip-evaluer', '03', "Le courrier de convocation.", petite=True)],
          ["Ouvrez <span class=\"clic\">Programmer une audition</span> : audition des parents, ou des enfants (même heure, reçus un par un).",
           "Choisissez la date, la durée, les <b>adultes convoqués</b> (un courrier chacun, à son adresse), les enfants (un courrier par foyer, à l'adulte qui les héberge) et les professionnels.",
           "Cliquez sur <b>Programmer et préparer les convocations</b> : les courriers sont produits aussitôt (lien <b>PDF</b> dans les démarches) et l'audition s'inscrit dans l'agenda."], []),
         ("Noter les présences et relancer", [fig('ip-evaluer', '04', "Noter les présences.")],
          ["Après l'audition, notez pour chacun : présent, absent, ou <b>absence justifiée – report convenu</b>.",
           "<b>Reconvoquer</b> : nouvelle date, à l'amiable (date convenue avec la famille) ou par lettre recommandée (le n° de LRAR est demandé)."],
          [("astuce", "Une famille qui ne vient pas malgré la LRAR peut être déclarée « non coopérante » dans le rapport.")]),
         ("Enregistrer les autres démarches", [fig('ip-evaluer', '05', "Appel, VAD, courriel, partenaire…")],
          ["Ouvrez <b>Enregistrer une autre démarche</b> (boutons rapides : Appel, VAD, Synthèse…) : type, date, résultat, personnes contactées, compte rendu.",
           "<b>Mettre à jour</b> sur une démarche prévue permet d'en noter le résultat (réalisé, absent, sans réponse…)."], []),
         ("Rédiger et soumettre le rapport", [fig('ip-evaluer', '06', "Le rapport : déroulé repris automatiquement, puis les rubriques."),
                                             fig('ip-evaluer', '07', "Conclusion pour chaque enfant, préconisation."),
                                             fig('ip-evaluer', '08', "Rapport soumis : le cadre est prévenu.")],
          ["Bouton <b>Rédiger / ouvrir</b> du cadre Rapport : le <b>déroulé de l'évaluation</b> est repris des démarches enregistrées.",
           "Complétez les rubriques (composition familiale, situation et parole des enfants, parole des parents, conditions de vie, partenaires, analyse).",
           "Pour <b>chaque enfant</b> : en danger, en risque de danger ou pas en danger, avec les types de danger constatés.",
           "Choisissez la <b>préconisation</b> et détaillez-la. <b>Enregistrer le brouillon</b> pour y revenir ; <b>Soumettre pour la synthèse</b> quand le rapport est prêt."], []),
     ],
     savoir=[DELAIS_IP, "Une fois soumis, le rapport n'est plus modifiable (sauf renvoi par le cadre ou l'inspecteur)."],
     ensuite=['ip-synthese', 'ip-saisine'])

page('ip-synthese', qui="Cadre de la MDS et binôme", ou="Rapport de l'IP", duree="2 minutes",
     intro="Après la réunion de synthèse, le cadre et un membre du binôme visent le rapport : il part alors à l'inspecteur enfance-famille.",
     etapes=[
         ("Visa du cadre", [fig('ip-synthese', '01', "Date de la réunion de synthèse, « Viser (cadre) ».")],
          ["Ouvrez le rapport soumis. Indiquez la <b>date de la réunion de synthèse</b> et cliquez sur <span class=\"clic\">Viser (cadre)</span>.",
           "Le rapport doit être repris ? Écrivez ce qu'il faut reprendre et cliquez sur <b>Renvoyer au binôme</b>."], []),
         ("Visa du binôme", [fig('ip-synthese', '02', "« Viser (AS) »."),
                            fig('ip-synthese', '03', "IP transmise à l'inspecteur.")],
          ["Un membre du binôme ouvre le rapport et clique sur <span class=\"clic\">Viser (AS)</span>.",
           "Dès que les deux visas sont posés, l'IP est <b>transmise à l'inspecteur</b>, qui est prévenu. La date d'envoi est la fin réelle de l'évaluation (délai respecté ou dépassé)."], []),
     ],
     savoir=["Le rapport s'imprime à tout moment (bouton <b>Imprimer (PDF)</b>)."],
     ensuite=['ip-inspecteur'])

page('ip-inspecteur', qui="Inspecteur enfance-famille", ou="Liste des informations préoccupantes", duree="5 minutes",
     intro="Donnez votre avis sur le rapport : contresigner la préconisation, décider d'une autre suite ou demander un complément.",
     etapes=[
         ("Ouvrir l'IP transmise", [fig('ip-inspecteur', '01', "La liste des IP : statut « Transmise à l'inspecteur ».")],
          ["Vous êtes prévenu par message CID ; dans la liste, l'IP est au statut <b>Transmise à l'inspecteur</b>. Ouvrez son rapport."], []),
         ("Donner son avis", [fig('ip-inspecteur', '02', "« Votre avis »."),
                             fig('ip-inspecteur', '03', "L'IP est clôturée avec votre décision.")],
          ["<b>D'accord avec la préconisation</b> : vous la contresignez.",
           "<b>Autre suite</b> : choisissez la décision (classement, droit commun, AED, saisine du procureur…) et motivez-la.",
           "<b>Complément d'évaluation</b> : le dossier revient au binôme, avec votre commentaire.",
           "Cliquez sur <b>Enregistrer mon avis</b> : en cas d'accord ou d'autre suite, l'IP est <b>clôturée</b> avec votre décision."], []),
     ],
     savoir=[ACCES_IP],
     ensuite=['ip-saisine'])

page('ip-saisine', qui="Binôme, cadre, inspecteur", ou="IP, cadre « Saisine du procureur »", duree="5 minutes",
     intro="À tout moment de l'évaluation : le binôme propose, le cadre décide, l'inspecteur valide. En cas de danger grave et imminent, le cadre peut saisir directement.",
     etapes=[
         ("Proposer (binôme)", [fig('ip-saisine', '01', "Proposer une saisine au cadre.")],
          ["Dans le cadre <b>Saisine du procureur</b>, ouvrez <b>Proposer une saisine du procureur</b> : décrivez le motif, cochez <b>danger grave et imminent</b> si c'est le cas, puis <span class=\"clic\">Proposer au cadre</span>."], []),
         ("Décider (cadre)", [fig('ip-saisine', '02', "Le choix du cadre.")],
          ["Le cadre choisit : <b>Demander à l'inspecteur</b>, <b>Urgence : saisir directement</b>, ou <b>Ne pas retenir</b> (avec un commentaire)."], []),
         ("Valider (inspecteur) et envoyer", [fig('ip-saisine', '03', "La validation de l'inspecteur."),
                                             fig('ip-saisine', '04', "Courrier de saisine et envoi.")],
          ["L'inspecteur <b>valide</b> ou <b>ne valide pas</b> la saisine.",
           "Une fois validée, <b>Imprimer le courrier de saisine</b> ; après l'envoi, indiquez la date et la référence ou le mode d'envoi, puis <b>Saisine envoyée</b>."], []),
     ],
     savoir=["Chaque étape est datée et tracée dans l'IP (journal et messages aux personnes concernées)."],
     ensuite=['ip-evaluer', 'ip-inspecteur'])


# =============================================================================
# AU QUOTIDIEN
page('messagerie', qui="Tous les agents", ou="Menu « Messagerie », ou bouton « Message » d'une fiche usager", duree="2 minutes",
     intro="La messagerie de CID relie les agents entre eux ; un message peut concerner un usager et porter des documents de sa GED.",
     etapes=[
         ("Écrire depuis la fiche usager", [fig('messagerie', '01', "Le bouton « Message » de la fiche usager."),
                                            fig('messagerie', '02', "Destinataire, objet, motif, priorité, message.")],
          ["Sur la fiche de l'usager, cliquez sur <span class=\"clic\">Message</span> : le message est rattaché à cet usager.",
           "Choisissez le <b>destinataire</b> (et éventuellement une copie), l'<b>objet</b>, le <b>motif</b> et la <b>priorité</b>, puis écrivez le message.",
           "Depuis le menu <b>Messagerie → Nouveau message</b>, vous pouvez aussi écrire sans usager, ou rechercher l'usager concerné."], []),
         ("Joindre des documents", [fig('messagerie', '03', "Documents de la GED à joindre, ou nouveaux fichiers.")],
          ["Cochez les <b>documents de la GED</b> de l'usager à joindre.",
           "<b>Ajouter de nouveaux fichiers</b> : ils sont classés automatiquement dans la GED de l'usager, dans la catégorie choisie.",
           "Cliquez sur <span class=\"clic\">Envoyer</span>."], []),
         ("Lire et répondre", [fig('messagerie', '04', "La boîte de réception : le nouveau message en tête."),
                              fig('messagerie', '05', "Le message, ses pièces jointes, « Répondre »."),
                              fig('messagerie', '06', "La réponse.")],
          ["Le nombre de messages non lus s'affiche sur le menu <b>Messagerie</b>.",
           "Ouvrez le message : les pièces jointes se téléchargent d'un clic ; un lien mène au dossier concerné (aide, IP…).",
           "<span class=\"clic\">Répondre</span> : écrivez la réponse (documents possibles), puis envoyez."], []),
         ("Trier ses messages", [fig('messagerie', '07', "Filtres : tous, non lus, urgents ; onglet Envoyés.")],
          ["Filtres <b>Tous</b>, <b>Non lus</b>, <b>Urgents</b> ; l'onglet <b>Envoyés</b> garde vos messages."], []),
     ],
     savoir=["Les circuits de CID (aides, IP…) envoient aussi des messages automatiques : décision à prendre, dossier transmis, rappel de délai."],
     ensuite=['ged-deposer', 'rdv-prendre'])

page('ged-deposer', qui="Agents de la MDS", ou="Fiche usager → bouton « Document »", duree="2 minutes",
     intro="Archivez les pièces d'un usager dans sa GED, avec un type et un niveau de confidentialité.",
     etapes=[
         ("Déposer un document", [fig('ged-deposer', '01', "Le bouton « Document » de la fiche usager."),
                                 fig('ged-deposer', '02', "Fichier, titre, type, confidentialité."),
                                 fig('ged-deposer', '03', "Document archivé.")],
          ["Sur la fiche de l'usager, cliquez sur <span class=\"clic\">Document</span>.",
           "Choisissez le <b>fichier</b>, donnez un <b>titre</b> et le <b>type de document</b> (une date d'expiration si besoin).",
           "<b>Confidentialité</b> : Public DITAS, MDS uniquement, ou Nominatif (agents autorisés).",
           "Cliquez sur <span class=\"clic\">Archiver</span>."],
          [("attention", "Un document médical ne s'enregistre pas dans CID : il se transmet sous pli scellé au médecin du service.")]),
         ("Consulter les documents", [fig('ged-deposer', '04', "Les derniers documents sur la fiche, « Voir tout »."),
                                     fig('ged-deposer', '05', "La GED de l'usager, classée par catégorie."),
                                     fig('ged-deposer', '06', "Le détail d'un document, « Télécharger ».")],
          ["La fiche usager affiche les derniers documents ; <b>Voir tout</b> ouvre la GED complète, classée par catégorie.",
           "Ouvrez un document pour le <b>télécharger</b>, le <b>modifier</b> (titre, type…) ou le supprimer."], []),
     ],
     savoir=["Les pièces déposées dans une demande d'aide ou jointes à un message arrivent aussi dans la GED de l'usager."],
     ensuite=['messagerie'])

page('rdv-prendre', qui="Agents de la MDS", ou="Fiche usager → « Prendre rendez-vous »", duree="2 minutes",
     intro="Réservez un créneau de permanence pour l'usager, ou notez un autre rendez-vous (VAD, hors permanence…).",
     etapes=[
         ("Choisir un créneau de permanence", [fig('rdv-prendre', '01', "« Prendre rendez-vous » sur la fiche usager."),
                                              fig('rdv-prendre', '02', "Les créneaux libres des 15 prochains jours.")],
          ["Sur la fiche de l'usager, cliquez sur <span class=\"clic\">Prendre rendez-vous</span>.",
           "CID liste les créneaux libres des permanences de sa MDS (de J+2 à J+17), ceux du référent en premier. Cliquez sur <span class=\"clic\">Réserver</span>."], []),
         ("Confirmer la réservation", [fig('rdv-prendre', '03', "Domaine, 1er rendez-vous, description, durée."),
                                      fig('rdv-prendre', '04', "Rendez-vous confirmé.")],
          ["Indiquez le <b>domaine</b>, cochez <b>1er rendez-vous</b> s'il y a lieu, décrivez l'objet du rendez-vous (co-intervenants et accompagnant possibles).",
           "<span class=\"clic\">Confirmer la réservation</span> : le rendez-vous apparaît dans l'agenda."], []),
         ("Noter un autre rendez-vous", [fig('rdv-prendre', '05', "VAD, hors permanence, partenaire…")],
          ["Pour une <b>VAD</b> ou un rendez-vous hors permanence : lien <b>noter un autre rendez-vous</b> (ou le bouton « 🏠 VAD, hors permanence… » de la fiche).",
           "Motif, date et heures, agent, lieu, co-intervenants et partenaires invités, puis <b>Enregistrer le rendez-vous</b>.",
           "Un partenaire invité peut recevoir une invitation (fichier agenda ou courriel)."], []),
     ],
     savoir=["Dans l'agenda, un collègue ne voit que « Occupé » : jamais le motif ni le nom de l'usager."],
     ensuite=['rdv-issue'])

page('rdv-issue', qui="Agent du rendez-vous, cadre", ou="Menu « Planning » → Calendrier", duree="1 minute",
     intro="Après le rendez-vous, notez ce qui s'est passé : ces issues alimentent les statistiques de la MDS.",
     etapes=[
         ("Ouvrir le rendez-vous", [fig('rdv-issue', '01', "L'agenda de la semaine.")],
          ["Ouvrez le <b>Calendrier</b> (flèches pour changer de semaine) et cliquez sur le rendez-vous."], []),
         ("Choisir l'issue", [fig('rdv-issue', '02', "Issue du rendez-vous."),
                             fig('rdv-issue', '03', "Issue enregistrée.")],
          ["Choisissez l'<b>issue</b> : réalisé, usager absent, venu non reçu, annulé ou reporté (par l'usager ou la MDS), VAD usager absent…",
           "Cochez <b>1er rendez-vous</b> si besoin, puis <span class=\"clic\">Enregistrer</span>.",
           "<b>Libérer le créneau</b> rend une permanence réservée de nouveau disponible."], []),
     ],
     savoir=["Seuls l'agent du rendez-vous et le cadre peuvent en noter l'issue."],
     ensuite=['rdv-prendre'])


# =============================================================================
# RSA – INSERTION
page('insertion-actions', qui="Tous les agents du module RSA", ou="Menu « Accompagnement » → RSA – Insertion", duree="1 minute",
     intro="Le référentiel réunit les actions départementales et les actions locales des MDS, chacune rattachée à un type commun.",
     etapes=[
         ("Ouvrir le référentiel", [fig('insertion-actions', '01', "L'accueil du module RSA – Insertion.")],
          ["Menu <b>Accompagnement → RSA – Insertion</b>, puis <span class=\"clic\">Actions d'insertion</span>.",
           "Les agents d'un pôle insertion voient aussi le pôle auquel ils appartiennent."], []),
         ("Chercher une action", [fig('insertion-actions', '02', "Filtres : texte, type, niveau, pôle, état.")],
          ["Tapez un mot (libellé, code, porteur, commune) ou choisissez un <b>type</b> d'action (mobilité, santé, garde d'enfants…).",
           "<b>Niveau</b> : actions départementales ou locales (MDS) ; <b>pôle</b> : actions d'un pôle insertion ; <b>état</b> : actives, inactives ou toutes.",
           "Les actions locales sont signalées par l'étiquette <b>locale</b>."], []),
         ("Lire la fiche d'une action", [fig('insertion-actions', '03', "Fiche d'une action.")],
          ["Cliquez sur l'action : périmètre, porteur, durée, public visé, <b>destinataires de la prescription</b>, <b>pièces à joindre</b>, passage en comité de suivi technique."], []),
     ],
     savoir=["Les actions départementales sont visibles de tous ; les actions locales, des agents de la MDS et du pôle insertion qui la couvre.",
             "Une action qui s'arrête passe <b>inactive</b> : elle n'est jamais supprimée (l'historique des parcours reste lisible)."],
     ensuite=['insertion-action-locale', 'insertion-import'])

page('insertion-action-locale', qui="Cadres de MDS", ou="RSA – Insertion → Actions d'insertion", duree="3 minutes",
     intro="Une MDS enregistre ses propres actions (par exemple celles financées pour son territoire), rattachées à un type commun pour des statistiques comparables.",
     etapes=[
         ("Nouvelle action", [fig('insertion-action-locale', '01', "Le bouton « Nouvelle action ».")],
          ["Dans la liste des actions, cliquez sur <span class=\"clic\">Nouvelle action</span>."], []),
         ("Décrire l'action", [fig('insertion-action-locale', '02', "Code, libellé, type, MDS, porteur…")],
          ["<b>Code</b> court propre à CID (ex. LOC-GARDE) et <b>libellé</b>.",
           "<b>Type d'action</b> : obligatoire, il range l'action dans la typologie commune.",
           "Le niveau est <b>Locale (MDS)</b> ; choisissez la <b>MDS</b> si vous en avez plusieurs.",
           "Porteur (ou sa fiche dans l'annuaire des partenaires), territoire, public visé, durée, destinataires de la prescription et pièces à joindre (une par ligne), comité de suivi technique."], []),
         ("Enregistrer", [fig('insertion-action-locale', '03', "L'action est créée.")],
          ["Cliquez sur <span class=\"clic\">Enregistrer</span>. Le bouton <b>Modifier</b> de la fiche permet de la compléter ou de la passer inactive."], []),
     ],
     savoir=["Les actions départementales sont gérées par les pôles insertion (et l'administration)."],
     ensuite=['insertion-actions', 'insertion-import'])

page('insertion-import', qui="Agents des pôles insertion (et cadres de MDS pour leurs actions locales)", ou="RSA – Insertion → Actions d'insertion → Importer (CSV)", duree="5 minutes",
     intro="Créez ou mettez à jour beaucoup d'actions d'un coup avec un tableur : CID montre ce qu'il va faire avant d'enregistrer.",
     etapes=[
         ("Préparer le fichier", [fig('insertion-import', '01', "Le fichier modèle et les codes à utiliser.")],
          ["Téléchargez le <span class=\"clic\">fichier modèle</span> (ou l'export des actions existantes pour les mettre à jour).",
           "Une action par ligne : code, libellé, <b>type</b> (code de la liste « Codes à utiliser »), niveau (DEPARTEMENTAL ou LOCAL), MDS pour une action locale, pôles…",
           "Enregistrez au format <b>CSV</b>, séparateur point-virgule."], []),
         ("Analyser, puis enregistrer", [fig('insertion-import', '02', "L'aperçu : créations, mises à jour, erreurs."),
                                        fig('insertion-import', '03', "Import terminé.")],
          ["Déposez le fichier et cliquez sur <b>Analyser le fichier</b> : rien n'est encore enregistré.",
           "L'aperçu donne, ligne par ligne, les <b>créations</b>, les <b>mises à jour</b> (code déjà connu) et les <b>erreurs</b> (type inconnu, droits insuffisants…).",
           "Cliquez sur <span class=\"clic\">Enregistrer</span> : les lignes en erreur sont ignorées ; corrigez-les dans le fichier et importez-le de nouveau."], []),
         ("Exporter", [fig('insertion-import', '04', "« Exporter (CSV) » reprend les filtres de la liste.")],
          ["<span class=\"clic\">Exporter (CSV)</span> produit un fichier au même format : modifiez-le et réimportez-le pour des mises à jour en masse."], []),
     ],
     savoir=["Rien n'est jamais supprimé par un import : pour retirer une action, mettez « actif » à non.",
             "Chaque ligne est contrôlée avec vos droits : un cadre de MDS n'importe que les actions locales de sa MDS."],
     ensuite=['insertion-actions', 'contrat-rediger'])

page('contrat-rediger', qui="Référents des MDS (agents qui peuvent créer des dossiers)", ou="Fiche du bénéficiaire → Parcours RSA", duree="15 minutes",
     intro="Le contrat se prépare avec le bénéficiaire, s'imprime pour la signature, puis part au pôle insertion d'un clic : plus de ressaisie ni d'envoi papier.",
     etapes=[
         ("Ouvrir les contrats du bénéficiaire", [fig('contrat-rediger', '01', "Le bouton « Parcours RSA » de la fiche."),
                                                  fig('contrat-rediger', '02', "Les contrats du bénéficiaire.")],
          ["Sur la fiche du bénéficiaire, cliquez sur <span class=\"clic\">Parcours RSA</span> (contrats et prescriptions).",
           "Choisissez le type : <b>ouverture</b> (premier contrat), <b>prolongement</b> ou <b>rétablissement</b> (après une suspension ; après une radiation, c'est une nouvelle demande à la CAF et donc une ouverture).",
           "Un prolongement ou un rétablissement reprend le diagnostic et les actions en cours du dernier contrat validé."], []),
         ("Remplir le contrat", [fig('contrat-rediger', '03', "Type, nature, durée, heures d'activité."),
                                 fig('contrat-rediger', '04', "La parole du bénéficiaire et les engagements du référent.")],
          ["Les rubriques suivent l'imprimé : conjoint, diagnostic, incidence financière, <b>parole du bénéficiaire</b>, objectifs et étapes du référent, aide aux transports.",
           "Le conjoint, les enfants et l'identifiant France Travail viennent de la fiche du bénéficiaire.",
           "Le contrat d'engagement sur mesure prévoit <b>au moins 15 heures d'activité par semaine</b> (réglable en administration)."], []),
         ("Choisir les actions", [fig('contrat-rediger', '05', "Les actions du contrat.")],
          ["Choisissez une action du référentiel (actions départementales et actions locales de votre MDS), ou décrivez une autre démarche.",
           "Deux lignes vides sont proposées à chaque enregistrement : enregistrez pour en ajouter d'autres."], []),
         ("Signer et transmettre", [fig('contrat-rediger', '06', "Signature, engagements, transmission."),
                                    fig('contrat-rediger', '07', "Le contrat est transmis au pôle.")],
          ["Imprimez le <span class=\"clic\">Contrat (PDF)</span> pour la signature, puis indiquez la date de signature et cochez l'accord du bénéficiaire.",
           "<span class=\"clic\">Enregistrer et transmettre au pôle</span> : CID vérifie qu'il ne manque rien (signature, accord, objectifs, une action au moins) et prévient l'administratif du pôle."], []),
     ],
     savoir=["Tant qu'il n'est pas transmis, le contrat reste modifiable ; vous pouvez aussi l'annuler.",
             "Un contrat <b>ajourné</b> par la commission revient chez vous, modifiable, avec le motif ; transmettez-le de nouveau une fois repris.",
             "Chaque étape est tracée dans l'historique du contrat, et la décision vous arrive par la messagerie."],
     ensuite=['contrat-sante', 'contrat-pole', 'contrat-renouveler'])

page('contrat-pole', qui="Agents des pôles insertion : administratif et cadre", ou="RSA – Insertion → Contrats et file active", duree="5 minutes",
     intro="Le pôle reçoit les contrats des MDS qu'il couvre, les réceptionne, puis le cadre enregistre la décision de la commission.",
     etapes=[
         ("Voir ce qui est à traiter", [fig('contrat-pole', '01', "La tuile « Contrats et file active »."),
                                        fig('contrat-pole', '02', "L'onglet « À traiter ».")],
          ["L'onglet <b>À traiter</b> montre à chacun ce qu'il doit faire : réceptionner (administratif), décider (cadre), donner un avis (médecin).",
           "Les agents du pôle voient le contrat, pas le reste du dossier social du bénéficiaire."], []),
         ("Réceptionner", [fig('contrat-pole', '03', "La réception, par l'administratif du pôle.")],
          ["Indiquez la date de réception et cliquez sur <span class=\"clic\">Réceptionner le contrat</span> : le cadre est prévenu (et le médecin, pour un contrat santé)."], []),
         ("Décider en commission", [fig('contrat-pole', '04', "La décision du cadre."),
                                    fig('contrat-pole', '05', "La décision enregistrée.")],
          ["<b>Validé</b> : date de début et durée ; CID calcule la date de fin.",
           "<b>Ajourné</b> ou <b>non validé</b> : le motif est obligatoire ; un contrat ajourné repart chez le référent.",
           "Si une aide aux transports est demandée : accordée ou refusée, avec son motif (dérogation, durée maximale déjà accordée, conditions non remplies)."], []),
         ("Valider sauf une action", [fig('contrat-pole', '06', "L'action non retenue et son motif."),
                                      fig('contrat-pole', '07', "La notification au bénéficiaire.")],
          ["<b>Validé sauf action</b> : cochez l'action non retenue et donnez son motif ; le contrat est validé pour <b>3 mois</b> (réglable en administration), le temps de retravailler ce point.",
           "La <span class=\"clic\">Notification au bénéficiaire</span> (PDF) reprend la décision ; son texte se modifie dans les modèles de courriers."], []),
     ],
     savoir=["Le référent est prévenu par la messagerie à chaque décision.",
             "Un contrat santé d'une personne de moins de 60 ans ne peut être validé qu'après l'avis du médecin du pôle."],
     ensuite=['contrat-sante', 'contrat-renouveler'])

page('contrat-sante', qui="Référents des MDS et médecins des pôles insertion", ou="Fiche du contrat", duree="3 minutes",
     intro="Pour un contrat santé d'une personne de moins de 60 ans, le médecin traitant adresse un certificat au seul médecin du pôle. CID ne garde aucun contenu médical.",
     etapes=[
         ("Demander le certificat (référent)", [fig('contrat-sante', '01', "« Demande de certificat » sur la fiche du contrat."),
                                                fig('contrat-sante', '02', "Le courrier remis au bénéficiaire pour son médecin.")],
          ["Dans le contrat, choisissez la nature <b>Santé</b> et le mode de transmission du certificat : <b>sous pli cacheté</b> ou par <b>MSSanté</b> (si le pôle a une adresse MSSanté).",
           "Imprimez la <span class=\"clic\">Demande de certificat</span> et remettez-la au bénéficiaire pour son médecin traitant.",
           "Sans mode de transmission, le contrat ne peut pas partir au pôle."], []),
         ("Donner l'avis (médecin du pôle)", [fig('contrat-sante', '03', "Les contrats santé en attente d'avis."),
                                              fig('contrat-sante', '04', "L'avis du médecin.")],
          ["Les contrats santé en attente d'avis sont dans l'onglet <b>À traiter</b>.",
           "Indiquez la date de réception du certificat, l'avis <b>favorable</b> ou <b>défavorable</b> et, s'il est défavorable, sa motivation.",
           "<b>Aucun détail médical</b> dans la motivation : ni diagnostic, ni traitement. Le certificat reste chez vous."], []),
         ("Suite", [fig('contrat-sante', '05', "L'avis apparaît sur le contrat.")],
          ["Le cadre du pôle est prévenu : la commission peut statuer. Le référent voit l'avis et sa motivation."], []),
     ],
     savoir=["L'âge limite (60 ans) et l'adresse MSSanté du médecin du pôle se règlent en administration.",
             "À partir de 60 ans, le certificat est facultatif."],
     ensuite=['contrat-pole', 'contrat-rediger'])

page('contrat-renouveler', qui="Référents des MDS (et pôles insertion)", ou="RSA – Insertion → Contrats et file active", duree="3 minutes",
     intro="La file active signale les contrats qui arrivent à échéance : le bénéficiaire s'engage à renouveler son contrat un mois avant la fin.",
     etapes=[
         ("Repérer les échéances", [fig('contrat-renouveler', '01', "Les onglets de la file active.")],
          ["<b>À renouveler</b> : contrats validés qui se terminent dans les 30 jours (réglable) et n'ont pas encore de suite.",
           "<b>Échus, sans renouvellement</b> : la date de fin est passée. <b>Validés sauf action</b> : contrats de 3 mois en cours.",
           "La tuile du module donne les mêmes compteurs."], []),
         ("Préparer le contrat suivant", [fig('contrat-renouveler', '02', "« Préparer le contrat suivant »."),
                                          fig('contrat-renouveler', '03', "Le prolongement, prérempli.")],
          ["Sur le contrat en cours, choisissez <b>prolongement</b> ou <b>rétablissement</b>, puis <span class=\"clic\">Préparer le contrat suivant</span>.",
           "Le nouveau contrat reprend le diagnostic, et les souhaits du contrat précédent deviennent « ce que j'ai déjà fait ». Les actions en cours sont reprises."], []),
         ("Reprendre un contrat ajourné", [fig('contrat-renouveler', '04', "Un contrat ajourné, de nouveau modifiable.")],
          ["Un contrat ajourné apparaît dans votre onglet <b>À traiter</b>, avec le motif de la commission : complétez-le et transmettez-le de nouveau."], []),
     ],
     savoir=["Dès qu'un contrat suivant existe, l'alerte du contrat précédent disparaît."],
     ensuite=['contrat-rediger', 'contrat-pole'])

page('prescription-rediger', qui="Référents des MDS (agents qui peuvent créer des dossiers)", ou="Fiche du bénéficiaire → Parcours RSA → Nouvelle prescription", duree="10 minutes",
     intro="La prescription remplace la fiche de liaison papier : CID préremplit le tronc commun, ajoute les questions propres à l'action et l'adresse au porteur (ou au pôle).",
     etapes=[
         ("Choisir l'action", [fig('prescription-rediger', '01', "« Nouvelle prescription » dans le parcours RSA."),
                               fig('prescription-rediger', '02', "Les actions proposées.")],
          ["Dans le <b>Parcours RSA</b> du bénéficiaire, cliquez sur <span class=\"clic\">Nouvelle prescription</span>.",
           "CID propose les actions départementales de votre pôle et les actions locales de votre MDS. Chaque carte indique si l'action passe par le pôle, ses questions propres et ses pièces à joindre.",
           "Cliquez sur <span class=\"clic\">Prescrire cette action</span>."], []),
         ("Compléter le tronc commun", [fig('prescription-rediger', '03', "La situation, préremplie."),
                                        fig('prescription-rediger', '04', "Les freins et l'orientation.")],
          ["La situation est préremplie à partir du dossier et du contrat en cours : identifiant France Travail, qualification, objectifs.",
           "Cochez les <b>freins</b> (liste commune à toutes les MDS) et rédigez le diagnostic, l'avis motivé et les objectifs de l'orientation."], []),
         ("Répondre aux questions de l'action", [fig('prescription-rediger', '05', "Les questions propres à l'action.")],
          ["Les questions marquées d'un astérisque sont obligatoires pour adresser la prescription.",
           "Une réponse <b>à accès restreint</b> (cadenas) n'est visible que de la MDS, du cadre et du médecin du pôle."], []),
         ("Consentement et envoi", [fig('prescription-rediger', '06', "Pièces, consentement, envoi."),
                                    fig('prescription-rediger', '07', "La prescription est adressée.")],
          ["Cochez les pièces fournies (déposées dans les documents de l'usager) et le <b>consentement</b> du bénéficiaire à la transmission.",
           "<span class=\"clic\">Enregistrer et adresser</span> : au porteur directement, ou au pôle si l'action l'exige.",
           "La <span class=\"clic\">Fiche de liaison (PDF)</span> s'imprime pour la signature et pour le porteur, avec un cadre « retour du porteur »."], []),
     ],
     savoir=["Sans consentement, la prescription ne part pas.",
             "Si un contrat est en cours, la prescription y est rattachée : la ligne de l'action s'ajoute toute seule au tableau des actions."],
     ensuite=['prescription-suivi', 'prescription-pole'])

page('prescription-pole', qui="Agents des pôles insertion (administratif et cadre)", ou="RSA – Insertion → Prescriptions", duree="3 minutes",
     intro="Certaines actions passent par le pôle avant le porteur. Le pôle peut aussi noter le retour du porteur quand c'est lui qui le reçoit.",
     etapes=[
         ("Voir ce qui est à valider", [fig('prescription-pole', '01', "La tuile « Prescriptions »."),
                                        fig('prescription-pole', '02', "L'onglet « À traiter ».")],
          ["L'onglet <b>À traiter</b> liste les prescriptions qui attendent la validation de votre pôle.",
           "Le pôle ne voit une prescription qu'une fois adressée par la MDS (jamais en préparation)."], []),
         ("Valider ou refuser", [fig('prescription-pole', '03', "La validation du pôle.")],
          ["<b>Valider</b> : la prescription est adressée au porteur. <b>Refuser</b> : le motif est obligatoire.",
           "Le prescripteur est prévenu par la messagerie."], []),
         ("Noter le retour du porteur", [fig('prescription-pole', '04', "Premier rendez-vous et intégration."),
                                         fig('prescription-pole', '05', "Le suivi enregistré.")],
          ["Premier rendez-vous (présent, absent, excusé, reconvoqué), diagnostic finalisé, puis l'issue : <b>intégrée</b> (date d'entrée), <b>non intégrée</b> (motif) ou <b>réorientée</b>.",
           "Le prescripteur est prévenu, et la ligne de l'action dans le contrat est mise à jour."], []),
     ],
     savoir=["Une action passe par le pôle quand sa fiche porte « Prescription validée par le pôle insertion » (réglage du référentiel, aussi dans l'import CSV : colonne validation_pole)."],
     ensuite=['prescription-suivi', 'action-questions'])

page('prescription-suivi', qui="Référents des MDS", ou="RSA – Insertion → Prescriptions", duree="3 minutes",
     intro="Les prescriptions se suivent jusqu'à la sortie ; le tableau des actions du contrat suit, sans ressaisie.",
     etapes=[
         ("Retrouver ses prescriptions", [fig('prescription-suivi', '01', "Les onglets.")],
          ["<b>En attente du porteur</b> : adressées, pas encore intégrées. <b>En cours</b> : intégrées. <b>Sorties</b> : terminées, arrêtées, réorientées ou non intégrées.",
           "Une prescription <b>refusée</b> par le pôle apparaît dans votre onglet <b>À traiter</b>."], []),
         ("Noter la sortie", [fig('prescription-suivi', '02', "La sortie de l'action.")],
          ["Sur une prescription en cours : <b>terminée</b>, <b>arrêtée</b> (motif obligatoire) ou <b>réorientée</b> (vers l'ASI, un autre dispositif ou France Travail), avec la date de sortie."], []),
         ("Le tableau des actions du contrat", [fig('prescription-suivi', '03', "Entrée, sortie et motif, venus de la prescription.")],
          ["La ligne de l'action porte le numéro et le statut de la prescription ; ses dates et son motif de sortie viennent du retour du porteur.",
           "Dans la rédaction du contrat, ces lignes ne se saisissent pas : elles sont tenues à jour par la prescription."], []),
     ],
     savoir=["Chaque étape est tracée dans l'historique de la prescription."],
     ensuite=['prescription-rediger', 'contrat-renouveler'])

page('action-questions', qui="Pôles insertion (actions départementales), cadres de MDS (actions locales)", ou="RSA – Insertion → Actions d'insertion → une action", duree="5 minutes",
     intro="Chaque action peut ajouter ses propres questions à la prescription : permis de conduire, garde d'enfants, type de projet…",
     etapes=[
         ("Ouvrir les questions de l'action", [fig('action-questions', '01', "Les questions sur la fiche de l'action.")],
          ["Sur la fiche d'une action que vous gérez, cliquez sur <span class=\"clic\">Modifier les questions</span>."], []),
         ("Écrire les questions", [fig('action-questions', '02', "Une question par bloc.")],
          ["Pour chaque question : le libellé, le type de réponse (texte, oui / non, un ou plusieurs choix, date, nombre), les choix (un par ligne), une aide, l'ordre.",
           "<b>Obligatoire</b> : la prescription ne part pas sans réponse. <b>Accès restreint</b> : réponse visible de la MDS, du cadre et du médecin du pôle seulement (jamais de détail médical)."], []),
     ],
     savoir=["Supprimer une question efface aussi ses réponses dans les prescriptions : préférez la reformuler.",
             "Les questions des actions départementales sont conservées par la remise à zéro de démonstration."],
     ensuite=['insertion-actions', 'prescription-rediger'])

page('reorientation-demander', qui="Référents des MDS", ou="Fiche du bénéficiaire → Parcours RSA → Demander une réorientation", duree="5 minutes",
     intro="Quand une personne doit être accompagnée ailleurs (France Travail, CAF, association), le référent inscrit sa situation à la commission trimestrielle de réorientation du pôle. Pas besoin de l'accord du cadre de MDS.",
     etapes=[
         ("Créer la demande", [fig('reorientation-demander', '01', "La rubrique « Réorientation » du parcours RSA.")],
          ["Dans le <b>Parcours RSA</b>, cliquez sur <span class=\"clic\">Demander une réorientation</span>. Les freins de la dernière prescription sont repris."], []),
         ("Motiver la réorientation", [fig('reorientation-demander', '02', "Motif, orientation proposée, avis de la personne.")],
          ["Le <b>motif</b> et l'<b>orientation proposée</b> (France Travail, CAF, association, autre) sont obligatoires ; l'organisme vient de la liste tenue par le pôle.",
           "Indiquez si la personne est informée et d'accord."], []),
         ("Inscrire en commission", [fig('reorientation-demander', '03', "La demande inscrite.")],
          ["<span class=\"clic\">Enregistrer et inscrire en commission</span> : la demande rejoint la prochaine commission programmée de votre pôle, ou attend la suivante. Le pôle est prévenu."], []),
     ],
     savoir=["La décision vous arrive par la messagerie à la clôture de la commission.",
             "Acceptée : à la date d'effet, l'organisme retenu devient le référent RSA de la personne ; elle sort de la file active RSA de la MDS (plus d'alerte de renouvellement), son parcours reste consultable.",
             "Ajournée : la demande est présentée à la commission suivante, sans nouvelle saisie."],
     ensuite=['commission-reorientation', 'contrat-renouveler'])

page('commission-reorientation', qui="Administratifs et cadres des pôles insertion", ou="RSA – Insertion → Réorientation", duree="selon la séance",
     intro="Tous les trimestres, la commission (un membre de chaque MDS, administratifs et cadres du pôle) examine les demandes de réorientation. CID prépare l'ordre du jour, garde les décisions et prévient les référents.",
     etapes=[
         ("Programmer la commission", [fig('commission-reorientation', '01', "La tuile « Réorientation »."),
                                       fig('commission-reorientation', '02', "Programmer une commission.")],
          ["Indiquez la date, l'heure et le lieu : toutes les demandes en attente sont inscrites d'office à l'ordre du jour.",
           "Les demandes inscrites ensuite rejoignent automatiquement la prochaine commission."], []),
         ("Préparer la séance", [fig('commission-reorientation', '03', "L'ordre du jour, par MDS."),
                                 fig('commission-reorientation', '04', "Les participants.")],
          ["L'<span class=\"clic\">Ordre du jour</span> (PDF) se distribue aux membres.",
           "Cochez les agents présents et notez les autres participants.",
           "Un dossier peut être <b>retiré</b> de l'ordre du jour : il passe à la commission suivante."], []),
         ("Noter les décisions", [fig('commission-reorientation', '05', "Réorientation acceptée."),
                                  fig('commission-reorientation', '06', "Réorientation refusée, avec son motif.")],
          ["<b>Acceptée</b> : l'organisme retenu et la date d'effet. <b>Refusée</b> ou <b>ajournée</b> : le motif est obligatoire.",
           "Une décision se corrige tant que la commission n'est pas clôturée."], []),
         ("Clôturer", [fig('commission-reorientation', '07', "La clôture."),
                       fig('commission-reorientation', '08', "Le relevé de décisions.")],
          ["<span class=\"clic\">Clôturer la commission</span> (toutes les décisions notées) : les référents sont prévenus, les dossiers ajournés passent à la commission suivante.",
           "Le <span class=\"clic\">Relevé de décisions</span> (PDF) garde la trace de chaque dossier examiné, ajournés compris."], []),
         ("Informer la personne", [fig('commission-reorientation', '09', "La décision sur la demande."),
                                   fig('commission-reorientation', '10', "La notification au bénéficiaire.")],
          ["Sur chaque demande décidée, la <span class=\"clic\">Notification au bénéficiaire</span> (PDF) reprend la décision et les coordonnées du nouveau référent ; son texte se modifie dans les modèles de courriers."], []),
     ],
     savoir=["Les demandes en préparation ne sont pas visibles du pôle : seulement une fois inscrites."],
     ensuite=['organismes-reorientation', 'reorientation-demander'])

page('organismes-reorientation', qui="Pôles insertion", ou="RSA – Insertion → Réorientation → Organismes de réorientation", duree="2 minutes",
     intro="La liste des organismes qui peuvent devenir le référent RSA d'une personne : France Travail, la CAF et les associations du territoire.",
     etapes=[
         ("Tenir la liste", [fig('organismes-reorientation', '01', "Les organismes.")],
          ["France Travail et la CAF sont créés à l'installation ; ajoutez les associations (nom, catégorie, ville, courriel, téléphone).",
           "Désactivez un organisme qui ne prend plus de bénéficiaires, plutôt que de le supprimer : son historique reste."], []),
     ],
     savoir=["La liste est conservée par la remise à zéro de démonstration."],
     ensuite=['commission-reorientation'])

page('file-active', qui="Référents, cadres de MDS, agents des pôles insertion", ou="RSA – Insertion → File active et statistiques → File active", duree="2 minutes",
     intro="La file active réunit, dans votre périmètre, toutes les personnes suivies au titre du RSA, avec leurs alertes : plus de tableau Excel tenu à la main.",
     etapes=[
         ("Ouvrir la file active", [fig('file-active', '01', "La tuile « File active et statistiques »."),
                                    fig('file-active', '02', "Une ligne par personne.")],
          ["Chacun voit son périmètre : le référent sa file active, le cadre sa MDS, le pôle les MDS de son pôle.",
           "Pour chaque personne : le contrat (en vigueur, sinon le dernier), son échéance, les actions en cours et les <b>alertes</b> (sans contrat en vigueur, à renouveler, échu, validé sauf action, en cours de validation, ajourné, réorientation inscrite)."], []),
         ("Filtrer", [fig('file-active', '03', "Les filtres.")],
          ["Par nom, MDS, référent, commune, nature du contrat ou alerte. « Personnes réorientées » montre celles qui ont quitté la file active (France Travail, CAF, association)."], []),
         ("Exporter", [fig('file-active', '04', "L'export CSV.")],
          ["<span class=\"clic\">Exporter (CSV)</span> reprend la liste filtrée. Le fichier (séparateur « ; », UTF-8) s'ouvre dans LibreOffice, Excel ou tout autre outil."], []),
     ],
     savoir=["La file active ne demande aucune saisie : elle vient des contrats, des prescriptions et des réorientations.",
             "Les agents du pôle voient le contrat, pas le reste du dossier social."],
     ensuite=['statistiques-rsa', 'contrat-renouveler'])

page('statistiques-rsa', qui="Référents, cadres de MDS, agents des pôles insertion", ou="RSA – Insertion → File active et statistiques → Statistiques", duree="2 minutes",
     intro="Les chiffres du RSA, sans saisie : contractualisation, décisions, délais, prescriptions, réorientations, dans votre périmètre et sur la période choisie.",
     etapes=[
         ("Les indicateurs", [fig('statistiques-rsa', '01', "File active, contractualisation, délais.")],
          ["<b>Taux de contractualisation</b> : part de la file active qui a un contrat en vigueur aujourd'hui.",
           "<b>Délais</b> moyens : de la transmission à la réception par le pôle, puis de la réception à la décision.",
           "Choisissez la période (par défaut, depuis le 1er janvier) et, si besoin, une MDS."], []),
         ("Par MDS et par action", [fig('statistiques-rsa', '02', "Comparaison des MDS."),
                                    fig('statistiques-rsa', '03', "Prescriptions et taux d'intégration par action.")],
          ["Pour le pôle et le département : file active, contrats en vigueur, contractualisation, renouvellements et échus par MDS.",
           "Par action : prescriptions, intégrations, non-intégrations et <b>taux d'intégration</b> ; freins relevés et sorties d'action ; décisions de la commission, aide aux transports, contrats santé ; réorientations décidées et vers qui."], []),
         ("Exporter", [fig('statistiques-rsa', '04', "L'export CSV.")],
          ["<span class=\"clic\">Exporter (CSV)</span> rassemble tous les tableaux en une liste « section ; libellé ; nombre ; part », facile à retravailler dans un tableur."], []),
     ],
     savoir=["Les alertes cliquables renvoient vers la file active filtrée."],
     ensuite=['file-active'])

page('journal-activite', qui="Cadres de MDS (dossiers de leur MDS), super-administrateurs (tout)", ou="Fiche de l'usager → Journal du dossier, ou menu Cadre → Journal d'activité", duree="2 minutes",
     intro="CID note qui consulte, modifie, exporte ou télécharge un dossier, et les connexions : en cas de question d'un usager ou de doute, on sait qui a fait quoi.",
     etapes=[
         ("Ouvrir le journal d'un dossier", [fig('journal-activite', '01', "« Journal du dossier » sur la fiche de l'usager.")],
          ["Sur la fiche de l'usager, cliquez sur <span class=\"clic\">Journal du dossier</span> (visible des cadres et des administrateurs)."], []),
         ("Lire le journal", [fig('journal-activite', '02', "Consultations, modifications avec l'avant / après, exports.")],
          ["Chaque ligne : la date, l'agent, l'action (consultation, création, modification, suppression, export, téléchargement) et le détail.",
           "Une modification montre l'<b>avant / après</b> des champs modifiés ; les champs sensibles (n° de sécurité sociale…) ne sont jamais recopiés."], []),
         ("Chercher et exporter", [fig('journal-activite', '03', "Les filtres.")],
          ["Filtrez par usager, agent, action et période (les 30 derniers jours par défaut). <span class=\"clic\">Exporter (CSV)</span> reprend la sélection."], []),
     ],
     savoir=["Le journal est conservé 12 mois, puis effacé automatiquement (durée réglable : clé JOURNAL_DUREE_MOIS de la configuration).",
             "Une même page rouverte par le même agent dans les 10 minutes n'est notée qu'une fois.",
             "Un cadre ne voit que ce qui touche aux dossiers de sa MDS."],
     ensuite=['beneficiaire-modifier'])

page('archivage-rgpd', qui="Cadres de MDS (dossiers de leur MDS), super-administrateurs (tout le département et l'effacement)", ou="Menu Cadre → Archivage RGPD", duree="3 minutes",
     intro="Le RGPD interdit de garder indéfiniment les dossiers des personnes qu'on n'accompagne plus. CID propose les dossiers inactifs depuis 3 ans ; le cadre les archive, l'administrateur les efface ensuite sur décision.",
     etapes=[
         ("Voir les dossiers proposés", [fig('archivage-rgpd', '01', "Les dossiers sans activité depuis 3 ans.")],
          ["Menu <span class=\"clic\">Cadre → Archivage RGPD</span> : la liste des dossiers de votre MDS <b>sans aucune activité depuis 3 ans</b> (fiche, rendez-vous, aides, RSA, documents, messages…), avec la date de la dernière activité.",
           "Les dossiers liés à une <b>information préoccupante</b> ou à un <b>suivi enfance</b> ne sont jamais proposés."], []),
         ("Archiver", [fig('archivage-rgpd', '02', "Le dossier archivé n'apparaît plus que dans cette liste.")],
          ["Cochez les dossiers, choisissez le <b>motif</b> (fin d'accompagnement, sans nouvelles, déménagement…), puis <span class=\"clic\">Archiver la sélection</span>.",
           "Le dossier est <b>masqué partout dans CID</b> (recherche, liste, agenda, famille des proches) et <b>en lecture seule</b>."], []),
         ("Consulter ou désarchiver", [fig('archivage-rgpd', '03', "Le dossier archivé, en lecture seule.")],
          ["Dans « Dossiers archivés », cliquez sur le nom : identité, dates, motif et contenu du dossier.",
           "L'usager revient ? Choisissez le motif puis <span class=\"clic\">Désarchiver</span> : le dossier retrouve son statut d'avant."], []),
         ("Effacer définitivement (administrateur)", [fig('archivage-rgpd', '04', "L'effacement, sur confirmation.")],
          ["Réservé aux super-administrateurs : <span class=\"clic\">Admin → Archivage RGPD → Effacement définitif</span> liste les dossiers <b>archivés depuis au moins 12 mois</b>, avec ce qui sera effacé.",
           "Cochez, tapez <b>EFFACER</b>, confirmez. C'est <b>irréversible</b> : il ne reste qu'une trace anonyme (MDS, dates, motif)."], []),
     ],
     savoir=["Durées réglables dans la configuration : RGPD_ARCHIVAGE_ANS (3 ans) et RGPD_EFFACEMENT_MOIS (12 mois).",
             "Avant d'effacer, vérifier les durées de conservation propres à certaines pièces (comptables notamment) : l'effacement supprime aussi les aides du dossier.",
             "Les rendez-vous passés restent dans l'agenda de la MDS, sans l'usager ; le journal d'activité perd son nom."],
     ensuite=['journal-activite'])

page('journal-accompagnement', qui="Agents de la MDS de l'usager (dossier complet)", ou="Fiche usager → encart « Journal de l'accompagnement »", duree="3 minutes",
     intro="Le journal rassemble les entretiens et, sans ressaisie, tout ce que CID sait déjà du parcours : rendez-vous, aides, RSA, ateliers, budgets. Chaque entretien a une synthèse partagée et une synthèse privée.",
     etapes=[
         ("Ouvrir le journal", [fig('journal-accompagnement', '01', "L'encart de la fiche : les derniers entretiens et les suites en attente.")],
          ["Sur la fiche, l'encart montre les <b>3 derniers entretiens</b> et leurs suites non faites.",
           "<span class=\"clic\">Tout le journal</span> ouvre le fil complet, du plus récent au plus ancien."], []),
         ("Lire et filtrer", [fig('journal-accompagnement', '02', "Le journal filtré sur les entretiens.")],
          ["Cochez une ou plusieurs natures (entretiens, rendez-vous, aides…) ou choisissez un <b>type d'accompagnement</b>, puis <span class=\"clic\">Filtrer</span>.",
           "Le badge <b>légal</b> signale un accompagnement prévu par un texte (RSA, suivi de mesure, MASP).",
           "Votre <b>synthèse privée</b> apparaît sous un cadenas : vos collègues ne la voient pas."],
          [("astuce", "Les informations préoccupantes et la protection de l'enfance n'apparaissent pas dans le journal : elles restent dans leur module, avec leurs propres droits.")]),
         ("Saisir un entretien", [fig('journal-accompagnement', '03', "Le formulaire d'entretien.")],
          ["<span class=\"clic\">Nouvel entretien</span> : date, mode (accueil, RDV, VAD, téléphone…), durée, <b>objet</b> (obligatoire), types d'accompagnement.",
           "Cochez les autres personnes du foyer présentes et, si besoin, les co-intervenants.",
           "<b>Synthèse</b> : des faits, lisibles par les agents qui ont accès au dossier. <b>Synthèse privée</b> : vos notes de travail, pour vous seul(e).",
           "Indiquez une orientation vers un partenaire de l'annuaire et une <b>suite à donner</b> avec son échéance."],
          [("astuce", "Après un rendez-vous réalisé, le journal propose <b>Rédiger le compte rendu</b> : date, heure, mode et durée sont déjà remplis.")]),
         ("Suivre ses suites à donner", [fig('journal-accompagnement', '04', "Mes suites à donner : les échéances dépassées en rouge.")],
          ["Menu <span class=\"clic\">Planning → Mes suites à donner</span> : toutes vos suites non faites (auteur ou co-intervenant).",
           "<span class=\"clic\">Fait</span> quand c'est réglé : la suite apparaît barrée dans le journal."], []),
     ],
     savoir=["Seul l'auteur modifie son entretien.",
             "La synthèse privée reste une donnée du dossier : en cas de demande d'accès de l'usager (RGPD), elle peut lui être communiquée.",
             "Les types d'accompagnement se règlent dans l'administration (Bénéficiaires → Types d'accompagnement)."],
     ensuite=['budget-foyer', 'rdv-issue'])

page('budget-foyer', qui="Agents de la MDS de l'usager (saisie : agents avec le droit de création)", ou="Fiche usager → encart « Budget du foyer »", duree="5 minutes",
     intro="Le budget du foyer se saisit sur la même grille que la demande d'AFASE. Il est daté et historisé, commun aux personnes qui vivent au même foyer, et repris automatiquement dans une nouvelle demande d'AFASE.",
     etapes=[
         ("Voir le budget en cours", [fig('budget-foyer', '01', "L'encart de la fiche : reste à vivre et dettes."),
                                      fig('budget-foyer', '02', "Le détail du budget.")],
          ["L'encart de la fiche résume le dernier budget : ressources, charges payées, <b>reste à vivre</b> par jour et par personne, dettes.",
           "<span class=\"clic\">Voir le détail</span> : les rubriques, les charges <b>non payées</b> (en orange), les dettes et les observations."], []),
         ("Établir ou mettre à jour", [fig('budget-foyer', '04', "La grille de saisie, identique à celle de l'AFASE."),
                                       fig('budget-foyer', '05', "Une ligne par prestation.")],
          ["<span class=\"clic\">Mettre à jour (nouveau budget)</span> : la grille arrive pré-remplie avec le budget précédent ; corrigez ce qui a changé.",
           "Ressources par rubrique (demandeur, conjoint, autres), charges <b>payées</b> ou <b>non payées</b>, dettes, nombre de personnes au foyer.",
           "Chaque prestation a <b>sa ligne</b> : aides au logement, allocations familiales, complément familial, ASF, PAJE, PreParE, prime d'activité, AAH, AEEH, PCH, ADA, bourses. « Autres » sert seulement à ce qui n'a pas de ligne, en précisant.",
           "Le reste à vivre se calcule en direct : (ressources − charges payées) / personnes / 30."],
          [("astuce", "Pas encore de budget du foyer ? La page propose de repartir du budget de la dernière demande d'AFASE.")]),
         ("Retrouver l'historique", [fig('budget-foyer', '03', "Les budgets successifs.")],
          ["Chaque mise à jour crée un nouveau budget daté : les anciens restent dans l'<b>historique</b>.",
           "<span class=\"clic\">Corriger ce budget</span> sert seulement à rectifier une erreur de saisie."], []),
     ],
     savoir=["Une personne du même foyer (lien « vit au foyer ») sans budget à elle voit celui du foyer, avec la mention « même foyer ».",
             "Une nouvelle demande d'AFASE reprend le budget du foyer : vérifiez-le à l'étape Budget."],
     ensuite=['afase-demander', 'journal-accompagnement'])

page('ateliers-collectifs', qui="Agents de la MDS (consultation) ; agents avec le droit de création (séances, inscriptions)", ou="Menu Planning → Ateliers collectifs", duree="5 minutes",
     intro="Un atelier est un thème (cuisine, budget, numérique…), une séance une date de cet atelier. CID gère les places, la liste d'attente, la condition d'âge, les présences et la feuille d'émargement.",
     avant=["Les ateliers (thèmes) sont créés par un administrateur : Admin → Planning → Ateliers, pour une MDS ou pour tout le Département."],
     etapes=[
         ("Voir les séances et en créer une", [fig('ateliers-collectifs', '01', "Les séances à venir de la MDS.")],
          ["Menu <span class=\"clic\">Planning → Ateliers collectifs</span> : les séances à venir et passées de votre MDS, avec les inscrits et la liste d'attente.",
           "<span class=\"clic\">Nouvelle séance</span> : atelier, date, horaires, lieu, animateur, partenaire, places (vide = sans limite), condition d'âge, gratuit ou payant."], []),
         ("Inscrire", [fig('ateliers-collectifs', '03', "Inscrire un usager suivi ou une personne extérieure.")],
          ["<b>Usager suivi</b> : cherchez-le par son nom ou son code, puis <span class=\"clic\">Inscrire</span>. Si l'âge ne correspond pas, CID prévient et propose <b>Inscrire quand même</b>.",
           "<b>Personne extérieure</b> ou <b>accompagnant</b> : prénom et nom, et seulement de quoi la prévenir.",
           "Séance complète : la personne part en <b>liste d'attente</b>."],
          [("astuce", "Quand un inscrit se désinscrit, la première personne de la liste d'attente passe inscrite automatiquement. Pensez à la prévenir.")]),
         ("Le jour de la séance", [fig('ateliers-collectifs', '04', "La feuille d'émargement à imprimer."),
                                   fig('ateliers-collectifs', '02', "Présences et paiements.")],
          ["<span class=\"clic\">Feuille d'émargement</span> : le PDF des inscrits, avec 3 lignes libres. <span class=\"clic\">CSV</span> pour un tableur.",
           "Après la séance, notez la présence de chacun (présent, absent, excusé) et, si c'est payant, le paiement, puis <span class=\"clic\">Enregistrer les présences</span>."], []),
     ],
     savoir=["La participation apparaît sur la fiche de l'usager (encart « Ateliers collectifs ») et dans son journal.",
             "Une séance annulée n'accepte plus d'inscription ; elle peut être rétablie."],
     ensuite=['journal-accompagnement'])

page('statistiques-accompagnement', qui="Cadres de MDS (leur MDS, détail par agent) ; direction (tout le département, sans détail par agent)", ou="Menu Accompagnement → Statistiques de l'accompagnement", duree="2 minutes",
     intro="Une page pour trois usages : piloter l'équipe de la MDS, préparer le rapport d'activité annuel, comparer les MDS. Elle compte les entretiens du journal, le public accompagné, les budgets du foyer et les ateliers.",
     etapes=[
         ("Choisir la période", [fig('statistiques-accompagnement', '01', "Les chiffres clés de la période.")],
          ["Par défaut : du 1er janvier à aujourd'hui. Changez les dates, ou cliquez une année après <b>Rapport annuel</b>.",
           "Les cartes du haut : entretiens, heures, <b>file active</b> (personnes vues), personnes vues pour la première fois, part d'accompagnement <b>légal</b>, suites en retard.",
           "<span class=\"clic\">Imprimer / PDF</span> donne une page propre pour le rapport ; <span class=\"clic\">CSV</span> ouvre les chiffres dans un tableur."], []),
         ("Lire l'activité", [fig('statistiques-accompagnement', '02', "Types d'accompagnement, modes d'entretien, orientations.")],
          ["Par type d'accompagnement : nombre d'entretiens et de personnes. Par mode : rendez-vous, téléphone, visite à domicile…",
           "Les <b>orientations</b> montrent vers quels partenaires la MDS oriente le plus."], []),
         ("Piloter l'équipe (cadre de MDS)", [fig('statistiques-accompagnement', '03', "Le détail par agent, réservé au cadre de la MDS.")],
          ["Pour chaque agent : entretiens, heures, personnes vues, suites en retard.",
           "Ce tableau n'apparaît que pour le cadre de la MDS : la direction ne le voit jamais."], []),
         ("Budgets et ateliers", [fig('statistiques-accompagnement', '04', "Reste à vivre, impayés, dettes.")],
          ["Budgets : le dernier budget de chaque foyer établi sur la période, réparti par tranches de reste à vivre, avec la médiane, les impayés et les dettes.",
           "Ateliers : séances, remplissage, présence, et la <b>liste d'attente</b>, qui mesure un besoin non couvert."], []),
         ("Comparer les MDS (direction)", [fig('statistiques-accompagnement', '05', "Une ligne par MDS.")],
          ["Avec le droit « statistiques du département », la page couvre toutes les MDS et ajoute le tableau de comparaison.",
           "Choisissez une MDS dans la liste pour voir son détail (sans le détail par agent)."], []),
     ],
     savoir=["<b>Secret statistique</b> : de 1 à 4 personnes ou foyers, la page affiche « &lt; 5 », sans pourcentage qui permettrait de retrouver le chiffre.",
             "Aucun texte libre n'est compté : ni les synthèses, ni les synthèses privées.",
             "Les chiffres valent ce que vaut la saisie : un entretien non noté dans le journal n'existe pas pour les statistiques.",
             "Un entretien est compté dans la MDS actuelle de l'usager.",
             "Rendez-vous, aides, RSA et IP gardent leurs propres pages de statistiques."],
     ensuite=['journal-accompagnement', 'budget-foyer', 'ateliers-collectifs'])

page('mds-organisation', qui="Cadres de MDS (agents de leur MDS) ; super-administrateurs (type et rattachement des MDS)",
     ou="Fiche de la MDS → Gestion des agents", duree="5 minutes",
     intro="Chaque agent a une fonction dans sa MDS ; son intitulé est repris sous sa signature. Le cadre désigne aussi l'équipe IP. Une MDS de proximité dépend d'une MDS de territoire, dont le CODIR voit ses dossiers.",
     etapes=[
         ("Type de MDS et rattachement", [fig('mds-organisation', '01', "MDS de proximité rattachée à sa MDS de territoire.")],
          ["Sur la fiche de la MDS, <span class=\"clic\">Modifier</span> : choisissez le <b>type</b> (MDS de territoire ou de proximité).",
           "Pour une MDS de proximité, choisissez sa <b>MDS de territoire de rattachement</b>, puis enregistrez."], []),
         ("Fonction et intitulé", [fig('mds-organisation', '02', "La fonction et l'intitulé repris sur les courriers.")],
          ["<span class=\"clic\">Gestion des agents</span> → icône de modification de l'agent.",
           "<b>Fonction</b> : directeur, adjoint enfance, adjoint prévention, médecin PMI, secrétaire général (CODIR), cadre ou adjoint de proximité, ou « Autre ».",
           "L'<b>intitulé</b> est proposé d'après la fonction et la MDS. Corrigez-le au besoin (« Directrice de la MDS de territoire de … »). Pour « Autre », écrivez-le (référent RSA…)."],
          [("info", "L'intitulé figure sous la signature des notifications AFASE, dans la demande d'AFASE, la remise des chèques service, le visa du rapport IP et la saisine. Vide : seul le nom apparaît.")]),
         ("Désigner l'équipe IP", [fig('mds-organisation', '03', "La case « Équipe IP ».")],
          ["Sur la même page, cochez <b>Équipe IP</b> pour les professionnels qui évaluent les informations préoccupantes, puis <span class=\"clic\">Mettre à jour le profil</span>.",
           "Ils sont proposés en premier pour les binômes, avec la mention « équipe IP ». Vous restez libre de choisir quelqu'un d'autre."], []),
         ("Le CODIR et les MDS de proximité", [fig('mds-organisation', '04', "Dans la MDS de proximité : les membres du CODIR du territoire.")],
          ["Un agent dont la fonction est au CODIR de la MDS de territoire reçoit <b>automatiquement</b> un accès à chaque MDS de proximité rattachée : il en voit les dossiers.",
           "Dans la liste des agents de la MDS de proximité, il apparaît avec la mention <b>CODIR</b> et « Géré depuis … » : cet accès se modifie depuis la MDS de territoire, et suit son rattachement d'origine (désactivation, changement de fonction)."],
          [("attention", "Cet accès ne donne pas la gestion des comptes de la MDS de proximité. Ses agents, eux, ne voient pas les dossiers de la MDS de territoire.")]),
     ],
     savoir=["Pilote des IP : le cadre de proximité en MDS de proximité, l'adjoint enfance en MDS de territoire ; à défaut, le responsable de la MDS.",
             "Le médecin PMI de la MDS de territoire couvre aussi les MDS de proximité : il peut y être proposé pour un binôme IP.",
             "L'adresse mail des agents reste interne : elle n'apparaît sur aucun courrier."],
     ensuite=['ip-binome'])

page('fsl-acces', qui="Agents de la MDS de l'usager (saisie : agents avec le droit de création, dont les administratifs pour l'énergie et l'eau) ; cadre de la MDS (pièces manquantes)",
     ou="Fiche usager → encart « Logement – FSL »", duree="15 minutes",
     intro="CID prépare la demande au FSL (accès, maintien ou concordat, impayés d'énergie ou d'eau) avec ce qu'il connaît déjà, imprime le dossier sur les formulaires du gestionnaire (ou une trame CID) et suit l'envoi et la réponse.",
     avant=["Mettez à jour le <b>budget du foyer</b> et le <b>réseau familial</b> : la demande en reprend les ressources et la composition."],
     etapes=[
         ("Créer la demande", [fig('fsl-acces', '01', "Les boutons de l'encart « Logement – FSL ».")],
          ["Sur la fiche, encart <b>Logement – FSL</b>, cliquez sur <span class=\"clic\">FSL accès</span>, <span class=\"clic\">FSL maintien</span>, <span class=\"clic\">FSL énergie</span> ou <span class=\"clic\">FSL eau</span>.",
           "CID ouvre la demande préremplie : n° CAF, situation familiale, personnes du foyer, ressources du budget, loyer et aide au logement actuels, vos coordonnées (courriel de la MDS)."], []),
         ("Compléter et vérifier", [fig('fsl-acces', '02', "Les ressources reprises du budget du foyer."),
                                   fig('fsl-acces', '03', "Les pièces : fournie, à fournir, sans objet.")],
          ["Vérifiez chaque rubrique : ressources par personne, logement antérieur, <b>nouveau logement</b> (bailleur social ou privé, loyer, caution, AL prévisionnelle).",
           "Indiquez la <b>proposition</b> : garantie de paiement, caution, 1<sup>er</sup> loyer, compteurs, assurance, équipements ; puis l'<b>avis motivé</b> et le prêt ou la subvention proposés.",
           "Cochez l'état de chaque <b>pièce</b>, puis <span class=\"clic\">Enregistrer</span>."],
          [("astuce", "CID calcule le total des ressources et un taux d'effort indicatif, et prévient si un plafond du règlement est dépassé.")]),
         ("Imprimer le dossier", [fig('fsl-acces', '04', "La demande et la liste des documents du dossier."),
                                  fig('fsl-acces', '05', "Le dossier PDF (ici la trame CID).", petite=True)],
          ["<span class=\"clic\">Dossier PDF</span> : CID assemble les documents qui concernent la demande (contrat de prêt si prêt, fiche du logement si bailleur privé…).",
           "Quand les formulaires du gestionnaire sont déposés dans CID, ils sont remplis <b>à leur place</b>, page par page ; sinon CID produit une trame avec les mêmes rubriques et signale les imprimés à joindre vierges.",
           "Faites signer, ajoutez le cachet de la structure."], []),
         ("Le visa du cadre", [fig('fsl-acces', '06', "Le cadre vise la demande (et rédige la note s'il manque des pièces).")],
          ["Toute demande FSL part avec le <b>visa du cadre</b> : cliquez sur <span class=\"clic\">Demander le visa du cadre</span>, il reçoit un message CID.",
           "En un clic sur <span class=\"clic\">Viser la demande</span>, le cadre appose ses <b>initiales et la date</b> (et sa signature numérisée si elle a été validée) sur le dossier.",
           "S'il manque des pièces, il rédige en plus la <b>note explicative</b>, jointe au dossier (argumentaire de pièces manquantes). Il peut aussi renvoyer la demande à l'agent."], []),
         ("Envoyer : par mail d'abord", [fig('fsl-acces', '09', "Envoi par mail ou impression pour envoi.")],
          ["Une fois la demande visée : <span class=\"clic\">Envoi par mail</span> (destinataire à saisir, objet prérempli, pièces de la GED à joindre) ou, seulement si le destinataire l'exige, <span class=\"clic\">Imprimer pour envoi</span>.",
           "Chaque envoi par mail compte dans le <b>papier économisé</b> (menu Accompagnement).",
           "À réception de la réponse : accordée (montants, garantie), ajournée (pièces demandées : complétez puis renvoyez) ou refusée."], []),
         ("Maintien ou concordat", [fig('fsl-acces', '08', "Logement et dette locative : maintien ou concordat.")],
          ["Choisissez <b>FSL maintien</b> (paiement du résiduel repris depuis 3 mois) ou <b>FSL concordat</b> (6 mois, remise de dette du bailleur).",
           "La partie logement est à compléter par le bailleur : CID la préremplit (loyer, AL) ; indiquez la dette locative, le mois de reprise du paiement, la saisine de la CCAPEX ou de la commission de surendettement et, pour un concordat, la remise du bailleur.",
           "Le dossier ajoute les engagements du locataire et du bailleur et, pour un concordat, la convention de résorption de la dette."],
          [("attention", "Concordat : CID prévient si la remise du bailleur est absente ou inférieure au tiers de la dette.")]),
         ("Énergie et eau", [fig('fsl-acces', '07', "Une demande d'aide aux impayés d'énergie instruite par un agent administratif.")],
          ["Même démarche : CID préremplit l'adresse, le loyer, le foyer, les ressources et, pour l'énergie, la dette d'électricité non payée du budget du foyer.",
           "Indiquez le fournisseur ou le distributeur, la facture ou les dettes, la participation du ménage et le plan proposé par le fournisseur.",
           "Pour une facture de <b>moins de 500 €</b>, un <b>agent administratif</b> peut instruire la demande : cochez « Instruite par un agent administratif » et ajoutez un commentaire si besoin ; l'avis du travailleur social n'est alors pas demandé. Au-delà, CID demande l'avis d'un travailleur social."], []),
     ],
     savoir=["Les formulaires officiels se déposent vierges en administration (Logement → Formulaires officiels), avec un aperçu sur données fictives. Ils ne sont jamais publiés avec CID.",
             "Tout est daté dans l'historique de la demande."],
     ensuite=['budget-foyer', 'beneficiaire-famille'])

page('copp', qui="Agents de la MDS de l'usager (saisie : agents avec le droit de création)",
     ou="Fiche usager → encart « Logement »", duree="20 minutes",
     intro="Renseignez la demande de logement social (numéro unique, DALO, Al'In), puis saisissez la commission des publics prioritaires : CID préremplit la fiche de saisine, vous rédigez le rapport social, joignez les justificatifs et envoyez le tout par mail.",
     etapes=[
         ("La demande de logement social", [fig('copp', '01', "L'encart « Logement » de la fiche."),
                                            fig('copp', '02', "Numéro unique, DALO, mutation, Al'In, souhaits.")],
          ["Encart <b>Logement</b> → <span class=\"clic\">Demande de logement</span> : numéro unique et date de création (CID calcule l'ancienneté et prévient avant le renouvellement annuel), DALO, mutation, Al'In, communes et logement souhaités.",
           "Ces informations sont reprises dans la saisine de la commission et le diagnostic social et financier."], []),
         ("Saisir la commission", [fig('copp', '03', "Motifs de la demande et rapport social.")],
          ["<span class=\"clic\">Saisine commission des publics prioritaires (COPP)</span> : la fiche arrive préremplie (référent, ménage, n° de sécurité sociale, logement actuel, ressources, taux d'effort, reste à vivre, endettement, DALO, souhaits) et la prochaine séance est proposée.",
           "Complétez ce que CID ne connaît pas (revenu fiscal de référence, plafonds, typologie…), cochez un ou plusieurs <b>motifs</b> (DALO trop ancien ou refusé, expulsion, sur-occupation, logement indigne, handicap, violences intrafamiliales…) et rédigez le <b>rapport social</b>."],
          [("astuce", "La mesure d'accompagnement en cours se choisit dans une liste (ASELL, AVDL, MASP…) ou s'écrit librement.")]),
         ("Les justificatifs", [fig('copp', '04', "Cocher les pièces de la GED ou en ajouter.")],
          ["Cochez les pièces déjà dans la GED de l'usager.",
           "Pour une mise à jour ou un remplacement (identité, situation familiale ou professionnelle, ressources…), ajoutez le fichier : il est déposé dans la GED de l'usager et joint à la saisine."], []),
         ("Envoyer par mail", [fig('copp', '05', "La saisine prête à partir."), fig('copp', '06', "Destinataire, objet prérempli, pièces jointes.")],
          ["<span class=\"clic\">Envoi par mail</span> : saisissez l'adresse de la commission de votre territoire ; l'objet est prérempli (« MDST – ville – Fiche saisine rapport social et justificatifs pour COPP – NOM Prénom ») ; la fiche PDF et les pièces cochées sont jointes.",
           "<span class=\"clic\">Imprimer pour envoi</span> seulement si le destinataire l'exige.",
           "Après la séance, enregistrez la <b>décision ou préconisation</b> de la commission."], []),
         ("Le papier économisé", [fig('copp', '07', "La statistique collective.")],
          ["Menu <span class=\"clic\">Accompagnement → Papier économisé</span> : les pages non imprimées grâce aux envois par mail (FSL, COPP), pour la MDS ou tout le Département.",
           "La statistique est collective : elle n'est jamais calculée par agent."], []),
     ],
     savoir=["Les séances de la commission (date, date limite de dépôt, lieu) se paramètrent en administration : Logement → Commissions des publics prioritaires. La fiche officielle se dépose vierge dans Logement → Formulaires officiels ; sinon CID imprime une trame avec les mêmes rubriques.",
             "Le dispositif est local : un autre territoire peut le nommer autrement ou ne pas l'utiliser."],
     ensuite=['fsl-acces', 'budget-foyer'])

# =============================================================================
# Sommaire
a_venir = ''.join(f'<a class="avenir"><b>{t}</b><span>Fiche à venir</span></a>' for t in
                  ["RSA – comités de suivi technique, suivi des heures d'activité", "Enfance",
                   "Logement – prévention des expulsions locatives"])
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
