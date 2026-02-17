from anthropic import Anthropic
from dotenv import load_dotenv

# .env dosyasındaki API anahtarını yükle
load_dotenv()

# Claude istemcisini oluştur
client = Anthropic()

# Sohbet geçmişini tutan liste
sohbet_gecmisi = []

# Sistem mesajı — botun kişiliğini ve görevini tanımlar
SISTEM_MESAJI = """Sen vergiai.com'un yapay zeka asistanısın. 
Türk vergi mevzuatı konusunda uzman bir asistansın.
Kullanıcılara Türk vergi kanunları, KDV, gelir vergisi, kurumlar vergisi, 
beyanname süreçleri ve diğer vergi konularında yardımcı oluyorsun.
Her zaman Türkçe cevap ver. Cevaplarının sonunda ilgili kanun maddesini belirt.
Yasal uyarı: Verdiğin bilgiler genel bilgi amaçlıdır, kesin hukuki görüş için 
bir vergi uzmanına danışılması önerilir."""

def soru_sor(soru):
    """Kullanıcının sorusunu Claude'a gönderir ve cevap alır."""
    
    # Soruyu geçmişe ekle
    sohbet_gecmisi.append({
        "role": "user",
        "content": soru
    })
    
    # Claude'a gönder
    cevap = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=2048,
        system=SISTEM_MESAJI,
        messages=sohbet_gecmisi
    )
    
    # Cevabı al
    asistan_cevabi = cevap.content[0].text
    
    # Cevabı da geçmişe ekle
    sohbet_gecmisi.append({
        "role": "assistant", 
        "content": asistan_cevabi
    })
    
    return asistan_cevabi


def main():
    """Ana chatbot döngüsü."""
    print("=" * 50)
    print("   VERGİAI.COM — Vergi Asistanı")
    print("=" * 50)
    print("Türk vergi mevzuatı hakkında soru sorabilirsiniz.")
    print("Çıkmak için 'q' veya 'çıkış' yazın.")
    print("=" * 50)
    print()
    
    while True:
        # Kullanıcıdan soru al
        soru = input("Siz: ").strip()
        
        # Boş girişi atla
        if not soru:
            continue
            
        # Çıkış kontrolü
        if soru.lower() in ["q", "çıkış", "exit", "quit"]:
            print("Görüşmek üzere!")
            break
        
        # Cevap al ve göster
        print("\nVergiai: ", end="")
        cevap = soru_sor(soru)
        print(cevap)
        print()


if __name__ == "__main__":
    main()
