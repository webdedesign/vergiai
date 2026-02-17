import os
import fitz
import lancedb
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()

VERITABANI_YOLU = "./veritabani"
TABLO_ADI = "vergi_belgeleri"
BELGELER_KLASORU = "./belgeler"

db = lancedb.connect(VERITABANI_YOLU)


def tablo_var_mi():
    try:
        sonuc = db.list_tables()
        return TABLO_ADI in str(sonuc)
    except Exception:
        return False


def pdf_oku(dosya_yolu):
    doc = fitz.open(dosya_yolu)
    sayfalar = []
    for i in range(len(doc)):
        metin = doc[i].get_text()
        if metin.strip():
            sayfalar.append({"sayfa_no": i + 1, "metin": metin})
    return sayfalar


def metni_parcala(sayfalar, boyut=400, kesisme=40):
    parcalar = []
    for sayfa in sayfalar:
        kelimeler = sayfa["metin"].split()
        i = 0
        while i < len(kelimeler):
            metin = " ".join(kelimeler[i:i+boyut])
            if metin.strip():
                parcalar.append({"metin": metin, "sayfa": sayfa["sayfa_no"]})
            i += boyut - kesisme
    return parcalar


def yukle(belge_adi, parcalar):
    veriler = [
        {"belge": belge_adi, "sayfa": p["sayfa"], "metin": p["metin"]}
        for p in parcalar
    ]

    if tablo_var_mi():
        tablo = db.open_table(TABLO_ADI)
        mevcut = tablo.to_pandas()["belge"].unique().tolist()
        if belge_adi in mevcut:
            print(f"  '{belge_adi}' zaten yuklu, atlaniyor.")
            return 0
        tablo.add(veriler)
    else:
        db.create_table(TABLO_ADI, data=veriler)

    return len(veriler)


def main():
    if not os.path.exists(BELGELER_KLASORU):
        print("HATA: 'belgeler' klasoru bulunamadi!")
        return

    pdf_listesi = [f for f in os.listdir(BELGELER_KLASORU) if f.lower().endswith(".pdf")]
    if not pdf_listesi:
        print("HATA: 'belgeler' klasorunde hic PDF yok!")
        return

    print(f"{len(pdf_listesi)} PDF bulundu.\n")
    toplam = 0

    for pdf in pdf_listesi:
        yol = os.path.join(BELGELER_KLASORU, pdf)
        ad = os.path.splitext(pdf)[0]
        print(f"Isleniyor: {pdf}")
        sayfalar = pdf_oku(yol)
        parcalar = metni_parcala(sayfalar)
        n = yukle(ad, parcalar)
        toplam += n
        print(f"  {len(sayfalar)} sayfa, {len(parcalar)} parca -> {n} kaydedildi.\n")

    tablo = db.open_table(TABLO_ADI)
    genel_toplam = len(tablo.to_pandas())
    print(f"Bitti! Veritabaninda toplam {genel_toplam} parca var.")


if __name__ == "__main__":
    main()
