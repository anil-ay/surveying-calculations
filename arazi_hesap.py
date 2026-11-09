import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Jeodezik Ölçüm & Hata Analizi", layout="wide", page_icon="📐")

st.title("📐 Jeodezik Ölçüm & Bağıl Hata Analiz Aracı")
st.caption("Dinamik ölçü girişleri, Bessel formülü, sınır hata ve bağıl hata denetimi")

# --- Yan Panel: Ayarlar ---
st.sidebar.header("Ölçüm Türü & Parametreler")
veri_tipi = st.sidebar.selectbox("Ölçü Türü", ["Uzunluk / Kenar", "Açı (Doğrultu / Kenar Açısı)"])

if veri_tipi.startswith("Uzunluk"):
    birim = st.sidebar.selectbox("Birim", ["Metre (m)", "Kilometre (km)", "Milimetre (mm)"])
    varsayilanlar = [152.342, 152.348, 152.339]
else:
    birim = st.sidebar.selectbox("Birim", ["Grad (gon)", "Derece (DD.MMSS)", "Radyan"])
    varsayilanlar = [124.5020, 124.5045, 124.5015]

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

# Giriş Kutucukları Grid Düzeni
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
    # 1. Aritmetik Ortalama
    ortalama = np.mean(olculer)
    
    # 2. Düzeltmeler (v = x̄ - x_i)
    v = ortalama - olculer
    v_kare_toplam = np.sum(v**2)
    
    # 3. Tek Ölçünün Ortalama Karesel Hatası (Bessel): m = sqrt([vv] / (n - 1))
    m = np.sqrt(v_kare_toplam / (n - 1))
    
    # 4. Aritmetik Ortalamanın Ortalama Karesel Hatası: M = m / sqrt(n)
    m_ortalama = m / np.sqrt(n)
    
    # 5. Bağıl Hata Hesabı (Relative Error)
    # Bağıl hata = M / |x̄| -> Jeodezide 1 / K paydası şeklinde gösterilir (ör. 1/15000)
    if abs(ortalama) > 1e-9:
        bagil_oran = m_ortalama / abs(ortalama)
        bagil_payda = int(round(1 / bagil_oran)) if bagil_oran > 0 else 0
        bagil_hata_str = f"1 / {bagil_payda:,}".replace(",", ".")
        bagil_yuzde = f"% {bagil_oran * 100:.4f}"
    else:
        bagil_hata_str = "Tanımsız (Ortalama 0)"
        bagil_yuzde = "0"

    # 6. Sınır Hata & Kaba Hata Taraması
    sinir_hata = manuel_tolerans if manuel_tolerans > 0 else (sinir_katsayisi * m)
    aykiri_indeksler = np.where(np.abs(v) > sinir_hata)[0]

    # --- Sonuç Panelleri ---
    st.markdown("---")
    st.subheader("2. İstatistik & Hata Değerlendirmesi")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ölçü Adedi (n)", f"{n}")
    c2.metric("Aritmetik Ortalama (x̄)", f"{ortalama:.5f} {birim.split()[0]}")
    c3.metric("Tek Ölçü OKH (m)", f"{m:.5f}")
    c4.metric("Ortalama OKH (M)", f"{m_ortalama:.5f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Bağıl Hata (M / x̄)", bagil_hata_str, help="Jeodezide standart hassasiyet gösterimi (1/payda)")
    c6.metric("Bağıl Hata (%)", bagil_yuzde)
    c7.metric("Sınır Hata (Sh)", f"{sinir_hata:.5f}")

    # Uyarı ve Tolerans Durumu
    if len(aykiri_indeksler) == 0:
        st.success("✅ Tüm ölçümler sınır hata içinde kalmaktadır (Kaba hata tespit edilmedi).")
    else:
        hatali_nolar = ", ".join([str(i + 1) for i in aykiri_indeksler])
        st.error(f"❌ {len(aykiri_indeksler)} adet ölçü sınır hatayı aşıyor! Hatalı ölçü no: {hatali_nolar}")

    # --- Düzeltme Cetveli ---
    st.subheader("3. Düzeltme Cetveli (v Dağılımı)")
    tablo_satirlari = []
    for i in range(n):
        tablo_satirlari.append({
            "Ölçü No": f"#{i + 1}",
            f"Ölçü ({birim.split()[0]})": f"{olculer[i]:.5f}",
            "Düzeltme (v = x̄ - x)": f"{v[i]:+.5f}",
            "v²": f"{v[i]**2:.8f}",
            "Durum": "⚠️ Sınır Dışı" if i in aykiri_indeksler else "Normal"
        })

    df = pd.DataFrame(tablo_satirlari)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"[vv] (Düzeltme kareleri toplamı): {v_kare_toplam:.8f}  |  [v] Kontrol toplamı: {np.sum(v):.6f} (~0 olmalıdır)")
