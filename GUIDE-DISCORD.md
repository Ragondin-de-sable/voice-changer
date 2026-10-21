# Utiliser Voice Changer avec Discord

Ce guide part du principe que l'installation est faite (`install.bat` lancé, PC redémarré). Les libellés de Discord peuvent légèrement varier selon la version.

## Le principe en une image

```
Ton micro ──► Voice Changer ──► CABLE Input ══(câble virtuel)══ CABLE Output ──► Discord
                  │
                  └──► Retour casque (optionnel, pour t'entendre)
```

Discord n'écoute plus ton micro directement. Il écoute le câble virtuel, dans lequel Voice Changer envoie ta voix transformée.

## 1. Préparer Voice Changer

1. Lance **Voice Changer** depuis le Bureau.
2. Dans le cadre **Audio** :
   - **API audio** : laisse `Windows WASAPI`. Passe en `MME` seulement si le démarrage échoue.
   - **Micro** : ton vrai micro (casque, micro USB…).
   - **Sortie vers Discord** : `CABLE Input (VB-Audio Virtual Cable)`.
3. Clique sur **Démarrer**. Le statut affiche « En direct — Normale ».

Ne choisis **jamais** `CABLE Input` comme « Retour casque ». Le retour casque doit être ton casque.

## 2. Régler Discord

Ouvre Discord → **Paramètres utilisateur** (roue dentée en bas à gauche) → **Voix et vidéo**.

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Périphérique d'entrée | `CABLE Output (VB-Audio Virtual Cable)` | Discord écoute la voix transformée |
| Périphérique de sortie | ton casque, comme d'habitude | inchangé |
| Volume d'entrée | 100 % | le niveau se règle dans Voice Changer |
| Suppression du bruit | **Aucune** (désactive Krisp) | Krisp prend les voix de démon ou de robot pour du bruit et les efface |
| Annulation de l'écho | **Désactivée** | elle déforme les effets d'écho et de réverbération |
| Contrôle automatique du gain | **Désactivé** | il écrase les différences de volume entre presets |

Le bouton Krisp est aussi accessible dans le panneau vocal en bas à gauche (icône d'onde sonore). Vérifie qu'il est bien éteint.

### Mode de saisie

Les deux modes fonctionnent :
- **Détection de la voix** : désactive « Déterminer automatiquement la sensibilité d'entrée » si ta voix est coupée en début de phrase, puis place le curseur juste au-dessus de ton bruit de fond.
- **Appuyer pour parler** : rien de particulier, c'est même le plus fiable avec les presets à réverbération.

## 3. Tester avant d'entrer en vocal

1. Dans **Voix et vidéo**, clique sur **Vérifions** (test du micro) et parle : Discord te renvoie ce que les autres entendront.
2. Change de preset dans Voice Changer pendant le test pour écouter chacun.
3. Ajuste au besoin :
   - voix trop forte ou trop faible → `output_gain_db` du preset (voir le README) ;
   - bruit de fond qui passe → monte le **Noise gate** ;
   - début des mots coupé → baisse le **Noise gate**.

## 4. En partie

- **Changer de voix** : clique sur un preset, ou utilise les raccourcis, actifs même en jeu :

  | Raccourci | Preset |
  |---|---|
  | Ctrl+Shift+F1 | Normale |
  | Ctrl+Shift+F2 | Féminine |
  | Ctrl+Shift+F3 | Masculine |
  | Ctrl+Shift+F4 | Enfant |
  | Ctrl+Shift+F5 | Démon |
  | Ctrl+Shift+F6 | Géant |
  | Ctrl+Shift+F7 | Robot |
  | Ctrl+Shift+F8 | Fantôme |
  | Ctrl+Shift+F9 | Radio |
  | Ctrl+Shift+F10 | Chipmunk |
  | Ctrl+Shift+F11 | Alien |
  | Ctrl+Shift+F12 | Chorale |
  | Ctrl+Shift+PageDown / PageUp | Preset suivant / précédent |

- **Retrouver ta voix naturelle** : preset **Normale** (Ctrl+Shift+F1). Il n'ajoute aucun retard.
- **Vérifier tes raccourcis Discord** : si l'un d'eux utilise déjà Ctrl+Shift+F-quelque chose (Paramètres → Raccourcis clavier), change-le dans Discord ou dans `presets.json`.
- **Si tu fermes Voice Changer** : Discord n'entend plus rien, puisque plus rien n'arrive dans le câble. Relance l'app, ou remets ton vrai micro comme périphérique d'entrée dans Discord.

## 5. Partage d'écran et stream

Quand tu partages ton écran avec le son, Discord envoie le son du jeu, pas ta voix. Ta voix passe toujours par le micro, donc par Voice Changer. Rien à changer.

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Les autres n'entendent rien | Voice Changer arrêté ou mauvaise sortie | Vérifie « En direct » et la sortie `CABLE Input` |
| Les autres entendent ta voix normale | Discord écoute encore ton vrai micro | Entrée Discord = `CABLE Output` |
| La voix transformée est coupée ou disparaît | Krisp ou la sensibilité d'entrée de Discord | Suppression du bruit sur **Aucune**, sensibilité manuelle |
| Tu t'entends en double ou en écho | Retour casque activé en plus du test Discord | Désactive l'un des deux |
| Son haché ou robotique non voulu | PC chargé ou API audio | Passe en `MME`, ferme les applications gourmandes |
| Les raccourcis ne marchent pas en jeu | Jeu lancé en administrateur ou anti-cheat | Lance Voice Changer en administrateur, ou change de preset à la souris |
| « Impossible de démarrer l'audio » | Périphérique occupé ou incompatible | Choisis `MME`, vérifie que le micro n'est pas en mode exclusif dans Windows |
| `CABLE` absent des listes | VB-Cable non installé ou PC pas redémarré | Redémarre, sinon relance `install.bat` |

En cas de plantage, le détail de l'erreur se trouve dans `%APPDATA%\VoiceChanger\error.log`.
