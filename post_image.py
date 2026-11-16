"""Amazon fırsatı için sade 1080x1350 (4:5) Instagram görseli üretir."""
import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
PAD = 72

NAVY = (19, 25, 33)        # Amazon koyu lacivert
ORANGE = (255, 153, 0)     # Amazon turuncusu
RED = (204, 12, 57)        # Amazon indirim kırmızısı
GRAY = (110, 115, 122)
LIGHT = (232, 234, 237)
WHITE = (255, 255, 255)

FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _font(weight, size):
    return ImageFont.truetype(str(FONT_DIR / f"Inter-{weight}.ttf"), size)


def tl(value):
    """1359.98 -> '1.359,98 TL' ; tam sayılarda kuruş gösterilmez."""
    if abs(value - round(value)) < 0.005:
        s = f"{round(value):,}".replace(",", ".")
    else:
        s = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} TL"


def short_title(title):
    """Amazon başlıklarındaki virgül/tire sonrası anahtar kelime yığınını atar."""
    for sep in (", ", " - ", " | ", " – "):  # "2,0 Ah" gibi ondalıklar bölünmesin
        head = title.split(sep)[0].strip()
        if len(head) >= 15:
            title = head
    if title.count("(") > title.count(")"):  # kesim parantezin ortasına denk geldiyse
        head = title[:title.rfind("(")].strip()
        if len(head) >= 15:
            title = head
    return title


def _wrap(draw, text, font, max_w, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
            continue
        if cur:
            lines.append(cur)
        cur = w
        if len(lines) == max_lines:
            break
    if len(lines) < max_lines and cur:
        lines.append(cur)
    lines = lines[:max_lines]
    used = " ".join(lines)
    if len(used) < len(" ".join(words)):  # kesildi -> sona … ekle
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_w:
            last = last[:-1].rstrip()
        lines[-1] = last.rstrip(" ,-–") + "…"
    return lines


def _pill(draw, x, y, text, font, bg, fg, pad_x=22, pad_y=12, anchor_right=False):
    tw = draw.textlength(text, font=font)
    asc, desc = font.getmetrics()
    h = asc + desc + 2 * pad_y - 6
    w = tw + 2 * pad_x
    if anchor_right:
        x = x - w
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    draw.text((x + pad_x, y + pad_y - 3), text, font=font, fill=fg)
    return w, h


def _product_photo(url, box_w, box_h):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    # Amazon görsellerinin etrafındaki beyaz boşluğu kırp
    gray = img.convert("L").point(lambda v: 255 if v < 245 else 0)
    bbox = gray.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.thumbnail((box_w, box_h), Image.LANCZOS)
    return img


def create_post(item, out_path):
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # ── Üst şerit: kaynak + rozet ────────────────────────────────────────────
    top = 64
    f_src = _font("Bold", 34)
    d.text((PAD, top), "amazon", font=f_src, fill=NAVY)
    aw = d.textlength("amazon", font=f_src)
    d.text((PAD + aw, top), ".com.tr", font=_font("Medium", 34), fill=GRAY)
    # Amazon'u çağrıştıran turuncu alt çizgi
    d.rounded_rectangle([PAD, top + 48, PAD + aw - 8, top + 54], radius=3, fill=ORANGE)

    badge = f"{item['days']} GÜNÜN EN DÜŞÜK FİYATI"
    _pill(d, W - PAD, top - 6, badge, _font("Bold", 26), ORANGE, NAVY, anchor_right=True)

    # ── Alt bilgi bloğunun yüksekliğini hesapla (blok alta yaslanır) ──────────
    f_title = _font("SemiBold", 40)
    title_lines = _wrap(d, short_title(item["title"]), f_title, W - 2 * PAD, 2)
    brand_h = 44 if item.get("brand") else 0
    block_h = 36 + brand_h + 54 * len(title_lines) + 22 + 118 + 44
    divider_y = H - 110 - block_h

    # ── Ürün görseli: üst şerit ile ayraç arasındaki alanı doldurur ─────────
    photo_top, photo_bottom = 170, divider_y - 40
    box_w, box_h = W - 2 * PAD - 40, photo_bottom - photo_top
    photo = _product_photo(item["image"], box_w, box_h)
    px = (W - photo.width) // 2
    py = photo_top + (box_h - photo.height) // 2
    img.paste(photo, (px, py), photo)

    # ── Alt bilgi alanı ─────────────────────────────────────────────────────
    y = divider_y
    d.line([PAD, y, W - PAD, y], fill=LIGHT, width=2)
    y += 36

    if item.get("brand"):
        d.text((PAD, y), item["brand"].upper(), font=_font("SemiBold", 26), fill=GRAY)
        y += brand_h

    for line in title_lines:
        d.text((PAD, y), line, font=f_title, fill=NAVY)
        y += 54
    y += 22

    # Fiyat satırı
    f_price = _font("ExtraBold", 96)
    price_txt = tl(item["price"])
    d.text((PAD, y), price_txt, font=f_price, fill=NAVY)
    pw = d.textlength(price_txt, font=f_price)

    f_disc = _font("Bold", 38)
    disc_txt = f"-%{item['discount']}"
    _pill(d, PAD + pw + 28, y + 30, disc_txt, f_disc, RED, WHITE, pad_x=20, pad_y=12)

    y += 118
    f_old = _font("Medium", 34)
    old_txt = tl(item["old_price"])
    label = "Önceki fiyat  "
    d.text((PAD, y), label, font=f_old, fill=GRAY)
    lw = d.textlength(label, font=f_old)
    d.text((PAD + lw, y), old_txt, font=f_old, fill=GRAY)
    ow = d.textlength(old_txt, font=f_old)
    d.line([PAD + lw, y + 22, PAD + lw + ow, y + 22], fill=GRAY, width=3)

    # ── Alt kenar: turuncu çizgi + hesap adı ───────────────────────────────
    d.text((W - PAD, H - 64), "@firsatcokiyi", font=_font("SemiBold", 28), fill=GRAY, anchor="rs")
    d.rectangle([0, H - 14, W, H], fill=ORANGE)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


def caption(item):
    lines = [
        f"🔻 Son {item['days']} günün en düşük fiyatı!",
        "",
        item["title"],
        "",
        f"💰 {tl(item['price'])}  (önceki fiyat {tl(item['old_price'])}, -%{item['discount']})",
    ]
    if item.get("rating") and item.get("review_count"):
        lines.append(f"⭐ {item['rating']:.1f} / 5  ({item['review_count']} değerlendirme)")
    lines += [
        "",
        f"🛒 {item['url']}",
        "",
        "Fiyat, paylaşım anında Amazon.com.tr'den alınmıştır; stok ve fiyat değişebilir.",
        "",
        "#amazon #amazontürkiye #indirim #fırsat #enucuz #kampanya #firsatcokiyi",
    ]
    return "\n".join(lines)
