rmdir /q /s build
rmdir /q /s dist

pyinstaller --add-data="res;res" --add-data="default.yaml;." gacha_loop.py

copy config.yaml dist\gacha_loop\config.yaml
