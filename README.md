# Voice Changer pour Discord (Windows, 100 % gratuit)

Petite app qui transforme ta voix en direct, avec 30 presets et des raccourcis clavier pour changer de voix en pleine partie.

```
Micro → Voice Changer (preset) → CABLE Input ══ CABLE Output → Discord
```

## Installation

1. Copie ce dossier sur le PC Windows.
2. Double-clique sur `install.bat`. Le script :
   - installe Python 3.12 (via winget) s'il est absent ;
   - télécharge et installe **VB-Audio Virtual Cable** : accepte la demande d'administrateur, puis clique sur « Install Driver » ;
   - installe l'app dans `%LOCALAPPDATA%\VoiceChanger` ;
   - crée un raccourci « Voice Changer » sur le Bureau et dans le menu Démarrer.
3. Redémarre Windows si VB-Cable vient d'être installé.

## Configuration de Discord

Guide complet (réglages, tests, raccourcis en partie, dépannage) : [GUIDE-DISCORD.md](GUIDE-DISCORD.md).

Paramètres → Voix et vidéo :
- **Périphérique d'entrée** : `CABLE Output (VB-Audio Virtual Cable)`
- **Désactive** la suppression de bruit (Krisp), l'annulation d'écho et le contrôle automatique du gain. Sinon, ils écrasent l'effet.

## Utilisation

1. Lance « Voice Changer ».
2. Vérifie le **micro** et la **sortie vers Discord**, qui doit être `CABLE Input`.
3. Clique sur **Démarrer**, puis sur un preset. Tu peux changer de preset à tout moment, en direct.
4. **Retour casque** : coche-le pour t'entendre, avant de démarrer.
5. **Noise gate** : baisse-le si ta voix est coupée, monte-le si le bruit de fond passe.

Raccourcis globaux, actifs même quand le jeu a le focus :

| Raccourci | Action |
|---|---|
| Ctrl+Shift+F1 à F12 | Presets principaux (affichés sur les boutons) |
| Ctrl+Shift+PageDown / PageUp | Preset suivant / précédent |

## Créer ou modifier des presets

Bouton « Modifier les presets » → édite `presets.json` → « Recharger les presets ».

```json
{ "name": "Ma voix", "category": "Perso", "hotkey": "<ctrl>+<shift>+<f2>",
  "voices": [{ "pitch": -5, "formant": -3 }, { "pitch": -12, "gain": 0.5 }],
  "effects": [{ "type": "Distortion", "drive_db": 10 }, { "type": "Reverb", "room_size": 0.6, "wet_level": 0.3 }],
  "output_gain_db": 0 }
```

- `voices` : une ou plusieurs voix transformées et mélangées. Si tu l'omets, ta voix reste intacte.
  - `pitch` : hauteur, en demi-tons.
  - `formant` : timbre, en demi-tons. À 0, le timbre reste naturel. Si tu lui donnes la même valeur que `pitch`, tu obtiens l'effet Chipmunk.
  - `gain` : volume de la voix.
  - `mode` : `normal`, `robot` ou `whisper` (voix chuchotée).
- `effects` : effets [pedalboard](https://spotify.github.io/pedalboard/reference/pedalboard.html), appliqués dans l'ordre. Effets disponibles : `Bitcrush`, `Chorus`, `Clipping`, `Compressor`, `Delay`, `Distortion`, `Gain`, `HighpassFilter`, `HighShelfFilter`, `LadderFilter`, `Limiter`, `LowpassFilter`, `LowShelfFilter`, `NoiseGate`, `PeakFilter`, `Phaser`, `Reverb`.
- `hotkey` : au format pynput, par exemple `<ctrl>+<alt>+<f5>`. Évite Ctrl+Alt+chiffre, qui correspond à AltGr sur un clavier AZERTY.

Une réinstallation conserve ton `presets.json`. Les presets d'origine restent disponibles dans `presets.default.json`.

## Dépannage

- **« Impossible de démarrer l'audio »** : choisis l'API audio `MME`. La latence est un peu plus élevée, mais c'est plus tolérant.
- **Les raccourcis ne marchent pas en jeu** : certains jeux lancés en administrateur ou protégés par un anti-cheat bloquent les raccourcis globaux. Lance alors Voice Changer en administrateur, ou change de preset avec la souris.
- **Voix hachée** : ferme les applications gourmandes, ou passe en `MME`.
- **Latence** : environ 25 à 35 ms au total, imperceptible en vocal.

## Limites

Le traitement est du DSP classique (phase vocoder avec contrôle séparé du pitch et des formants), pas de l'IA. Les voix féminine et masculine sont nettement plus naturelles qu'un simple pitch shift, mais restent reconnaissables comme des voix transformées. Pour une voix vraiment crédible, il faut une solution IA comme w-okada + RVC (carte NVIDIA conseillée).
