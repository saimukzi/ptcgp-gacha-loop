python -c "import datetime; print(datetime.datetime.now().strftime('%%Y%%m%%d%%H%%M%%S'))" > tmp-yyyymmddhhmmss.txt
set /p YYYYMMDDHHMMSS=<tmp-yyyymmddhhmmss.txt
set YYYYMMDD=%YYYYMMDDHHMMSS:~0,8%
set HHMMSS=%YYYYMMDDHHMMSS:~8,6%

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

git diff --exit-code
if %ERRORLEVEL% NEQ 0 (
  echo "GIT DIFF ERROR"
  exit 1
)

git tag zb-%YYYYMMDD%-%HHMMSS%

pyinstaller --add-data="res;res" --add-data="default.yaml;." gacha_loop.py

echo %YYYYMMDD%-%HHMMSS% > dist\gacha_loop\_internal\version.txt
copy config.yaml dist\gacha_loop\config.yaml
copy config-god-pack.yaml dist\gacha_loop\config-god-pack.yaml
copy help.txt dist\gacha_loop\help.txt

pushd dist
"D:\Program Files\7-Zip\7z.exe" a -tzip gacha_loop-%YYYYMMDD%-%HHMMSS%.zip gacha_loop
popd
