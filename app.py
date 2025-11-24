import streamlit as st
import pdfplumber
import matplotlib.pyplot as plt
import zipfile
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Sınav Okuma Sistemi", layout="centered")

# --- BAŞLIK ---
st.title("📄 Otomatik Sınav Okuma Sistemi")
st.info("Sistem, 'Cevap Anahtarı' satırlarını ve öğrencileri PDF içerisinden otomatik tespit eder.")

# --- YENİ İMZA METNİ ---
imza_metni = "Öğr.Gör. Berkay AKSU tarafından kişisel kullanım amaçlı oluşturulmuştur. Hatalı sonuç verebilir lütfen kontrol edin. Oluşan sonuçlar ve kontrolü tamamen kullanan kişinin sorumluluğundadır."

# Sol Menüye İmza
st.sidebar.markdown("---")
st.sidebar.warning(imza_metni)

# --- FONKSİYONLAR ---

def cevap_anahtarlarini_bul(uploaded_file):
    """
    PDF'in ilk sayfalarında 'CevapAnahtarı' kelimesini arar ve
    otomatik olarak A ve B anahtarlarını çeker.
    """
    bulunan_anahtarlar = {}
    
    with pdfplumber.open(uploaded_file) as pdf:
        # Genelde cevap anahtarı ilk sayfada olur, garanti olsun diye ilk 2 sayfaya bakalım
        for i in range(min(2, len(pdf.pages))):
            page = pdf.pages[i]
            tables = page.extract_tables()
            
            for table in tables:
                for row in table:
                    for cell in row:
                        if cell:
                            # Temizlik: Boşlukları sil, büyük harf yap
                            text_raw = str(cell).replace("\n", " ").strip()
                            text_clean = text_raw.replace(" ", "").upper()
                            
                            # "CEVAPANAHTARI" kelimesini içeriyor mu?
                            if "CEVAPANAHTARI" in text_clean:
                                # Metni parçala: "CevapAnahtarı CDBC... A" formatını ayıkla
                                # 'CevapAnahtarı' kelimesinden sonrasını al
                                try:
                                    # Anahtarın kendisini bulmaya çalış (en uzun harf dizisi)
                                    parts = text_raw.split()
                                    candidate_key = ""
                                    booklet_type = ""
                                    
                                    for part in parts:
                                        # Uzun harf dizisi anahtardır
                                        if len(part) > 15 and part.upper() != "CEVAPANAHTARI":
                                            candidate_key = part.strip()
                                        # Tek harf (A/B) kitapçık türüdür
                                        if part.strip() in ["A", "B"]:
                                            booklet_type = part.strip()
                                    
                                    # Eğer satırda A/B yazmıyorsa, sırayla atama yapabiliriz ama 
                                    # senin formatında satır sonunda A veya B yazıyor.
                                    if candidate_key and booklet_type:
                                        bulunan_anahtarlar[booklet_type] = candidate_key.upper()
                                        
                                except:
                                    continue
                                    
    return bulunan_anahtarlar

def puan_hesapla(cevap_string, kitapcik, keys):
    """
    Her soru 4 puan, 25 soru.
    """
    cevap = str(cevap_string).replace(" ", "").upper()
    
    # Kitapçık anahtarı yoksa 0 ver
    if kitapcik not in keys:
        return [0] * 25

    dogru_cevaplar = keys[kitapcik]
    
    # Uzunluk sabitleme (25 Soru)
    if len(cevap) < 25:
        cevap = cevap + "X" * (25 - len(cevap))
    cevap = cevap[:25]
    
    puanlar = []
    for i in range(25):
        # Anahtar uzunluğunu aşmamaya dikkat et
        if i < len(dogru_cevaplar) and cevap[i] == dogru_cevaplar[i]:
            puanlar.append(4)
        else:
            puanlar.append(0)
    return puanlar

def tablo_olustur(ogrenci_adi, puanlar):
    toplam_puan = sum(puanlar)
    
    fig, ax = plt.subplots(figsize=(12, 2.8))
    ax.axis('tight')
    ax.axis('off')

    # Veri Hazırlama
    row1 = [str(i) for i in range(1, 21)]
    row2 = [str(p) for p in puanlar[:20]]
    row3 = [str(i) for i in range(21, 26)] + [""] * 15
    row4 = [str(p) for p in puanlar[20:]] + [""] * 15
    
    index_yerlesim = 8 
    row3[index_yerlesim] = "TOPLAM PUAN"
    row4[index_yerlesim] = str(toplam_puan)

    table_data = [row1, row2, row3, row4]
    
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)

    # Renklendirme
    for (row, col), cell in table.get_celld().items():
        if row == 0 or row == 2:
            cell.set_text_props(weight='bold')
            if col >= 5 and row == 2 and col != index_yerlesim:
                 cell.set_edgecolor('white') 

        if row == 1 or row == 3:
            cell.set_text_props(color='red', weight='bold')
            if col >= 5 and row == 3:
                 if col != index_yerlesim: 
                     cell.set_edgecolor('white')
                     cell.get_text().set_text("")
        
        if col == index_yerlesim:
            if row == 2:
                cell.set_text_props(color='black', weight='bold')
                cell.set_edgecolor('black') 
            if row == 3:
                cell.set_text_props(color='blue', weight='bold', size=14)
                cell.set_edgecolor('black')

    plt.title(f"{ogrenci_adi} - Sınav Sonuç Tablosu", y=1.05)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close()
    buf.seek(0)
    return buf

def pdf_den_veri_oku_standart(uploaded_file):
    """
    KONT 1 formatına göre öğrenci verilerini okur.
    """
    data = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    cleaned_row = [str(item) for item in row if item is not None]
                    
                    if len(cleaned_row) < 3: continue
                    
                    try:
                        # Cevap Stringi Bulma (Sayı olmayan, uzun metin)
                        cevap_adaylari = [
                            s for s in cleaned_row 
                            if len(str(s)) > 15 
                            and not str(s).replace(" ","").isdigit()
                            and "CevapAnahtarı" not in str(s) # Cevap anahtarı satırını öğrenci sanmasın
                        ]
                        
                        if not cevap_adaylari: continue
                        cevap_raw = cevap_adaylari[-1]
                        
                        # Kitapçık Türü Bulma
                        kitapcik = "A" 
                        clean_raw = cevap_raw.replace('\n', ' ').strip()
                        if clean_raw.endswith(" A") or clean_raw.endswith("A"): kitapcik = "A"
                        elif clean_raw.endswith(" B") or clean_raw.endswith("B"): kitapcik = "B"
                        
                        # İsim Bulma
                        isim_adaylari = [
                            s for s in cleaned_row 
                            if s != cevap_raw 
                            and len(str(s)) > 3
                            and not any(char.isdigit() for char in str(s))
                            and "CevapAnahtarı" not in str(s)
                        ]
                        
                        ad_soyad = "Öğrenci"
                        if isim_adaylari:
                            ad_soyad = max(isim_adaylari, key=len).replace('\n', ' ')

                        # Cevap Temizliği
                        cevap_sadece_harf = ''.join(filter(str.isalpha, cevap_raw.upper()))
                        if len(cevap_sadece_harf) > 25:
                            if cevap_sadece_harf.endswith(kitapcik):
                                cevap_sadece_harf = cevap_sadece_harf[:-1]
                        
                        # Veriyi Ekle
                        if len(cevap_sadece_harf) >= 10:
                             data.append([ad_soyad, kitapcik, cevap_sadece_harf])

                    except:
                        continue
    return data

# --- ARAYÜZ AKIŞI ---

uploaded_file = st.file_uploader("Sınav Sonuç PDF Dosyasını Yükleyin", type="pdf")

if uploaded_file is not None:
    st.write("🔍 Dosya taraniyor...")
    
    # 1. Önce Cevap Anahtarlarını Otomatik Bul
    bulunan_keys = cevap_anahtarlarini_bul(uploaded_file)
    
    if not bulunan_keys:
        st.error("⚠️ PDF içinde 'CevapAnahtarı' satırı bulunamadı! Lütfen dosya formatını kontrol edin.")
    else:
        # Bulunan anahtarları ekrana yaz (Kullanıcı görsün)
        st.success("✅ Cevap Anahtarları Otomatik Algılandı:")
        cols = st.columns(len(bulunan_keys))
        for idx, (k, v) in enumerate(bulunan_keys.items()):
            cols[idx].info(f"**Kitapçık {k}:** {v}")
        
        # 2. Öğrencileri Oku
        ogrenciler = pdf_den_veri_oku_standart(uploaded_file)
        
        if len(ogrenciler) > 0:
            st.write(f"📊 **{len(ogrenciler)}** öğrenci tespit edildi.")
            
            # İşlem Butonu
            if st.button("Sonuçları Oluştur ve İndir"):
                progress_bar = st.progress(0)
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, (ad, ktp, cvp) in enumerate(ogrenciler):
                        # Hesapla (Bulunan otomatik anahtarları kullan)
                        puanlar = puan_hesapla(cvp, ktp, bulunan_keys)
                        # Çiz
                        img_buf = tablo_olustur(ad, puanlar)
                        # Kaydet
                        dosya_adi = f"{ad.replace(' ', '_')}.png"
                        zf.writestr(dosya_adi, img_buf.getvalue())
                        
                        progress_bar.progress((i + 1) / len(ogrenciler))
                
                zip_buffer.seek(0)
                st.balloons()
                st.download_button(
                    label="📥 Sonuçları ZIP İndir",
                    data=zip_buffer,
                    file_name="Sinav_Sonuclari.zip",
                    mime="application/zip"
                )
        else:
            st.warning("Cevap anahtarı bulundu ancak öğrenci verisi okunamadı.")

# --- ALT İMZA (Sayfa Sonu) ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8em;'>{imza_metni}</div>", unsafe_allow_html=True)
