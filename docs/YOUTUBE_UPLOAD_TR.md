# YouTube otomatik yükleme kurulumu (bir kerelik, tabletten)

Sonuç: Actions sekmesinden "upload-youtube" çalıştırınca bitmiş video YouTube'a **özel** yüklenir. Sen Studio'dan "Herkese açık" yaparsın.
Not: Google, onaylanmamış API projelerinin videolarını zaten özel tutar. Bu yüzden son adım (yayına alma) elle kalır.

## 1. Google Cloud projesi
1. console.cloud.google.com → yeni proje (ad: cosmic-uploader). Kanalın bağlı olduğu Google hesabıyla gir.
2. APIs & Services → Library → **YouTube Data API v3** → Enable.
3. OAuth consent screen → External → ad ve e-postanı yaz → Publishing status: **In production** (Testing'de kalırsa token 7 günde ölür).
4. Credentials → Create credentials → OAuth client ID → **Web application** → Authorized redirect URI: `https://developers.google.com/oauthplayground`
5. Client ID ve Client secret'ı kopyala.

## 2. Refresh token
1. developers.google.com/oauthplayground
2. Sağ üst dişli → **Use your own OAuth credentials** → ID ve secret'ı yapıştır.
3. Scope kutusuna yaz: `https://www.googleapis.com/auth/youtube.upload` → Authorize APIs.
4. Hesap seçiminde **Cosmic Storyline kanalını** seç, izin ver.
5. "Exchange authorization code for tokens" → **Refresh token**'ı kopyala.

## 3. GitHub secret'ları
Repo → Settings → Secrets and variables → Actions → New repository secret. Üç tane:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

Bu değerleri asla dosyaya yazma (repo public).

## 4. Kullanım
Actions → upload-youtube → Run workflow → release tag (ör. `enceladus_trial_v2-r12`) ve başlığı yaz → Run.
Log'un sonunda Studio linki çıkar. Altyazıyı (`captions.srt`) Studio'dan elle ekle.
