import os
import fitz
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Pinecone baglantisi
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "vergiai"

# Index olustur
if index_name not in [idx.name for idx in pc.list_indexes()]:
    print(f"'{index_name}' index'i olusturuluyor...")
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("Index olusturuldu!")

index = pc.Index(index_name)

# Embedding modeli
print("Embedding modeli yukleniyor...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# PDF'leri yukle
pdf_klasoru = "./belgeler"
pdfler = [f for f in os.listdir(pdf_klasoru) if f.endswith('.pdf')]

print(f"\n{len(pdfler)} PDF bulundu, yukleniyor...\n")

toplam = 0
for pdf_adi in pdfler:
    print(f"► {pdf_adi} isleniyor...")
    yol = os.path.join(pdf_klasoru, pdf_adi)
    doc = fitz.open(yol)
    
    vektorler = []
    for sayfa_no in range(len(doc)):
        metin = doc[sayfa_no].get_text()
        if not metin.strip():
            continue
        
        # 400 kelimelik parcalar
        kelimeler = metin.split()
        for i in range(0, len(kelimeler), 360):
            parca = " ".join(kelimeler[i:i+400])
            if not parca.strip():
                continue
            
            # Embedding
            vektor = model.encode(parca).tolist()
            
            # ID olustur
            vektor_id = f"{pdf_adi}_{sayfa_no}_{i}"
            
            vektorler.append({
                'id': vektor_id,
                'values': vektor,
                'metadata': {
                    'belge': os.path.splitext(pdf_adi)[0],
                    'sayfa': sayfa_no + 1,
                    'metin': parca
                }
            })
    
    # Pinecone'a yukle (100'er grup halinde)
    for j in range(0, len(vektorler), 100):
        batch = vektorler[j:j+100]
        index.upsert(vectors=batch)
    
    print(f"  ✓ {len(vektorler)} parca yuklendi")
    toplam += len(vektorler)

print(f"\n✓ TAMAM! Toplam {toplam} belge parcasi Pinecone'a yuklendi.")
print(f"\nIndex durumu:")
print(index.describe_index_stats())
