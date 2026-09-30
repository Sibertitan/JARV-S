# JARVIS Android client

This source project connects to the existing JARVIS desktop/LAN server. The Gemini API key stays in the desktop app's private `config/api_keys.json`; it is never compiled into the APK.

## Connect

1. Start JARVIS on the Windows or Linux computer.
2. Keep the phone and computer on the same Wi-Fi network.
3. In JARVIS, copy the displayed phone address (port `8765`) and connection code into this app.
4. Tap **Bağlan**, then send a message.

The client calls the authenticated `/ping` and `/ask` endpoints. It does not need a server, account, or paid hosting.

## Build

Open this folder in Android Studio, or run `gradle assembleDebug` with Gradle 8.9 and Android SDK Platform 35 installed. The debug APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

The current client uses cleartext HTTP to reach the desktop app on a trusted local network, matching JARVIS's existing LAN server. Do not forward port `8765` to the public internet.
