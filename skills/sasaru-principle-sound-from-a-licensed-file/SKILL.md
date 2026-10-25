---
name: sasaru-principle-sound-from-a-licensed-file
description: "Apply when adding BGM or sound effects, and when exporting. Every audible sound comes from a separate file whose license is recorded next to the cut. Never use the reference video's audio or a stem separated from it, and strip audio returned by generation APIs."
disable-model-invocation: true
---

# Sound from a Licensed File

聞こえる音は、声（自分の声か TTS）と、ライセンスを記録した別ファイルの曲と効果音だけにする。編集記録に、各音のファイルパスとライセンスを書く。

参照の mp4 を音の入力にしない。生成 API が音を付けて返したクリップは、映像だけにしてから組む。

動画の中で使う許諾と、ファイルを公開する許諾は別である。曲ファイルはリポジトリにコミットしない。
