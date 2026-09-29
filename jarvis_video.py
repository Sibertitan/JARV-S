"""JARVIS video motoru: videoları bulur, inceler (kareler) ve ffmpeg ile düzenler."""

import ctypes
import io
import os
import re
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".3gp"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}
def _pick_font():
    for f in ["C:/Windows/Fonts/ariblk.ttf",   # Arial Black — meme/altyazı için en okunaklı
              "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(f):
            return f
    return "C:/Windows/Fonts/arial.ttf"


FONT = _pick_font()
NO_WINDOW = subprocess.CREATE_NO_WINDOW

SIZES = {"vertical": (1080, 1920), "square": (1080, 1080), "horizontal": (1920, 1080)}
COLORS = {
    "vivid": "eq=saturation=1.35:contrast=1.08:brightness=0.02",
    "cinematic": "eq=contrast=1.12:saturation=0.85,colorbalance=rs=0.04:gs=-0.01:bs=-0.06:rh=0.04:bh=-0.04,vignette=PI/5",
    "warm": "colorbalance=rs=0.08:gs=0.02:bs=-0.08,eq=saturation=1.1",
    "cool": "colorbalance=rs=-0.06:bs=0.08,eq=saturation=1.05",
    "bw": "hue=s=0,eq=contrast=1.15",
}
TEXT_SIZES = {"small": 0.035, "medium": 0.05, "large": 0.07}


def _known_folder(csidl):
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf)
    return Path(buf.value) if buf.value else None


def edit_dir():
    d = (_known_folder(14) or Path.home() / "Videos") / "JARVIS Edit"  # CSIDL_MYVIDEO
    d.mkdir(parents=True, exist_ok=True)
    return d


def meme_dir():
    d = edit_dir() / "Memler"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_memes():
    return sorted(p for p in meme_dir().iterdir() if p.suffix.lower() in VIDEO_EXT)


def download_meme(url, name=None):
    """Bir video URL'sinden (YouTube, doğrudan bağlantı) meme kesiti indirip kütüphaneye koyar."""
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("İndirme aracı (yt-dlp) kurulu değil; meme dosyasını elle Memler klasörüne koyabilirsin.")
    safe = re.sub(r'[<>:"/\\|?*]', "", name or "meme").strip() or "meme"
    out = meme_dir() / f"{safe}.%(ext)s"
    opts = {"format": "mp4/best", "outtmpl": str(out), "quiet": True, "noplaylist": True,
            "merge_output_format": "mp4"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    final = meme_dir() / f"{safe}.mp4"
    return final if final.exists() else meme_dir() / f"{safe}.{info.get('ext', 'mp4')}"


def _search_roots():
    home = Path.home()
    roots = [_known_folder(14), _known_folder(39), _known_folder(13), _known_folder(0x10),
             home / "Downloads", home / "OneDrive" / "Masaüstü", home / "Desktop",
             home / "OneDrive" / "Resimler" / "Film Rulosu", home / "Pictures" / "Camera Roll"]
    seen, out = set(), []
    for r in roots:
        if r and r.exists() and str(r).lower() not in seen:
            seen.add(str(r).lower())
            out.append(r)
    return out


def find_media(kind="video", limit=10):
    """En yeni video (ya da müzik) dosyalarını listeler."""
    exts = VIDEO_EXT if kind == "video" else AUDIO_EXT
    files = []
    for root in _search_roots():
        for dirpath, dirs, names in os.walk(root):
            if dirpath.count(os.sep) - str(root).count(os.sep) > 3:
                dirs[:] = []
                continue
            for n in names:
                if Path(n).suffix.lower() in exts:
                    p = Path(dirpath) / n
                    try:
                        files.append((p.stat().st_mtime, p))
                    except OSError:
                        pass
    files.sort(reverse=True)
    return [p for _, p in files[:limit]]


def probe(path):
    """Süre, çözünürlük, fps ve ses var mı bilgisini döndürür."""
    r = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    err = r.stderr
    info = {"path": str(path), "duration": 0.0, "width": 0, "height": 0, "fps": 30.0, "audio": False, "rotation": 0}
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", err)
    if m:
        info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    m = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", err)
    if m:
        info["width"], info["height"] = int(m[1]), int(m[2])
    m = re.search(r"(\d+(?:\.\d+)?) fps", err)
    if m:
        info["fps"] = float(m[1])
    m = re.search(r"rotation of (-?\d+)", err) or re.search(r"rotate\s*:\s*(-?\d+)", err)
    if m and abs(int(float(m[1]))) in (90, 270):
        info["width"], info["height"] = info["height"], info["width"]  # telefon videoları dik kaydedilmiş olabilir
    info["audio"] = "Audio:" in err
    if not info["duration"]:
        raise ValueError(f"Video okunamadı: {path}")
    return info


def frames_sheet(path, count=8, start=None, end=None):
    """Videodan eşit aralıklı kareler alıp zaman damgalı tek bir görsel (PNG) üretir."""
    info = probe(path)
    s = max(0.0, float(start or 0))
    e = min(info["duration"], float(end or info["duration"]))
    count = max(2, min(int(count), 16))
    times = [s + (e - s) * (i + 0.5) / count for i in range(count)]
    thumbs = []
    for t in times:
        r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                            "-frames:v", "1", "-vf", "scale=360:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                           capture_output=True, creationflags=NO_WINDOW)
        if r.stdout:
            thumbs.append((t, Image.open(io.BytesIO(r.stdout)).convert("RGB")))
    if not thumbs:
        raise ValueError("Kare alınamadı")
    cols = 4 if len(thumbs) > 4 else len(thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    tw = max(im.width for _, im in thumbs)
    th = max(im.height for _, im in thumbs)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 28)), (15, 15, 20))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT, 18)
    for i, (t, im) in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * (th + 28)
        sheet.paste(im, (x, y + 28))
        draw.text((x + 6, y + 3), f"{int(t // 60)}:{t % 60:04.1f}", fill=(255, 220, 90), font=font)
    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    return buf.getvalue(), info


def story_video(scenes, voice="tr-TR-AhmetNeural", music_path=None, out_name=None, size="vertical"):
    """Sahnelerden anlatımlı, altyazılı bir video üretir (prompt→video).
    scenes: [{text, bg, fg, image_path, seconds, voiceover}]. Her sahne bir görsel + seslendirme."""
    import asyncio
    import tempfile
    import jarvis_image as ji
    W, H = SIZES.get(size, SIZES["vertical"])
    tmp = Path(tempfile.mkdtemp(prefix="jarvis_story_"))
    seg_paths = []

    try:
        import edge_tts
        have_tts = True
    except ImportError:
        have_tts = False

    for i, sc in enumerate(scenes):
        # 1) sahne görseli (yazı + arka plan/foto)
        img = ji.create_text_image(
            text=sc.get("text", ""), bg=sc.get("bg", "#0b1220"), fg=sc.get("fg", "#ffffff"),
            image_path=sc.get("image_path"), size=size, output_format="png", out_name=f"_sahne{i}")
        # 2) seslendirme
        vo = tmp / f"vo{i}.mp3"
        vo_dur = 0.0
        text = sc.get("voiceover") or sc.get("text") or ""
        if have_tts and text.strip():
            try:
                asyncio.run(edge_tts.Communicate(text, voice, rate="-6%").save(str(vo)))
                vo_dur = probe(vo)["duration"]
            except Exception:
                vo = None
        else:
            vo = None
        dur = max(float(sc.get("seconds") or 0), vo_dur + 0.6, 2.2)
        # 3) sahne videosu: görseli yavaşça yakınlaştır (Ken Burns), sesi ekle
        seg = tmp / f"seg{i}.mp4"
        args = [FF, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-t", f"{dur:.2f}", "-i", str(img)]
        if vo:
            args += ["-i", str(vo)]  # seslendirme
        else:
            args += ["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]  # sessiz ses
        zoom = (f"scale={W*2}:{H*2},zoompan=z='min(zoom+0.0006,1.12)':d={int(dur*30)}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps=30,setsar=1,format=yuv420p")
        # ses her zaman tam süreye eşitlenir (apad + atrim) ki birleştirmede kaymasın
        args += ["-filter_complex", f"[0:v]{zoom}[v];[1:a]aresample=44100,apad,atrim=0:{dur:.2f},aformat=channel_layouts=stereo[a]",
                 "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-c:a", "aac", "-b:a", "160k", "-t", f"{dur:.2f}", str(seg)]
        r = subprocess.run(args, capture_output=True, text=True, creationflags=NO_WINDOW, timeout=600)
        if not seg.exists():
            raise RuntimeError("Sahne oluşturulamadı:\n" + "\n".join(r.stderr.splitlines()[-6:]))
        seg_paths.append(seg)

    # sahneleri birleştir
    listf = tmp / "list.txt"
    listf.write_text("".join(f"file '{p.as_posix()}'\n" for p in seg_paths), encoding="utf-8")
    joined = tmp / "joined.mp4"
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(listf), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", str(joined)], creationflags=NO_WINDOW, timeout=900)

    name = re.sub(r'[<>:"/\\|?*]', "", out_name or f"jarvis_video_{time.strftime('%Y%m%d_%H%M%S')}").strip() or "jarvis_video"
    out = edit_dir() / f"{name}.mp4"
    n = 2
    while out.exists():
        out = edit_dir() / f"{name} ({n}).mp4"
        n += 1

    if music_path and Path(music_path).exists():
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined),
                        "-stream_loop", "-1", "-i", str(music_path),
                        "-filter_complex", "[1:a]volume=0.22[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(out)], creationflags=NO_WINDOW, timeout=600)
    else:
        import shutil
        shutil.copy(str(joined), str(out))
    return out, len(scenes)


def _atempo(speed):
    """atempo 0.5-2 aralığında çalışır; dışındaki hızlar zincirle yapılır."""
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


def _esc(path):
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def edit(spec, on_progress=None):
    """Düzenleme tarifini (spec) uygular, çıktı dosyasının yolunu döndürür.

    spec = {
      "clips": [{"path", "start", "end", "speed"}],       # sırayla birleştirilir
      "format": "vertical|square|horizontal|original", "fit": "blur|crop",
      "color": "none|vivid|cinematic|warm|cool|bw",
      "texts": [{"text", "start", "end", "position": "top|center|bottom", "size": "small|medium|large"}],
      "music": {"path", "volume", "start_at"}, "original_volume": 1.0,
      "fade_in": 0.5, "fade_out": 0.8, "output_name": "..."
    }
    """
    clips = spec.get("clips") or []
    if not clips:
        raise ValueError("En az bir klip gerekli")
    infos = [probe(c["path"]) for c in clips]

    fmt = spec.get("format", "vertical")
    if fmt in SIZES:
        W, H = SIZES[fmt]
    else:
        W, H = infos[0]["width"] or 1080, infos[0]["height"] or 1920
        scale = min(1.0, 1920 / max(W, H))
        W, H = int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
    fit = spec.get("fit", "blur")
    orig_vol = float(spec.get("original_volume", 1.0))

    args, filters, labels = [FF, "-hide_banner", "-y"], [], []
    total = 0.0
    for i, (c, info) in enumerate(zip(clips, infos)):
        start = max(0.0, float(c.get("start") or 0))
        end = min(info["duration"], float(c.get("end") or info["duration"]))
        if end <= start:
            raise ValueError(f"Klip {i + 1}: bitiş başlangıçtan önce")
        speed = min(4.0, max(0.25, float(c.get("speed") or 1.0)))
        dur = (end - start) / speed
        total += dur
        args += ["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(c["path"])]

        v = f"[{i}:v]setpts=(PTS-STARTPTS)/{speed}"
        if fit == "crop":
            filters.append(f"{v},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                           f"fps=30,setsar=1,format=yuv420p[v{i}]")
        else:  # bulanık arka plan: videonun tamamı görünür, boşluklar şık dolar
            filters.append(f"{v},split[va{i}][vb{i}]")
            filters.append(f"[va{i}]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,"
                           f"crop={W // 4}:{H // 4},boxblur=10:3,scale={W}:{H}[bg{i}]")
            filters.append(f"[vb{i}]scale={W}:{H}:force_original_aspect_ratio=decrease[fg{i}]")
            filters.append(f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1,format=yuv420p[v{i}]")
        if info["audio"] and orig_vol > 0:
            filters.append(f"[{i}:a]asetpts=PTS-STARTPTS,{_atempo(speed)},aresample=44100,"
                           f"aformat=channel_layouts=stereo,volume={orig_vol}[a{i}]")
        else:
            filters.append(f"anullsrc=r=44100:cl=stereo,atrim=duration={dur:.3f}[a{i}]")
        labels.append(f"[v{i}][a{i}]")

    filters.append(f"{''.join(labels)}concat=n={len(clips)}:v=1:a=1[vc][ac]")

    vchain = []
    color = spec.get("color", "none")
    if color in COLORS:
        vchain.append(COLORS[color])
    tmp = Path(tempfile.mkdtemp(prefix="jarvis_edit_"))
    for k, t in enumerate(spec.get("texts") or []):
        # Emoji ve diğer simgeler yazı tipinde olmadığı için kutu çıkar; temizle
        txt = re.sub(r"[^\w\s.,!?;:'\"()\-–—%&/+@#öçşğüıİÖÇŞĞÜ]", "", str(t.get("text", "")), flags=re.UNICODE).strip()
        if not txt:
            continue
        size = int(H * TEXT_SIZES.get(t.get("size", "medium"), 0.05)) if fmt != "horizontal" else int(H * TEXT_SIZES.get(t.get("size", "medium"), 0.05) * 1.2)
        width_chars = max(8, int(W / (size * 0.55)))
        tf = tmp / f"t{k}.txt"
        tf.write_text("\n".join(textwrap.wrap(txt, width_chars)), encoding="utf-8")
        pos = t.get("position", "bottom")
        y = {"top": "h*0.12", "center": "(h-text_h)/2", "bottom": "h*0.80-text_h/2"}.get(pos, "h*0.80-text_h/2")
        s, e = float(t.get("start") or 0), float(t.get("end") or total)
        style = t.get("style", "band")  # band: arkada koyu şerit; outline: sadece kenarlık
        pad = max(12, size // 3)
        common = (f"drawtext=fontfile='{_esc(FONT)}':textfile='{_esc(tf)}':fontcolor=white:fontsize={size}:"
                  f"line_spacing={max(4, size // 8)}:x=(w-text_w)/2:y={y}:"
                  f"borderw={max(3, size // 9)}:bordercolor=black:shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                  f"enable='between(t,{s:.2f},{e:.2f})'")
        if style == "band":
            common += f":box=1:boxcolor=black@0.55:boxborderw={pad}"
        vchain.append(common)
    fi, fo = float(spec.get("fade_in") or 0), float(spec.get("fade_out") or 0)
    if fi > 0:
        vchain.append(f"fade=t=in:st=0:d={fi}")
    if fo > 0:
        vchain.append(f"fade=t=out:st={max(0.0, total - fo):.3f}:d={fo}")
    filters.append(f"[vc]{','.join(vchain) if vchain else 'null'}[vout]")

    achain = []
    if fi > 0:
        achain.append(f"afade=t=in:st=0:d={fi}")
    if fo > 0:
        achain.append(f"afade=t=out:st={max(0.0, total - fo):.3f}:d={fo}")
    music = spec.get("music") or {}
    if music.get("path"):
        mi = len(clips)
        args += ["-stream_loop", "-1", "-ss", f"{float(music.get('start_at') or 0):.2f}", "-i", str(music["path"])]
        mvol = float(music.get("volume", 0.35))
        filters.append(f"[{mi}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,aresample=44100,"
                       f"aformat=channel_layouts=stereo,volume={mvol},afade=t=out:st={max(0.0, total - 1.5):.3f}:d=1.5[mus]")
        filters.append("[ac][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[amx]")
        filters.append(f"[amx]{','.join(achain) if achain else 'anull'}[aout]")
    else:
        filters.append(f"[ac]{','.join(achain) if achain else 'anull'}[aout]")

    script = tmp / "filter.txt"
    script.write_text(";\n".join(filters), encoding="utf-8")
    name = re.sub(r'[<>:"/\\|?*]', "", spec.get("output_name") or f"jarvis_{time.strftime('%Y%m%d_%H%M%S')}").strip() or "jarvis_edit"
    out = edit_dir() / f"{name}.mp4"
    n = 2
    while out.exists():
        out = edit_dir() / f"{name} ({n}).mp4"
        n += 1
    args += ["-filter_complex_script", str(script), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=NO_WINDOW, timeout=1800)
    if r.returncode != 0 or not out.exists():
        tail = "\n".join(r.stderr.strip().splitlines()[-8:])
        raise RuntimeError(f"ffmpeg hatası:\n{tail}")
    return out, total
