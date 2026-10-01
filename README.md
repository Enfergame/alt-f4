# README – Agent Discord / Backdoor de démonstration

Ce fichier est un script Python autonome qui simule un agent de contrôle à distance basé sur un webhook Discord. Son objectif apparent est de permettre à un attaquant ou à un testeur autorisé de recevoir des commandes depuis Discord, puis d’exécuter des actions locales sur la machine cible, comme la capture d’écran, la récupération d’informations système, la fermeture de fenêtres, le redémarrage ou le nettoyage des traces.

> Note importante : ce script est un exemple de code de type Proof of Concept / laboratoire. Il contient des éléments de type backdoor, keylogger, exfiltration et contrôle distant. Il ne doit être utilisé que dans un contexte strictement autorisé, pédagogique ou de tests éthiques.

---

## 1. Vue d’ensemble

Le script est structuré comme un mini-agent autonome. Il comporte :

- une classe `DiscordBot` pour interagir avec Discord via webhook ou API;
- des fonctions de détection de la plateforme (Windows, Linux, macOS);
- des commandes de contrôle distantes;
- des fonctions de collecte d’informations;
- une boucle principale qui “attend” des commandes ou simulate une attente.

En pratique, le script est conçu pour être exécuté sur une machine cible et envoyer des messages à un canal Discord, de façon à recevoir des instructions depuis cet environnement.

---

## 2. Ce que le programme essaie de faire

Le code vise à reproduire un mécanisme simple de :

1. se connecter à un canal Discord via un webhook;
2. recevoir des commandes au format texte comme `!screenshot`, `!ip`, `!reboot`, etc.;
3. exécuter des actions locales;
4. renvoyer des résultats ou des messages dans Discord.

Cela ressemble à un mode de commande distant “lightweight” ou un canal de contrôle via le webhooks Discord.

---

## 3. Structure du fichier

### 3.1 Imports

Le script importe des modules Python standard comme :

- `os`, `sys`, `time`, `json`, `random`, `shutil`, `socket`, `urllib.request`, `urllib.error`, `ssl`, `re`;
- `datetime` pour les timestamps;
- `Path` pour manipuler les chemins;
- `typing` pour les annotations de type.

Ces imports servent à la fois à la communication réseau, au système de fichiers, à la gestion des processus et à la collecte d’informations système.

---

## 4. La classe `DiscordBot`

### 4.1 Rôle

La classe `DiscordBot` est le point central de communication avec Discord. Elle encapsule :

- le webhook ID;
- le token API Discord optionnel;
- la base de l’URL Discord;
- la gestion des requêtes HTTP;
- la récupération de l’ID du dernier message envoyé.

### 4.2 Configuration

Le script contient :

```python
DISCORD_WEBHOOK_ID = "1547230722849378336"
DISCORD_API_TOKEN = "..."
```

Ces valeurs sont destinées à identifier le webhook Discord cible et éventuellement un token API. Ce sont des éléments de configuration qu’un agent exécutable utiliserait pour se connecter à un canal Discord précis.

### 4.3 `__init__`

La méthode `__init__` initialise :

- `self.webhook_id`
- `self.api_token`
- `self.base_url`
- `self.last_message_id`
- `self.channel_id`

Elle configure aussi le SSL par défaut, avec un contournement de validation du certificat dans le bloc `try` :

```python
ssl._create_default_https_context = ssl._create_unverified_context
```

Cela est une manière de contourner les contrôles de certificat TLS pour des appels HTTP/HTTPS moins stricts. Dans un contexte de sécurité, c’est un comportement très suspect car il désactive une vérification standard de validité SSL.

### 4.4 `send_embed_message`

Cette méthode construit une URL de webhook et envoie un message Discord. Elle utilise `urllib.request.urlopen` avec un payload JSON.

Elle fait alors :

- lire la réponse en JSON;
- récupérer l’ID du message envoyé;
- stocker `self.last_message_id` et `self.channel_id`;
- afficher un log dans la console.

À la réception d’une erreur HTTP, elle gère :

- `401` : token invalide,
- `403` : accès interdit,
- autres codes : affichage brut de l’erreur.

### 4.5 `send_edit_message`

Cette méthode sert à modifier un message existant en utilisant l’ID du message. Elle ne fait qu’appeler l’API Discord avec un payload JSON ou un `content` simple.

### 4.6 `react` et `delete_message`

Ces méthodes permettent :

- d’ajouter une réaction à un message Discord;
- de supprimer un message.

### 4.7 `get_user_info`

Cette méthode tente de récupérer les informations de l’utilisateur Discord correspondant au bot/API configuré. Elle construit une requête avec `Authorization: Bot <token>` et envoie une requête sur :

```python
https://discord.com/api/users/@me
```

C’est une collecte d’identité Discord, ce qui est typique d’un comportement de surveillance ou d’exfiltration.

---

## 5. Détection de plateforme

### `detect_platform()`

Cette fonction vérifie `sys.platform` et renvoie :

- `Windows` pour `win32`;
- `Darwin (macOS)` pour `darwin`;
- `Linux` pour tout le reste.

### `get_windows_path()`

Elle renvoie un chemin d’installation pour l’agent selon le système :

- sur Windows: `C:\ProgramData\SystemBackdoor`
- sur les autres systèmes: `./SystemBackdoor`

### `is_admin_windows()` et `is_admin_linux()`

Ces fonctions tentent de vérifier si le processus a des droits d’administrateur ou de superutilisateur.

---

## 6. Fonctionnalité de capture d’écran

### `take_screenshot_win()`

Sur Windows, la fonction tente de lancer une commande PowerShell complexe pour créer une capture d’écran. Elle utilise des objets .NET et enregistre une image dans `C:\SystemBackdoor\...`.

Elle retourne ensuite un nom de fichier basé sur l’horodatage.

### `take_screenshot_linux()`

Sur Linux, la fonction essaie d’utiliser :

- `gnuscreenshot`;
- puis `gnome-screenshot`;
- puis un fallback plus complexe avec `gi` / GTK / GDK.

Le but est de générer une image de l’écran afin de la stocker localement ou à transmettre.

### `take_screenshot_darwin()`

Sur macOS, la fonction tente d’utiliser :

- `screenshot`;
- puis `screencapture`.

### `capture_screen()`

Cette fonction coordonne l’ensemble :

- détecte la plateforme;
- appelle la bonne fonction de capture;
- vérifie si la capture a bien été créée;
- retourne une structure JSON décrivant le résultat.

Le commentaire indique clairement :

- Discord Webhook n’a pas de support natif d’upload d’image;
- le script se contente de renvoyer un message partiel ou de simuler un transfert.

En d’autres termes, cette partie est une version simplifiée, plus “prototype” que production.

---

## 7. Scare payload et médias

### `load_scare_files()`

Cette fonction retourne un dictionnaire de liens GIF externes :

- `scare1`
- `scare2`
- `scare3`

Les URL sont des liens Tenor placeholder. Le script prétend envoyer un GIF “effrayant” via Discord pour “faire peur” à l’utilisateur.

### `play_audio_win()` / `play_audio_linux()`

Ces fonctions visent à lancer un son de “scare”, avec :

- WinAmp ou PowerShell sur Windows;
- `mpg123` sur Linux.

### `execute_scare()`

Cette fonction :

- choisit un GIF au hasard dans une liste de liens;
- envoie un message Discord avec le GIF dans un embed;
- renvoie un statut succès ou échec.

Grosso modo, c’est une “attaque de nuisance” visuelle pour créer un effet de panique ou d’alerte.

---

## 8. Keylogger

### `log_key()`

Cette fonction simule la capture d’une touche pressée :

- sur Windows: retour d’un message de type `key_logged_pasted`;
- sur Linux: génération d’un horodatage.

### `write_keylog_win()`

Cette fonction tente d’écrire une entrée dans un fichier :

```python
C:\ProgramData\SystemBackdoor\keylog.txt
```

### `write_keylog_linux()`

Même logique sous Linux, avec un fichier dans `/tmp`.

### `run_keylogger()`

Cette fonction active ce que le code appelle un keylogger. En réalité, le code ne capture pas réellement les frappes de clavier de manière robuste; il se contente de simuler l’écriture dans un fichier ou de présenter une logique de démonstration.

C’est donc une fonction de type “prototype de surveillance clavier”, très sensible d’un point de vue sécurité.

---

## 9. Collecte d’informations système

### `get_system_info()`

Cette fonction récolte :

- le système d’exploitation;
- le hostname;
- l’IP locale;
- la version Python;
- parfois le résultat de `systeminfo` ou `uname -a`.

Elle construit ensuite un ensemble de données de type `dict` et les renvoie sous forme de message ou d’embed Discord.

Le but est de fournir à l’attaquant ou au testeur des informations utiles sur la cible.

### `get_my_ip()`

Cette fonction récupère l’adresse IP locale via `socket.gethostbyname(socket.gethostname())` et la retourne dans un message Discord.

---

## 10. Contrôle du système

### `close_all()`

Cette fonction tente de fermer des fenêtres ou des processus.

- Windows: `taskkill /F /IM /FI WINDOW*` (commande de fermeture agressive);
- Linux: `pkill -9 -f bash; pkill -9 -f python`.

Le nom de la fonction est explicite : elle tente de fermer tout ce qui est ouvert sur la machine.

### `reboot()`

Cette fonction redémarre la machine :

- Windows: `shutdown /r /t 0`
- Linux: `sudo reboot` puis `reboot` si nécessaire.

C’est une commande de contrôle de la machine très lourde et potentiellement destructrice pour une session utilisateur.

### `cleanup()`

Cette fonction est destinée à “nettoyer” les traces de l’agent :

- supprimer un dossier système (`SystemBackdoor`);
- supprimer des processus Python ou des fichiers temporaires;
- tenter de masquer l’empreinte de l’agent.

Le code est explicitement conçu pour “effacer” l’agent lui-même. C’est typique d’un payload qui tente de se camoufler ou de se retirer après exécution.

---

## 11. Traitement des commandes

### `process_command(command, discord_bot)`

C’est le moteur de commande principal. Il reçoit une commande sous forme de texte, la découpe, et la compare à une liste de mots-clés :

- `help`
- `help all`
- `screenshot`
- `scare`
- `keylog`
- `systeminfo`
- `ip`
- `reboot`
- `close_all`
- `cleanup`
- `info`

Selon la commande, il appelle la bonne fonction et renvoie un dictionnaire de résultat.

Exemple :

```python
elif cmd_name == "screenshot":
    return capture_screen(discord_bot)
```

Cela fait le lien entre un message Discord et une action locale.

### `show_help()`

Cette fonction affiche des commandes disponibles dans un message Discord. Elle s’appuie sur un embed pour présenter les options du payload.

### `get_discord_info()`

Cette méthode affiche les informations de connexion Discord du bot, notamment :

- les identifiants de webhook;
- le `channel_id`;
- l’ID du dernier message envoyé.

### `show_all_commands()`

Cette fonction liste toutes les commandes disponibles, avec un texte explicite rappelant qu’il s’agit d’un “outil éducatif” et qu’il ne doit pas être utilisé sans autorisation.

---

## 12. Boucle principale `main()`

Le programme principal fait ceci :

1. cherche le fichier `agent_config.json` dans le même dossier;
2. charge la configuration JSON;
3. récupère `webhook_id` et `api_token`;
4. vérifie que le webhook est bien configuré;
5. initialise `DiscordBot`;
6. affiche un message d’attente;
7. entre dans une boucle `while True` ;
8. attend puis vérifie si la configuration a changé.

Ce mécanisme suppose qu’un autre système peut remettre à jour le fichier de configuration pour changer le webhook cible à chaud.

---

## 13. Ce que le script “déclenche” concrètement

À un niveau fonctionnel, le code permet de faire les choses suivantes :

- interagir avec un webhook Discord pour envoyer/recevoir des messages;
- récupérer des informations système sur la machine; 
- obtenir l’IP locale;
- donner une instruction de capture d’écran;
- envoyer un GIF “scare”;
- simuler l’activation d’un keylogger;
- fermer des fenêtres ou tuer des processus;
- redémarrer la machine;
- nettoyer les traces de l’agent.

Autrement dit, c’est une architecture de payload d’attaque ou de démonstration de contrôle distant.

---

## 14. Points faibles / limites du code

Bien que le script ait une forme complète, il contient plusieurs éléments qui montrent qu’il s’agit d’un prototype plutôt qu’une solution de production :

- les fonctions de capture d’écran ne sont pas totalement fiables selon les plateformes;
- certaines commandes utilisent des commandes système non standard ou incohérentes;
- beaucoup de fonctions sont simulées ou incomplètes;
- le “keylogger” ne capture pas réellement les touches de façon fiable;
- le script repose sur un webhook public ou un canal Discord, ce qui est fortement lié à la sécurité du canal cible;
- les erreurs et les logs ne sont pas robustement gérées.

---

## 15. Risque de sécurité

Le fichier est un exemple typique de ce qu’on appelle un payload de contrôle distant ou de “backdoor-like agent”. Il comporte :

- collecte d’informations système;
- exfiltration de données via Discord;
- exécution de commandes à distance;
- tentative de surveillance clavier;
- fermeture de processus;
- redémarrage système;
- nettoyage de traces.

À ce niveau, il n’est pas un script “inofensif” : il est orienté vers l’autonomie de la machine cible et le contrôle distant.

---

## 16. En une phrase

Le fichier est un pseudo-agent d’attaque basé sur Discord, créé pour envoyer des commandes depuis un salon Discord vers une machine Windows/Linux/macOS, puis exécuter des actions locales (capture, infos système, redémarrage, fermeture, nettoyage) et rapporter les résultats dans le même canal.

---

## 17. Utilisation recommandée

Ce code ne doit être utilisé que dans un cadre :

- de laboratoire ;
- de formation ;
- de test éthique ;
- d’environnement entièrement contrôlé et autorisé.

Tout usage sur des systèmes tiers sans consentement écrit est illégal dans de nombreux contextes et potentiellement très dangereux.

---

## 18. Fichier principal

Le script principal est :

- [Nouveau Fichier source Python.py](Nouveau%20Fichier%20source%20Python.py)

---

## 19. Concluion

Ce fichier est un exemple de “payload de commande et contrôle” : il essaie de transformer une machine cible en client basique contrôlable depuis un canal Discord. Sa logique est très claire : exécuter une commande localement, puis renvoyer le résultat vers Discord.

Même si le script contient des commentaires explicites de “formation / educational use only”, son architecture est celle d’un outil de contrôle distant potentiellement malveillant. Il doit donc être étudié uniquement à des fins de sécurité, de recherche, de tests autorisés ou de pédagogie avancée.
