import warnings
warnings.filterwarnings("ignore")
import streamlit as st
from anthropic import Anthropic
import re

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except:
    PINECONE_AVAILABLE = False

st.set_page_config(page_title="vergiAI", page_icon="⚖", layout="centered", initial_sidebar_state="collapsed")

def md_to_html(text):
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'^---+$', r'<hr>', text, flags=re.MULTILINE)
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', text, flags=re.MULTILINE)
    text = re.sub(r'(<li>.*?</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', text, flags=re.DOTALL)
    paragraphs = text.split('\n\n')
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p: continue
        if p.startswith('<h') or p.startswith('<ul') or p.startswith('<hr'):
            result.append(p)
        else:
            p = p.replace('\n', ' ')
            result.append(f'<p>{p}</p>')
    return '\n'.join(result)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
*,*::before,*::after{box-sizing:border-box}html,body,.stApp{background:#050505 !important;font-family:'Sora',sans-serif !important}.main .block-container{padding:2rem 1.5rem 4rem !important;max-width:780px !important}header[data-testid="stHeader"],footer,section[data-testid="stSidebar"]{display:none !important}.stApp::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(240,168,32,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(240,168,32,0.04) 1px,transparent 1px);background-size:56px 56px;pointer-events:none;z-index:0}.stApp::after{content:'';position:fixed;width:600px;height:600px;background:radial-gradient(circle,rgba(240,168,32,0.08) 0%,transparent 70%);top:-200px;right:-100px;border-radius:50%;filter:blur(100px);pointer-events:none;z-index:0}.va-topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:0;position:relative;z-index:10}.va-logo{font-weight:800;font-size:20px;letter-spacing:-0.5px;color:#f5f0e8}.va-logo-ai{color:#ffc040;text-shadow:0 0 20px rgba(255,192,64,0.4)}.va-badge{display:inline-flex;align-items:center;gap:7px;background:rgba(240,168,32,0.08);border:1px solid rgba(240,168,32,0.2);border-radius:100px;padding:5px 14px;font-family:'DM Mono',monospace;font-size:11px;color:#f0a820;letter-spacing:1px}.va-pdot{display:inline-block;width:6px;height:6px;background:#ffc040;border-radius:50%;box-shadow:0 0 8px #ffc040;animation:blink 2s ease-in-out infinite}@keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}.va-hero{text-align:center;padding:48px 0 40px;position:relative;z-index:10}.va-eyebrow{font-family:'DM Mono',monospace;font-size:11px;letter-spacing:4px;color:#f0a820;text-transform:uppercase;margin-bottom:16px;opacity:0.9}.va-title{font-weight:800;font-size:clamp(52px,10vw,88px);line-height:0.92;letter-spacing:-4px;margin-bottom:14px}.va-title-vergi{background:linear-gradient(135deg,#f5f0e8 0%,#c8b898 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}.va-title-ai{background:linear-gradient(135deg,#ffc040 0%,#e09010 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;filter:drop-shadow(0 0 30px rgba(255,192,64,0.3))}.va-sub{font-size:16px;font-weight:400;color:#707070;margin-bottom:24px}.va-chips{display:flex;justify-content:center;gap:10px;flex-wrap:wrap}.va-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:100px;padding:7px 16px;font-size:13px;font-weight:500;color:#606060}.stTextInput>div>div>input{background:#101010 !important;border:1.5px solid #282828 !important;border-radius:14px !important;color:#f0ebe0 !important;font-family:'Sora',sans-serif !important;font-size:16px !important;padding:16px 20px !important;caret-color:#ffc040 !important;box-shadow:0 4px 24px rgba(0,0,0,0.4) !important}.stTextInput>div>div>input:focus{border-color:rgba(240,168,32,0.6) !important;box-shadow:0 0 0 3px rgba(240,168,32,0.08) !important}.stTextInput>div>div>input::placeholder{color:#404040 !important}.stTextInput label{display:none !important}.stButton>button{background:linear-gradient(135deg,#ffc040,#e09010) !important;color:#000 !important;border:none !important;border-radius:14px !important;font-family:'Sora',sans-serif !important;font-size:16px !important;font-weight:700 !important;padding:16px 28px !important;width:100% !important;box-shadow:0 4px 20px rgba(240,168,32,0.3) !important}.stButton>button:hover{transform:translateY(-1px) !important;box-shadow:0 6px 28px rgba(240,168,32,0.45) !important}.va-msg-user{display:flex;justify-content:flex-end;margin:12px 0}.va-bubble-user{background:#141414;border:1px solid rgba(255,255,255,0.09);border-radius:16px 16px 4px 16px;padding:14px 20px;font-size:16px;color:#e8e0d0;max-width:75%;line-height:1.65}.va-msg-bot{display:flex;gap:14px;margin:14px 0;align-items:flex-start}.va-avatar{width:32px;height:32px;flex-shrink:0;background:linear-gradient(135deg,#141414,#1f1f1f);border:1px solid#282828;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:15px;margin-top:3px;box-shadow:0 0 16px rgba(240,168,32,0.1)}.va-bot-text{flex:1}.va-bot-text p{color:#d0c8b8;font-size:15px;line-height:1.85;margin-bottom:12px;text-align:justify;font-family:'Sora',sans-serif}.va-bot-text h1,.va-bot-text h2,.va-bot-text h3{color:#f0ebe0;font-weight:700;font-size:16px;margin:16px 0 8px;font-family:'Sora',sans-serif}.va-bot-text strong{color:#f0ebe0;font-weight:600}.va-bot-text em{color:#c8c0b0;font-style:italic}.va-bot-text ul{margin:8px 0 12px 20px}.va-bot-text li{color:#d0c8b8;font-size:15px;line-height:1.8;margin-bottom:5px;font-family:'Sora',sans-serif}.va-bot-text hr{border:none;border-top:1px solid #1e1e1e;margin:12px 0}.va-source{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px;padding-top:12px;border-top:1px solid #141414;align-items:center}.va-slabel{font-family:'DM Mono',monospace;font-size:10px;color:#303030;letter-spacing:2px;text-transform:uppercase}.va-schip{font-family:'DM Mono',monospace;font-size:11px;color:#f0a820;background:rgba(240,168,32,0.08);border:1px solid rgba(240,168,32,0.2);border-radius:6px;padding:3px 10px}.va-divider{border:none;border-top:1px solid #111;margin:16px 0}div[data-testid="column"] .stButton>button{background:transparent !important;color:#505050 !important;border:1px solid #1c1c1c !important;border-radius:100px !important;font-size:12px !important;font-weight:500 !important;padding:8px 14px !important;box-shadow:none !important;transform:none !important}div[data-testid="column"] .stButton>button:hover{border-color:rgba(240,168,32,0.4) !important;color:#f0a820 !important;background:rgba(240,168,32,0.05) !important;transform:none !important}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def baglanti():
    # Streamlit secrets kullan
    anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
    pinecone_key = st.secrets.get("PINECONE_API_KEY")
    
    client = Anthropic(api_key=anthropic_key)
    
    if not PINECONE_AVAILABLE or not pinecone_key:
        return None, client, 0
    
    try:
        pc = Pinecone(api_key=pinecone_key)
        index_name = "vergiai"
        if index_name not in [idx.name for idx in pc.list_indexes()]:
            pc.create_index(name=index_name, dimension=384, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        count = stats.get('total_vector_count', 0)
        return index, client, count
    except:
        return None, client, 0

index, client, belge_sayisi = baglanti()

def ara(soru, n=5):
    if not index or belge_sayisi == 0:
        return [], []
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        query_vec = model.encode(soru).tolist()
        results = index.query(vector=query_vec, top_k=n, include_metadata=True)
        parcalar, kaynaklar = [], []
        for match in results.matches:
            if match.score > 0.3:
                meta = match.metadata
                parcalar.append(meta.get('metin', ''))
                kaynaklar.append({'belge': meta.get('belge', ''), 'sayfa': meta.get('sayfa', 1)})
        return parcalar, kaynaklar
    except:
        return [], []

def cevap_al(soru, gecmis):
    parcalar, kaynaklar = ara(soru)
    if parcalar:
        icerik = "\n".join(f"[{k['belge']} - Sayfa {k['sayfa']}]\n{p}" for p, k in zip(parcalar, kaynaklar))
        sistem = f"Sen vergiai.com Turk vergi mevzuati uzman asistanisin. Su belge bolumlerini kullanarak soruyu Turkce yanitla, kaynagi belirt.\nBELGELER:\n{icerik}"
    else:
        sistem = "Sen vergiai.com Turk vergi mevzuati uzman asistanisin. Sorulari Turkce yanitla."
    msgs = gecmis + [{"role": "user", "content": soru}]
    tam_cevap = ""
    with client.messages.stream(model="claude-haiku-4-5-20251001", max_tokens=2048, system=sistem, messages=msgs) as stream:
        for text in stream.text_stream:
            tam_cevap += text
            yield tam_cevap, kaynaklar

for k, v in [("gecmis", []), ("mesajlar", []), ("ornek", "")]:
    if k not in st.session_state: st.session_state[k] = v

st.markdown(f'<div class="va-topbar"><div class="va-logo">vergi<span class="va-logo-ai">AI</span></div><div class="va-badge"><span class="va-pdot"></span>{belge_sayisi:,} BELGE</div></div>', unsafe_allow_html=True)

if not st.session_state.mesajlar:
    st.markdown('<div class="va-hero"><div class="va-eyebrow">Türk Vergi Mevzuatı · Yapay Zeka Asistanı</div><div class="va-title"><span class="va-title-vergi">vergi</span><span class="va-title-ai">AI</span></div><div class="va-sub">Vergi kanunlarını saniyeler içinde öğrenin — kaynakları ile birlikte.</div><div class="va-chips"><div class="va-chip">🔍 Anlık mevzuat araması</div><div class="va-chip">📋 Kaynak alıntısı</div><div class="va-chip">⚡ Claude AI destekli</div></div></div>', unsafe_allow_html=True)

if st.session_state.mesajlar:
    for m in st.session_state.mesajlar:
        if m["rol"] == "kullanici":
            st.markdown(f'<div class="va-msg-user"><div class="va-bubble-user">{m["icerik"]}</div></div>', unsafe_allow_html=True)
        else:
            html_icerik = md_to_html(m["icerik"])
            kaynak_html = ""
            if m.get("kaynak"):
                chips = "".join(f'<span class="va-schip">{k}</span>' for k in m["kaynak"].split(" · ") if k)
                kaynak_html = f'<div class="va-source"><span class="va-slabel">KAYNAK</span>{chips}</div>'
            st.markdown(f'<div class="va-msg-bot"><div class="va-avatar">⚖</div><div class="va-bot-text">{html_icerik}{kaynak_html}</div></div>', unsafe_allow_html=True)
    st.markdown('<hr class="va-divider">', unsafe_allow_html=True)

varsayilan = st.session_state.ornek
st.session_state.ornek = ""

with st.form("chat", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        soru = st.text_input("soru", value=varsayilan, placeholder="Vergi mevzuatı hakkında sorunuzu yazın...", label_visibility="collapsed")
    with col2:
        gonder = st.form_submit_button("↑ Gönder")

if gonder and soru.strip():
    st.session_state.mesajlar.append({"rol": "kullanici", "icerik": soru})
    stream_kutu = st.empty()
    son_cevap = ""
    son_kaynaklar = []
    for anlik, kaynaklar in cevap_al(soru, st.session_state.gecmis):
        son_cevap = anlik
        son_kaynaklar = kaynaklar
        html_anlik = md_to_html(son_cevap)
        stream_kutu.markdown(f'<div class="va-msg-bot"><div class="va-avatar">⚖</div><div class="va-bot-text">{html_anlik}</div></div>', unsafe_allow_html=True)
    st.session_state.gecmis += [{"role":"user","content":soru}, {"role":"assistant","content":son_cevap}]
    kaynak_str = " · ".join(set(f"{k['belge']} S.{k['sayfa']}" for k in son_kaynaklar)) if son_kaynaklar else ""
    st.session_state.mesajlar.append({"rol": "bot", "icerik": son_cevap, "kaynak": kaynak_str})
    st.rerun()

if not st.session_state.mesajlar:
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    ornekler = ["KDV oranları nelerdir?", "İhracat istisnası nedir?", "Gelir vergisi dilimleri?", "Kurumlar vergisi oranı?"]
    for col, ornek in zip([c1,c2,c3,c4], ornekler):
        with col:
            if st.button(ornek, key=ornek):
                st.session_state.ornek = ornek
                st.rerun()

if st.session_state.mesajlar:
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    _, c = st.columns([5,1])
    with c:
        if st.button("✕ Sil", key="sil"):
            st.session_state.gecmis = []
            st.session_state.mesajlar = []
            st.rerun()
