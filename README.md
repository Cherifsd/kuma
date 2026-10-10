# Kuma — transcription et compte rendu de discussions

Kuma enregistre une discussion sur votre **téléphone Android**, la transcrit
(français, bambara, peul, maninka, khassonké, sarakolé, bomu, tamasheq, minianka,
songhay, dogon, dioula, anglais, arabe, allemand, portugais, chinois…)
puis rédige un compte rendu : résumé, points clés, décisions, actions, passages à vérifier.

Le **téléphone** sert à enregistrer et lire. L'**ordinateur** fait le travail lourd.
Les deux doivent être sur le **même Wi-Fi** (ou le téléphone en partage de connexion pour l'ordinateur).

```
Téléphone Android (application Kuma)  ──Wi-Fi──►  Ordinateur (Demarrer-Kuma)
```

---

## 1. Sur l'ordinateur : démarrer Kuma

**Une seule fois** : installez Python depuis https://www.python.org/downloads/
en **cochant « Add python.exe to PATH »**.

Ensuite, à chaque utilisation :

- **Windows** : double-cliquez sur **`Demarrer-Kuma.bat`**
- **Mac** : double-cliquez sur **`demarrer-kuma.command`**

La première fois, l'installation prend 2 à 5 minutes (Internet nécessaire).
Si Windows affiche une alerte du **pare-feu**, cliquez sur **Autoriser**.

Quand c'est prêt, la fenêtre affiche par exemple :

```
  KUMA est prêt.
  Dans l'application Android, tapez : 192.168.1.25:8000
```

Gardez cette fenêtre ouverte pendant l'utilisation.

## 2. Sur le téléphone : installer l'application

1. Sur le téléphone, ouvrez le lien de téléchargement de **Kuma.apk**
   (page « Releases » du dépôt GitHub) et touchez **Kuma.apk**.
2. Android demande d'autoriser l'installation depuis Chrome (ou « sources inconnues ») :
   touchez **Paramètres**, activez **Autoriser**, puis revenez et touchez **Installer**.
   Si « Play Protect » affiche un avertissement, touchez **Plus de détails** puis **Installer quand même** :
   c'est normal pour une application qui ne vient pas du Play Store.
3. Ouvrez **Kuma**, tapez l'adresse affichée sur l'ordinateur (ex. `192.168.1.25:8000`)
   et touchez **Se connecter**.

## 3. Utiliser Kuma

1. Choisissez la **langue parlée** (important pour la qualité).
2. Touchez le **bouton rouge** et autorisez le micro la première fois.
   Le texte apparaît par tranches de 25 secondes. Gardez l'écran allumé.
3. Ou touchez **Importer un fichier audio** (note vocale, enregistrement WhatsApp…).
4. Touchez un passage pour le **corriger**.
5. Touchez **Générer le compte rendu**, puis **Tout copier** pour le coller dans WhatsApp ou un e-mail.

Sur l'ordinateur, la même interface est disponible sur **http://localhost:8000**.

---

## Mode démo et vraie transcription

Au départ, Kuma tourne en **mode démo** : le texte affiché est factice. Cela permet de vérifier
que le téléphone, le micro et l'ordinateur communiquent bien.

### Activer le compte rendu

Créez une clé sur https://console.anthropic.com, ouvrez le fichier **`.env`** du dossier Kuma
avec le Bloc-notes, collez la clé après `ANTHROPIC_API_KEY=`, enregistrez, puis relancez Kuma.

### Activer la vraie transcription

Elle utilise [Omnilingual ASR](https://github.com/facebookresearch/omnilingual-asr) de Meta,
qui tourne sur l'ordinateur (l'audio ne part pas sur Internet).

- **Mac / Linux** : dans le dossier Kuma, `.venv-unix/bin/pip install omnilingual-asr`
  (Mac : `brew install libsndfile` avant), puis relancez.
- **Windows** : ce moteur ne fonctionne pas directement sous Windows. Il faut **WSL** (Ubuntu dans Windows 11).
  1. Pour que le téléphone puisse joindre WSL, créez le fichier `C:\Users\<votre nom>\.wslconfig` contenant :
     ```
     [wsl2]
     networkingMode=mirrored
     ```
     puis, dans PowerShell : `wsl --shutdown`.
  2. Dans Ubuntu, allez dans le dossier Kuma (`cd /mnt/c/Users/<votre nom>/Downloads/kuma`, par exemple), puis :
     ```bash
     sudo apt install python3-venv libsndfile1
     python3 -m venv .venv-unix && .venv-unix/bin/pip install -r requirements.txt
     ./demarrer-kuma.command
     ```

Au premier enregistrement, le modèle se télécharge (environ 6 Go, une seule fois).
Sans carte graphique, la transcription est lente.

| Modèle (`KUMA_ASR_MODEL` dans `.env`) | Téléchargement | Pour quelle machine |
|---------------------------------------|---------------:|---------------------|
| `omniASR_LLM_Unlimited_300M_v2` (défaut) | 6 Go        | PC avec 16 Go de RAM |
| `omniASR_LLM_Unlimited_1B_v2`         | 8,5 Go         | PC avec carte NVIDIA |
| `omniASR_LLM_Unlimited_7B_v2`         | 30 Go          | serveur GPU          |

---

## Problèmes fréquents

| Problème | Solution |
|---|---|
| « Impossible de joindre l'ordinateur » | Kuma est-il lancé ? Même Wi-Fi ? Adresse exacte (avec `:8000`) ? Sous Windows, autorisez Python dans le pare-feu (Paramètres > Confidentialité et sécurité > Sécurité Windows > Pare-feu > Autoriser une application). |
| Plusieurs adresses affichées | Essayez celle qui commence par `192.168.` |
| Le micro ne marche pas | Paramètres du téléphone > Applications > Kuma > Autorisations > Micro > Autoriser. |
| L'enregistrement s'arrête | L'écran s'est éteint : gardez-le allumé pendant l'enregistrement. |
| Réseau d'entreprise ou d'hôtel | Certains Wi-Fi isolent les appareils. Utilisez le partage de connexion du téléphone. |

---

## Pour les développeurs

```
server.py              serveur FastAPI (transcription + résumé, CORS ouvert pour l'application)
static/index.html      interface (navigateur et application)
android/               application Android (Capacitor) qui embarque static/index.html
.github/workflows/     fabrication automatique de Kuma.apk sur GitHub
```

Fabriquer l'APK à la main (Android Studio / SDK requis) :

```bash
cd android && npm ci && npm run android:create
cd android && ./gradlew assembleDebug
```
