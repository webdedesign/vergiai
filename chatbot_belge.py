import warnings
warnings.filterwarnings("ignore")
import lancedb
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

client = Anthropic()
db = lancedb.connect("./veritabani")
gecmis = []


def tablo_var_mi():
    """vergi_belgeleri tablosunun var olup olmadigini kontrol eder."""
    try:
        sonuc = db.list_tables()
        # Sonuc bir obje olabilir, string'e cevirip icinde ariyoruz
        return "vergi_belgeleri" in str(sonuc)
    except Exception:
        return False


def belge_say():
    try:
        if not tablo_var_mi():
            return 0
        tablo = db.open_table("vergi_belgeleri")
        df = tablo.to_pandas()
        return len(df)
    except Exception as e:
        print(f"Hata: {e}")
        return 0


def ara(soru, n=5):
    try:
        if not tablo_var_mi():
            return [], []
        tablo = db.open_table("vergi_belgeleri")
        df = tablo.to_pandas()
        if df.empty:
            return [], []

        kelimeler = [k.lower() for k in soru.split() if len(k) > 2]

        def puan(metin):
            m = metin.lower()
            return sum(1 for k in kelimeler if k in m)

        df["puan"] = df["metin"].apply(puan)
        df = df[df["puan"] > 0].sort_values("puan", ascending=False).head(n)

        if df.empty:
            return [], []

        parcalar = df["metin"].tolist()
        kaynaklar = [{"belge": r["belge"], "sayfa": r["sayfa"]} for _, r in df.iterrows()]
        return parcalar, kaynaklar
    except Exception as e:
        print(f"Arama hatasi: {e}")
        return [], []


def sor(soru):
    parcalar, kaynaklar = ara(soru)

    if parcalar:
        icerik = ""
        for p, k in zip(parcalar, kaynaklar):
            icerik += f"\n[{k['belge']} - Sayfa {k['sayfa']}]\n{p}\n"
        sistem = f"""Sen vergiai.com'un Turk vergi mevzuati uzman asistanisin.
Asagidaki belge bolumlerini kullanarak soruyu Turkce yanitla.
Hangi belgeden ve kacinci sayfadan aldigini belirt.

BELGELER:
{icerik}"""
    else:
        sistem = "Sen vergiai.com'un Turk vergi mevzuati uzman asistanisin. Sorulari Turkce yanitla."

    gecmis.append({"role": "user", "content": soru})
    yanit = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=2048,
        system=sistem,
        messages=gecmis
    )
    cevap = yanit.content[0].text
    gecmis.append({"role": "assistant", "content": cevap})
    return cevap, kaynaklar


def main():
    print("=" * 55)
    print("  VERGIAI.COM - Vergi Mevzuati Asistani")
    print("=" * 55)

    n = belge_say()
    if n > 0:
        print(f"  {n} belge parcasi yuklu ve hazir.")
    else:
        print("  Belge bulunamadi! Once belge_yukle.py calistirin.")
    print("  Cikmak icin: q")
    print("=" * 55)
    print()

    while True:
        try:
            soru = input("Siz: ").strip()
        except KeyboardInterrupt:
            print("\nGorusuruz!")
            break

        if not soru:
            continue
        if soru.lower() in ["q", "quit", "exit", "cikis"]:
            print("Gorusuruz!")
            break

        cevap, kaynaklar = sor(soru)
        print(f"\nVergiai:\n{cevap}")

        if kaynaklar:
            gosterilen = set()
            satirlar = []
            for k in kaynaklar:
                anahtar = f"{k['belge']} (Sayfa {k['sayfa']})"
                if anahtar not in gosterilen:
                    satirlar.append(anahtar)
                    gosterilen.add(anahtar)
            print("\nKaynak:", " | ".join(satirlar))
        print()


if __name__ == "__main__":
    main()
