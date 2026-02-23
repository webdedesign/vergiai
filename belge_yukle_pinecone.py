import os
import voyageai
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API clients
voyage_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

# Pinecone index - voyage-multilingual-2 uses 1024 dimensions
INDEX_NAME = "vergiai"
DIMENSION = 1024

# Delete old index and create new one with correct dimensions
existing = [idx.name for idx in pc.list_indexes()]
if INDEX_NAME in existing:
    print(f"Eski index siliniyor: {INDEX_NAME}")
    pc.delete_index(INDEX_NAME)

print(f"Yeni index oluşturuluyor: {INDEX_NAME} (dim={DIMENSION})")
pc.create_index(
    name=INDEX_NAME,
    dimension=DIMENSION,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)
index = pc.Index(INDEX_NAME)

def pdf_oku(pdf_yolu):
    """PDF dosyasını oku ve metni çıkar"""
    try:
        import pymupdf
        doc = pymupdf.open(pdf_yolu)
        parcalar = []
        for sayfa_no, sayfa in enumerate(doc):
            metin = sayfa.get_text()
            if metin.strip():
                # Her sayfayı chunk'lara böl (max 500 karakter)
                kelimeler = metin.split()
                chunk = []
                for kelime in kelimeler:
                    chunk.append(kelime)
                    if len(" ".join(chunk)) > 500:
                        parcalar.append({
                            "metin": " ".join(chunk),
                            "sayfa": sayfa_no + 1,
                            "belge": Path(pdf_yolu).stem
                        })
                        chunk = []
                if chunk:
                    parcalar.append({
                        "metin": " ".join(chunk),
                        "sayfa": sayfa_no + 1,
                        "belge": Path(pdf_yolu).stem
                    })
        return parcalar
    except Exception as e:
        print(f"Hata: {pdf_yolu} - {e}")
        return []

def voyage_embed(metinler):
    """Voyage AI ile embedding oluştur"""
    result = voyage_client.embed(
        metinler,
        model="voyage-multilingual-2",
        input_type="document"
    )
    return result.embeddings

# PDF'leri yükle
belgeler_klasoru = Path("belgeler")
pdf_dosyalari = list(belgeler_klasoru.glob("*.pdf"))
print(f"{len(pdf_dosyalari)} PDF bulundu: {[p.name for p in pdf_dosyalari]}")

tum_parcalar = []
for pdf in pdf_dosyalari:
    print(f"Okunuyor: {pdf.name}")
    parcalar = pdf_oku(pdf)
    tum_parcalar.extend(parcalar)
    print(f"  → {len(parcalar)} parça")

print(f"\nToplam {len(tum_parcalar)} parça, Pinecone'a yükleniyor...")

# Batch olarak yükle (Voyage max 128 metin/istek)
BATCH = 32
yuklenen = 0
for i in range(0, len(tum_parcalar), BATCH):
    batch = tum_parcalar[i:i+BATCH]
    metinler = [p["metin"] for p in batch]
    
    import time
    time.sleep(22)  # 3 RPM limit icin bekle (60/3 = 20sn, +2 guvenlik)
    try:
        embeddings = voyage_embed(metinler)
        vectors = []
        for j, (parca, emb) in enumerate(zip(batch, embeddings)):
            vectors.append({
                "id": f"doc_{i+j}",
                "values": emb,
                "metadata": {
                    "metin": parca["metin"],
                    "belge": parca["belge"],
                    "sayfa": parca["sayfa"]
                }
            })
        index.upsert(vectors=vectors)
        yuklenen += len(vectors)
        print(f"  {yuklenen}/{len(tum_parcalar)} yüklendi")
    except Exception as e:
        print(f"Hata batch {i}: {e}")

print(f"\n✅ Tamamlandı! {yuklenen} vektör Pinecone'a yüklendi.")
stats = index.describe_index_stats()
print(f"Pinecone'daki toplam vektör: {stats['total_vector_count']}")
