#!/usr/bin/env python3
"""
Combina los archivos de video (fdash-...v.mp4) y audio (fdash-...a.m4a)
descargados por separado en un solo archivo MP4 listo para analizar con Gemini.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


VIDEOS_DIR = Path(__file__).parent / "videos"
OUTPUT_SUFFIX = ".mp4"


def find_ffmpeg():
    """Busca ffmpeg en el sistema."""
    for cmd in ["ffmpeg", "ffmpeg.exe"]:
        result = subprocess.run(
            ["where" if sys.platform == "win32" else "which", cmd],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return cmd
    return None


def group_files(videos_dir: Path) -> dict:
    """
    Agrupa los archivos por número de hook.
    Retorna un dict: hook_id -> {"video": Path|None, "audio": Path|None, "combined": Path|None}
    """
    groups = {}

    # Patrón para archivos separados: hook_XXXX.fdash-YYYYYYYv.mp4 o hook_XXXX.fdash-YYYYYYYa.m4a
    pattern_dash = re.compile(r"^(hook_\d+)\.fdash-\d+([va])\.(mp4|m4a)$")
    # Patrón para archivos ya combinados: hook_XXXX.mp4
    pattern_combined = re.compile(r"^(hook_\d+)\.mp4$")

    for f in videos_dir.iterdir():
        if not f.is_file():
            continue

        m = pattern_dash.match(f.name)
        if m:
            hook_id, stream_type, _ = m.groups()
            groups.setdefault(hook_id, {"video": None, "audio": None, "combined": None})
            if stream_type == "v":
                groups[hook_id]["video"] = f
            else:
                groups[hook_id]["audio"] = f
            continue

        m = pattern_combined.match(f.name)
        if m:
            hook_id = m.group(1)
            groups.setdefault(hook_id, {"video": None, "audio": None, "combined": None})
            groups[hook_id]["combined"] = f

    return groups


def merge_streams(ffmpeg: str, video_path: Path, audio_path: Path, output_path: Path) -> bool:
    """Combina video y audio en un solo MP4 sin re-encodear."""
    cmd = [
        ffmpeg,
        "-y",                   # sobreescribir si existe
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c", "copy",           # sin re-encodear, solo muxear
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-movflags", "+faststart",  # útil para streaming/análisis
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def convert_m4a_only(ffmpeg: str, audio_path: Path, output_path: Path) -> bool:
    """Convierte un m4a sin video a mp4 (solo audio, para casos sin video)."""
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(audio_path),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def main():
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ERROR: ffmpeg no encontrado. Instálalo con: winget install ffmpeg")
        print("  o descárgalo de https://ffmpeg.org/download.html")
        sys.exit(1)

    print(f"Usando: {ffmpeg}")
    print(f"Carpeta de videos: {VIDEOS_DIR}\n")

    groups = group_files(VIDEOS_DIR)
    hooks_sorted = sorted(groups.keys())

    needs_merge = [h for h in hooks_sorted if groups[h]["video"] and groups[h]["audio"] and not groups[h]["combined"]]
    already_done = [h for h in hooks_sorted if groups[h]["combined"]]
    only_audio = [h for h in hooks_sorted if groups[h]["audio"] and not groups[h]["video"] and not groups[h]["combined"]]

    print(f"Hooks ya combinados (se omiten):  {len(already_done)}")
    print(f"Hooks con video+audio a combinar: {len(needs_merge)}")
    print(f"Hooks solo con audio (sin video): {len(only_audio)}")
    print()

    if not needs_merge and not only_audio:
        print("Nada que convertir.")
        return

    ok_count = 0
    fail_count = 0

    # Combinar video + audio
    for hook_id in needs_merge:
        g = groups[hook_id]
        output = VIDEOS_DIR / f"{hook_id}.mp4"
        print(f"  [{hook_id}] Combinando video + audio -> {output.name} ...", end=" ", flush=True)
        success, stderr = merge_streams(ffmpeg, g["video"], g["audio"], output)
        if success:
            print("OK")
            ok_count += 1
            # Eliminar los archivos fuente separados
            g["video"].unlink()
            g["audio"].unlink()
        else:
            print("FALLO")
            print(f"    ffmpeg error: {stderr[-300:]}")
            fail_count += 1

    # Convertir m4a sin video (raro, pero por si acaso)
    for hook_id in only_audio:
        g = groups[hook_id]
        output = VIDEOS_DIR / f"{hook_id}.mp4"
        print(f"  [{hook_id}] Convirtiendo solo audio m4a -> {output.name} ...", end=" ", flush=True)
        success, stderr = convert_m4a_only(ffmpeg, g["audio"], output)
        if success:
            print("OK")
            ok_count += 1
            g["audio"].unlink()
        else:
            print("FALLO")
            print(f"    ffmpeg error: {stderr[-300:]}")
            fail_count += 1

    print(f"\nResultado: {ok_count} convertidos correctamente, {fail_count} fallidos.")

    if fail_count == 0:
        print("Todos los videos están listos para analizar con Gemini.")


if __name__ == "__main__":
    main()
