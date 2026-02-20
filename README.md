# kokoro-fr-tts

Synthèse vocale en français avec [Kokoro TTS](https://github.com/hexgrad/kokoro) (82M params). Interface web Gradio avec streaming audio pour une lecture quasi-instantanée.

## Fonctionnalités

- **TTS français naturel** — voix `ff_siwis` via le modèle Kokoro-82M
- **Corrections de prononciation** — dictionnaire de mots français qu'espeak-ng traite incorrectement comme anglais (ex: "dos", "pull"), corrigés avant le passage au G2P
- **Streaming audio** — les chunks audio sont joués sur les haut-parleurs dès qu'ils sont générés, sans attendre la fin de la synthèse
- **Interface web** — Gradio pour tester directement dans le navigateur

## Installation

### Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets recommandé)
- `espeak-ng` (dépendance système pour le G2P)

### Système

```bash
# Fedora / RHEL
sudo dnf install espeak-ng

# Ubuntu / Debian
sudo apt install espeak-ng

# macOS
brew install espeak-ng
```

### Projet

```bash
git clone https://github.com/Gheop/kokoro-fr-tts.git
cd kokoro-fr-tts
uv sync
```

## Utilisation

### Interface web

```bash
uv run app.py
```

Ouvre http://localhost:7860 dans le navigateur. Entrez du texte en français, l'audio est généré et joué directement sur les haut-parleurs du serveur, puis affiché dans le navigateur.

### En Python

```python
from tts_engine import KokoroEngine

engine = KokoroEngine()

# Audio complet
audio, sr = engine.generate("Bonjour, comment allez-vous ?")

# Streaming chunk par chunk
for chunk in engine.generate_stream("Un texte plus long..."):
    # chunk est un np.ndarray, jouable immédiatement
    pass
```

## Docker

```bash
docker build -t kokoro-fr-tts .
docker run --rm -p 7860:7860 kokoro-fr-tts
```

> **Note** : le conteneur ne supporte pas la lecture audio sur les HP du serveur (pas de device audio). L'audio reste accessible via l'interface web Gradio dans le navigateur.

## Corrections de prononciation

Le moteur G2P (espeak-ng) traite parfois des mots français comme anglais. Par exemple, "dos" est phonémisé `/dɒs/` au lieu de `/do/`. Le dictionnaire `FRENCH_FIXES` dans `tts_engine.py` corrige ces cas en remplaçant les mots problématiques par des graphies phonétiques avant le G2P :

```python
FRENCH_FIXES = {
    r"\bdos\b": "deau",
    r"\bpull\b": "pul",
}
```

Pour ajouter une correction, il suffit d'ajouter une entrée `{regex: graphie_correcte}` au dictionnaire.

## Tests

```bash
uv run pytest
```

## Structure

```
├── app.py            # Interface Gradio
├── tts_engine.py     # Moteur TTS (Kokoro) + corrections prononciation
├── audio_player.py   # Lecture audio (play + play_stream)
├── tests/            # Tests
├── Dockerfile
└── pyproject.toml
```

## Licence

MIT
