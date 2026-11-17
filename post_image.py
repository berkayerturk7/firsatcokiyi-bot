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


def _header(d, top, width):
    """Sol: amazon.com.tr  —  Sağ: @firsatcokiyi"""
    f_src = _font("Bold", 34)
    d.text((PAD, top), "amazon", font=f_src, fill=NAVY)
    aw = d.textlength("amazon", font=f_src)
    d.text((PAD + aw, top), ".com.tr", font=_font("Medium", 34), fill=GRAY)
    d.rounded_rectangle([PAD, top + 48, PAD + aw - 8, top + 54], radius=3, fill=ORANGE)
    d.text((width - PAD, top + 40), "@firsatcokiyi", font=_font("SemiBold", 28), fill=GRAY,
           anchor="rs")


def _badge_strip(d, top, width, days, height=190):
    """Büyük gün sayısı + "GÜNÜN EN DÜŞÜK FİYATI".
    365 günlük: turuncu zemin / lacivert yazı — 90 günlük: lacivert zemin / turuncu yazı."""
    bg, fg = (ORANGE, NAVY) if days == 365 else (NAVY, ORANGE)
    sub = NAVY if days == 365 else WHITE
    d.rounded_rectangle([PAD, top, width - PAD, top + height], radius=28, fill=bg)
    f_num = _font("ExtraBold", 150)
    num = str(days)
    num_w = d.textlength(num, font=f_num)
    f_l1, f_l2 = _font("Bold", 44), _font("ExtraBold", 62)
    l1, l2 = "GÜNÜN", "EN DÜŞÜK FİYATI"
    text_w = max(d.textlength(l2, font=f_l2), d.textlength(l1, font=f_l1))
    gap = 36
    x0 = (width - (num_w + gap + text_w)) // 2
    mid = top + height // 2
    d.text((x0, mid), num, font=f_num, fill=fg, anchor="lm")
    tx = x0 + num_w + gap
    d.text((tx, mid - 8), l1, font=f_l1, fill=sub, anchor="ls")
    d.text((tx, mid + 6), l2, font=f_l2, fill=fg, anchor="lt")
    return top + height


def _info_block(d, item, y, width, title_lines):
    """Marka, başlık, fiyat, indirim ve eski fiyat; bitişteki y'yi döndürür."""
    if item.get("brand"):
        d.text((PAD, y), item["brand"].upper(), font=_font("SemiBold", 26), fill=GRAY)
        y += 44
    f_title = _font("SemiBold", 40)
    for line in title_lines:
        d.text((PAD, y), line, font=f_title, fill=NAVY)
        y += 54
    y += 22

    f_price = _font("ExtraBold", 96)
    price_txt = tl(item["price"])
    d.text((PAD, y), price_txt, font=f_price, fill=NAVY)
    pw = d.textlength(price_txt, font=f_price)
    _pill(d, PAD + pw + 28, y + 30, f"-%{item['discount']}", _font("Bold", 38), RED, WHITE,
          pad_x=20, pad_y=12)
    y += 118

    f_old = _font("Medium", 34)
    old_txt = tl(item["old_price"])
    label = "Önceki fiyat  "
    d.text((PAD, y), label, font=f_old, fill=GRAY)
    lw = d.textlength(label, font=f_old)
    d.text((PAD + lw, y), old_txt, font=f_old, fill=GRAY)
    ow = d.textlength(old_txt, font=f_old)
    d.line([PAD + lw, y + 22, PAD + lw + ow, y + 22], fill=GRAY, width=3)
    return y + 44


def _info_height(item, n_title_lines):
    return (44 if item.get("brand") else 0) + 54 * n_title_lines + 22 + 118 + 44


def _paste_photo(img, item, top, bottom, width):
    box_w, box_h = width - 2 * PAD - 40, bottom - top
    photo = _product_photo(item["image"], box_w, box_h)
    img.paste(photo, ((width - photo.width) // 2, top + (box_h - photo.height) // 2), photo)


def _save(img, out_path):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


def create_post(item, out_path):
    """1080x1350 feed postu."""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _header(d, 64, W)
    badge_bottom = _badge_strip(d, 150, W, item["days"])

    title_lines = _wrap(d, short_title(item["title"]), _font("SemiBold", 40), W - 2 * PAD, 2)
    divider_y = H - 64 - 36 - _info_height(item, len(title_lines))
    _paste_photo(img, item, badge_bottom + 40, divider_y - 36, W)

    d.line([PAD, divider_y, W - PAD, divider_y], fill=LIGHT, width=2)
    _info_block(d, item, divider_y + 36, W, title_lines)
    d.rectangle([0, H - 14, W, H], fill=ORANGE)
    return _save(img, out_path)


SW, SH = 1080, 1920  # story


def create_story(item, category, out_path):
    """1080x1920 story. Instagram üstte ve altta ~250 px'i kendi arayüzüyle kapatır;
    içerik bu güvenli alanın içinde tutulur."""
    img = Image.new("RGB", (SW, SH), WHITE)
    d = ImageDraw.Draw(img)
    _header(d, 230, SW)

    # Kategori etiketi — öne çıkanlara eklerken kolay ayırt etmek için
    f_cat = _font("ExtraBold", 40)
    cat_txt = category.replace("i", "İ").upper()
    tw = d.textlength(cat_txt, font=f_cat)
    cy = 320
    d.rounded_rectangle([PAD, cy, PAD + tw + 56, cy + 72], radius=36, outline=NAVY, width=4)
    d.text((PAD + 28, cy + 36), cat_txt, font=f_cat, fill=NAVY, anchor="lm")

    badge_bottom = _badge_strip(d, 420, SW, item["days"])

    # Alt: profil linki çağrısı (güvenli alanın hemen üstü)
    cta_h, cta_bottom = 110, SH - 260
    cta_top = cta_bottom - cta_h
    d.rounded_rectangle([PAD, cta_top, SW - PAD, cta_bottom], radius=cta_h // 2, fill=ORANGE)
    d.text((SW // 2, cta_top + cta_h // 2), "ÜRÜN LİNKİ PROFİLDE  ↑", font=_font("ExtraBold", 46),
           fill=NAVY, anchor="mm")

    title_lines = _wrap(d, short_title(item["title"]), _font("SemiBold", 40), SW - 2 * PAD, 2)
    info_top = cta_top - 56 - _info_height(item, len(title_lines))
    _paste_photo(img, item, badge_bottom + 50, info_top - 60, SW)
    d.line([PAD, info_top - 30, SW - PAD, info_top - 30], fill=LIGHT, width=2)
    _info_block(d, item, info_top, SW, title_lines)
    d.rectangle([0, SH - 14, SW, SH], fill=ORANGE)
    return _save(img, out_path)


def caption(item):
    lines = [
        f"🔥 SON {item['days']} GÜNÜN EN DÜŞÜK FİYATI 🔥",
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
