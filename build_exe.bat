python -c "import datetime; print(datetime.datetime.now().strftime('%%Y%%m%%d'))" > tmp-yyyymmdd.txt
set /p YYYYMMDD=<tmp-yyyymmdd.txt

rmdir /q /s build
rmdir /q /s dist

if exist build\ (
  echo "build EXISTS"
  exit 1
)
if exist dist\ (
  echo "dist EXISTS"
  exit 1
)

pyinstaller --add-data="res;res" --add-data="default.yaml;." gacha_loop.py

copy config.yaml dist\gacha_loop\config.yaml

cd dist
"D:\Program Files\7-Zip\7z.exe" a -tzip gacha_loop-%YYYYMMDD%.zip gacha_loop
