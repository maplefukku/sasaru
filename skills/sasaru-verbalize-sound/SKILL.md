---
name: sasaru-verbalize-sound
description: "Verbalize only the sound of local reference shorts into verbalization.sound. Use for a fine pass that marks where sound enters and drops, classes each span as hit, bed, voice, or silence, says what a hit is synced to, and says whether a silence is the hold before a payoff. Does not transcribe, copy lyrics, or add a command."
disable-model-invocation: true
---

# sasaru-verbalize-sound

参照の音だけを、細い順で読む。出力は `verbalization.sound` だけ。絵の切片、字の切片、カットの切片、シナリオ、動画は書かない。スキーマ、ルーター、テンプレート、他のスキル、設計の文書は変えない。新しい CLI は足さない。

秒の根拠に使ってよいのは、耳と、既に手元にある計測だけである。`sasaru-ingest` が書いた `audio.json`、および ffmpeg と ffprobe の既存の出力。この流れの道具としては登録しない。

## Start

一本ずつ、次の順で進める。渡された一覧にあってファイルが無いものは、名前だけを残し、区間は作らない。

1. 入りと落ち
2. 四つに分ける
3. ヒットの同期
4. 無音は回収の前の溜めか
5. `verbalization.sound` を書く

## Phase A: 入りと落ち

尺の上で、層がどこで入り、どこで落ちるかを秒で置く。

- 頭から鳴っていれば、入りは 0。
- 最終フレームまで鳴っていれば、落ちていない。終わりの秒は尺で、`dropped` は偽。
- 層が重なるときは、層ごとに入りと落ちを書く。
- 音量だけが下がってまだ聞こえるときは、その層の落ちにしない。下がりとして区間の中に秒を書く。
- 聞こえなくなったときだけ、その層は落ちたとする。

## Phase B: 四つに分ける

各区間の `class` は次のどれか一つ。

- `hit`。短い打撃。衝突、風切り、クリック、刺す音。ベッドではない。
- `bed`。絵の下に居続ける曲、または部屋の音。
- `voice`。人かキャラクターの声がいること。喋っているか歌っているかだけを書いてよい。言っている中身は書かない。
- `silence`。その層、またはミックス全体が無い区間。

同じ分類が同じ同期のまま続く区間は、一つにまとめてよい。分類か同期が変わった秒で割る。打撃が周期的なら、区間に `periodSec` を書く。打撃を一回ずつ全部は書かない。

## Phase C: ヒットは何に同期しているか

`hit` ごとに、同じ秒に見えた絵の出来事を `syncedTo` に一つ書く。参照の字は書かない。

- `cut`。カット。
- `caption-in`。字のカードが出る、または差し替わる。文は書かない。
- `zoom`。寄り、または引き。
- `contact`。物が物に当たる。
- `payoff`。回収の拍。
- `beat`。曲の拍だけで、上の絵の出来事には寄っていない。
- `other`。上のどれでもない。

同時に見えたことは `syncBasis: seen`。編集の意図は推論で、`syncBasis` を `seen` にしない。

## Phase D: 無音は回収の前の溜めか

`silence` ごとに `holdBeforePayoff` を書く。

- 真。ミックスが落ち、あとの回収の拍まで空のまま残る。空いていることが待ちである。
- 偽。息、打撃の無いカット、ベッドが声の下へ下がっただけの穴。回収を待っていない。

無音が一度も無いときは、`silence` の区間を作らない。溜めも作らない。

回収の拍が、渡された playbook のビートとして既にあるとき、無音の終わりとそのビートの頭が揃うかは見たことである。溜めと読むこと自体は推論で、`holdBasis` は `inferred`。

## Phase E: 書く

`verbalization.sound` だけを書く。見たことと推論を分ける（**sasaru-principle-measure-or-label**）。

- `seen`。耳で聞いたこと、または既存の計測がファイル上で出した入り、落ち、分類、周期、同時に見えた絵の出来事。計測なら、出したコマンドかファイルの名を `probe` に書く。
- `inferred`。目分量の秒、気分、溜めの読み、意図。

歌詞、セリフ、曲名、作者、元の音の写しは書かない（**sasaru-principle-describe-the-form-not-the-work**）。声の文字起こしをこの流れのために新しく走らせない。

```yaml
verbalization:
  sound:
    sourceFile: local-basename.mp4
    durationSec: 6.0
    durationBasis: seen
    probe: ffprobe
    spans:
      - tIn: 0.0
        tOut: 6.0
        entered: start
        dropped: false
        class: bed
        basis: seen
      - tIn: 0.4
        tOut: 5.6
        entered: mid
        dropped: true
        class: hit
        basis: seen
        syncedTo: caption-in
        syncBasis: seen
        periodSec: 0.5
        periodBasis: seen
      - tIn: 5.6
        tOut: 6.0
        entered: mid
        dropped: false
        class: silence
        basis: seen
        holdBeforePayoff: false
        holdBasis: inferred
```

- `entered` は `start` か `mid`。
- `syncedTo` と `syncBasis` は `hit` だけ。
- `periodSec` は、打撃が繰り返す区間だけ。
- `holdBeforePayoff` と `holdBasis` は `silence` だけ。
- 一行足すなら型の言葉だけ。歌詞にしない。

## Outputs

- ファイルごとの `verbalization.sound`。上の形。
- 一覧にあって無いファイルは、`sourceFile` と `missing: true` だけ。区間は空。
- 参照の音、歌詞、文字起こし、曲名、作者は含めない。
