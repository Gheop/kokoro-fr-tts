# kokoro-fr-tts

Synthèse vocale en français avec [Kokoro TTS](https://github.com/hexgrad/kokoro) (82M params). Interface web Gradio avec streaming audio pour une lecture quasi-instantanée.

## Fonctionnalités

- **TTS français naturel** — voix `ff_siwis` via le modèle Kokoro-82M
- **Corrections de prononciation** — détection automatique et correction des mots qu'espeak-ng bascule en anglais (anglicismes : parking, football...) + dictionnaire manuel pour les cas spéciaux (dos, pull)
- **Streaming audio** — les chunks audio sont joués sur les haut-parleurs dès qu'ils sont générés, sans attendre la fin de la synthèse
- **Interface web** — Gradio pour tester directement dans le navigateur

## Installation

### Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets recommandé) ou pip
- `espeak-ng` (dépendance système pour le G2P)

### Installer uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

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

Alternativement, avec pip :

```bash
pip install -e .
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

Le moteur G2P (espeak-ng) bascule silencieusement certains mots français en anglais. La correction se fait en deux couches :

### Layer 1 : corrections textuelles (`FRENCH_FIXES`)

Pour les vrais mots français où le mapping phonémique ne suffit pas (ex: "dos" → le `s` final devrait être muet), on remplace le mot par une graphie phonétique avant le G2P :

```python
FRENCH_FIXES = {
    r"\bdos\b": "deau",
    r"\bpull\b": "pul",
}
```

Pour ajouter une correction, il suffit d'ajouter une entrée `{regex: graphie_correcte}` au dictionnaire.

### Layer 2 : correction automatique des switches anglais (`FrenchG2P`)

Pour les anglicismes courants (parking, football, weekend, jogging...), `FrenchG2P` détecte automatiquement les marqueurs de switch `(en)...(fr)` dans la sortie du phonemizer et convertit les phonèmes anglais en phonèmes français via une table de mapping IPA. Aucune maintenance manuelle nécessaire — tous les mots détectés comme anglais par espeak-ng sont corrigés automatiquement.

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
