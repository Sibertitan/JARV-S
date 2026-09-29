"""JARVIS görsel motoru: fotoğraf düzenleme ve yazı/meme/poster oluşturma (çıktı PNG/JPG)."""

import ctypes
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
FONT_BOLD = next((f for f in ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
                              "C:/Windows/Fonts/segoeuib.ttf",
                              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
                  if os.path.exists(f)), None)


def _pictures():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as k:
            p = Path(winreg.QueryValueEx(k, "My Pictures")[0])
            if p.is_absolute() and p.exists():
                return p
    except (OSError, ImportError, AttributeError):
        pass
    for c in (Path.home() / "OneDrive" / "Resimler", Path.home() / "OneDrive" / "Pictures",
              Path.home() / "Pictures", Path.home() / "Resimler"):
        if c.exists():
            return c
    return Path.home() / "Pictures"


def out_dir():
    d = _pictures() / "JARVIS Görseller"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save(img, name, fmt="png"):
    fmt = "jpg" if fmt.lower() in ("jpg", "jpeg") else "png"
    safe = re.sub(r'[<>:"/\\|?*]', "", name).strip() or "gorsel"
    path = out_dir() / f"{safe}.{fmt}"
    n = 2
    while path.exists():
        path = out_dir() / f"{safe} ({n}).{fmt}"
        n += 1
    if fmt == "jpg":
        img.convert("RGB").save(path, "JPEG", quality=95)
    else:
        img.save(path, "PNG")
    return path


def edit_image(path, operations=None, output_format="png", out_name=None):
    """Var olan bir fotoğrafı düzenler. operations: sözlük.
    Anahtarlar: resize_w, crop_ratio ("1:1","4:5","9:16","16:9"), rotate (derece),
    brightness, contrast, saturation, sharpness (1.0=aynı), filter
    (grayscale/sepia/blur/sharpen/auto/vivid/warm/cool), border (px, renk için border_color)."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # telefon fotoğraflarının yönünü düzelt
    img = img.convert("RGB")
    ops = operations or {}

    if ops.get("rotate"):
        img = img.rotate(-float(ops["rotate"]), expand=True)

    ratio = ops.get("crop_ratio")
    if ratio and ":" in str(ratio):
        rw, rh = [float(x) for x in str(ratio).split(":")]
        target = rw / rh
        w, h = img.size
        cur = w / h
        if cur > target:  # çok geniş → yanlardan kırp
            nw = int(h * target)
            img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:  # çok uzun → üst/alttan kırp
            nh = int(w / target)
            img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))

    if ops.get("resize_w"):
        w, h = img.size
        nw = int(ops["resize_w"])
        img = img.resize((nw, max(1, int(h * nw / w))), Image.LANCZOS)

    f = ops.get("filter")
    if f == "grayscale":
        img = ImageOps.grayscale(img).convert("RGB")
    elif f == "sepia":
        g = ImageOps.grayscale(img)
        img = ImageOps.colorize(g, "#2b1d0e", "#ffe9c4").convert("RGB")
    elif f == "blur":
        img = img.filter(ImageFilter.GaussianBlur(4))
    elif f == "sharpen":
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
    elif f == "auto":
        img = ImageOps.autocontrast(img, cutoff=1)
    elif f == "vivid":
        img = ImageEnhance.Color(ImageEnhance.Contrast(img).enhance(1.08)).enhance(1.35)
    elif f == "warm":
        r, g, b = img.split()
        img = Image.merge("RGB", (r.point(lambda i: min(255, int(i * 1.08))), g, b.point(lambda i: int(i * 0.92))))
    elif f == "cool":
        r, g, b = img.split()
        img = Image.merge("RGB", (r.point(lambda i: int(i * 0.92)), g, b.point(lambda i: min(255, int(i * 1.08)))))

    for key, enh in (("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast),
                     ("saturation", ImageEnhance.Color), ("sharpness", ImageEnhance.Sharpness)):
        if ops.get(key) is not None:
            img = enh(img).enhance(float(ops[key]))

    if ops.get("border"):
        img = ImageOps.expand(img, border=int(ops["border"]), fill=ops.get("border_color", "white"))

    return _save(img, out_name or (Path(path).stem + "_edit"), output_format)


def _font(size):
    return ImageFont.truetype(FONT_BOLD, size) if FONT_BOLD else ImageFont.load_default()


def _fit_font(draw, text, max_w, start):
    size = start
    while size > 12:
        font = _font(size)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 2
    return _font(12)


def _draw_text(draw, text, cx, y, max_w, size, fill="white", outline="black"):
    font = _font(size)
    words_per = max(6, int(max_w / (size * 0.6)))
    for line in textwrap.wrap(text, words_per):
        w = draw.textlength(line, font=font)
        x = cx - w / 2
        draw.text((x, y), line, font=font, fill=fill,
                  stroke_width=max(2, size // 12), stroke_fill=outline)
        y += int(size * 1.15)
    return y


def create_text_image(text="", top_text="", bottom_text="", bg="#111826", fg="#ffffff",
                      image_path=None, size="square", output_format="png", out_name=None):
    """Yazı/meme/poster görseli oluşturur. image_path verilirse o fotoğrafın üstüne yazar
    (klasik meme), yoksa düz/gradyan arka plan. size: square/vertical/horizontal/story."""
    dims = {"square": (1080, 1080), "vertical": (1080, 1350), "story": (1080, 1920),
            "horizontal": (1920, 1080)}.get(size, (1080, 1080))
    if image_path:
        base = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        base = ImageOps.fit(base, dims, Image.LANCZOS)
    else:
        base = Image.new("RGB", dims, bg)
    W, H = base.size
    draw = ImageDraw.Draw(base)

    if top_text:
        _draw_text(draw, top_text.upper(), W // 2, int(H * 0.04), W * 0.92, int(H * 0.09), fg)
    if bottom_text:
        y0 = int(H * 0.80)
        _draw_text(draw, bottom_text.upper(), W // 2, y0, W * 0.92, int(H * 0.09), fg)
    if text and not image_path:
        _draw_text(draw, text, W // 2, int(H * 0.40), W * 0.86, int(H * 0.08), fg, outline=bg)
    elif text:
        _draw_text(draw, text, W // 2, int(H * 0.44), W * 0.9, int(H * 0.075), fg)

    return _save(base, out_name or "gorsel", output_format)
