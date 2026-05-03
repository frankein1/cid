# Contribuer à ce projet / Contributing to this Project

---

###### 🇫🇷 Français ######

Merci de votre intérêt pour cet outil destiné aux travailleurs sociaux ! 
Ce projet est conçu pour être libre, ouvert et évolutif grâce à la communauté.

### Comment contribuer ?

Nous accueillons toutes les propositions d'améliorations, de corrections de bugs ou de nouvelles fonctionnalités. Voici la procédure détaillée à suivre :

1. **Fork le projet** : Cliquez sur le bouton "Fork" en haut à droite du dépôt pour créer une copie sur votre compte GitHub.
2. **Clonez et créez une branche** : Clonez votre fork localement et créez une nouvelle branche dédiée à votre tâche.
   ```bash
   git clone https://github.com/VOTRE_UTILISATEUR/cid.git
   cd cid
   git checkout -b feature/nouvelle-fonctionnalite

    Commitez vos changements : Faites vos modifications et validez-les avec des messages clairs.

    git add .
    git commit -m "Ajout de la fonction X"

    Poussez vers votre fork : Envoyez votre branche vers votre dépôt distant.

    git push origin feature/nouvelle-fonctionnalite

    Astuce importante : Avant de pousser, assurez-vous que votre fork est à jour avec le projet original. Si le projet a évolué depuis votre fork, mettez-le à jour pour éviter les conflits de fusion :

    # Ajoutez le dépôt original comme "upstream"
    git remote add upstream https://github.com/frankein1/cid.git

    # Récupérez les dernières mises à jour
    git fetch upstream

    # Fusionnez la branche principale du projet original avec votre branche locale
    git merge upstream/main

    # Poussez votre branche mise à jour vers VOTRE fork
    git push origin feature/votre-branche

    Ouvrez une Pull Request (PR) : Allez sur le dépôt original et cliquez sur "Compare & pull request".
        Titre : Soyez descriptif (ex: "Ajout du module de gestion des dossiers patients").
        Description : Expliquez ce que vous avez fait, pourquoi c'est utile pour les travailleurs sociaux, et comment tester la fonctionnalité.
        Lien vers une Issue : Si vous répondez à une demande existante, mentionnez-la (ex: "Closes #12").
        Une fois la PR ouverte, le mainteneur recevra une notification pour examiner et potentiellement fusionner votre code.

Pourquoi ouvrir une PR ?

Notre objectif est de créer un outil communautaire riche. En ouvrant une Pull Request plutôt que de laisser votre code dans un fork isolé :

    Vous permettez à la communauté de bénéficier de vos ajouts immédiatement.
    Vous aidez à améliorer le projet principal pour tous les acteurs du social.
    Vous facilitez l'intégration de fonctionnalités que je n'avais pas envisagées initialement.

Note importante : Bien que la licence AGPLv3 garantisse que vos modifications restent open-source, nous vous encourageons vivement à proposer vos améliorations via une PR pour qu'elles soient intégrées directement au projet principal. Cela évite la fragmentation de l'outil et assure que tout le monde bénéficie des mêmes évolutions.
Directives de code

    Respectez le style de code existant (indentation, noms de variables, etc.).
    Si vous ajoutez une fonctionnalité complexe, ajoutez des commentaires explicatifs et mettez à jour la documentation si nécessaire.
    Assurez-vous que le code fonctionne sur les environnements cibles (navigateurs modernes, systèmes d'exploitation courants utilisés par les travailleurs sociaux).
    Testez vos modifications localement avant de pousser.

Questions ?

Si vous avez des questions sur la manière de contribuer, des problèmes techniques ou des besoins spécifiques du projet, n'hésitez pas à ouvrir une "Issue" pour en discuter.

Merci de faire partie de cette initiative pour le bien commun !


###### 🇬🇧 English ######

Thank you for your interest in this tool designed for social workers! This project is built to be free, open, and evolving thanks to the community.
How to Contribute

We welcome all proposals for improvements, bug fixes, or new features. Here is the detailed procedure to follow:

    Fork the project : Click the "Fork" button in the top right corner of the repository to create a copy on your GitHub account.
    Clone and create a branch : Clone your fork locally and create a new branch dedicated to your task.

    git clone https://github.com/YOUR_USERNAME/cid.git
    cd cid
    git checkout -b feature/new-feature

    Commit your changes : Make your modifications and validate them with clear messages.

    git add .
    git commit -m "Add feature X"

    Push to your fork : Send your branch to your remote repository.

    git push origin feature/new-feature

    Important Tip : Before pushing, ensure your fork is up-to-date with the original project. If the project has evolved since you forked it, update it to avoid merge conflicts:

    # Add the original repository as "upstream"
    git remote add upstream https://github.com/frankein1/cid.git

    # Fetch the latest updates
    git fetch upstream

    # Merge the main branch of the original project with your local branch
    git merge upstream/main

    # Push your updated branch to YOUR fork
    git push origin feature/your-branch

    Open a Pull Request (PR) : Go to the original repository and click "Compare & pull request".
        Title : Be descriptive (e.g., "Add patient file management module").
        Description : Explain what you did, why it is useful for social workers, and how to test the feature.
        Link to an Issue : If you are addressing an existing request, mention it (e.g., "Closes #12").
        Once the PR is opened, the maintainer will receive a notification to review and potentially merge your code.

Why Open a PR?

Our goal is to create a rich community tool. By opening a Pull Request instead of leaving your code in an isolated fork:

    You allow the community to benefit from your additions immediately.
    You help improve the main project for all social sector actors.
    You facilitate the integration of features I hadn't initially envisioned.

Important Note: While the AGPLv3 license ensures that your modifications remain open-source, we strongly encourage you to propose your improvements via a PR so they can be integrated directly into the main project. This avoids fragmenting the tool and ensures everyone benefits from the same evolutions.
Code Guidelines

    Respect the existing code style (indentation, variable names, etc.).
    If you add a complex feature, add explanatory comments and update the documentation if necessary.
    Ensure the code works on target environments (modern browsers, common operating systems used by social workers).
    Test your modifications locally before pushing.

Questions?

If you have questions about how to contribute, encounter technical issues, or have specific project needs, please feel free to open an "Issue" to discuss.

Thank you for being part of this initiative for the common good!