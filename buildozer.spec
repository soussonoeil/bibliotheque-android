[app]
title = Ma bibliothèque
package.name = mabiblio
package.domain = org.debutant
source.dir = .
source.include_exts = py,kv,png,jpg,json,atlas
source.exclude_dirs = .github, apercus
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
log_level = 2
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.private_storage = True
android.presplash_color = #090a0d
# Kivy 2.3 n'est pas compatible avec Python 3.14 : on épingle la version de
# python-for-android qui utilise Python 3.11.5 (dernière compatible Kivy 2.3).
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
