import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Jeodezik Ölçüm & Hata Analizi", layout="wide", page_icon="📐")

st.title("📐 Jeodezik Ölçüm & Bağıl Hata Analiz Aracı")
st.caption("Kaba hata taraması (Robust/Leave-one-out), Bessel formülü ve sınır denetimi")

# --- Yan Panel: Ayarlar ---
st.sidebar.header("Ölçüm Türü & Parametreler")
veri_tipi = st.sidebar.selectbox("Ölçü Türü", ["Uzunluk / Kenar", "Açı (Doğrultu / Kenar Açısı)"])

if veri_tipi.startswith("Uzunluk"):
    birim = st.sidebar.selectbox("Birim", ["Metre (m)", "Kilometre (km)", "Milimetre (mm)"])
    varsayilanlar = [152.342, 152.348, 152.339, 92.551]
else:
    birim = st.sidebar.selectbox("Birim", ["Grad (gon)", "Derece (DD.MMSS)", "Radyan"])
    varsayilanlar = [124.5020, 124.5045, 124.5015]

sinir_katsayisi = st.sidebar.number_input("Sınır Hata Katsayısı (k)", value=2.5, step=0.1, help="Genelde 2.5 veya 3 alınır")
manuel_tolerans = st.sidebar.number_input("Manuel Tolerans Sınırı (0 ise otomatik hesaplar)", value=0.0, step=0.001)

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
    # 1. Ham İstatistikler
    ortalama_ham = np.mean(olculer)
    v_ham = ortalama_ham - olculer
    v_kare_ham = np.sum(v_ham**2)
    m_ham = np.sqrt(v_kare_ham / (n - 1))
    
    # 2. Akıllı Kaba Hata Taraması (Leave-One-Out / Bulaşmayı Önleme)
    # Eğer n >= 3 ise, her ölçüyü gruptan çıkarıp kalan grubun saçılmasına bakarız.
    # Böylece 92.55 gibi absürt bir değer sınır hatayı şişiremez.
    aykiri_indeksler = []
    
    if manuel_tolerans > 0:
        aykiri_indeksler = np.where(np.abs(v_ham) > manuel_tolerans)[0].tolist()
        kullanilan_sinir = manuel_tolerans
    else:
        if n >= 3:
            # Medyan ve medyan mutlak sapması (MAD) ile dirençli referans
            medyan = np.median(olculer)
            mad = np.median(np.abs(olculer - medyan))
            # Normal dağılım eşdeğer standart sapması: sigma_robust ~ 1.4826 * MAD
            m_direncli = 1.4826 * mad if mad > 1e-9 else m_ham
            kullanilan_sinir = sinir_katsayisi * m_direncli
            
            # Eğer ölçü medyandan sınır kadar uzaksa kaba hatalıdır
            for i in range(n):
                if np.abs(olculer[i] - medyan) > kullanilan_sinir:
                    aykiri_indeksler.append(i)
        else:
            kullanilan_sinir = sinir_katsayisi * m_ham
            aykiri_indeksler = np.where(np.abs(v_ham) > kullanilan_sinir)[0].tolist()

    # 3. Temizlenmiş Küme Hesabı (Kaba hata varsa onları çıkarıp gerçek ortalamayı bulalım)
    mask_temiz = [i for i in range(n) if i not in aykiri_indeksler]
    
    if len(mask_temiz) >= 2 and len(aykiri_indeksler) > 0:
        olculer_temiz = olculer[mask_temiz]
        n_temiz = len(olculer_temiz)
        ortalama_nihai = np.mean(olculer_temiz)
        v_temiz = ortalama_nihai - olculer_temiz
        m_nihai = np.sqrt(np.sum(v_temiz**2) / (n_temiz - 1))
        M_nihai = m_nihai / np.sqrt(n_temiz)
    else:
        ortalama_nihai = ortalama_ham
        m_nihai = m_ham
        M_nihai = m_ham / np.sqrt(n)

    # 4. Bağıl Hata (Temizlenmiş verilere göre)
    if abs(ortalama_nihai) > 1e-9:
        bagil_oran = M_nihai / abs(ortalama_nihai)
        bagil_payda = int(round(1 / bagil_oran)) if bagil_oran > 0 else 0
        bagil_hata_str = f"1 / {bagil_payda:,}".replace(",", ".")
        bagil_yuzde = f"% {bagil_oran * 100:.4f}"
    else:
        bagil_hata_str = "Tanımsız"
        bagil_yuzde = "0"

    # --- Sonuç Panelleri ---
    st.markdown("---")
    st.subheader("2. İstatistik & Hata Değerlendirmesi")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Ölçü (n)", f"{n}")
    c2.metric("Güvenilir Ortalama (x̄)", f"{ortalama_nihai:.5f} {birim.split()[0]}")
    c3.metric("Tek Ölçü OKH (m)", f"{m_nihai:.5f}")
    c4.metric("Ortalama OKH (M)", f"{M_nihai:.5f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Bağıl Hata (M / x̄)", bagil_hata_str)
    c6.metric("Bağıl Hata (%)", bagil_yuzde)
    c7.metric("Etkin Sınır Hata (Sh)", f"{kullanilan_sinir:.5f}")

    # Uyarı ve Tolerans Durumu
    if len(aykiri_indeksler) == 0:
        st.success("✅ Tüm ölçümler sınır hata içinde kalmaktadır (Kaba hata tespit edilmedi).")
    else:
        hatali_nolar = ", ".join([f"#{i + 1} ({olculer[i]})" for i in aykiri_indeksler])
        st.error(f"❌ Kaba Hata Yakalandı! Sınır hatayı aşan ölçüler elendi: {hatali_nolar}")
        st.info("💡 Not: İstatistiksel sonuçlar (Ortalama, OKH ve Bağıl Hata), hatalı ölçü hariç tutularak güvenilir seriden hesaplanmıştır.")

    # --- Düzeltme Cetveli ---
    st.subheader("3. Düzeltme Cetveli (v Dağılımı)")
    tablo_satirlari = []
    for i in range(n):
        durum = "❌ Kaba Hata (Sınır Dışı)" if i in aykiri_indeksler else "✅ Normal"
        v_i = ortalama_nihai - olculer[i]
        tablo_satirlari.append({
            "Ölçü No": f"#{i + 1}",
            f"Ölçü ({birim.split()[0]})": f"{olculer[i]:.5f}",
            "Fark (x̄ - x)": f"{v_i:+.5f}",
            "v²": f"{v_i**2:.8f}",
            "Durum": durum
        })

    df = pd.DataFrame(tablo_satirlari)
    st.dataframe(df, use_container_width=True, hide_index=True)
