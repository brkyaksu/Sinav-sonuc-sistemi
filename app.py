import streamlit as st
import pdfplumber
import matplotlib.pyplot as plt
import zipfile
import io
import google.generativeai as genai
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Akıllı Sınav Okuma (AI)", layout="centered")

# --- BAŞLIK ---
st.title("🧠 Yapay Zeka Destekli Sınav Okuma")
st.info("Bu sistem, klasik kod yerine Google Gemini yapay zekasını kullanarak PDF'i analiz eder. Hata payı çok düşüktür.")

# --- YAN MENÜ ---
st.sidebar.header("🔑 Ayarlar")

# API Key Girişi
api_key = st.sidebar.text_input("Google Gemini API Key", type="password", help="aistudio.google.com adresinden alacağınız anahtar.")

# İmza
imza_metni = "Öğr.Gör. Berkay AKSU tarafından kişisel kullanım amaçlı oluşturulmuştur. Hatalı sonuç verebilir lütfen kontrol edin. Oluşan sonuçlar ve kontrolü tamamen kullanan kişinin sorumluluğundadır."
st.sidebar.markdown("---")
st.sidebar.warning(imza_metni)

# --- FONKSİYONLAR ---

def gemini_ile_analiz_et(text_data, api_key):
    """
    Metni Gemini'ye gönderir ve JSON formatında öğrenci listesi ister.
    """
    genai.configure(api_key=api_key)
    
    # Model Ayarları
    generation_config = {
        "temperature": 0.1, # Yaratıcılığı kıs, doğruluğu artır
        "response_mime_type": "application/json",
    }
    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Hızlı ve ekonomik model
        generation_config=generation_config,
    )

    prompt = f"""
    Sen uzman bir sınav veri analistisin. Aşağıdaki metin bir PDF sınav sonuç belgesinden alınmıştır.
    
    GÖREVLERİN:
    1. Metnin içindeki "Cevap Anahtarı" satırlarını bul. Genelde 'CevapAnahtarı' yazar ve sonunda A veya B kitapçık türü olur.
    2. Öğrenci satırlarını bul. Her satırda İsim, Kitapçık Türü (A veya B) ve Cevap Şıkları (yaklaşık 25 harf) bulunur.
    3. Başlıkları (Örn: "Ad Soyad", "Öğr. No", "Sıra") KESİNLİKLE öğrenci olarak alma.
    4. Sadece gerçek öğrenci verilerini çıkar.

    ÇIKTI FORMATI (JSON):
    {{
        "cevap_anahtarlari": {{
            "A": "BURAYA_A_ANAHTARI_HARFLERI",
            "B": "BURAYA_B_ANAHTARI_HARFLERI"
        }},
        "ogrenciler": [
            {{
                "ad_soyad": "OGRENCI_ADI",
                "kitapcik": "A",
                "cevaplar": "OGRENCI_CEVAPLARI"
            }}
        ]
    }}

    İŞTE ANALİZ EDECEĞİN METİN:
    {text_data}
    """

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Yapay zeka bağlantı hatası: {e}")
        return None

def puan_hesapla(cevap_string, kitapcik, keys):
    cevap = str(cevap_string).replace(" ", "").upper()
    if kitapcik not in keys or not keys[kitapcik]: return [0] * 25

    dogru_cevaplar = keys[kitapcik].replace(" ", "").upper()
    
    if len(cevap) < 25: cevap = cevap + "X" * (25 - len(cevap))
    cevap = cevap[:25]
    
    puanlar = []
    for i in range(25):
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
                     cell.set_edgecolor('white'); cell.get_text().set_text("")
        if col == index_yerlesim:
            if row == 2: cell.set_text_props(color='black', weight='bold'); cell.set_edgecolor('black') 
            if row == 3: cell.set_text_props(color='blue', weight='bold', size=14); cell.set_edgecolor('black')

    plt.title(f"{ogrenci_adi} - Sınav Sonuç Tablosu", y=1.05)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    plt.close()
    buf.seek(0)
    return buf

# --- ARAYÜZ AKIŞI ---
uploaded_file = st.file_uploader("PDF Dosyasını Yükleyin", type="pdf")

if uploaded_file and not api_key:
    st.warning("⚠️ Lütfen önce sol menüden Gemini API Key giriniz.")

if uploaded_file and api_key:
    st.write("⏳ PDF metne dönüştürülüyor ve yapay zekaya gönderiliyor...")
    
    # PDF'i Metne Çevir
    full_text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
    
    # Gemini'ye Gönder
    ai_result = gemini_ile_analiz_et(full_text, api_key)
    
    if ai_result:
        keys = ai_result.get("cevap_anahtarlari", {})
        ogrenciler = ai_result.get("ogrenciler", [])
        
        # "Ad Soyad" isimli sahte öğrenci varsa filtrele (Ekstra güvenlik)
        ogrenciler = [o for o in ogrenciler if "Ad Soyad" not in o["ad_soyad"] and "Öğrenci" not in o["ad_soyad"]]
        
        if not keys.get("A") and not keys.get("B"):
             st.error("Cevap anahtarı PDF içinde bulunamadı.")
        
        # Sonuçları Göster
        st.success(f"✅ Analiz Başarılı! {len(ogrenciler)} öğrenci bulundu.")
        st.write(f"🔑 **Algılanan Anahtarlar:** A: `{keys.get('A', 'Yok')}` | B: `{keys.get('B', 'Yok')}`")
        
        with st.expander("Öğrenci Listesini Kontrol Et"):
            st.dataframe(ogrenciler)

        if st.button("Sonuçları Oluştur ve İndir"):
            progress_bar = st.progress(0)
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, ogr in enumerate(ogrenciler):
                    puanlar = puan_hesapla(ogr["cevaplar"], ogr["kitapcik"], keys)
                    img_buf = tablo_olustur(ogr["ad_soyad"], puanlar)
                    
                    dosya_adi = f"{ogr['ad_soyad'].replace(' ', '_')}.png"
                    zf.writestr(dosya_adi, img_buf.getvalue())
                    progress_bar.progress((i + 1) / len(ogrenciler))
            
            zip_buffer.seek(0)
            st.download_button(
                label="📥 ZIP İndir",
                data=zip_buffer,
                file_name="AI_Sinav_Sonuclari.zip",
                mime="application/zip"
            )

# --- ALT İMZA ---
st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8em;'>{imza_metni}</div>", unsafe_allow_html=True)
