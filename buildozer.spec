[app]
title = Swim Start Trainer
package.name = swimstarttrainer
package.domain = org.gdel

source.dir = .
source.include_exts = py,ogg,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions =

# (int) Target Android API, should be as high as possible.
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
