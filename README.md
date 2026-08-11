# Instalasi
1. Upload index.html, berita.json, dan folder admin ke root repository GitHub.
2. Hubungkan repository ke Cloudflare Pages.
3. Tambahkan infocileungsi.web.id sebagai Custom Domain.
4. Di Cloudflare Zero Trust > Access > Applications, lindungi domain/path: infocileungsi.web.id/admin/*. Policy Allow hanya email Anda.
5. Buat GitHub Fine-grained Personal Access Token: Repository access = Only select repositories > ebonispace-hue/sekitar; Repository permissions > Contents = Read and write.
6. Buka https://infocileungsi.web.id/admin/ lalu masukkan token. Token tidak disimpan dalam file.
