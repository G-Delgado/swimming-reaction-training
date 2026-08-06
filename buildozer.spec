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

# Pin python-for-android to a known-good release. Its current master branch
# hardcodes the on-device Python version at 3.14.2, and p4a's own internal
# bootstrap build for that version is currently broken (its pip bootstrap
# fails with "cannot import name 'BuildDependencyInstallError'"). v2024.01.21
# is the last release confirmed to default to Python 3.11, which is stable.
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
