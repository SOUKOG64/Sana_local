[app]

title = Арт-Фехтование
package.name = artfencing
package.domain = ru.artfencing
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,ttf,txt
source.exclude_dirs = .buildozer,bin,build,dist,__pycache__,.venv,venv
version = 1.0.0
requirements = python3,kivy==2.3.0,sqlite3
orientation = portrait
fullscreen = 0

android.minapi = 23
android.api = 33
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a


# Проверенная связка с Kivy 2.3.0, Python 3.11 и NDK r25b
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 0
