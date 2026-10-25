---
name: sasaru-principle-quote-before-you-spend
description: "Apply before any step that calls a paid generation API (image, T2V, I2V, V2V, R2V, TTS, lip sync). Get a quote first, set a cap, and send only after the maker approves that amount. Do not resend the same generation to retry a look."
disable-model-invocation: true
---

# Quote Before You Spend

有料の生成は、見積もり、上限、承認の順に進める。見積もりだけの実行は確認なしでよい。送信は承認のあとだけ。

同じ入力の生成をやり直して見た目を探さない。直すのは入力（プロンプト、参照、尺）で、直した理由を記録してから一回送る。

鍵は環境変数から読む。値をコマンド、ログ、playbook に書かない。
