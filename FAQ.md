# FAQ

## .\venv\Scripts\activate.bat 出現錯誤

...

## 如何令程式只停在神包上？

參考 config-god-pack.yaml 的設定。
- TARGET_CARD_LIST 設為空列 []
- STOP_AT_RARE_PACK 設為 true

## 如何多開？

可以執行多個 ptcgp-gacha-loop 實現

1. 下載第二個 ptcgp-gacha-loop
2. 在該資料夾的 config.yaml ，把 LD_EMU_NAME 設為另一個模擬器的名稱
3. 同時執行新舊 ptcgp-gacha-loop
