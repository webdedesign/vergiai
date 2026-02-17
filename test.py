from anthropic import Anthropic
from dotenv import load_dotenv

# .env dosyasındaki API anahtarını yükle
load_dotenv()

# Claude istemcisini oluştur
client = Anthropic()

print("Claude'a bağlanılıyor...")
print("-" * 40)

# İlk mesajı gönder
mesaj = client.messages.create(
    model="claude-opus-4-5-20251101",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Merhaba! Türk vergi mevzuatı konusunda yardımcı olabilir misin? Kendini kısaca tanıt."
        }
    ]
)

# Cevabı ekrana yaz
print(mesaj.content[0].text)
print("-" * 40)
print("Bağlantı başarılı!")
