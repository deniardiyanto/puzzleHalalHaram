[app]
title = Puzzle Halal Haram
package.name = puzzlehalalharam
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,wav,kv,json
version = 0.1
requirements = python3,kivy==2.1.0
# if you need other modules: e.g. kivy-deps.sdl2,kivy-deps.glew
orientation = portrait

# icon and presplash
icon.filename = assets/icons/icon.png

# Android specifics
android.permissions = INTERNET
# increase apk size limit if needed
android.arch = armeabi-v7a

[buildozer]
log_level = 2
