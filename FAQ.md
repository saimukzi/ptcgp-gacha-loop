# FAQ

## 如何令程式只停在神包上？

參考 config-god-pack.yaml 的設定。
- HANDLE_WONDER_TARGET_PACK, HANDLE_NONWONDER_TARGET_PACK 設為 "IGNORE"
- HANDLE_WONDER_RARE_PACK, HANDLE_NONWONDER_RARE_PACK, HANDLE_WONDER_TARGET_RARE_PACK, HANDLE_NONWONDER_TARGET_RARE_PACK 設為 "STOP"

## 如何多開？

可以執行多個 ptcgp-gacha-loop 實現

1. 下載第二個 ptcgp-gacha-loop
2. 在該資料夾的 config.yaml ，把 LD_EMU_NAME 設為另一個模擬器的名稱
3. 同時執行新舊 ptcgp-gacha-loop

另外，在「多開優化設定」把 FPS 調低，反而會令刷包器變得不穩定。
