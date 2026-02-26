import os
import voyageai
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

voyage_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

INDEX_NAME = "vergiai"
DIMENSION = 1024

# Index'i sil ve yeniden oluştur
existing = [idx.name for idx in pc.list_indexes()]
if INDEX_NAME in existing:
    print(f"Eski index siliniyor...")
    pc.delete_index(INDEX_NAME)
    import time
    time.sleep(10)

print(f"Yeni index oluşturuluyor...")
pc.create_index(name=INDEX_NAME, dimension=DIMENSION, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
import time
time.sleep(5)
index = pc.Index(INDEX_NAME)

def pdf_oku(pdf_yolu):
    try:
        import pymupdf
        doc = pymupdf.open(pdf_yolu)
        parcalar = []
        for sayfa_no, sayfa in enumerate(doc):
            metin = sayfa.get_text()
            if metin.strip():
                kelimeler = metin.split()
                chunk = []
                for kelime in kelimeler:
                    chunk.append(kelime)
                    if len(" ".join(chunk)) > 500:
                        parcalar.append({"metin": " ".join(chunk), "sayfa": sayfa_no + 1, "belge": Path(pdf_yolu).stem})
                        chunk = []
                if chunk:
                    parcalar.append({"metin": " ".join(chunk), "sayfa": sayfa_no + 1, "belge": Path(pdf_yolu).stem})
        return parcalar
    except Exception as e:
        print(f"Hata: {pdf_yolu} - {e}")
        return []

belgeler_klasoru = Path("belgeler")
pdf_dosyalari = sorted(belgeler_klasoru.glob("*.pdf"))
print(f"{len(pdf_dosyalari)} PDF bulundu")

tum_parcalar = []
for pdf in pdf_dosyalari:
    print(f"Okunuyor: {pdf.name}")
    parcalar = pdf_oku(pdf)
    tum_parcalar.extend(parcalar)
    print(f"  → {len(parcalar)} parça")

print(f"\nToplam {len(tum_parcalar)} parça yükleniyor...")

BATCH = 64
yuklenen = 0
for i in range(0, len(tum_parcalar), BATCH):
    batch = tum_parcalar[i:i+BATCH]
    metinler = [p["metin"] for p in batch]
    try:
        result = voyage_client.embed(metinler, model="voyage-multilingual-2", input_type="document")
        vectors = [{"id": f"doc_{i+j}", "values": emb, "metadata": {"metin": parca["metin"], "belge": parca["belge"], "sayfa": parca["sayfa"]}} for j, (parca, emb) in enumerate(zip(batch, result.embeddings))]
        index.upsert(vectors=vectors)
        yuklenen += len(vectors)
        print(f"  {yuklenen}/{len(tum_parcalar)} yüklendi")
    except Exception as e:
        print(f"Hata batch {i}: {e}")

print(f"\n✅ Tamamlandı! {yuklenen} vektör yüklendi.")
print(f"Pinecone toplam: {index.describe_index_stats()['total_vector_count']}")
