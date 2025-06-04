[app]
title = Mix CD Scrobbler
package.name = mixcdscrobbler
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 0.1
requirements = python3,kivy,requests,urllib3,certifi

[buildozer]
log_level = 2

[app:android]
# Android specific
bootstrap = sdl2

# Accept all Android SDK licenses
android.accept_sdk_license = True

# Use specific API levels that work better with GitHub Actions
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 25b

# Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Force specific architectures to avoid compilation issues
android.archs = arm64-v8a

# Skip problematic recipes that cause libffi issues
android.skip_update = False
android.gradle_dependencies = 

# Use release mode for more stable compilation
android.release_unsigned = True

[app:android.gradle]
android.gradle_dependencies =
