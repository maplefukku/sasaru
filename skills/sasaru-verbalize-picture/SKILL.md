---
name: sasaru-verbalize-picture
description: "Apply while watching a reference video to fill a playbook draft. For each second, record what is on screen, what entered or left the frame, what the camera is doing, and what a viewer could point at. The agent judges. No command. Do not copy source sentences. Separate what was seen from inference. Writes verbalization.picture only."
disable-model-invocation: true
---

# sasaru-verbalize-picture

動画を見ているあいだに、絵だけを秒で言葉にする細い流れである。役ではない。ルーターはこれを振り分けない。判断はエージェントが持つ。新しいコマンドは無い。スクリプトも置かない。

スキーマ、ルーター、テンプレート、ほかのスキル、設計の文書は変えない。この流れが書くのは、playbook の下書きにある `verbalization.picture` だけである。ほかの鍵は変えない。スキーマがこの鍵をまだ持っていなくても、下書きには書く。検査が知らない鍵で落ちても、鍵を消したり検査を直したりしない。

## Start

手元の動画を、一秒ずつ見る。シートが既にあるなら、帯の秒を手がかりにしてよい。書く中身は、自分が見たことで決める。計測スクリプトの数で、この欄を埋めない。

下書きは `<home>/work/<id>/<id>.md`。無いときは playbook を新しく作らず、下書きが無いと返して止まる。

## 一秒

秒 `s` は、時刻 `s` 秒の画である。`s` は 0 から、尺を超えない最後の整数秒まで。一秒も飛ばさない。端の秒に画があれば、それも書く。

その秒について、この順で書く。

1. 画面にあるもの。
2. フレームに入ったものと、出たもの。直前の秒と比べる。無ければ「なし」。
3. カメラがしていること。
4. 見る人が指させそうなもの。

0 秒は直前が無い。出入りは「なし」とし、最初の画は画面の欄に書く。

切り替わりの秒は、出たものを直前の画、入ったものを今の画として書く。カメラには、別の画へ切り替わったと書く。

カメラが動いて物が端から出入りしたときも、出入りとカメラを両方書く。同じ出来事を、意図の説明にすり替えない。

## 見たことと推論

見たことは `seen` にだけ書く。推論は `inferred` にだけ書く。一つの文に混ぜない。

見たこと。その秒の画に見えた物、位置、色、大きさの印象。直前の秒との出入り。画面の動きとして見えたこと（止まっている、大きくなった、小さくなった、横へ流れた、縦へ流れた、揺れた、別の画に切り替わった）。

推論。見る人が指させそうなもの。カメラの操作名や機材を、見えた変化から推測するとき。その推測は `seen.camera` に書かず、`inferred.camera` に分ける。推測が無ければ `inferred.camera` は書かない。

数は測らない。目で読んだ値を、測った数として扱わない（**sasaru-principle-measure-or-label**）。この流れは `evidence` を動かさない。

## 文言を写さない

画面の字、声、看板の文を下書きに写さない。一語の引用もしない（**sasaru-principle-describe-the-form-not-the-work**）。字は、位置、色、縁、一枚か、差し替わったか、で書く。作者名、アカウント名、元の題も書かない。

音、心理、商品の置き場、台本は書かない。

## 下書きの形

`verbalization.picture` は秒の配列である。

```yaml
verbalization:
  picture:
    - sec: 0
      seen:
        onScreen: その秒の画面に見えたもの
        entered: 直前の秒に無く、この秒のフレームに入ったもの。無ければ なし
        left: 直前の秒にあり、この秒のフレームから出たもの。無ければ なし
        camera: 画面の動きとして見えたこと。止まっていれば 止まっている
      inferred:
        pointAt: 見る人が指させそうなもの。決められなければ 決められない
```

`seen` に推論を書かない。`inferred.pointAt` は、指が止まりそうなものを短い順で書く。元の文から物の名前を取らない。色、形、位置で書く。画面に指の先が無い秒も空にせず、どこが指の先になりそうか、または「決められない」と書く。

## Outputs

- 下書きの `verbalization.picture` だけ。
- 返答には、埋めた秒の範囲と、推論に残した項目だけを書く。元の文は書かない。
