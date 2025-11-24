import streamlit as st
import pdfplumber
import matplotlib.pyplot as plt
import zipfile
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Evrensel Sınav Okuma Sistemi", layout="wide")

st.title("📄 Evrensel Optik/Sınav Okuma Sistemi")
st.markdown("""
Bu sistem, farklı soru sayılarına ve kitapçık türlerine göre sınav kağıtlarını analiz eder.
**Ayarları sol menüden yapınız.**
""")

# --- YAN MENÜ (AYARLAR) ---
st.sidebar.header("⚙️ Sınav Ayarları")

# 1. Soru Sayısı Ayarı
soru_sayisi = st.sidebar.number_input("Sınavda Kaç Soru Var?", min_value=5, max_value=100, value=25, step=1)

# 2. Kitapçık Türü Ayarı
kitapcik_modu = st.sidebar.selectbox(
    "Kitapçık Düzeni",
    ("A-B (2 Kitapçık)", "Tek Kitapçık", "A-B-C (3 Kitapçık)", "A-B-C-D (4 Kitapçık)")
)

# 3. Cevap Anahtarlarını Dinamik Oluştur
keys = {}

st.sidebar.subheader("🔑 Cevap Anahtarlarını Giriniz")

if kitapcik_modu == "Tek Kitapçık":
    anahtar = st.sidebar.text_input("Cevap Anahtarı", help="Örn: ABCDE...")
    keys["A"] = anahtar.strip() # Tek kitapçıkta varsayılan 'A' kabul ederiz

elif kitapcik_modu == "A-B (2 Kitapçık)":
    keys["A"] = st.sidebar.text_input("A Kitapçığı", "CDBCBCBDCBBCCABEBBCABBCBC").strip()
    keys["B"] = st.sidebar.text_input("B Kitapçığı", "BBCBBDBABCBCCCCCAEBCDBBBC").strip()

elif kitapcik_modu == "A-B-C (3 Kitapçık)":
    keys["A"] = st.sidebar.text_input("A Kitapçığı").strip()
    keys["B"] = st.sidebar.text_input("B Kitapçığı").strip()
    keys["C"] = st.sidebar.text_input("C Kitapçığı").strip()

elif kitapcik_modu == "A-B-C-D (4 Kitapçık)":
    keys["A"] = st.sidebar.text_input("A Kitapçığı").strip()
    keys["B"] = st.sidebar.text_input("B Kitapçığı").strip()
    keys["C"] = st.sidebar.text_input("C Kitapçığı").strip()
    keys["D"] = st.sidebar.text_input("D Kitapçığı").strip()

# --- FONKSİYONLAR ---

def puan_hesapla(cevap_string, kitapcik, soru_adedi, anahtarlar):
    """Öğrenci cevabını anahtarla karşılaştırıp puan listesi döner."""
    cevap = str(cevap_string).replace(" ", "").upper()
    
    # Kitapçık türü belirleme (Tek kitapçıksa her zaman A'yı kullan)
    if kitapcik_modu == "Tek Kitapçık":
        aktif_kitapcik = "A"
    else:
        aktif_kitapcik = kitapcik if kitapcik in anahtarlar else None

    if not aktif_kitapcik or aktif_kitapcik not in anahtarlar:
        return [0] * soru_adedi # Kitapçık bulunamazsa 0 puan

    dogru_cevaplar = anahtarlar[aktif_kitapcik]
    
    # Eksik karakter varsa X ile doldur, fazlaysa kes
    if len(cevap) < soru_adedi:
        cevap = cevap + "X" * (soru_adedi - len(cevap))
    cevap = cevap[:soru_adedi]
    
    # Soru başına puan (Otomatik Hesaplama)
    birim_puan = 100 / soru_adedi
    
    puanlar = []
    for i in range(soru_adedi):
        # Anahtar o soru için tanımlıysa ve cevap doğruysa
        if i < len(dogru_cevaplar) and cevap[i] == dogru_cevaplar[i]:
            puanlar.append(birim_puan) # Tam puan (float olabilir)
        else:
            puanlar.append(0)
    return puanlar

def tablo_olustur_dinamik(ogrenci_adi, puanlar, soru_adedi):
    """Soru sayısına göre satırları otomatik bölen akıllı tablo oluşturucu."""
    toplam_puan = sum(puanlar)
    
    # Tabloyu parçalara bölmek için ayarlar
    sutun_limiti = 20 # Her satırda kaç soru gösterilsin? (Görsel genişlik için 20-25 ideal)
    
    # Kaç parça (chunk) olacak? (Örn: 45 soru varsa -> 20 + 20 + 5 = 3 parça)
    parca_sayisi = (soru_adedi + sutun_limiti - 1) // sutun_limiti
    
    # Resim yüksekliğini parça sayısına göre ayarla (Her parça 2 satır kaplar)
    fig_height = 1.5 + (parca_sayisi * 1.5) 
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.axis('tight')
    ax.axis('off')

    table_data = []
    
    for i in range(parca_sayisi):
        start = i * sutun_limiti
        end = min((i + 1) * sutun_limiti, soru_adedi)
        
        # Soru Numaraları Satırı
        row_nums = [str(k) for k in range(start + 1, end + 1)]
        # Puanlar Satırı (Ondalıklı sayıları düzgün formatla: 4.0 -> 4, 2.5 -> 2.5)
        row_scores = [f"{p:.2f}".rstrip('0').rstrip('.') for p in puanlar[start:end]]
        
        # Eğer satır kısa kaldıysa (son satır gibi), boşlukla doldur
        eksik = sutun_limiti - len(row_nums)
        if eksik > 0:
            row_nums += [""] * eksik
            row_scores += [""] * eksik
        
        table_data.append(row_nums)
        table_data.append(row_scores)

    # Toplam Puanı En Sona Ekle
    # Son satırın ortasına veya sonuna ekleyelim
    son_satir_index = len(table_data) - 1
    
    # Tabloyu Çiz
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8) # Hücre yüksekliği

    # --- Renklendirme ve Stil ---
    for (row, col), cell in table.get_celld().items():
        # Çift numaralı satırlar (0, 2, 4...) -> Soru Numaraları (Kalın)
        if row % 2 == 0:
            cell.set_text_props(weight='bold')
            # Boş hücrelerin çerçevesini gizle
            if cell.get_text().get_text() == "":
                 cell.set_edgecolor('white')

        # Tek numaralı satırlar (1, 3, 5...) -> Puanlar (Kırmızı)
        if row % 2 == 1:
            cell.set_text_props(color='red', weight='bold')
             # Boş hücrelerin çerçevesini gizle
            if cell.get_text().get_text() == "":
                 cell.set_edgecolor('white')

    # Toplam Puanı Başlık Olarak veya Resmin Altına Yazalım (Tablo içine sıkıştırmak yerine daha temiz)
    plt.title(f"{ogrenci_adi}\nTOPLAM PUAN: {toplam_puan:.2f}".rstrip('0').rstrip('.'), 
              fontsize=14, color='blue', weight='bold', y=0.98 if parca_sayisi>1 else 1.1)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close()
    buf.seek(0)
    return buf

def pdf_den_veri_oku(uploaded_file):
    """PDF'ten veri okuma (Hata toleransı artırılmış)."""
    data = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    cleaned_row = [str(item) for item in row if item is not None]
                    
                    # Basit bir filtre: İçinde en azından uzun bir cevap anahtarı benzeri string var mı?
                    # Ve isim sütunu var mı?
                    if len(cleaned_row) >= 3:
                        try:
                            # Genelde yapı: [Sıra, No, Ad, CevapStringi...]
                            # Cevap stringini bulmaya çalışalım (en uzun string genelde cevaptır)
                            cevap_adaylari = [s for s in cleaned_row if len(str(s)) > 10]
                            if not cevap_adaylari:
                                continue
                            
                            cevap_raw = cevap_adaylari[-1] # Genelde sondadır
                            
                            # İsim bulma (Cevap olmayan, sayı olmayan en uzun string)
                            isim_adaylari = [s for s in cleaned_row if s != cevap_raw and not any(char.isdigit() for char in str(s))]
                            ad_soyad = "Bilinmeyen İsim"
                            if isim_adaylari:
                                ad_soyad = max(isim_adaylari, key=len).replace('\n', ' ')

                            # Kitapçık Bulma
                            kitapcik = "A" # Varsayılan
                            if "A" in cevap_raw[-3:]: kitapcik = "A"
                            elif "B" in cevap_raw[-3:]: kitapcik = "B"
                            elif "C" in cevap_raw[-3:]: kitapcik = "C"
                            elif "D" in cevap_raw[-3:]: kitapcik = "D"
                            
                            # Cevap temizliği
                            cevap_string = cevap_raw.replace('\n', '').replace(' ', '')
                            # Sondaki A/B/C/D harfini temizle (Eğer cevap anahtarının parçası değilse)
                            if cevap_string.endswith(('A','B','C','D')) and len(cevap_string) > soru_sayisi:
                                cevap_string = cevap_string[:-1]

                            data.append([ad_soyad, kitapcik, cevap_string])
                        except:
                            continue
    return data

# --- ARAYÜZ AKIŞI ---
uploaded_file = st.file_uploader("Sınav Sonuç PDF Dosyasını Yükleyin", type="pdf")

if uploaded_file is not None:
    # Anahtar kontrolü
    eksik_anahtar = False
    if kitapcik_modu == "A-B (2 Kitapçık)" and (not keys.get("A") or not keys.get("B")): eksik_anahtar = True
    
    if eksik_anahtar:
        st.warning("Lütfen sol menüden cevap anahtarlarını eksiksiz giriniz.")
    else:
        st.info("Dosya analiz ediliyor...")
        try:
            ogrenciler = pdf_den_veri_oku(uploaded_file)
            
            if len(ogrenciler) > 0:
                st.success(f"{len(ogrenciler)} öğrenci bulundu. İşlem başlatılıyor...")
                
                if st.button("Sonuçları Oluştur"):
                    progress_bar = st.progress(0)
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i, (ad, ktp, cvp) in enumerate(ogrenciler):
                            # Hesapla
                            puanlar = puan_hesapla(cvp, ktp, soru_sayisi, keys)
                            # Çiz
                            img_buf = tablo_olustur_dinamik(ad, puanlar, soru_sayisi)
                            # Kaydet
                            dosya_adi = f"{ad.replace(' ', '_')}.png"
                            zf.writestr(dosya_adi, img_buf.getvalue())
                            
                            progress_bar.progress((i + 1) / len(ogrenciler))
                    
                    zip_buffer.seek(0)
                    st.balloons()
                    st.download_button(
                        label="📥 ZIP Olarak İndir",
                        data=zip_buffer,
                        file_name="Sinav_Sonuclari.zip",
                        mime="application/zip"
                    )
            else:
                st.error("PDF'ten veri okunamadı. Formatı kontrol edin.")
        except Exception as e:
            st.error(f"Hata: {e}")