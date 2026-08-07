[app]
title = Swim Start Trainer
package.name = swimstarttrainer
package.domain = org.gdel

source.dir = .
source.include_exts = py,ogg,png,jpg,kv,atlas

# docs/ is the web version — its audio and icons match the include filters, so
# without this the whole PWA gets bundled inside the APK for nothing.
source.exclude_dirs = docs,bin,.buildozer,.github,.git,__pycache__,.venv-build
source.exclude_patterns = build-local.sh,*.md

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
# arm64 only: every Android phone since ~2017 is arm64-v8a, and building the
# second architecture doubles build time for no practical gain. Add
# armeabi-v7a back if you need to support genuinely old hardware.
android.archs = arm64-v8a

# Pin python-for-android to a known-good release. Its current master branch
# hardcodes the on-device Python version at 3.14.2, and p4a's own internal
# bootstrap build for that version is currently broken (its pip bootstrap
# fails with "cannot import name 'BuildDependencyInstallError'"). v2024.01.21
# is the last release confirmed to default to Python 3.11, which is stable.
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
