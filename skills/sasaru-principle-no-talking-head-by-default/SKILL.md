---
name: sasaru-principle-no-talking-head-by-default
description: "Apply when choosing or writing a production route. A route that puts a generated or real person speaking to camera (R2V performer, lip sync, the maker's face) is never the default. It runs only when the maker asks for it by name for this cut."
disable-model-invocation: true
---

# No Talking Head by Default

喋る人のルート（`r2v-talking`、`talkingHead: true` のルート）は playbook に書いてよい。既定にはしない。スキーマがそれを止める。

参照動画が喋る人の型でも、制作は字幕中心、画面録画、コードのモーショングラフィックス、手元や物の映像のどれかに置き換えて既定ルートを書く。置き換えで失う要素は「なぜ伸びるか」に書く。

理由は費用と、口の同期の精度の上限である。
