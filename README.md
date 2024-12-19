# PTCGP 自動刷

## 警告

- 不要在有真賬號的模擬器上使用，你的賬號會消失！

## 功能

- 不斷地自動開新賬號刷包，直到中了想要的卡為止。

## 需求

- LDPlayer 9.1.32.0(64)
- Python 3.13.1

## 限制

- 只支援繁體中文

## 使用

1. 打開雷電多開器。建立新模擬器，例如名為"PTCGP-Gacha-00"。畫面橫 300 直 400 DPI 120，中文。打開 ADB 到本地。
2. 啟動新模擬器。
3. 安裝 PTCGP，亦確保沒有登入任何賬號。
4. 手動刷一次首抽。包括第一包自選，第二包制超夢，第三四包自選，第五包 12 沙漏。確認下載更新完成，也略過 Google Play 的問卷。完成後刪賬，回到標題畫面。
5. 修改 config.yaml
6. 打開命令提示字元並 cd 到本資料夾。
<pre>
python -m venv venv
.\venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel setuptools
python -m pip install --upgrade numpy opencv-python pyyaml

python gacha_loop.py config.yaml
</pre>

## 示範

https://www.youtube.com/watch?v=_-laRxczYmo
