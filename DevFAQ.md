# 開發 FAQ

## main

程式的 main 在 gacha_loop.py

## git branch

以下是西木子在 saimukzi/ptcgp-gacha-loop 中 branch 的意義。其他人不需要跟從，但理解了的話能知道西木子在想甚麼。

- main: 穩定的版本，可當作 release 版。新手進場也推薦試這個。
- fix: 針對 main 的錯誤修正，不會包含新功能。
- dev: 走在 Roadmap 發展的大道。想嘗鮮的可以試這個，但有點危險。
- testing: 準備進入 main 的版本。西木子會先把代碼送到 testing，建了 exe 包，再放進測試電腦跑大半天。沒太大問題的話，才送到 main，然後之前建的那個 exe 會當成發行版推出去。

## 程式運作原理 loop

1. 從模擬器獲取畫面 ldagent.screencap()
2. 從畫分析畫面狀態 state_list.get_state(img) ，狀態是指遊戲在標題畫面，抽包畫面，還是在顯示使用條款。參考 res\\state 資料夾。
3. 根據遊戲的狀態做相應的動作。
4. 回到 1

## 刷帳號流程

1. 開新帳號
2. 第一抽超夢包，必中嘎啦嘎啦ex。因為不會分享這個包，所以選甚麼也不會影響。
3. 第二抽超夢包。這是 PTCGP 強迫的，我沒辦法。輸出隨機，可能出二星，可能會分享。
4. 第三四抽自選包。輸出隨機，可能出二星，可能會分享。
5. 第五抽燒12漏斗。輸出隨機，可能出二星，可能會分享。因為介面搞怪，很容易會抽和第四抽相同的包。只要操作一下就可以抽不同的包。但這個挖壙器沒需要換包。
6. 刪帳
7. 回到 1

## 畫面狀態偵測

res\\state 資料夾

- xxx.min.png: 畫面像素 RGB 最小值
- xxx.max.png: 畫面像素 RGB 最大值
- xxx.svmin.png: 畫面由 RGB 轉成 HSV，無視 H 只計算 SV。此為最小 SV 值。
- xxx.svmax.png: 畫面由 RGB 轉成 HSV，無視 H 只計算 SV。此為最大 SV 值。
- xxx.mask.png: 偵測器需要留意和無視的部份。不透明為留意，透明為無視。

另外，由於一些畫面狀態太相似，可能會誤判，因此有 fix 機制

res\\state\\fix 資料夾

- state0.state1.zzz.png

state0 為之前判定的狀態，如果畫面符合圖像，狀態就會判定為 state1。

## 畫面狀態捕獲

打開模擬器，關閉挖壙機，執行：
<pre>
python state_capture.py config.yaml state_name
</pre>
新畫面狀態會出現在 res\\state\\state_name.xxx.png

如果要重覆捕獲，執行：
<pre>
python state_capture.py config.yaml --append state_name
</pre>

mask 檔案自己手動製作。可以複製 state_name.max.png 為 可以複製 state_name.mask.png ，然後手動把無視的部份變成透明。

min/max/svmin/svmax 必須不帶 alpha，mask 必須帶 alpha

## var

- var\\backup: 遊戲在無帳號狀態下的模擬器備份，可達 4GB。
- var\\instance\\xxx: xxx 為 config.yaml 的 INSTANCE_ID。
- var\\instance\\xxx\\tmp-screencap.png: 模擬器畫面
- var\\instance\\xxx\\user_idx: 未來新帳號流水號，數值 0-9999 。
