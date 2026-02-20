# kokoro-fr-tts

Synthèse vocale en français avec [Kokoro TTS](https://github.com/hexgrad/kokoro) (82M params). Interface web Gradio avec streaming audio pour une lecture quasi-instantanée.

## Fonctionnalités

- **TTS français naturel** — voix `ff_siwis` via le modèle Kokoro-82M
- **Corrections de prononciation** — détection automatique et correction des mots qu'espeak-ng bascule en anglais (anglicismes : parking, football...) + dictionnaire manuel pour les cas spéciaux (dos, pull, blockchain)
- **Streaming audio** — les chunks audio sont joués sur les haut-parleurs dès qu'ils sont générés, sans attendre la fin de la synthèse
- **API streaming** — endpoint `POST /v1/audio/speech` compatible OpenAI TTS, streaming WAV PCM en chunked transfer encoding
- **Page de test** — page web minimaliste (`/test`) pour tester le streaming : coller du texte → l'audio sort immédiatement
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

### API streaming

L'endpoint `POST /v1/audio/speech` est compatible avec l'API TTS d'OpenAI. L'audio est streamé en WAV PCM 16-bit mono 24 kHz dès que les premiers chunks sont prêts.

```bash
curl -X POST http://localhost:7860/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Bonjour, comment allez-vous ?", "voice": "ff_siwis", "speed": 1.0}' \
  --output output.wav
```

Ou en Python :

```python
import requests

response = requests.post(
    "http://localhost:7860/v1/audio/speech",
    json={"input": "Bonjour, comment allez-vous ?", "voice": "ff_siwis"},
    stream=True,
)
with open("output.wav", "wb") as f:
    for chunk in response.iter_content(chunk_size=4096):
        f.write(chunk)
```

Une page de test est disponible sur http://localhost:7860/test — collez du texte et l'audio démarre immédiatement.

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

### GPU (recommandé)

Par défaut le conteneur tourne sur CPU (~30x plus lent). Pour utiliser le GPU :

1. Installer `nvidia-container-toolkit` sur l'hôte (les drivers NVIDIA doivent déjà être installés) :
   ```bash
   # Fedora / RHEL
   sudo dnf install nvidia-container-toolkit

   # Ubuntu / Debian
   sudo apt install nvidia-container-toolkit
   ```
2. Redémarrer Docker :
   ```bash
   sudo systemctl restart docker
   ```
3. Lancer avec `--gpus all` :
   ```bash
   docker run --rm --gpus all -p 7860:7860 kokoro-fr-tts
   ```

L'image Docker reste identique — le toolkit monte le GPU de l'hôte dans le conteneur.

> **Note** : le conteneur ne supporte pas la lecture audio sur les HP du serveur (pas de device audio). L'audio reste accessible via l'interface web et l'API streaming.

## Corrections de prononciation

Le moteur G2P (espeak-ng) bascule silencieusement certains mots français en anglais. La correction se fait en deux couches :

### Layer 1 : corrections textuelles (`FRENCH_FIXES`)

Pour les vrais mots français où le mapping phonémique ne suffit pas (ex: "dos" → le `s` final devrait être muet), on remplace le mot par une graphie phonétique avant le G2P :

```python
FRENCH_FIXES = {
    r"\bdos\b": "deau",
    r"\bpull\b": "pul",
    r"\bblockchains?\b": "bloktchène",
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
├── app.py            # Interface Gradio + API streaming FastAPI
├── tts_engine.py     # Moteur TTS (Kokoro) + corrections prononciation
├── audio_player.py   # Lecture audio (play + play_stream)
├── test.html         # Page de test streaming
├── tests/            # Tests
├── Dockerfile
└── pyproject.toml
```

## Licence

MIT
