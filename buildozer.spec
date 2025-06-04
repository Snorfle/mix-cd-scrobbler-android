name: Build Android APK

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-android:
    name: Build for Android
    runs-on: ubuntu-latest

    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Build with Buildozer
      uses: ArtemSBulgakov/buildozer-action@v1
      id: buildozer
      with:
        command: buildozer android debug
        buildozer_version: stable
      env:
        APP_ANDROID_ACCEPT_SDK_LICENSE: ${{ secrets.ANDROID_SDK_LICENSE || 'true' }}

    - name: Upload artifacts
      uses: actions/upload-artifact@v4
      with:
        name: mix-cd-scrobbler-apk
        path: ${{ steps.buildozer.outputs.filename }}
