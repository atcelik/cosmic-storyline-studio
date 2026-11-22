# Görselleri tek seferde indirme (sunucuda)

İlk kez (paketi açtığın klasörde):
    bash scripts/setup_server.sh          # bir kez; TTS gerekmiyorsa: SKIP_TTS=1 bash scripts/setup_server.sh
    . .venv/bin/activate

Deneme listesi (Enceladus, 11 büyük NASA/JPL görseli):
    make assets EP=enceladus_test

Bitince ekranda "Upload these to Claude" altında zip dosya(lar)ı yazar, örneğin:
    episodes/enceladus_test/enceladus_test_assets_part01.zip
Bu zip'i Claude'a yükle. Her zip'in içinde kontrol sayfası (contact_sheet) ve rapor (report.json) da var.

Bir bölüm için:
    make assets EP=ep01          # Claude'un yazdığı asset_manifest.json listesini indirir
    make assets-search EP=ep01   # + episode.json'da sadece search_query olan planlar için NASA arşivinde arar (plan başına 2 aday)

Yarıda kesilirse aynı komutu tekrar çalıştır: bitenler atlanır, kalanlar indirilir.
Zip 400 MB'den büyükse otomatik bölünür (part01, part02 ...). Hepsini yükle.
Orijinal büyük dosyalar sunucuda episodes/<bölüm>/assets/originals/ içinde kalır.
