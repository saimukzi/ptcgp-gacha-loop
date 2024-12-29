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

## bot 在某個畫面卡住了

簡單的回答：試試把 config.yaml 的 STATE_DETECT_THRESHOLD 調高看看。

詳細的回答：

這個 bot 會看遊戲畫面來做動作。

但各電腦顯示的顏色 RGB 值可能會有不同。如果你畫面的顏色和我的偏差太大，就可能會認不出畫面，然後不會做動作。

而加大 STATE_DETECT_THRESHOLD 就可以令這個 bot 對 RGB 值的偏差更寬容。

不過，不要把這個值設太高。它可能會誤認為其他畫面，然後做錯動作。
