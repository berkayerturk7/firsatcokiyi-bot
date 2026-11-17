"""Ürünleri Instagram öne çıkanlarına uygun kategorilere ayırır.

Kategori adları Instagram öne çıkan adı sınırına (15 karakter) sığar.
Öncelik: Amazon kategori filtresi -> ürün tipi -> başlıktaki kelimeler.
"""

# (ad, emoji) — sayfadaki sıralama da budur
CATEGORIES = [
    ("Teknoloji", "📱"),
    ("Ev & Yaşam", "🏠"),
    ("Moda", "👟"),
    ("Sağlık & Bakım", "💊"),
    ("Anne & Bebek", "🍼"),
    ("Pet", "🐾"),
    ("Market", "🛒"),
    ("Spor", "🏃"),
    ("Hobi & Oyuncak", "🧸"),
    ("Kitap & Ofis", "📚"),
    ("Otomotiv", "🚗"),
    ("Diğer", "✨"),
]
EMOJI = dict(CATEGORIES)

# Amazon "deals-collection-..." filtre adı -> kategori
BUBBLE_MAP = {
    "camera-and-photo": "Teknoloji",
    "cell-phones-and-accessories": "Teknoloji",
    "computers-and-accessories": "Teknoloji",
    "headphones-speakers-and-music": "Teknoloji",
    "televisions": "Teknoloji",
    "beauty": "Sağlık & Bakım",
    "health-and-personal-care": "Sağlık & Bakım",
    "pets": "Pet",
    "fashion-apparel": "Moda",
    "fashion-bags-accessories": "Moda",
    "fashion-kids": "Moda",
    "fashion-luggage": "Moda",
    "fashion-shoes": "Moda",
    "fashion-watches": "Moda",
    "home": "Ev & Yaşam",
    "kitchen": "Ev & Yaşam",
    "garden": "Ev & Yaşam",
    "diy": "Ev & Yaşam",
    "baby": "Anne & Bebek",
    "grocery": "Market",
    "sports-and-outdoor": "Spor",
    "toys": "Hobi & Oyuncak",
    "music": "Hobi & Oyuncak",
    "books": "Kitap & Ofis",
    "office-products": "Kitap & Ofis",
    "otomotive": "Otomotiv",
}

# Amazon ürün tipi (product_type) içindeki parça -> kategori
TYPE_KEYWORDS = [
    (("PHONE", "COMPUTER", "HEADPHONE", "TELEVISION", "MONITOR", "CAMERA", "SPEAKER",
      "CHARGING", "CABLE", "POWER_BANK", "TABLET", "KEYBOARD", "MOUSE", "PROJECTOR",
      "MOTHERBOARD", "MICROPHONE", "AERIAL_VEHICLE", "CAMCORDER"), "Teknoloji"),
    (("PET", "LITTER", "ANIMAL"), "Pet"),
    (("SHOE", "BOOT", "SLIPPER", "SHIRT", "COAT", "SWEATSHIRT", "SWEATER", "SUIT", "PANTS", "DRESS",
      "HANDBAG", "BACKPACK", "WATCH", "SUNGLASSES", "LUGGAGE", "SUITCASE", "JACKET"), "Moda"),
    (("TOOTHBRUSH", "SHAVER", "RAZOR", "SKIN", "HAIR", "INCONTINENCE", "VITAMIN",
      "COSMETIC", "PERFUME", "LOTION"), "Sağlık & Bakım"),
    (("DIAPER", "BABY", "INFANT"), "Anne & Bebek"),
    (("FOOD", "COFFEE", "BEVERAGE", "SNACK", "TEA"), "Market"),
    (("FRYER", "VACUUM", "IRON", "CHAIR", "KITCHEN", "COOK", "DRILL", "SAW",
      "PRESSURE_WASHER", "GRILL", "LAMP", "PURIFICATION", "CUP", "STOOL"), "Ev & Yaşam"),
    (("TREADMILL", "SPORT", "FITNESS", "BICYCLE", "ICE_CHEST", "CAMPING"), "Spor"),
    (("TOY", "GUITAR", "INSTRUMENT", "MIDI", "TURNTABLE", "GAME"), "Hobi & Oyuncak"),
    (("BOOK", "OFFICE", "PEN", "PAPER"), "Kitap & Ofis"),
    (("AUTOMOTIVE", "JUMP_STARTER", "TIRE", "CAR_"), "Otomotiv"),
]

# Son çare: Türkçe başlıktaki kelimeler
TITLE_KEYWORDS = [
    (("telefon", "kulaklık", "şarj", "kablo", "laptop", "bilgisayar", "televizyon", "tv ",
      "monitör", "kamera", "tripod", "powerbank", "power bank", "tablet", "hoparlör",
      "gaming", "oyuncu"), "Teknoloji"),
    (("kedi", "köpek", "mama", "kum"), "Pet"),
    (("bebek", "bez", "emzik", "yenidoğan"), "Anne & Bebek"),
    (("ayakkabı", "bot", "terlik", "tişört", "mont", "ceket", "çanta", "saat", "valiz",
      "gözlük", "sweatshirt", "pantolon", "clog"), "Moda"),
    (("diş", "tıraş", "şampuan", "krem", "parfüm", "vitamin", "cilt", "saç"), "Sağlık & Bakım"),
    (("kahve", "çay", "maden suyu", "su ", "çikolata", "gıda", "kapsül"), "Market"),
    (("tuvalet kağıdı", "deterjan", "raf", "tencere", "tava", "süpürge", "mutfak",
      "banyo", "termos", "matkap", "priz", "lamba", "akü"), "Ev & Yaşam"),
    (("spor", "koşu", "fitness", "kamp", "bisiklet"), "Spor"),
    (("oyuncak", "lego", "gitar", "puzzle"), "Hobi & Oyuncak"),
    (("kitap", "defter", "kalem", "ofis"), "Kitap & Ofis"),
    (("araç", "oto ", "lastik", "motor yağı"), "Otomotiv"),
]


def _type_match(ptype, key):
    """Ürün tipini "_" ile bölünmüş kelimeler üzerinden eşleştirir; böylece
    CHAIR "HAIR"a, CARPET "PET"e takılmaz. "_" içeren anahtarlar düz aranır."""
    if "_" in key:
        return key in ptype
    return any(t in (key, key + "S", key + "ES") for t in ptype.split("_"))


# Her şeyden önce bakılan, başlıkta geçince kesin olan ifadeler
# (Amazon bebek bezini "INCONTINENCE_PROTECTOR" tipinde sınıflandırıyor)
TITLE_OVERRIDES = [
    (("bebek bezi", "biberon", "emzik", "yenidoğan", "bebek arabası", "bebek havlusu",
      "mama sandalyesi", "bebek bakım"), "Anne & Bebek"),
]


def categorize(item):
    # 0) kesin başlık ifadeleri; 1) Amazon'un kesin ürün tipi; 2) ürünün bulunduğu
    #    kategori filtresi (ürün birden çok filtrede çıkabildiği için geride); 3) başlık
    title = f" {(item.get('title') or '').lower()} "
    for keys, cat in TITLE_OVERRIDES:
        if any(k in title for k in keys):
            return cat
    ptype = (item.get("product_type") or "").upper()
    for keys, cat in TYPE_KEYWORDS:
        if any(_type_match(ptype, k) for k in keys):
            return cat
    bubble = item.get("category")
    if bubble in BUBBLE_MAP:
        return BUBBLE_MAP[bubble]
    title = f" {(item.get('title') or '').lower()} "
    for keys, cat in TITLE_KEYWORDS:
        if any(k in title for k in keys):
            return cat
    return "Diğer"
