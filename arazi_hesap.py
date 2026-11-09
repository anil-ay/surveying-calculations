import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Jeodezik Ölçüm & Hata Analizi", layout="wide", page_icon="📐")

st.title("📐 Jeodezik Ölçüm & Bağıl Hata Analiz Aracı")
st.caption("Dinamik ölçü girişleri, akıllı kaba hata filtreleme seçeneği ve Bessel analizi")

# --- Yan Panel: Ayarlar ---
st.sidebar.header("Ölçüm Türü & Parametreler")
veri_tipi = st.sidebar.selectbox("Ölçü Türü", ["Uzunluk / Kenar", "Açı (Doğrultu / Kenar Açısı)"])

if veri_tipi.startswith("Uzunluk"):
    birim = st.sidebar.selectbox("Birim", ["Metre (m)", "Kilometre (km)", "Milimetre (mm)"])
    varsayilanlar = [152.342, 152.348, 152.339, 92.551]
else:
    birim = st.sidebar.selectbox("Birim", ["Grad (gon)", "Derece (DD.MMSS)", "Radyan"])
    varsayilanlar = [124.5020, 124.5045, 124.5015]

st.sidebar.markdown("---")
st.sidebar.subheader("Hata & Tolerans Denetimi")

# Akıllı Kaba Hata Filtresi Açma/Kapama Düğmesi
filtre_aktif = st.sidebar.toggle(
    "🛡️ Akıllı Kaba Hata Filtresi (Robust/MAD)",
    value=True,
    help="Açıkken absürt/kaba hatalı ölçülerin ortalamayı ve sınır hatayı zehirlemesini engeller. Kapalıyken klasik Gauss yöntemini çalıştırır."
)

sinir_katsayisi = st.sidebar.number_input("Sınır Hata Katsayısı (k)", value=2.5, step=0.1, help="Genelde 2.5 veya 3 alınır")
manuel_tolerans = st.sidebar.number_input("Manuel Tolerans Sınırı (0 ise formülden alır)", value=0.0, step=0.001)

# --- Dinamik Ölçü Girişi (Session State) ---
if "olcumler" not in st.session_state:
    st.session_state.olcumler = varsayilanlar

col_btn1, col_btn2, _ = st.columns([1, 1, 4])
with col_btn1:
    if st.button("➕ Ölçü Ekle", use_container_width=True):
        st.session_state.olcumler.append(st.session_state.olcumler[-1] if st.session_state.olcumler else 0.0)
        st.rerun()

with col_btn2:
    if st.button("➖ Sonuncuyu Sil", use_container_width=True):
        if len(st.session_state.olcumler) > 2:
            st.session_state.olcumler.pop()
            st.rerun()
        else:
            st.toast("En az 2 ölçü kalmalıdır!", icon="⚠️")

st.subheader("1. Ölçü Değerleri")
cols_per_row = 3
satir_sayisi = (len(st.session_state.olcumler) + cols_per_row - 1) // cols_per_row

for r in range(satir_sayisi):
    cols = st.columns(cols_per_row)
    for c in range(cols_per_row):
        idx = r * cols_per_row + c
        if idx < len(st.session_state.olcumler):
            with cols[c]:
                st.session_state.olcumler[idx] = st.number_input(
                    f"{idx + 1}. Ölçü ({birim.split()[0]}):",
                    value=float(st.session_state.olcumler[idx]),
                    format="%.5f",
                    key=f"input_{idx}"
                )

# --- Hesaplama Motoru ---
olculer = np.array(st.session_state.olcumler)
n = len(olculer)

if n < 2:
    st.warning("Hata istatistiği hesaplamak için en az 2 ölçüm gereklidir.")
else:
    # 1. Ham İstatistikler (Klasik Gauss / Bessel)
    ortalama_ham = np.mean(olculer)
    v_ham = ortalama_ham - olculer
    v_kare_ham = np.sum(v_ham**2)
    m
