"""
Usage (Linux/macOS):
# 列出 zh-TW 可用 voices（輸出到檔案）
python tts_google.py --list_voices --lang zh-TW > output/voices_zh-TW.txt
# 文字直接轉 wav
python tts_google.py --text "你好，這是測試" --out test.wav
# txt 檔轉 wav
python tts_google.py --text_file input.txt --out book.wav
# 指定 voice（例如：cmn-TW-Wavenet-A）
python tts_google.py --text "你好" --voice_name cmn-TW-Wavenet-A --out test_wavenet.wav

Usage (Windows PowerShell):
python tts_google.py --list_voices --lang zh-TW | Out-File -Encoding utf8 output\voices_zh-TW.txt
python tts_google.py --text "你好，這是測試" --out test.wav
python tts_google.py --text_file input.txt --out book.wav

Notes:
你可以把它當模組用：
from tts_google import tts_text_to_wav, tts_txt_to_wav
tts_text_to_wav("你好，這是測試", out="test.wav")          # -> output/test.wav
tts_txt_to_wav("input.txt", out="book.wav")               # -> output/book.wav
"""

import argparse
import os
import re
import sys
import wave
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv
from tqdm import tqdm
from google.cloud import texttospeech


def split_text(text: str, limit: int = 4500):
    """
    Google TTS limit is ~5000 chars/request (varies). Use 4500 as safe margin.
    Split by punctuation/line breaks; fallback hard split.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    parts = re.split(r"([。！？!?\n])", text)
    chunks = []
    buf = ""
    for i in range(0, len(parts), 2):
        seg = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        piece = (seg + punct).strip()
        if not piece:
            continue

        if len(buf) + len(piece) + 1 <= limit:
            buf = (buf + " " + piece).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = piece

    if buf:
        chunks.append(buf)

    fixed = []
    for c in chunks:
        if len(c) <= limit:
            fixed.append(c)
        else:
            for j in range(0, len(c), limit):
                fixed.append(c[j : j + limit])
    return fixed


def write_wav(out_path: Path, pcm_bytes: bytes, sample_rate: int):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


def list_voices(client: texttospeech.TextToSpeechClient, lang: str):
    resp = client.list_voices(language_code=lang)
    for v in resp.voices:
        genders = {1: "MALE", 2: "FEMALE", 3: "NEUTRAL"}.get(v.ssml_gender, str(v.ssml_gender))
        print(f"{v.name}\t{','.join(v.language_codes)}\t{genders}\t{v.natural_sample_rate_hertz}Hz")

def tts_to_wav(
    *,
    text: Optional[str] = None,
    text_file: Optional[Union[str, Path]] = None,
    out: Union[str, Path] = "out.wav",
    out_dir: Union[str, Path] = "output",
    lang: str = "zh-TW",
    voice_name: Optional[str] = None,
    rate: float = 1.0,
    pitch: float = 0.0,
    sr: int = 24000,
) -> Path:
    """
    Core TTS function.
    - Provide exactly one: text OR text_file
    - Returns the final output wav Path (always forced under out_dir)
    """
    load_dotenv()

    if (text is None) == (text_file is None):
        raise ValueError("Provide exactly one: text OR text_file")

    # Ensure credentials env exists
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred:
        raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS. Put it in .env and re-run.")
    if not Path(cred).exists():
        raise RuntimeError(f"Credential file not found: {cred}")

    if text_file is not None:
        text = Path(text_file).read_text(encoding="utf-8")

    assert text is not None
    client = texttospeech.TextToSpeechClient()

    out_dir = Path(out_dir)
    out_path = resolve_out_path(out_dir, str(out))

    synthesize(
        client=client,
        text=text,
        out_path=out_path,
        lang=lang,
        voice_name=voice_name,
        rate=rate,
        pitch=pitch,
        sample_rate=sr,
    )
    return out_path


def tts_text_to_wav(
    text: str,
    *,
    out: Union[str, Path] = "out.wav",
    out_dir: Union[str, Path] = "output",
    lang: str = "zh-TW",
    voice_name: Optional[str] = None,
    rate: float = 1.0,
    pitch: float = 0.0,
    sr: int = 24000,
) -> Path:
    """Convenience wrapper: text -> wav"""
    return tts_to_wav(
        text=text,
        out=out,
        out_dir=out_dir,
        lang=lang,
        voice_name=voice_name,
        rate=rate,
        pitch=pitch,
        sr=sr,
    )


def tts_txt_to_wav(
    text_file: Union[str, Path],
    *,
    out: Union[str, Path] = "out.wav",
    out_dir: Union[str, Path] = "output",
    lang: str = "zh-TW",
    voice_name: Optional[str] = None,
    rate: float = 1.0,
    pitch: float = 0.0,
    sr: int = 24000,
) -> Path:
    """Convenience wrapper: txt file -> wav"""
    return tts_to_wav(
        text_file=text_file,
        out=out,
        out_dir=out_dir,
        lang=lang,
        voice_name=voice_name,
        rate=rate,
        pitch=pitch,
        sr=sr,
    )

def resolve_out_path(out_dir: Path, out_name_or_path: str) -> Path:
    """
    Force outputs into out_dir.
    - If user passes "foo.wav" -> output/foo.wav
    - If user passes "output/foo.wav" -> output/foo.wav (still ok)
    - If user passes "/abs/path/foo.wav" -> output/foo.wav (still forced)
    """
    p = Path(out_name_or_path)
    return out_dir / p.name


def synthesize(
    client: texttospeech.TextToSpeechClient,
    text: str,
    out_path: Path,
    lang: str,
    voice_name: Optional[str],
    rate: float,
    pitch: float,
    sample_rate: int,
):
    chunks = split_text(text, limit=4500)
    if not chunks:
        raise SystemExit("Empty text after cleaning; nothing to synthesize.")

    if voice_name:
        voice = texttospeech.VoiceSelectionParams(language_code=lang, name=voice_name)
    else:
        voice = texttospeech.VoiceSelectionParams(language_code=lang)

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=rate,
        pitch=pitch,
        sample_rate_hertz=sample_rate,
    )

    tqdm.write(f"[INFO] chars={len(text)}  chunks={len(chunks)}  sr={sample_rate}  lang={lang}  voice={voice_name or '(auto)'}")

    pcm_all = bytearray()
    for c in tqdm(chunks, desc="TTS", unit="chunk"):
        synthesis_input = texttospeech.SynthesisInput(text=c)
        resp = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        pcm_all.extend(resp.audio_content)

    write_wav(out_path, bytes(pcm_all), sample_rate)
    print(f"Saved: {out_path}  (chunks={len(chunks)}, sr={sample_rate})")


def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    ap.add_argument("--text", type=str, default=None, help="Text to synthesize (quick test)")
    ap.add_argument("--text_file", type=str, default=None, help="Text file path (utf-8)")
    ap.add_argument("--out", type=str, default="out.wav", help="Output filename (forced into --out_dir)")
    ap.add_argument("--out_dir", type=str, default="output", help="Output directory (default: output)")
    ap.add_argument("--lang", type=str, default="zh-TW", help="Language code, e.g., zh-TW, cmn-TW, zh-CN, yue-HK")
    ap.add_argument("--voice_name", type=str, default=None, help="Specific voice name (optional), e.g., cmn-TW-Wavenet-A")
    ap.add_argument("--rate", type=float, default=1.0, help="Speaking rate")
    ap.add_argument("--pitch", type=float, default=0.0, help="Pitch")
    ap.add_argument("--sr", type=int, default=24000, help="Sample rate (Hz)")
    ap.add_argument("--list_voices", action="store_true", help="List voices for --lang and exit")
    args = ap.parse_args()

    # Ensure credentials env exists
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred:
        raise SystemExit("Missing GOOGLE_APPLICATION_CREDENTIALS. Put it in .env and re-run.")
    if not Path(cred).exists():
        raise SystemExit(f"Credential file not found: {cred}")

    client = texttospeech.TextToSpeechClient()

    if args.list_voices:
        list_voices(client, args.lang)
        return

    if bool(args.text) == bool(args.text_file):
        raise SystemExit("Choose exactly one: --text OR --text_file")

    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    else:
        text = args.text

    out_dir = Path(args.out_dir)
    out_path = resolve_out_path(out_dir, args.out)

    synthesize(
        client=client,
        text=text,
        out_path=out_path,
        lang=args.lang,
        voice_name=args.voice_name,
        rate=args.rate,
        pitch=args.pitch,
        sample_rate=args.sr,
    )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # Avoid noisy stack traces when piping output into head/grep etc.
        sys.exit(0)