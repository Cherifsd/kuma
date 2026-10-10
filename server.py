"""
Kuma — transcription vocale multilingue + résumé de discussion.

Transcription : Meta Omnilingual ASR (1600+ langues, dont bambara, peul,
maninka, khassonké, soninké, tamasheq, minianka, bomu, songhay...).
Résumé : API Claude (Anthropic).

Lancer :  uvicorn server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).parent

# Charge le fichier .env (clé API, choix du modèle) s'il existe.
_env = BASE / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# ---------------------------------------------------------------- configuration
# Modèle de transcription. "Unlimited" = accepte les longs enregistrements.
#   omniASR_LLM_Unlimited_300M_v2  ~6 Go, tourne sur un PC (CPU possible, lent)
#   omniASR_LLM_Unlimited_1B_v2    ~8.5 Go, meilleur, GPU conseillé
#   omniASR_LLM_Unlimited_7B_v2    ~30 Go, le meilleur, GPU 24 Go requis
ASR_MODEL = os.getenv("KUMA_ASR_MODEL", "omniASR_LLM_Unlimited_300M_v2")
# "omnilingual" (réel), "demo" (texte factice, pour tester sans modèle)
# ou "auto" : réel si le moteur est installé, sinon démo.
ASR_ENGINE = os.getenv("KUMA_ASR_ENGINE", "auto")
if ASR_ENGINE == "auto":
    import importlib.util

    ASR_ENGINE = "omnilingual" if importlib.util.find_spec("omnilingual_asr") else "demo"
CLAUDE_MODEL = os.getenv("KUMA_CLAUDE_MODEL", "claude-sonnet-5-5")

# Langues proposées dans l'interface (code ISO 639-3 + écriture).
# Toute autre langue de la liste Omnilingual peut être saisie à la main.
LANGUAGES = [
    {"code": "fra_Latn", "label": "Français", "group": "Internationales"},
    {"code": "eng_Latn", "label": "Anglais", "group": "Internationales"},
    {"code": "arb_Arab", "label": "Arabe", "group": "Internationales"},
    {"code": "deu_Latn", "label": "Allemand", "group": "Internationales"},
    {"code": "por_Latn", "label": "Portugais", "group": "Internationales"},
    {"code": "cmn_Hans", "label": "Chinois (mandarin)", "group": "Internationales"},
    {"code": "bam_Latn", "label": "Bambara", "group": "Langues du Mali"},
    {"code": "ful_Latn", "label": "Peul (fulfulde)", "group": "Langues du Mali"},
    {"code": "fuc_Latn", "label": "Peul (pulaar)", "group": "Langues du Mali"},
    {"code": "mlq_Latn", "label": "Maninka", "group": "Langues du Mali"},
    {"code": "mnk_Latn", "label": "Mandinka", "group": "Langues du Mali"},
    {"code": "kao_Latn", "label": "Khassonké", "group": "Langues du Mali"},
    {"code": "snk_Latn", "label": "Sarakolé (soninké)", "group": "Langues du Mali"},
    {"code": "bmq_Latn", "label": "Bomu / Bwa (boua)", "group": "Langues du Mali"},
    {"code": "taq_Latn", "label": "Tamasheq (latin)", "group": "Langues du Mali"},
    {"code": "ttq_Tfng", "label": "Tamajaq (tifinagh)", "group": "Langues du Mali"},
    {"code": "myk_Latn", "label": "Minianka (mamara)", "group": "Langues du Mali"},
    {"code": "khq_Latn", "label": "Songhay (koyra chiini)", "group": "Langues du Mali"},
    {"code": "ses_Latn", "label": "Songhay (koyraboro senni)", "group": "Langues du Mali"},
    {"code": "dts_Latn", "label": "Dogon (toro so)", "group": "Langues du Mali"},
    {"code": "dyu_Latn", "label": "Dioula", "group": "Langues du Mali"},
]

# ---------------------------------------------------------------- transcription
_pipeline = None
_pipeline_lock = threading.Lock()


def _get_pipeline():
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            import torch
            from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline

            if torch.cuda.is_available():
                device, dtype = "cuda", torch.bfloat16
            else:
                device, dtype = "cpu", torch.float32
            print(f"[kuma] Chargement de {ASR_MODEL} sur {device}… (1re fois : téléchargement)")
            _pipeline = ASRInferencePipeline(model_card=ASR_MODEL, device=device, dtype=dtype)
        return _pipeline


def _ffmpeg() -> str:
    """ffmpeg du système, sinon celui fourni par le paquet pip imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise HTTPException(500, "ffmpeg est introuvable. Lancez : pip install imageio-ffmpeg")


def _to_wav16k(src: Path) -> Path:
    """Convertit n'importe quel audio (webm, mp3, m4a, ogg…) en WAV mono 16 kHz."""
    dst = src.with_suffix(".16k.wav")
    r = subprocess.run(
        [_ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not dst.exists():
        print("[kuma] ffmpeg :", r.stderr.strip()[:500])
        raise HTTPException(400, "Fichier audio illisible ou format non pris en charge.")
    return dst


def _duration(wav: Path) -> float:
    import wave

    with wave.open(str(wav)) as w:
        return w.getnframes() / float(w.getframerate())


def _transcribe_file(wav: Path, lang: str | None) -> str:
    if ASR_ENGINE == "demo":
        return f"[démo] Extrait de {_duration(wav):.1f} s transcrit en {lang or 'auto'}."
    pipe = _get_pipeline()
    with _pipeline_lock:  # un seul calcul à la fois (mémoire)
        out = pipe.transcribe([str(wav)], lang=[lang] if lang else None, batch_size=1)
    return (out[0] if out else "").strip()


# ---------------------------------------------------------------- résumé
SUMMARY_PROMPT = """Tu reçois la transcription automatique d'une discussion.
Elle peut contenir des erreurs de reconnaissance, des mots dans plusieurs langues
(par exemple bambara, peul, soninké, tamasheq, français, arabe) et pas de ponctuation.

Rédige un compte rendu en {out_lang}, fidèle à ce qui a été dit, sans inventer.
Structure exacte (titres en markdown) :

## Résumé
3 à 6 phrases sur l'objet et le déroulé de la discussion.

## Points clés
- liste à puces

## Décisions
- liste à puces (écris « Aucune décision explicite » s'il n'y en a pas)

## Actions à faire
- Qui — quoi — échéance si mentionnée (ou « Aucune action mentionnée »)

## Passages incertains
- mots ou phrases mal transcrits ou ambigus à vérifier (ou « Rien à signaler »)

Langue principale de l'enregistrement : {src_lang}.
{context}
Transcription :
\"\"\"
{transcript}
\"\"\"
"""


class SummaryRequest(BaseModel):
    transcript: str
    source_language: str = "inconnue"
    output_language: str = "français"
    context: str = ""


def _api_key_ok() -> bool:
    k = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return bool(k) and "..." not in k


# ---------------------------------------------------------------- application
app = FastAPI(title="Kuma")

# L'application Android appelle le serveur depuis une autre origine : on l'autorise.
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _lan_ips() -> list[str]:
    import socket

    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


@app.on_event("startup")
def _announce():
    port = os.getenv("KUMA_PORT", "8000")
    print("\n" + "=" * 60)
    print("  KUMA est prêt.")
    print(f"  Sur cet ordinateur : http://localhost:{port}")
    for ip in _lan_ips():
        print(f"  Dans l'application Android, tapez : {ip}:{port}")
    print(f"  Transcription : {'MODE DÉMO' if ASR_ENGINE == 'demo' else ASR_MODEL}")
    print("  Pour arrêter : fermez cette fenêtre (ou Ctrl + C)")
    print("=" * 60 + "\n", flush=True)


@app.get("/api/ping")
def ping():
    return {"ok": True, "app": "kuma"}


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/config")
def config():
    return {
        "languages": LANGUAGES,
        "asr_engine": ASR_ENGINE,
        "asr_model": ASR_MODEL,
        "summary_ready": _api_key_ok(),
    }


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), lang: str = Form("")):
    lang = lang.strip() or None
    suffix = Path(audio.filename or "audio").suffix or ".bin"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in{suffix}"
        src.write_bytes(await audio.read())
        if src.stat().st_size < 1000:
            return {"text": "", "seconds": 0}
        wav = _to_wav16k(src)
        secs = _duration(wav)
        if secs < 0.5:
            return {"text": "", "seconds": secs}
        try:
            text = await asyncio.to_thread(_transcribe_file, wav, lang)
        except HTTPException:
            raise
        except ImportError:
            raise HTTPException(
                500,
                "Le moteur de transcription n'est pas installé (pip install omnilingual-asr). "
                "Pour tester l'interface sans modèle : KUMA_ASR_ENGINE=demo.",
            )
        except Exception as e:  # erreur du modèle
            raise HTTPException(500, f"Échec de la transcription : {e}")
    return {"text": text, "seconds": round(secs, 1)}


@app.post("/api/summarize")
async def summarize(req: SummaryRequest):
    if not req.transcript.strip():
        raise HTTPException(400, "La transcription est vide.")
    if not _api_key_ok():
        raise HTTPException(
            500,
            "Clé API absente. Ajoutez ANTHROPIC_API_KEY dans le fichier .env puis relancez le serveur.",
        )
    import anthropic

    client = anthropic.AsyncAnthropic()
    prompt = SUMMARY_PROMPT.format(
        out_lang=req.output_language,
        src_lang=req.source_language,
        context=f"Contexte donné par l'utilisateur : {req.context}\n" if req.context.strip() else "",
        transcript=req.transcript[:150_000],
    )
    try:
        msg = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"L'API Claude a refusé la demande ({e.status_code}) : {e.message}")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "Impossible de joindre l'API Claude. Vérifiez la connexion Internet.")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return {"summary": text}
