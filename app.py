import streamlit as st
import pdfplumber
import matplotlib.pyplot as plt
import zipfile
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Sınav Okuma Sistemi", layout="centered")

# --- BAŞLIK ---
st.title("📄 Otomatik Sınav Okuma Sistemi")
st.info("Sistem cevap anahtarını PDF'ten çekmeye çalışır. Eğer çekemezse sol menüden siz düzeltebilirsiniz.")

# --- FONKSİYONLAR ---

def cevap_anahtarlarini_bul(uploaded_file):
    """
    PDF'in ilk sayfalarında 'CevapAnahtarı' satırını arar.
    Bulamazsa boş döner, hata vermez.
    """
    bulunan_anahtarlar = {"A": "", "B": ""}
    
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            # İlk 2 sayfaya bakmak yeterli
            for i in range(min(2, len(pdf.pages))):
                page = pdf.pages[i]
                text = page.extract_text() # Tablo yerine düz metin olarak da bakalım
                
                # Satır satır incele
                lines = text.split('\n')
                for line in lines:
                    # Temizlik
                    line_clean = line.replace(" ", "").upper()
                    
                    if "CEVAPANAHTARI" in line_clean:
                        # Bu satırda muhtemelen cevap var.
                        # Örnek satır: "CevapAnahtarı CDBCBC... A" veya sadece cevap.
                        
                        # Uzun harf dizisini (cevap şıklarını) bulalım
                        parts = line.split()
                        potential_key = ""
                        booklet = ""
                        
                        for part in parts:
                            # 15 karakterden uzun ve içinde "CEVAP" geçmeyen kısım anahtardır
                            if len(part) > 15 and "CEVAP" not in part.upper():
                                potential_key = part.strip().upper()
                            
                            # Tek harf A veya B ise kitapçık türüdür
                            if part.strip().upper() == "A":
                                booklet = "A"
                            elif part.strip().upper() == "B":
                                booklet = "B"
                        
                        # Eğer satırda kitapçık türü yazmıyorsa, sırayla atamayı deneyelim
                        # (Genelde önce A sonra B olur ama bu riskli, o yüzden sadece kesinleri alalım)
                        if potential_key and booklet:
                            bulunan_anahtarlar[booklet] = potential_key
                        elif potential_key and not booklet:
                            # Kitapçık türü yazmıyorsa ama anahtar bulduysak,
                            # hangisi boşsa ona atayalım (Önce A)
                            if not bulunan_anahtarlar["A"]:
                                bulunan_anahtarlar["A"] = potential_key
                            elif not bulunan_anahtarlar["B"]:
                                bulunan_anahtarlar["B"] = potential_key
                                
    except Exception as e:
        pass
        
    return bulunan_anahtarlar

def puan_hesapla(cevap_string, kitapcik, keys):
    # Temizlik
    cevap = str(cevap_string).replace(" ", "").upper()
    
    # Anahtar kontrolü: Kitapçık anahtarı yoksa 0 puan
    if kitapcik not in keys or not keys[kitapcik]:
        return [0] * 25

    dogru_cevaplar = keys[kitapcik].replace(" ", "").upper()
    
    # Öğrenci cevabını 25 karaktere tamamla veya kes
    if len(cevap) < 25:
        cevap = cevap + "X" * (25 - len(cevap))
    cevap = cevap[:25]
    
    puanlar = []
    for i in range(25):
        # Cevap anahtarı uzunluğu kadar kontrol et
        if i < len(dogru_cevaplar):
            if cevap[i] == dogru_cevaplar[i]:
                puanlar.append(4)
            else:
                puanlar.append(0)
        else:
            puanlar.append(0)
    return puanlar

def tablo_olustur(ogrenci_adi, puanlar):
    # Görsel oluşturma (Değişmedi)
    toplam_puan = sum(puanlar)
    fig, ax = plt.subplots(figsize=(12, 2.8))
    ax.axis('tight')
    ax.axis('off')
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
    for (row, col), cell in table.get_celld().items():
        if row == 0 or row == 2:
            cell.set_text_props(weight='bold')
            if col >= 5 and row == 2 and col != index_yerlesim: cell.set_edgecolor('white') 
        if row == 1 or row == 3:
            cell.set_text_props(color='red', weight='bold')
            if col >= 5 and row == 3:
                 if col != index_yerlesim: 
                     cell.set_edgecolor('white')
                     cell.get_text().set_text("")
        if col == index_yerlesim:
            if row == 2: cell.set_text_props(color='black', weight='bold'); cell.set_edgecolor('black') 
            if row == 3: cell.set_text_props(color='blue', weight='bold', size=14); cell.set_edgecolor('black')
    plt.title(f"{ogrenci_adi} - Sınav Sonuç Tablosu", y=1.05)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close()
    buf.seek(0)
    return buf

def pdf_den_veri_oku_standart(uploaded_file):
    # Öğrenci verilerini okuma (Hata toleranslı)
    data = []
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        cleaned_row = [str(item) for item in row if item is not None]
                        if len(cleaned_row) < 3: continue
                        
                        # Cevap Stringi Bulma
                        cevap_adaylari = [
                            s for s in cleaned_row 
                            if len(str(s)) > 15 
                            and not str(s).replace(" ","").isdigit()
                            and "CEVAP" not in str(s).upper()
                        ]
                        if not cevap_adaylari: continue
                        cevap_raw = cevap_adaylari[-1]
                        
                        # Kitapçık Türü Bulma
                        kitapcik = "A" # Varsayılan
                        clean_raw = cevap_raw.replace('\n', ' ').strip().upper()
                        if clean_raw.endswith(" A") or clean_raw.endswith("A"): kitapcik = "A"
                        elif clean_raw.endswith(" B") or clean_raw.endswith("B"): kitapcik = "B"
                        
                        # İsim Bulma
                        isim_adaylari = [
                            s for s in cleaned_row 
                            if s != cevap_raw 
                            and len(str(s)) > 3
                            and not any(char.isdigit() for char in str(s))
                            and "CEVAP" not in str(s).upper()
                        ]
                        ad_soyad = "Öğrenci"
                        if isim_adaylari:
                            ad_soyad = max(isim_adaylari, key=len).replace('\n', ' ')

                        # Cevap Temizliği (Sadece harfler)
                        cevap_sadece_harf = ''.join(filter(str.isalpha, cevap_raw.upper()))
                        
                        # Sondaki kitapçık harfini kesme (Eğer 25'ten uzunsa ve son harf kitapçık türüyle aynıysa)
                        if len(cevap_sadece_harf) > 25:
                            # Son harf kitapçık türüyse at
                            if cevap_sadece_harf.endswith(kitapcik):
                                cevap_sadece_harf = cevap_sadece_harf[:-1]
                        
                        if len(cevap_sadece_harf) >= 10:
                             data.append([ad_soyad, kitapcik, cevap_sadece_harf])
    except Exception:
        pass
    return data

# --- ARAYÜZ AKIŞI ---

# Dosya yükleyici en üstte olsun ki veriyi hemen okuyabilelim
uploaded_file = st.file_uploader("Sınav Sonuç PDF Dosyasını Yükleyin", type="pdf")

# Varsayılan anahtarlar (Boş)
default_keys = {"A": "", "B": ""}

if uploaded_file is not None:
    # Dosya yüklenince otomatik bulmayı dene
    found_keys = cevap_anahtarlarini_bul(uploaded_file)
    # Bulunanları varsayılan yap (Bulamazsa boş kalır)
    if found_keys["A"]: default_keys["A"] = found_keys["A"]
    if found_keys["B"]: default_keys["B"] = found_keys["B"]

# --- YAN MENÜ (KONTROL PANELİ) ---
st.sidebar.header("🔑 Cevap Anahtarları")
st.sidebar.info("Sistem aşağıdakileri otomatik buldu. Yanlışsa lütfen kutucukların içini düzeltin.")

# Buradaki 'value' parametresi otomatik dolacak
final_key_A = st.sidebar.text_input("A Kitapçığı", value=default_keys["A"]).strip().upper()
final_key_B = st.sidebar.text_input("B Kitapçığı", value=default_keys["B"]).strip().upper()

# Kullanılacak Nihai Anahtarlar
keys = {"A": final_key_A, "B": final_key_B}

# --- İMZA ---
imza_metni = "Öğr.Gör. Berkay AKSU tarafından kişisel kullanım amaçlı oluşturulmuştur. Hatalı sonuç verebilir lütfen kontrol edin. Oluşan sonuçlar ve kontrolü tamamen kullanan kişinin sorumluluğundadır."
st.sidebar.markdown("---")
st.sidebar.warning(imza_metni)

# --- ANA İŞLEM ---
if uploaded_file is not None:
    # Kullanıcı anahtarları kontrol etsin diye uyarı
    if not keys["A"] and not keys["B"]:
        st.warning("⚠️ Otomatik cevap anahtarı bulunamadı! Lütfen sol menüden cevapları elle giriniz.")
    else:
        st.write("---")
        # Öğrencileri oku (Dosya pointer'ını başa almamız gerekebilir, pdfplumber halleder ama garanti olsun)
        # Streamlit'te uploaded_file her çağrıldığında baştan okunabilir, sorun yok.
        
        ogrenciler = pdf_den_veri_oku_standart(uploaded_file)
        
        if len(ogrenciler) > 0:
            st.success(f"✅ Toplam **{len(ogrenciler)}** öğrenci tespit edildi.")
            
            # Hızlı kontrol tablosu
            with st.expander("Öğrenci Listesini ve Algılanan Cevapları Gör"):
                st.write("Aşağıdaki listede 'Algılanan Cevap' sütunu ile sol menüdeki anahtar eşleşiyor mu kontrol edebilirsiniz.")
                st.table([{"Ad": x[0], "Kitapçık": x[1], "Algılanan Cevap": x[2]} for x in ogrenciler[:5]])

            if st.button("Sonuçları Hesapla ve İndir"):
                # Anahtarları son kez kontrol et (Kullanıcı değiştirmiş olabilir)
                current_keys = {"A": final_key_A, "B": final_key_B}
                
                progress_bar = st.progress(0)
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, (ad, ktp, cvp) in enumerate(ogrenciler):
                        # Hesapla
                        puanlar = puan_hesapla(cvp, ktp, current_keys)
                        # Çiz
                        img_buf = tablo_olustur(ad, puanlar)
                        # Kaydet
                        dosya_adi = f"{ad.replace(' ', '_')}.png"
                        zf.writestr(dosya_adi, img_buf.getvalue())
                        
                        progress_bar.progress((i + 1) / len(ogrenciler))
                
                zip_buffer.seek(0)
                st.balloons()
                st.download_button(
                    label="📥 Sonuçları ZIP Olarak İndir",
                    data=zip_buffer,
                    file_name="Sinav_Sonuclari.zip",
                    mime="application/zip"
                )
        else:
            st.error("Öğrenci verisi okunamadı. PDF formatı desteklenmiyor olabilir.")

# Sayfa sonu imzası
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8em;'>{imza_metni}</div>", unsafe_allow_html=True)
