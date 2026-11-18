#!/usr/bin/env python3
"""10 dakikalık Türkçe futbol videosu üretici.

Türkçe seslendirme (espeak-ng) + yakılmış Türkçe altyazı + 1920x1080 yatay MP4.
Kullanım: python3 build_video.py [çıktı_klasörü]
"""
import re, subprocess, sys, wave, os, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
W, H, FPS = 1920, 1080, 30
TARGET = 600.0  # saniye
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ---------------------------------------------------------------- senaryo
SEGMENTS = [
 ("intro", "HAFTANIN FUTBOL GÜNDEMİ", [
  "Merhaba, haftanın futbol gündemine hoş geldiniz.",
  "Bu videoda son iki haftanın en çok konuşulan üç başlığını inceliyoruz.",
  "Önce Şampiyonlar Ligi'nde tarihe geçen, 9-1'lik Como Lens maçı.",
  "Sonra Süper Lig'in on birinci haftasında zirve yarışının son durumu.",
  "Ve en sonunda, A Milli Takım'ın İzmir'de Belçika'ya karşı oynadığı maç.",
  "Skorlar ve isimler Türk spor basınındaki haberlerden derlendi.",
  "Resmi sonuçları UEFA ve TFF sayfalarından da kontrol edebilirsiniz.",
  "Hazırsanız başlayalım.",
 ]),
 ("como", "ŞAMPİYONLAR LİGİ: COMO 9-1 LENS", [
  "Konumuz, 4 Kasım gecesi Lens'in kendi evinde yaşadığı hezimet.",
  "Şampiyonlar Ligi lig aşamasının dördüncü haftasında Como, Lens'i 9-1 yendi.",
  "Haberlere göre bu skor, Şampiyonlar Ligi tarihinde bir takımın tek maçta attığı en fazla gol rekoruna ortak oluyor.",
  "Üstelik bu fark, turnuva tarihinin en büyük deplasman galibiyeti olarak kayıtlara geçti.",
  "Como'nun hücum hattında Anastasios Douvikas hat-trick yaptı.",
  "Nico Paz da skora katkı yapan isimlerden biri oldu.",
  "Lens'in tek golünü Ruben Aguilar attı.",
  "Bu sonuçla Como puanını 9'a çıkardı, Lens ise 3 puanda kaldı.",
  "Böyle bir skoru anlamak için biraz geriye çekilip büyük resme bakmak lazım.",
  "Şampiyonlar Ligi'nin yeni formatında averaj, sıralamayı belirleyen en önemli ölçütlerden biri.",
  "Yani Como'nun attığı her gol, sadece bir maçı değil, ilk sekize girme yarışını da etkiliyor.",
  "Lens açısından ise tablo tam tersi: sekiz gollük bir fark, averajda kolay kapanmayacak bir çukur demek.",
  "Futbolda bu kadar farklı skorlar genellikle bir anda gelmez.",
  "Çoğu zaman bir takım öne geçer, rakip riske girer, savunma arkasında boşluklar açılır ve skor katlanarak büyür.",
  "Elbette tek bir maç, iki takımın sezonunun tamamını anlatmaz.",
  "Ama böyle bir gecenin hem moral hem de averaj açısından bıraktığı iz, kolay silinmez.",
  "Aynı gece oynanan diğer maçlar da gol açısından hareketliydi.",
  "Kaynaklara göre Fenerbahçe, Liverpool'u 3-2 yenerek bu turnuvadaki ilk galibiyetini aldı.",
  "Real Madrid, AEK Atina'yı 3-2, Manchester City de RB Leipzig'i 3-2 geçti.",
  "Arsenal, Slavia Prag'ı 2-1, Porto ise Napoli'yi 4-1 mağlup etti.",
  "Yani gece boyunca gol de heyecan da eksik olmadı.",
  "Bu maçların bazı ayrıntıları, özellikle gol dakikaları ve isimler, kaynaklar arasında farklılık gösteriyor.",
  "Bu yüzden kesin bilgi için resmi UEFA sayfasına bakmanızı öneririm.",
  "Şimdi gözümüzü kendi liğimize çevirelim.",
 ]),
 ("lig", "SÜPER LİG: 11. HAFTA", [
  "Gelelim Süper Lig'e.",
  "Ligin on birinci haftası 6 ile 8 Kasım arasında oynandı ve zirve yarışı netleşmeye başladı.",
  "Galatasaray, sahasında Amed Sportif Faaliyetler'i 4-3 yendi.",
  "Yedi gollü bu maç, karşılaşmanın ne kadar çekişmeli geçtiğini gösteriyor.",
  "Sarı kırmızılılar bu galibiyetle 28 puana ulaştı ve liderliğini korudu.",
  "Üstelik ligde art arda beşinci galibiyetlerini aldılar.",
  "Trabzonspor, deplasmanda Alanyaspor'u 2-0 yendi.",
  "Bordo mavililer 25 puanla ikinci sıraya yükseldi.",
  "Beşiktaş, Gençlerbirliği'ni 3-0 geçti ve 22 puanla dördüncü sırada yer aldı.",
  "Fenerbahçe ise Çorum FK deplasmanında 5-0 kazandı.",
  "Bu maç, yeni teknik direktör Emre Belözoğlu yönetiminde oynanan ilk maç olarak aktarılıyor.",
  "Fenerbahçe 19 puanla altıncı sırada, ama ligin en çok gol atan takımı: 29 golle.",
  "Tabloya bakınca ilginç bir denge görüyoruz.",
  "Lider ile ikinci arasında sadece 3 puan var.",
  "Lider ile Fenerbahçe arasındaki fark ise 9 puan.",
  "Bu kadar erken bir aşamada 9 puan kapanamayacak bir fark değil.",
  "Ama her hafta hata yapma lüksünüz de olmuyor.",
  "Bir de golleri düşünün: Fenerbahçe en golcü takım, ama puan tablosunda altıncı.",
  "Bu, hücum gücünün tek başına yetmediğini, kritik maçlarda puan kaybetmenin bedelini gösteriyor olabilir.",
  "Galatasaray'ın 4-3'lük maçı da başka bir soruyu gündeme getiriyor: üç gol yemek.",
  "Lider olmak istiyorsanız, sadece gol atmak değil, savunma istikrarını da korumak zorundasınız.",
  "Bu yüzden önümüzdeki haftalarda puanın yanında averajı ve yenilen golleri de izlemek gerekecek.",
  "Trabzonspor'un deplasmandaki temiz galibiyeti ise istikrar mesajı veriyor.",
  "İki sıfır, kolay gibi görünür ama sezonun bu döneminde kazanılan deplasman maçları şampiyonluk yarışında çok değerli.",
  "Beşiktaş ve Fenerbahçe'nin üçlü skorlu galibiyetleri de takımların toparlandığını düşündürüyor.",
  "On ikinci hafta yaklaşırken Galatasaray'ın maçının stadyumunun değiştiği de haberlerde yer aldı.",
  "Güncel puan durumunu TFF ve spor sitelerinden takip edebilirsiniz.",
  "Gelelim bu videonun belki de en çok tartışılan başlığına.",
 ]),
 ("milli", "A MİLLİ TAKIM: TÜRKİYE 1-2 BELÇİKA", [
  "A Milli Takım, İzmir'de Gürsel Aksel Stadı'nda Belçika'ya 2-1 yenildi.",
  "Haberlere göre bu, Sergen Yalçın'ın milli takımın başındaki ilk maçıydı.",
  "Vincenzo Montella dönemi, kötü sonuçların ardından sona ermişti.",
  "Maça Türkiye önde başladı.",
  "Arda Güler yirminci dakikada takımı öne geçirdi.",
  "Ama sadece yedi dakika sonra, yirmi yedinci dakikada Kevin De Bruyne eşitliği sağladı.",
  "Ve yirminci dakikadan tam on dakika sonra, otuzuncu dakikada Charles De Ketelaere Belçika'yı öne taşıdı.",
  "Yani maçın kaderi, yalnızca on dakikalık bir bölümde belirlendi.",
  "Türkiye üstünlüğünü koruyamadı.",
  "Bu sonuçla Türkiye grupta beşinci maçında da puan alamadı.",
  "Belçika ise bu galibiyetle 9 puana yükseldi.",
  "Burada aslında iki ayrı konu var.",
  "Birincisi sonuç: art arda beş maçta puan alamamak, her teknik direktör için ağır bir tablo.",
  "İkincisi süreç: yeni bir hocayla çıkılan ilk maçta, ilk yarım saatte hem öne geçmek hem de geri düşmek.",
  "Kısa sürede arka arkaya yenilen goller, çoğu zaman konsantrasyon ve geçiş savunmasıyla ilgili soruları akla getirir.",
  "Belçika gibi oyuncu kalitesi yüksek bir rakibe karşı, en küçük boşluk bile cezalandırılıyor.",
  "Kevin De Bruyne gibi bir oyuncuya, sadece bir anlık serbestlik vermek bile yeterli.",
  "Öte yandan Arda Güler'in golü, bu maçın tek olumlu notu olarak öne çıkıyor.",
  "Genç oyuncunun milli takımdaki etkisi, bu tabloda umut verici bir işaret.",
  "Yine de tek bir maçla yeni bir dönemin hükmünü vermek için henüz çok erken.",
  "Sergen Yalçın'ın elinde hazırlanmak için zaman var mı, hangi oyuncu sistemini kuracak, bunu önümüzdeki maçlarda göreceğiz.",
  "Asıl soru şu: Bu takım, geriye düştüğünde nasıl tepki verecek?",
  "Çünkü iyi takımları ayıran şey, kötü gidişatı ne kadar çabuk durdurabildikleri.",
  "Taraftarın beklentisi de yüksek, sabrı da sınırlı.",
 ]),
 ("outro", "ÖZETLE", [
  "Özetleyelim.",
  "Şampiyonlar Ligi'nde Como, Lens'i 9-1 yenerek tarihe geçti.",
  "Süper Lig'de Galatasaray 28 puanla lider, Trabzonspor 25 puanla ikinci.",
  "Fenerbahçe ligin en golcü takımı olsa da puan tablosunda altıncı sırada.",
  "A Milli Takım ise Belçika'ya 2-1 yenilerek beşinci maçta da puan alamadı.",
  "Bu videodaki skorlar ve isimler haber kaynaklarından derlendi.",
  "Tek tek maçların ayrıntıları kaynaklar arasında farklılık gösterebilir.",
  "Mutlaka resmi sonuçları da kontrol edin.",
  "Hangi konu sizce haftanın en önemli olayıydı?",
  "Yorumlara yazın, tartışalım.",
  "Videoyu beğendiyseniz abone olmayı ve bildirimleri açmayı unutmayın.",
  "Bir sonraki videoda görüşmek üzere, hoşça kalın.",
 ]),
]

# ------------------------------------------------- sayı -> Türkçe okunuş
ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
def num_tr(n):
    if n == 0: return "sıfır"
    if n < 100: return (TENS[n // 10] + " " + ONES[n % 10]).strip()
    if n < 1000:
        h = "yüz" if n // 100 == 1 else ONES[n // 100] + " yüz"
        return (h + " " + (num_tr(n % 100) if n % 100 else "")).strip()
    return str(n)
def speakable(t):
    t = re.sub(r"(\d+)-(\d+)", lambda m: f"{num_tr(int(m[1]))} {num_tr(int(m[2]))}", t)
    t = re.sub(r"\d+", lambda m: num_tr(int(m[0])), t)
    return t.replace("hat-trick", "hat trik").replace("FK", "ef ka").replace("TFF", "te ef ef").replace("UEFA", "uefa").replace("AEK", "a e ka").replace("RB", "ar be")

# --------------------------------------------------------------- ses
def tts(text, path, speed):
    subprocess.run(["espeak-ng", "-v", "tr", "-s", str(speed), "-p", "45", "-a", "170", "-g", "2",
                    "-w", path, speakable(text)], check=True)
def wav_samples(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16), w.getframerate()

# --------------------------------------------------------------- görüntü
def font(p, s): return ImageFont.truetype(p, s)
def background(seg_idx):
    img = Image.new("RGB", (W, H))
    px = np.zeros((H, W, 3), dtype=np.uint8)
    y = np.linspace(0, 1, H)[:, None]
    px[..., 0] = (10 + 8 * y).astype(np.uint8)
    px[..., 1] = (45 + 35 * (1 - y)).astype(np.uint8)
    px[..., 2] = (25 + 10 * y).astype(np.uint8)
    img = Image.fromarray(px)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([60, 60, W - 60, H - 60], outline=(255, 255, 255, 40), width=4)
    d.line([W // 2, 60, W // 2, H - 60], fill=(255, 255, 255, 40), width=4)
    d.ellipse([W // 2 - 180, H // 2 - 180, W // 2 + 180, H // 2 + 180], outline=(255, 255, 255, 40), width=4)
    return img
def center(d, xy, text, f, fill):
    w = d.textlength(text, font=f)
    d.text((xy[0] - w / 2, xy[1]), text, font=f, fill=fill)
def panel(d, box, fill=(0, 0, 0, 150)):
    d.rounded_rectangle(box, radius=28, fill=fill)
def scoreboard(d, left, ls, rs, right, y=300):
    panel(d, (260, y, W - 260, y + 230))
    center(d, (560, y + 85), left, font(FB, 56), "white")
    center(d, (W - 560, y + 85), right, font(FB, 56), "white")
    center(d, (W // 2, y + 35), f"{ls} - {rs}", font(FB, 130), (255, 215, 0))
def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def visual(kind, title):
    img = background(0); d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, 150], fill=(0, 0, 0, 170))
    d.text((90, 38), title, font=font(FB, 66), fill="white")
    d.rectangle([0, 146, W, 154], fill=(255, 215, 0))
    if kind == "intro":
        center(d, (W // 2, 230), "Bu videoda 3 başlık", font(FB, 60), (255, 215, 0))
        items = ["1  Como 9-1 Lens (Şampiyonlar Ligi)", "2  Süper Lig 11. hafta ve zirve yarışı", "3  Türkiye 1-2 Belçika (İzmir)"]
        for i, t in enumerate(items):
            panel(d, (260, 340 + i * 150, W - 260, 340 + i * 150 + 120))
            d.text((320, 340 + i * 150 + 25), t, font=font(FB, 56), fill="white")
    elif kind == "como":
        scoreboard(d, "LENS", 1, 9, "COMO", y=210)
        center(d, (W // 2, 460), "Şampiyonlar Ligi · 4. hafta · 4 Kasım 2026", font(FR, 40), (220, 220, 220))
        panel(d, (160, 520, 900, 780))
        d.text((200, 545), "Como", font=font(FB, 44), fill=(255, 215, 0))
        d.text((200, 610), "Douvikas (hat-trick)", font=font(FR, 40), fill="white")
        d.text((200, 665), "Nico Paz + diğerleri", font=font(FR, 40), fill="white")
        d.text((200, 720), "Lens: Aguilar", font=font(FR, 40), fill="white")
        panel(d, (960, 520, W - 160, 780))
        d.text((1000, 545), "Aynı gece", font=font(FB, 44), fill=(255, 215, 0))
        for i, t in enumerate(["Fenerbahçe 3-2 Liverpool", "Real Madrid 3-2 AEK", "Man. City 3-2 RB Leipzig",
                               "Arsenal 2-1 Slavia Prag", "Porto 4-1 Napoli"]):
            d.text((1000, 595 + i * 36), t, font=font(FR, 30), fill="white")
    elif kind == "lig":
        teams = [("Galatasaray", 28, (255, 165, 0)), ("Trabzonspor", 25, (120, 170, 255)),
                 ("Beşiktaş", 22, (230, 230, 230)), ("Fenerbahçe", 19, (255, 235, 59))]
        center(d, (W // 2, 190), "Puan durumu (11. hafta sonrası, haber kaynaklarına göre)", font(FR, 36), (220, 220, 220))
        for i, (n, p, c) in enumerate(teams):
            y = 250 + i * 95
            d.text((140, y + 8), n, font=font(FB, 44), fill="white")
            d.rounded_rectangle((520, y, 520 + int(p / 28 * 1150), y + 70), radius=16, fill=c + (255,))
            d.text((540 + int(p / 28 * 1150), y + 8), f"{p}", font=font(FB, 46), fill="white")
        panel(d, (140, 630, W - 140, 770))
        r = ["Galatasaray 4-3 Amed SF", "Alanyaspor 0-2 Trabzonspor", "Gençlerbirliği 0-3 Beşiktaş", "Çorum FK 0-5 Fenerbahçe"]
        for i, t in enumerate(r):
            d.text((200 + (i % 2) * 800, 650 + (i // 2) * 60), t, font=font(FB, 40), fill="white")
    elif kind == "milli":
        scoreboard(d, "TÜRKİYE", 1, 2, "BELÇİKA", y=210)
        center(d, (W // 2, 460), "İzmir · Gürsel Aksel Stadı · Teknik direktör: Sergen Yalçın", font(FR, 40), (220, 220, 220))
        d.rectangle((260, 620, W - 260, 632), fill=(255, 255, 255, 120))
        for m, who, c in [(20, "Arda Güler", (255, 80, 80)), (27, "De Bruyne", (255, 215, 0)), (30, "De Ketelaere", (255, 215, 0))]:
            x = 260 + int(m / 90 * (W - 520))
            d.ellipse((x - 18, 607, x + 18, 645), fill=c + (255,))
            d.text((x - 25, 555 - (m == 27) * 50), f"{m}'", font=font(FB, 40), fill="white")
        d.text((260, 660), "0'", font=font(FR, 34), fill="white"); d.text((W - 300, 660), "90'", font=font(FR, 34), fill="white")
        for i, t in enumerate(["20'  Arda Güler (TÜR)", "27'  De Bruyne (BEL)", "30'  De Ketelaere (BEL)"]):
            d.text((W // 2 - 270, 750 + i * 0), "", font=font(FR, 10))
        center(d, (W // 2, 715), "20' Arda Güler · 27' De Bruyne · 30' De Ketelaere", font(FB, 40), "white")
    else:  # outro
        center(d, (W // 2, 200), "Bu haftanın özeti", font(FB, 56), (255, 215, 0))
        for i, t in enumerate(["Como 9-1 Lens: Şampiyonlar Ligi'nde tarihi gece", "Süper Lig: Galatasaray 28, Trabzonspor 25 puan",
                               "Türkiye 1-2 Belçika: 5. maçta da puan yok"]):
            panel(d, (200, 290 + i * 130, W - 200, 290 + i * 130 + 105))
            d.text((250, 290 + i * 130 + 25), t, font=font(FB, 46), fill="white")
        center(d, (W // 2, 715), "Skorlar haber kaynaklarından derlenmiştir · Resmi sonuçlar: UEFA / TFF", font(FR, 34), (220, 220, 220))
    return img

def with_subtitle(base, text):
    img = base.copy(); d = ImageDraw.Draw(img, "RGBA")
    f = font(FB, 46)
    lines = wrap(d, text, f, 1660)
    lh = 60; bh = lh * len(lines) + 40; y0 = H - 80 - bh
    d.rounded_rectangle((120, y0, W - 120, y0 + bh), radius=22, fill=(0, 0, 0, 190))
    for i, l in enumerate(lines):
        center(d, (W // 2, y0 + 20 + i * lh), l, f, "white")
    return img

# --------------------------------------------------------------- ana
def srt_time(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def synth_all(speed, tmp):
    items = []
    for si, (kind, title, sents) in enumerate(SEGMENTS):
        for j, s in enumerate(sents):
            p = os.path.join(tmp, f"{si}_{j}.wav"); tts(s, p, speed)
            items.append((si, s, p))
    return items

def total_len(items, pause, segpause):
    tot = 0.0
    for k, (si, s, p) in enumerate(items):
        a, sr = wav_samples(p)
        tot += len(a) / sr + pause + (segpause if (k + 1 < len(items) and items[k + 1][0] != si) else 0)
    return tot

def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
    tmp = os.path.join(OUT, "_tmp"); os.makedirs(tmp)
    pause, segpause = 0.45, 1.2
    lo, hi, speed = 105, 175, 140
    for _ in range(5):  # hedef süreye en yakın hızı bul
        speed = (lo + hi) // 2
        items = synth_all(speed, tmp); L = total_len(items, pause, segpause)
        print(f"hız {speed} -> {L:.1f} sn")
        if abs(L - TARGET) < 8: break
        if L > TARGET: lo = speed
        else: hi = speed
    # kısaysa duraklamaları büyüterek hedefe tamamla
    if L < TARGET - 8:
        pause += (TARGET - L) / len(items) * 0.8
        print("duraklama ->", round(pause, 2))
    bases = [visual(k, t) for k, t, _ in SEGMENTS]
    audio, cues, t = [], [], 0.0
    lines_concat = []
    sr0 = None
    for k, (si, s, p) in enumerate(items):
        a, sr = wav_samples(p); sr0 = sr
        gap = pause + (segpause if (k + 1 < len(items) and items[k + 1][0] != si) else 0)
        if k == len(items) - 1: gap += 1.5
        dur = len(a) / sr + gap
        audio.append(a); audio.append(np.zeros(int(gap * sr), dtype=np.int16))
        png = os.path.join(tmp, f"f{k:04}.png"); with_subtitle(bases[si], s).save(png)
        lines_concat += [f"file '{png}'", f"duration {dur:.4f}"]
        cues.append((t, t + len(a) / sr, s)); t += dur
    lines_concat.append(lines_concat[-2])
    with open(os.path.join(tmp, "list.txt"), "w") as f: f.write("\n".join(lines_concat))
    wavp = os.path.join(OUT, "seslendirme.wav")
    with wave.open(wavp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr0); w.writeframes(np.concatenate(audio).tobytes())
    with open(os.path.join(OUT, "altyazi_tr.srt"), "w", encoding="utf-8") as f:
        for i, (a, b, s) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n")
    mp4 = os.path.join(OUT, "futbol_gundemi_1080p.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"),
                    "-i", wavp, "-vf", f"fps={FPS},format=yuv420p", "-af", "highpass=f=80,acompressor,loudnorm=I=-16:TP=-1.5",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", mp4], check=True)
    shutil.rmtree(tmp)
    print("bitti:", mp4, f"{t:.1f} sn")

if __name__ == "__main__":
    main()
