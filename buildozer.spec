[app]
title = Mix CD Scrobbler
package.name = mixcdscrobbler
package.domain = com.yourname.mixcdscrobbler
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy,requests
presplash.filename = %(source.dir)s/presplash.png
icon.filename = %(source.dir)s/icon.png
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
bin_dir = ./.buildozer/bin
