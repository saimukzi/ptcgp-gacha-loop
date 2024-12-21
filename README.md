# PTCGP 自動刷

## 警告

- 不要在有真帳號的模擬器上使用，你的帳號會被刪除！

## 功能

- 不斷地自動開新帳號刷包，直到中了想要的卡為止。

## 需求

- Windows 作業系統
- [LDPlayer 9.1.32.0(64)](https://www.ldplayer.tw/)
- [Python 3.13.1](https://www.python.org/)

## 限制

- 只支援繁體中文

## 使用

1. [下載 gacha_loop-20241221-213005.zip](https://mega.nz/file/RVc21B5Z#hFwFfAIzEtlreutR1ZX8k8DFfSIkQGZZ0SjjVd8Q4Fw)
2. 打開雷電多開器。建立新模擬器，例如名為"PTCGP-Gacha-00"。畫面橫 300 直 400 DPI 120，中文。打開 ADB 到本地。
3. 啟動新模擬器。
4. 在模擬器安裝 PTCGP，亦確保沒有登入任何帳號。
5. 修改 config.yaml
6. 執行 gacha_loop.exe

## 示範

https://www.youtube.com/watch?v=_-laRxczYmo (舊版本)

## config.yaml

TARGET_PACK: 抽甚麼包
- charizard: A1 噴火龍
- mewtwo: A1 超夢
- pikachu: A1 皮卡丘
- mew: A1a 夢幻

TARGET_CARD_LIST: 抽到甚麼卡的時候會停下來，卡片代號請參考 res\card 資料夾

STOP_AT_RARE_PACK: 抽到神包停下來

USERNAME: 新帳號的名字，{IDX}是三位數流水號

LD_EMU_NAME: 模擬器名稱

LDPLAYER_PATH: 雷電模擬器的安裝資料夾，「\\」符號要寫成「\\\\」

DEBUG_MODE: 除錯資訊輸出到 log

ENABLE_BACKUP_SEED: 備份遊戲在沒有帳號時的狀態，以在卡死時回朔到遊戲初始狀態，預設為開啟(true)

## FAQ

- [FAQ](FAQ.md)
- [Not FAQ](NotFAQ.md)
- [FAQ is LOVE](https://www.youtube.com/watch?v=kSr5bjoKU9I)

## Links

- [This project](https://github.com/saimukzi/ptcgp-gacha-loop)

## 支援

- [西木子DC](https://discord.gg/kdZ5fQxP)
- 電郵 saimukzi@hiauntie.com ，請附上 log 資料夾 zip 及 var\\instances\\default\\tmp-screencap.png 。

## 感謝

- [Game asset source](https://x.com/ElChicoEevee/status/1839298287012294867)
- [哲盟BiiMiu](https://www.youtube.com/@BiiMiu)
