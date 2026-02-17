# vergiai.com — Kurulum Rehberi

## Dosyalar Ne İşe Yarıyor?

| Dosya | Açıklama |
|-------|----------|
| `test.py` | API bağlantısını test eder — ilk çalıştırılacak dosya |
| `chatbot.py` | Terminalde çalışan vergi chatbotu |
| `.env` | API anahtarını güvenli saklar (sen oluşturuyorsun) |

---

## Kurulum Adımları

### 1. .env dosyasını oluştur
vergiai klasörünün içinde `.env` adlı bir dosya oluştur ve şunu yaz:
```
ANTHROPIC_API_KEY=sk-ant-buraya-kendi-anahtarını-yaz
```

### 2. Kütüphaneleri kur (bir kez yapılır)
```
pip install anthropic python-dotenv
```

### 3. Önce bağlantıyı test et
```
python test.py
```
Claude'dan Türkçe bir cevap görüyorsan her şey çalışıyor!

### 4. Chatbotu çalıştır
```
python chatbot.py
```
Vergi soruları sorabilirsin. Çıkmak için `q` yaz.

---

## Sık Karşılaşılan Hatalar

**"API key not found" hatası:**
→ .env dosyasının vergiai klasörünün içinde olduğundan emin ol

**"Module not found" hatası:**
→ `pip install anthropic python-dotenv` komutunu tekrar çalıştır

**"(venv) görünmüyor" sorunu:**
→ `venv\Scripts\activate` komutunu tekrar çalıştır
