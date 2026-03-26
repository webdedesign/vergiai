import warnings
warnings.filterwarnings("ignore")
import os
import streamlit as st
from anthropic import Anthropic
import re

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except:
    PINECONE_AVAILABLE = False

try:
    import voyageai
    VOYAGE_AVAILABLE = True
except:
    VOYAGE_AVAILABLE = False

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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*,*::before,*::after{box-sizing:border-box}

html,body,.stApp{
  background:#0a0a0f !important;
  font-family:'Plus Jakarta Sans',sans-serif !important;
}

.main .block-container{
  padding:2rem 1.5rem 5rem !important;
  max-width:760px !important;
}

header[data-testid="stHeader"],footer,section[data-testid="stSidebar"]{display:none !important}

/* Ambient glow blobs */
.stApp::before{
  content:'';position:fixed;width:500px;height:500px;
  background:radial-gradient(circle,rgba(138,43,226,0.12) 0%,transparent 70%);
  top:-150px;right:-100px;border-radius:50%;filter:blur(80px);pointer-events:none;z-index:0;
}
.stApp::after{
  content:'';position:fixed;width:400px;height:400px;
  background:radial-gradient(circle,rgba(255,165,0,0.07) 0%,transparent 70%);
  bottom:-100px;left:-100px;border-radius:50%;filter:blur(80px);pointer-events:none;z-index:0;
}

/* Logo button */
.va-logo-btn button{
  background:transparent !important;border:none !important;padding:0 !important;
  box-shadow:none !important;font-weight:800 !important;font-size:18px !important;
  letter-spacing:-0.5px !important;color:#f0ebe0 !important;
  font-family:'Plus Jakarta Sans',sans-serif !important;width:auto !important;
  text-transform:none !important;
}
.va-logo-btn button:hover{
  transform:none !important;background:transparent !important;
  box-shadow:none !important;color:#ffc040 !important;
}
.va-logo-ai-span{
  background:linear-gradient(135deg,#ffc040,#ff8c00);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}

/* Badge */
.va-badge{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(255,255,255,0.04);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:100px;padding:5px 14px;
  font-family:'JetBrains Mono',monospace;font-size:10px;
  color:#888;letter-spacing:1px;
}
.va-pdot{
  display:inline-block;width:5px;height:5px;
  background:#7c3aed;border-radius:50%;
  box-shadow:0 0 8px #7c3aed;
  animation:blink 2s ease-in-out infinite;
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}

/* Hero */
.va-hero{text-align:center;padding:52px 0 44px;position:relative;z-index:10}
.va-eyebrow{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:4px;color:#7c3aed;text-transform:uppercase;
  margin-bottom:20px;opacity:0.9;
}
.va-title{
  font-weight:800;font-size:clamp(48px,9vw,82px);
  line-height:0.95;letter-spacing:-3px;margin-bottom:16px;
}
.va-title-vergi{
  background:linear-gradient(135deg,#f0ebe0 0%,#a89880 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.va-title-ai{
  background:linear-gradient(135deg,#a855f7 0%,#ec4899 60%,#ffc040 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  filter:drop-shadow(0 0 40px rgba(168,85,247,0.4));
}
.va-sub{font-size:15px;font-weight:400;color:#555;margin-bottom:28px;line-height:1.6}
.va-chips{display:flex;justify-content:center;gap:8px;flex-wrap:wrap}
.va-chip{
  display:inline-flex;align-items:center;gap:6px;
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.06);
  border-radius:100px;padding:6px 14px;
  font-size:12px;font-weight:500;color:#555;
}

/* Input */
.stTextInput>div>div>input{
  background:rgba(255,255,255,0.04) !important;
  border:1.5px solid rgba(255,255,255,0.08) !important;
  border-radius:16px !important;color:#f0ebe0 !important;
  font-family:'Plus Jakarta Sans',sans-serif !important;
  font-size:15px !important;padding:16px 20px !important;
  caret-color:#a855f7 !important;
  box-shadow:none !important;
  transition:border-color 0.2s,box-shadow 0.2s;
}
.stTextInput>div>div>input:focus{
  border-color:rgba(168,85,247,0.5) !important;
  box-shadow:0 0 0 3px rgba(168,85,247,0.08) !important;
  background:rgba(255,255,255,0.06) !important;
}
.stTextInput>div>div>input::placeholder{color:#333 !important}
.stTextInput label{display:none !important}

/* Send button */
.stButton>button{
  background:linear-gradient(135deg,#7c3aed,#a855f7) !important;
  color:#fff !important;border:none !important;border-radius:14px !important;
  font-family:'Plus Jakarta Sans',sans-serif !important;
  font-size:15px !important;font-weight:700 !important;
  padding:16px 24px !important;width:100% !important;
  box-shadow:0 4px 20px rgba(124,58,237,0.35) !important;
  transition:all 0.2s !important;
}
.stButton>button:hover{
  transform:translateY(-1px) !important;
  box-shadow:0 6px 28px rgba(124,58,237,0.5) !important;
}

/* User message */
.va-msg-user{display:flex;justify-content:flex-end;margin:10px 0}
.va-bubble-user{
  background:linear-gradient(135deg,#7c3aed,#a855f7);
  border-radius:18px 18px 4px 18px;
  padding:14px 18px;font-size:14px;color:#fff;
  max-width:72%;line-height:1.65;
  box-shadow:0 4px 20px rgba(124,58,237,0.3);
}

/* Bot message */
.va-msg-bot{display:flex;gap:12px;margin:12px 0;align-items:flex-start}
.va-avatar{
  width:30px;height:30px;flex-shrink:0;
  background:linear-gradient(135deg,#1a1a2e,#16213e);
  border:1px solid rgba(168,85,247,0.2);
  border-radius:10px;display:flex;align-items:center;
  justify-content:center;font-size:14px;margin-top:2px;
  box-shadow:0 0 16px rgba(168,85,247,0.15);
}
.va-bot-card{
  flex:1;
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.07);
  border-radius:4px 18px 18px 18px;
  padding:16px 18px;
}
.va-bot-card p{color:#e0dbd0;font-size:14px;line-height:1.85;margin-bottom:10px;text-align:justify;font-family:'Plus Jakarta Sans',sans-serif}
.va-bot-card h1,.va-bot-card h2,.va-bot-card h3{color:#f0ebe0;font-weight:700;font-size:15px;margin:14px 0 8px;font-family:'Plus Jakarta Sans',sans-serif}
.va-bot-card strong{color:#f0ebe0;font-weight:600}
.va-bot-card em{color:#e0dbd0;font-style:italic}
.va-bot-card ul{margin:6px 0 10px 18px}
.va-bot-card li{color:#e0dbd0;font-size:14px;line-height:1.8;margin-bottom:4px;font-family:'Plus Jakarta Sans',sans-serif}
.va-bot-card hr{border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0}

/* Source chips */
.va-source{
  display:flex;flex-wrap:wrap;gap:5px;
  margin-top:12px;padding-top:10px;
  border-top:1px solid rgba(255,255,255,0.05);
  align-items:center;
}
.va-slabel{
  font-family:'JetBrains Mono',monospace;font-size:9px;
  color:#333;letter-spacing:2px;text-transform:uppercase;
}
.va-schip{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  color:#a855f7;background:rgba(168,85,247,0.08);
  border:1px solid rgba(168,85,247,0.2);
  border-radius:6px;padding:2px 8px;
}

.va-divider{border:none;border-top:1px solid rgba(255,255,255,0.05);margin:14px 0}

/* Column buttons (ana sayfa) */
div[data-testid="column"] .stButton>button{
  background:transparent !important;color:#444 !important;
  border:1px solid rgba(255,255,255,0.06) !important;
  border-radius:100px !important;font-size:12px !important;
  font-weight:500 !important;padding:7px 14px !important;
  box-shadow:none !important;transform:none !important;
}
div[data-testid="column"] .stButton>button:hover{
  border-color:rgba(168,85,247,0.4) !important;
  color:#a855f7 !important;
  background:rgba(168,85,247,0.05) !important;
  transform:none !important;
}

  95%{transform:scaleY(0.1)}
}

/* Bot character */
.va-bot-avatar{width:48px;flex-shrink:0;display:flex;align-items:flex-start;padding-top:2px;overflow:visible}
.va-bot-char{overflow:visible;animation:va-float 3s ease-in-out infinite}
@keyframes va-float{0%,100%{transform:translateY(0px)}50%{transform:translateY(-4px)}}
.va-eye-anim{animation:va-blink 4s ease-in-out infinite}
.va-eye-anim2{animation:va-blink 4s ease-in-out infinite 0.08s}
@keyframes va-blink{0%,88%,100%{transform:scaleY(1)}93%{transform:scaleY(0.08)}}

</style>
""", unsafe_allow_html=True)

def baglanti():
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    pinecone_key = os.environ.get("PINECONE_API_KEY")
    voyage_key = os.environ.get("VOYAGE_API_KEY")
    client = Anthropic(api_key=anthropic_key)
    voyage = voyageai.Client(api_key=voyage_key) if VOYAGE_AVAILABLE and voyage_key else None
    if not PINECONE_AVAILABLE or not pinecone_key:
        return None, client, voyage
    try:
        pc = Pinecone(api_key=pinecone_key)
        index_name = "vergiai"
        if index_name not in [idx.name for idx in pc.list_indexes()]:
            pc.create_index(name=index_name, dimension=1024, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
        index = pc.Index(index_name)
        return index, client, voyage
    except:
        return None, client, voyage

index, client, voyage = baglanti()

try:
    belge_sayisi = index.describe_index_stats().get('total_vector_count', 0) if index else 0
except:
    belge_sayisi = 0

def ara(soru, n=5):
    if not index or not voyage or belge_sayisi == 0:
        return [], []
    try:
        result = voyage.embed([soru], model="voyage-3", input_type="query")
        query_vec = result.embeddings[0]
        results = index.query(vector=query_vec, top_k=n, include_metadata=True)
        parcalar, kaynaklar = [], []
        for match in results.matches:
            if match.score > 0.3:
                meta = match.metadata
                parcalar.append(meta.get('metin', ''))
                kaynaklar.append({'belge': meta.get('kaynak', meta.get('belge', '')), 'sayfa': meta.get('sayfa', 1)})
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

for k, v in [("gecmis", []), ("mesajlar", [])]:
    if k not in st.session_state: st.session_state[k] = v

# Topbar
col_logo, col_badge = st.columns([4, 1])
with col_logo:
    st.markdown('<div class="va-logo-btn">', unsafe_allow_html=True)
    if st.button("vergiAI", key="logo"):
        st.session_state.gecmis = []
        st.session_state.mesajlar = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with col_badge:
    st.markdown(f'<div style="display:flex;justify-content:flex-end;padding-top:4px"><div class="va-badge"><span class="va-pdot"></span>{belge_sayisi:,} KAYIT</div></div>', unsafe_allow_html=True)

# Hero
if not st.session_state.mesajlar:
    st.markdown(f'''
    <div class="va-hero">
      <div class="va-eyebrow">Turk Vergi Mevzuati &middot; Yapay Zeka</div>
      <div class="va-title">
        <span class="va-title-vergi">vergi</span><span class="va-title-ai">AI</span>
      </div>
      <div class="va-sub">Vergi sorularinizi saniyelerde yanitliyoruz &mdash; kaynakli, guncel, guvenilir.</div>
      <div class="va-chips">
        <div class="va-chip">⚡ Anlik mevzuat aramasi</div>
        <div class="va-chip">📋 Kaynak alintisi</div>
        <div class="va-chip">🔒 {belge_sayisi:,} belge parcasi</div>
      </div>
    </div>
    ''', unsafe_allow_html=True)

# Messages
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
            st.markdown(f'<div class="va-msg-bot"><div class="va-bot-avatar"><svg class="va-bot-char" width="44" height="52" viewBox="0 0 44 52" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="bg" cx="50%" cy="40%" r="60%"><stop offset="0%" stop-color="#c084fc"/><stop offset="100%" stop-color="#7c3aed"/></radialGradient><radialGradient id="eye-bg" cx="35%" cy="30%" r="70%"><stop offset="0%" stop-color="#1a0a2e"/><stop offset="100%" stop-color="#0a0a0f"/></radialGradient></defs><!-- Body --><ellipse cx="22" cy="20" rx="20" ry="19" fill="url(#bg)" filter="drop-shadow(0 4px 8px rgba(124,58,237,0.6))"/><!-- Tail --><polygon points="14,36 22,46 26,36" fill="#7c3aed"/><!-- Left eye --><g class="va-eye-anim" style="transform-origin:13px 19px"><ellipse cx="13" cy="19" rx="6" ry="6.5" fill="url(#eye-bg)"/><circle cx="11" cy="17" r="2" fill="rgba(255,255,255,0.85)"/></g><!-- Right eye --><g class="va-eye-anim2" style="transform-origin:31px 19px"><ellipse cx="31" cy="19" rx="6" ry="6.5" fill="url(#eye-bg)"/><circle cx="29" cy="17" r="2" fill="rgba(255,255,255,0.85)"/></g><!-- Shine --><ellipse cx="26" cy="8" rx="7" ry="3.5" fill="rgba(255,255,255,0.15)" transform="rotate(-20,26,8)"/></svg></div><div class="va-bot-card">{html_icerik}{kaynak_html}</div></div>', unsafe_allow_html=True)
    st.markdown('<hr class="va-divider">', unsafe_allow_html=True)

# Input form
with st.form("chat", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        soru = st.text_input("soru", value="", placeholder="Vergi mevzuati hakkinda sorunuzu yazin...", label_visibility="collapsed")
    with col2:
        gonder = st.form_submit_button("Gonder")

if gonder and soru.strip():
    st.session_state.mesajlar.append({"rol": "kullanici", "icerik": soru})
    stream_kutu = st.empty()
    son_cevap = ""
    son_kaynaklar = []
    for anlik, kaynaklar in cevap_al(soru, st.session_state.gecmis):
        son_cevap = anlik
        son_kaynaklar = kaynaklar
        html_anlik = md_to_html(son_cevap)
        stream_kutu.markdown(f'<div class="va-msg-bot"><div class="va-bot-avatar"><svg class="va-bot-char" width="44" height="52" viewBox="0 0 44 52" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="bg" cx="50%" cy="40%" r="60%"><stop offset="0%" stop-color="#c084fc"/><stop offset="100%" stop-color="#7c3aed"/></radialGradient><radialGradient id="eye-bg" cx="35%" cy="30%" r="70%"><stop offset="0%" stop-color="#1a0a2e"/><stop offset="100%" stop-color="#0a0a0f"/></radialGradient></defs><!-- Body --><ellipse cx="22" cy="20" rx="20" ry="19" fill="url(#bg)" filter="drop-shadow(0 4px 8px rgba(124,58,237,0.6))"/><!-- Tail --><polygon points="14,36 22,46 26,36" fill="#7c3aed"/><!-- Left eye --><g class="va-eye-anim" style="transform-origin:13px 19px"><ellipse cx="13" cy="19" rx="6" ry="6.5" fill="url(#eye-bg)"/><circle cx="11" cy="17" r="2" fill="rgba(255,255,255,0.85)"/></g><!-- Right eye --><g class="va-eye-anim2" style="transform-origin:31px 19px"><ellipse cx="31" cy="19" rx="6" ry="6.5" fill="url(#eye-bg)"/><circle cx="29" cy="17" r="2" fill="rgba(255,255,255,0.85)"/></g><!-- Shine --><ellipse cx="26" cy="8" rx="7" ry="3.5" fill="rgba(255,255,255,0.15)" transform="rotate(-20,26,8)"/></svg></div><div class="va-bot-card">{html_anlik}</div></div>', unsafe_allow_html=True)
    st.session_state.gecmis += [{"role":"user","content":soru}, {"role":"assistant","content":son_cevap}]
    kaynak_str = " · ".join(set(f"{k['belge']} S.{k['sayfa']}" for k in son_kaynaklar)) if son_kaynaklar else ""
    st.session_state.mesajlar.append({"rol": "bot", "icerik": son_cevap, "kaynak": kaynak_str})
    st.rerun()

if st.session_state.mesajlar:
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    _, c = st.columns([5,1])
    with c:
        if st.button("Ana Sayfa", key="anasayfa"):
            st.session_state.gecmis = []
            st.session_state.mesajlar = []
            st.rerun()
