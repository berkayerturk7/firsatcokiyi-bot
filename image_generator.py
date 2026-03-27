import os
import requests
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

LOGO_PATH   = Path("assets/logo.png")
FONTS_DIR   = Path("assets/fonts")
PHOTOS_DIR  = Path("assets/photos")
OUTPUT_DIR  = Path("output")

WIDTH, HEIGHT = 1080, 1350  # Instagram 4:5 dikey

CATEGORIES_META = {
    "E-Ticaret":         {"accent": "#FF6B00", "photo_query": "online shopping sale discount"},
    "Havacılık":         {"accent": "#1A7FFF", "photo_query": "airplane flight sky travel"},
    "Yemek":             {"accent": "#E63946", "photo_query": "food restaurant meal delicious"},
    "Giyim & Moda":      {"accent": "#A855F7", "photo_query": "fashion clothing style shopping"},
    "Teknoloji":         {"accent": "#00B4D8", "photo_query": "technology electronics gadget"},
    "Sağlık & Güzellik": {"accent": "#10B981", "photo_query": "beauty cosmetics skincare wellness"},
    "Ev & Yaşam":        {"accent": "#F59E0B", "photo_query": "home interior living room furniture"},
    "Spor":              {"accent": "#3B82F6", "photo_query": "sport fitness exercise athletic"},
    "Turizm & Otel":     {"accent": "#06D6A0", "photo_query": "hotel travel vacation beach"},
    "Otomotiv":          {"accent": "#F97316", "photo_query": "car automobile vehicle road"},
}

SYSTEM_FONTS = [
    # macOS
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    # Linux (Ubuntu/Debian) — fonts-liberation
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    # Linux — fonts-dejavu-core
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    # Linux — noto
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]

SYSTEM_FONTS_BOLD = [
    # macOS
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    font_list = SYSTEM_FONTS_BOLD if bold else SYSTEM_FONTS
    for path in font_list:
        if os.path.exists(path):
            try:
                idx = 1 if (bold and path.endswith(".ttc")) else 0
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    # Inter fallback — indir veya cache'den kullan
    font_file = FONTS_DIR / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf")
    if not font_file.exists():
        url = (
            "https://github.com/rsms/inter/releases/download/v4.0/Inter-Bold.ttf"
            if bold else
            "https://github.com/rsms/inter/releases/download/v4.0/Inter-Regular.ttf"
        )
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                font_file.write_bytes(r.content)
        except Exception:
            pass
    if font_file.exists():
        try:
            return ImageFont.truetype(str(font_file), size)
        except Exception:
            pass
    return ImageFont.load_default()

def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _wrap(text, font, max_w, draw, max_lines=2):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines

def _get_photo(category_name: str, query: str, pexels_key: str) -> Image.Image | None:
    PHOTOS_DIR.mkdir(exist_ok=True)
    cache = PHOTOS_DIR / f"{category_name.replace(' ', '_').replace('&', 've')}.jpg"

    # Cache varsa kullan (her gün yeni çek)
    if cache.exists():
        try:
            return Image.open(cache).convert("RGB")
        except Exception:
            pass

    if not pexels_key or pexels_key == "BURAYA_PEXELS_KEY":
        return None

    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": pexels_key},
            params={"query": query, "per_page": 3, "orientation": "portrait", "size": "large"},
            timeout=15,
        )
        if resp.status_code == 200:
            photos = resp.json().get("photos", [])
            if photos:
                import random
                photo = random.choice(photos)
                photo_url = photo["src"]["large2x"]
                img_resp = requests.get(photo_url, timeout=20)
                cache.write_bytes(img_resp.content)
                return Image.open(cache).convert("RGB")
    except Exception as e:
        print(f"  Fotoğraf indirilemedi: {e}")
    return None

def _make_background(photo: Image.Image | None, accent_rgb: tuple) -> Image.Image:
    bg = Image.new("RGB", (WIDTH, HEIGHT))

    if photo:
        # Fotoğrafı canvas'a ölçekle ve kırp
        ph_ratio = photo.width / photo.height
        cv_ratio = WIDTH / HEIGHT
        if ph_ratio > cv_ratio:
            new_h = HEIGHT
            new_w = int(HEIGHT * ph_ratio)
        else:
            new_w = WIDTH
            new_h = int(WIDTH / ph_ratio)
        photo = photo.resize((new_w, new_h), Image.LANCZOS)
        x = (new_w - WIDTH) // 2
        y = (new_h - HEIGHT) // 2
        photo = photo.crop((x, y, x + WIDTH, y + HEIGHT))

        # Hafif bulanıklaştır
        photo = photo.filter(ImageFilter.GaussianBlur(radius=2))
        # Karart
        photo = ImageEnhance.Brightness(photo).enhance(0.32)
        bg.paste(photo)
    else:
        # Fotoğraf yoksa gradient
        r, g, b = accent_rgb
        draw = ImageDraw.Draw(bg)
        for yi in range(HEIGHT):
            t = yi / HEIGHT
            draw.line(
                [(0, yi), (WIDTH, yi)],
                fill=(int(r * 0.08 + t * r * 0.04), int(g * 0.08 + t * g * 0.04), int(b * 0.08 + t * b * 0.04))
            )

    # Alt kısma koyu gradient overlay (metin okunabilirliği için)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for yi in range(HEIGHT // 2, HEIGHT):
        alpha = int(220 * ((yi - HEIGHT // 2) / (HEIGHT // 2)))
        od.line([(0, yi), (WIDTH, yi)], fill=(0, 0, 0, alpha))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    return bg

def create_post_image(deal: dict, category: dict, pexels_key: str = "") -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)

    cat_name = category["name"]
    meta     = CATEGORIES_META.get(cat_name, {"accent": "#FF6B00", "photo_query": cat_name})
    acc_rgb  = _hex(meta["accent"])
    acc_hex  = meta["accent"]

    # Arka plan fotoğrafı
    photo = _get_photo(cat_name, meta["photo_query"], pexels_key)
    img   = _make_background(photo, acc_rgb)
    draw  = ImageDraw.Draw(img)

    PAD = 60

    # ── Sol accent çizgisi ──────────────────────────────────────
    draw.rectangle([(0, 0), (7, HEIGHT)], fill=acc_rgb)

    # ── Üst bölüm: Badge + Tarih ────────────────────────────────
    f_badge = _load_font(38, bold=True)
    badge_text = cat_name.upper()
    bw = int(draw.textlength(badge_text, font=f_badge)) + 52
    bh = 64
    bx, by = PAD, 52
    draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=32, fill=acc_rgb)
    draw.text((bx + 26, by + 13), badge_text, font=f_badge, fill=(255, 255, 255))

    f_date = _load_font(32)
    date_str = datetime.now().strftime("%d.%m.%Y")
    dw = int(draw.textlength(date_str, font=f_date))
    draw.text((WIDTH - dw - PAD, 66), date_str, font=f_date, fill=(200, 200, 200))

    # ── Orta içerik (aşağıdan hizalanmış) ──────────────────────
    BOTTOM_START = HEIGHT - 90  # alt bar başlangıcı
    y = BOTTOM_START

    # Özellikler (bullet points)
    ozellikler = deal.get("ozellikler", [])
    if ozellikler:
        f_oz = _load_font(40)
        for oz in reversed(ozellikler[:3]):
            y -= 60
            draw.ellipse([(PAD, y + 14), (PAD + 14, y + 28)], fill=acc_rgb)
            draw.text((PAD + 28, y), oz[:52], font=f_oz, fill=(215, 215, 215))
        y -= 16
        f_label = _load_font(32, bold=True)
        draw.text((PAD, y - 36), "KAMPANYA KOŞULLARI", font=f_label, fill=acc_rgb)
        y -= 48

    # Ayırıcı
    draw.rectangle([(PAD, y), (WIDTH - PAD, y + 1)], fill=(*acc_rgb, 120))
    y -= 20

    # Fiyat
    eski = deal.get("eski_fiyat")
    yeni = deal.get("yeni_fiyat")
    if eski and yeni:
        f_yeni = _load_font(94, bold=True)
        yeni_text = f"{yeni} TL"
        yw = int(draw.textlength(yeni_text, font=f_yeni))
        y -= 100
        draw.text((PAD, y), yeni_text, font=f_yeni, fill=(255, 255, 255))

        f_eski = _load_font(54)
        eski_text = f"{eski} TL"
        ew = int(draw.textlength(eski_text, font=f_eski))
        draw.text((PAD + yw + 22, y + 28), eski_text, font=f_eski, fill=(140, 140, 140))
        mid = y + 28 + 27
        draw.line([(PAD + yw + 22, mid), (PAD + yw + 22 + ew, mid)], fill=(140, 140, 140), width=3)
        y -= 8
    elif yeni:
        f_yeni = _load_font(94, bold=True)
        y -= 104
        draw.text((PAD, y), f"{yeni} TL", font=f_yeni, fill=(255, 255, 255))
        y -= 8

    # Kampanya detayı (büyük vurgu)
    kampanya_detay = deal.get("kampanya_detay", "")
    if kampanya_detay and not (eski or yeni):
        f_kd = _load_font(86, bold=True)
        for line in reversed(_wrap(kampanya_detay, f_kd, WIDTH - PAD * 2, draw)):
            y -= 104
            draw.text((PAD, y), line, font=f_kd, fill=acc_rgb)
        y -= 8

    # Açıklama
    aciklama = deal.get("aciklama", "")
    if aciklama:
        f_desc = _load_font(44)
        for line in reversed(_wrap(aciklama, f_desc, WIDTH - PAD * 2, draw)):
            y -= 62
            draw.text((PAD, y), line, font=f_desc, fill=(205, 205, 205))
        y -= 14

    # Başlık
    baslik = deal.get("baslik", "")
    if baslik:
        f_title = _load_font(72, bold=True)
        for line in reversed(_wrap(baslik, f_title, WIDTH - PAD * 2, draw)):
            y -= 90
            draw.text((PAD, y), line, font=f_title, fill=(255, 255, 255))
        y -= 14

    # Marka
    marka = deal.get("marka", "")
    if marka:
        f_brand = _load_font(50, bold=True)
        y -= 64
        draw.text((PAD, y), marka.upper(), font=f_brand, fill=acc_rgb)

    # İndirim rozeti (sağ orta)
    indirim = deal.get("indirim_orani")
    if indirim:
        cx, cy, r = WIDTH - 155, HEIGHT // 2 - 60, 150
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=acc_rgb)
        f_pct = _load_font(78, bold=True)
        f_off = _load_font(36, bold=True)
        pct_text = f"%{indirim}"
        pw = int(draw.textlength(pct_text, font=f_pct))
        draw.text((cx - pw // 2, cy - 58), pct_text, font=f_pct, fill=(255, 255, 255))
        off_text = "İNDİRİM"
        ow = int(draw.textlength(off_text, font=f_off))
        draw.text((cx - ow // 2, cy + 28), off_text, font=f_off, fill=(255, 255, 255))

    # ── Alt bar ─────────────────────────────────────────────────
    BAR_H = 90
    bar_y = HEIGHT - BAR_H
    overlay2 = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od2 = ImageDraw.Draw(overlay2)
    od2.rectangle([(0, bar_y), (WIDTH, HEIGHT)], fill=(0, 0, 0, 220))
    img = Image.alpha_composite(img.convert("RGBA"), overlay2).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, bar_y), (WIDTH, bar_y + 3)], fill=acc_rgb)

    # Marka adı — şık tipografi
    f_brand_light = _load_font(34)
    f_brand_bold  = _load_font(34, bold=True)
    light_text = "fırsat"
    bold_text  = "çok iyi"
    lw = int(draw.textlength(light_text, font=f_brand_light))
    bw2 = int(draw.textlength(bold_text, font=f_brand_bold))
    total_w = lw + bw2 + 4
    tx = WIDTH - total_w - PAD
    ty = bar_y + (BAR_H - 34) // 2
    draw.text((tx, ty), light_text, font=f_brand_light, fill=(200, 200, 200))
    draw.text((tx + lw + 4, ty), bold_text, font=f_brand_bold, fill=acc_rgb)

    # Kaydet
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = cat_name.replace(" ", "_").replace("&", "ve")
    path = OUTPUT_DIR / f"{name}_{ts}.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"  Görsel: {path}")
    return str(path)


def create_story_image(deal: dict, category: dict, pexels_key: str = "") -> str:
    """1080x1920 Instagram Story görseli üretir."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    SW, SH = 1080, 1920  # Story boyutu 9:16

    cat_name = category["name"]
    meta     = CATEGORIES_META.get(cat_name, {"accent": "#FF6B00", "photo_query": cat_name})
    acc_rgb  = _hex(meta["accent"])

    # Arka plan
    photo = _get_photo(cat_name, meta["photo_query"], pexels_key)

    img = Image.new("RGB", (SW, SH))

    if photo:
        # Fotoğrafı story boyutuna kırp
        ph_ratio = photo.width / photo.height
        cv_ratio = SW / SH
        if ph_ratio > cv_ratio:
            new_h = SH
            new_w = int(SH * ph_ratio)
        else:
            new_w = SW
            new_h = int(SW / ph_ratio)
        photo = photo.resize((new_w, new_h), Image.LANCZOS)
        x = (new_w - SW) // 2
        y = (new_h - SH) // 2
        photo = photo.crop((x, y, x + SW, y + SH))
        photo = photo.filter(ImageFilter.GaussianBlur(radius=3))
        photo = ImageEnhance.Brightness(photo).enhance(0.28)
        img.paste(photo)

        # Alt yarıya koyu overlay
        ov = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for yi in range(SH // 3, SH):
            a = int(200 * ((yi - SH // 3) / (SH * 2 / 3)))
            od.line([(0, yi), (SW, yi)], fill=(0, 0, 0, min(a, 200)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    else:
        draw_tmp = ImageDraw.Draw(img)
        r, g, b = acc_rgb
        for yi in range(SH):
            t = yi / SH
            draw_tmp.line([(0, yi), (SW, yi)],
                fill=(int(r*0.07 + t*r*0.05), int(g*0.07 + t*g*0.05), int(b*0.07 + t*b*0.05)))

    draw = ImageDraw.Draw(img)
    PAD = 70

    # Sol accent çizgisi
    draw.rectangle([(0, 0), (8, SH)], fill=acc_rgb)

    # ── Üst alan: Kategori badge + tarih ───────────────────────
    f_badge = _load_font(46, bold=True)
    badge_text = cat_name.upper()
    bw = int(draw.textlength(badge_text, font=f_badge)) + 60
    bh = 74
    draw.rounded_rectangle([(PAD, 80), (PAD + bw, 80 + bh)], radius=37, fill=acc_rgb)
    draw.text((PAD + 30, 93), badge_text, font=f_badge, fill=(255, 255, 255))

    f_date = _load_font(38)
    date_str = datetime.now().strftime("%d.%m.%Y")
    dw = int(draw.textlength(date_str, font=f_date))
    draw.text((SW - dw - PAD, 97), date_str, font=f_date, fill=(190, 190, 190))

    # ── Orta alan: büyük indirim rozeti ────────────────────────
    indirim = deal.get("indirim_orani")
    if indirim:
        cx, cy, r = SW // 2, SH // 2 - 80, 230
        draw.ellipse([(cx-r, cy-r), (cx+r, cy+r)], fill=acc_rgb)
        f_pct = _load_font(136, bold=True)
        f_off = _load_font(54, bold=True)
        pt = f"%{indirim}"
        pw = int(draw.textlength(pt, font=f_pct))
        draw.text((cx - pw//2, cy - 112), pt, font=f_pct, fill=(255, 255, 255))
        ot = "İNDİRİM"
        ow = int(draw.textlength(ot, font=f_off))
        draw.text((cx - ow//2, cy + 44), ot, font=f_off, fill=(255, 255, 255))

    # ── Alt alan: içerik ────────────────────────────────────────
    BAR_H = 100
    bar_y = SH - BAR_H
    y = bar_y

    # Özellikler
    ozellikler = deal.get("ozellikler", [])
    if ozellikler:
        f_oz = _load_font(46)
        for oz in reversed(ozellikler[:3]):
            y -= 70
            draw.ellipse([(PAD, y+16), (PAD+16, y+32)], fill=acc_rgb)
            draw.text((PAD+30, y), oz[:48], font=f_oz, fill=(215, 215, 215))
        y -= 24

    # Ayırıcı
    draw.rectangle([(PAD, y), (SW-PAD, y+1)], fill=(*acc_rgb, 100))
    y -= 28

    # Kampanya detayı / fiyat
    kampanya_detay = deal.get("kampanya_detay", "")
    eski = deal.get("eski_fiyat")
    yeni = deal.get("yeni_fiyat")

    if eski and yeni:
        f_yeni = _load_font(118, bold=True)
        yt = f"{yeni} TL"
        yw = int(draw.textlength(yt, font=f_yeni))
        y -= 126
        draw.text((PAD, y), yt, font=f_yeni, fill=(255, 255, 255))
        f_eski = _load_font(64)
        et = f"{eski} TL"
        ew = int(draw.textlength(et, font=f_eski))
        draw.text((PAD + yw + 26, y + 36), et, font=f_eski, fill=(130, 130, 130))
        draw.line([(PAD+yw+26, y+68), (PAD+yw+26+ew, y+68)], fill=(130, 130, 130), width=3)
        y -= 10
    elif yeni:
        f_yeni = _load_font(118, bold=True)
        y -= 130
        draw.text((PAD, y), f"{yeni} TL", font=f_yeni, fill=(255, 255, 255))
    elif kampanya_detay:
        f_kd = _load_font(106, bold=True)
        for line in reversed(_wrap(kampanya_detay, f_kd, SW - PAD*2, draw)):
            y -= 124
            draw.text((PAD, y), line, font=f_kd, fill=acc_rgb)
        y -= 10

    # Açıklama
    aciklama = deal.get("aciklama", "")
    if aciklama:
        f_desc = _load_font(52)
        for line in reversed(_wrap(aciklama, f_desc, SW - PAD*2, draw)):
            y -= 72
            draw.text((PAD, y), line, font=f_desc, fill=(200, 200, 200))
        y -= 14

    # Başlık
    baslik = deal.get("baslik", "")
    if baslik:
        f_title = _load_font(90, bold=True)
        for line in reversed(_wrap(baslik, f_title, SW - PAD*2, draw)):
            y -= 110
            draw.text((PAD, y), line, font=f_title, fill=(255, 255, 255))
        y -= 14

    # Marka
    marka = deal.get("marka", "")
    if marka:
        f_brand = _load_font(64, bold=True)
        y -= 82
        draw.text((PAD, y), marka.upper(), font=f_brand, fill=acc_rgb)

    # Alt bar
    ov2 = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    od2 = ImageDraw.Draw(ov2)
    od2.rectangle([(0, bar_y), (SW, SH)], fill=(0, 0, 0, 220))
    img = Image.alpha_composite(img.convert("RGBA"), ov2).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, bar_y), (SW, bar_y+3)], fill=acc_rgb)

    # "fırsat çok iyi" yazısı alt bar
    f_bl = _load_font(44)
    f_bb = _load_font(44, bold=True)
    lt = "fırsat"
    bt = "çok iyi"
    lw2 = int(draw.textlength(lt, font=f_bl))
    bw3 = int(draw.textlength(bt, font=f_bb))
    tx = (SW - lw2 - bw3 - 6) // 2
    ty = bar_y + (BAR_H - 48) // 2
    draw.text((tx, ty), lt, font=f_bl, fill=(200, 200, 200))
    draw.text((tx + lw2 + 6, ty), bt, font=f_bb, fill=acc_rgb)

    # Kaydet
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = cat_name.replace(" ", "_").replace("&", "ve")
    path = OUTPUT_DIR / f"{name}_story_{ts}.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"  Story görseli: {path}")
    return str(path)
