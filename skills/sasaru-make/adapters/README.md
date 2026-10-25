# sasaru-make の生成メディアのアダプタ

make が有料の生成 API を呼ぶときの口。need ごとに一本のスクリプトがあり、どれも同じ口でプロバイダを差し替えられる。標準ライブラリだけで動く（PEP 723、`dependencies = []`）。

| need | スクリプト |
| --- | --- |
| `image-gen` | `image_gen.py` |
| `t2v` | `t2v.py` |
| `i2v` | `i2v.py` |
| `r2v` | `r2v.py` |
| `v2v` | `v2v.py` |
| `tts` | `tts.py` |

## 口

```bash
uv run --script adapters/<need>.py quote --request req.json
uv run --script adapters/<need>.py run --request req.json --out <dir> --cap-usd <n> --yes
uv run --script adapters/<need>.py providers
```

- `quote` は課金しない。鍵も通信も要らない。stdout に `{"usdMin","usdMax","asOf","basis"}`。
- `run` は `--yes` と `--cap-usd` の両方があり、見積もりの `usdMax` が cap 以下のときだけ送る。stdout に `{"files":[...],"usd":n,"provider":"..."}`。`usd` は見積もりの上限で、請求額ではない。
- `providers` は入っているプロバイダと既定を JSON で返す。
- プロバイダは req.json の `provider` か `--provider` で選ぶ。無ければ下の表の既定。

終了コード: 0 成功、2 入力の誤り（req.json、入力ファイル、鍵の環境変数が無い）、3 拒否（cap、喋る人、顔、参照の素材）、4 プロバイダの失敗（HTTP エラー、モデレーション、時間切れ）。

## req.json

必須は make の口のとおり: `need`、`cutId`、`beat`、`prompt`（tts は `text`）。`durationSec` は動画で必須。`aspect`（既定 `9:16`）、`fps`、`inputs`（パスの配列。相対パスは req.json の場所から）。

任意の欄:

| 欄 | 意味 |
| --- | --- |
| `provider` | プロバイダの id |
| `resolution` | 動画は `480p`/`720p`/`1080p`（既定 720p）、画像は `1k`/`2k`/`4k` など（既定 1k） |
| `quality` | xAI の画像の `low`/`medium` |
| `count` | 画像の枚数（1〜4） |
| `voice` | TTS の声（ElevenLabs は voice_id、Gemini は声の名前。既定 `Kore`） |
| `routeNeeds` | 使う playbook のルートの `needs` をそのまま渡す。喋る人と顔の参照の許可はここだけで決まる |
| `talkingHead` | 人がカメラに喋る生成なら `true` |
| `referenceKind` | 参照の種類。`face`、`character`、`product`、`object`、`scene`、`style` |

生成クリップの音はアダプタでは外さない（make が外す）。fps はプロバイダの固定値で出る。合わせるのは make。

## アダプタが止めること

- **送信**: 既定は見積もりだけ。`--yes` と `--cap-usd` の片方でも無いとき、cap が見積もりの上限より小さいとき、見積もりが 0 のとき、入力の尺を確かめられないとき（v2v で ffprobe が無い、尺が読めない）は送らない。送信の POST は再送せず、リダイレクトもたどらない（応答が失われても課金された可能性があるため）。繰り返すのはポーリングの GET だけ。
- **喋る人**: `talkingHead: true` のときは、`routeNeeds` に `lipsync` か `r2v` が無ければ拒否する。プロンプトが人のカメラへの語りを指しているとき（英語と日本語の言い回しを広めに見る。全角、ゼロ幅文字、ハイフンは正規化してから見る）も同じ。画像と動画の中身は見ない。言い換えて通すのではなく、playbook の needs を直す。
- **顔の同一性**: `referenceKind: face` は、`routeNeeds` に `r2v` が無ければ拒否する。`r2v` で `referenceKind` が無いときは顔として扱う。
- **参照の素材**: `sasaru/work/` と `$SASARU_HOME/work/` の下のファイルは入力にしない（取り込んだ参照リールとそのフレーム）。シンボリックリンクは、リンクの場所と指す先の両方を見る。よそへのコピーやハードリンクは見分けられないので、これは境界ではなく誤用を止める仕掛けである。
- **鍵**: 環境変数から読む。鍵はそのプロバイダの API のホスト（完全一致）にだけ、https で付ける。リダイレクトは自前でたどり、移った先が API のホストでなければ鍵を外す。生成物の取得先は https の公開ホストだけで、IP アドレスと localhost は開かない。エラー文の中の鍵の値は `***` に置き換える。

## プロバイダ

`routes.md`（2026-10-25）が現役と書いたもののうち、送り方と単価が決まるものだけを入れた。単価は 2026-10-25 の公開ページの値で、`basis` に出典の URL が入る。

| need | id（太字が既定） | モデル | 鍵の環境変数 | 見積もりの式 |
| --- | --- | --- | --- | --- |
| t2v | **`xai-grok-imagine-video-1.5-lite`** | grok-imagine-video-1.5-lite | `XAI_API_KEY` | 720p $0.03/秒（480p $0.02、1080p $0.14）× 切り上げ秒。1〜15 秒 |
| t2v | `xai-grok-imagine-video-1.5` | grok-imagine-video-1.5 | `XAI_API_KEY` | 720p $0.14/秒（480p $0.08、1080p $0.25） |
| t2v | `runway-gen4.5` | gen4.5 | `RUNWAYML_API_SECRET` | $0.12/秒。2〜10 秒、`9:16` と `16:9` |
| i2v | **`xai-grok-imagine-video-1.5-lite`** | 同上 | `XAI_API_KEY` | t2v と同じ + 入力画像 $0.01 |
| i2v | `xai-grok-imagine-video-1.5` | 同上 | `XAI_API_KEY` | t2v と同じ + 入力画像 $0.01 |
| i2v | `runway-gen4.5` | gen4.5（先頭フレームだけ） | `RUNWAYML_API_SECRET` | $0.12/秒 |
| r2v | **`xai-grok-imagine-video-1.5`** | grok-imagine-video-1.5（参照画像 1〜14 枚） | `XAI_API_KEY` | 720p $0.14/秒 + 参照画像 $0.01/枚。720p と 15 秒まで |
| v2v | **`runway-aleph2`** | aleph2 | `RUNWAYML_API_SECRET` | $0.28/秒 × 入力の尺（ffprobe）、最低 $0.56。入力 2〜30 秒 |
| v2v | `xai-grok-imagine-video` | grok-imagine-video（編集） | `XAI_API_KEY` | 出力 $0.07/秒 + 入力 $0.01/秒。入力 8.7 秒まで |
| image-gen | **`google-nano-banana-2.1`** | gemini-nano-banana-2.1（参照 14 枚まで） | `GEMINI_API_KEY`（または `GOOGLE_API_KEY`） | 1K $0.0336、2K $0.0504、4K は資料の食い違いで $0.0756〜0.1134。上限に入力分を $2/100万トークンの仮定で足す |
| image-gen | `bfl-flux-3-image-klein` | flux-3-image-klein（参照なし） | `BFL_API_KEY` | 1k $0.009、1.5k $0.011、2k $0.014、4k $0.036 |
| image-gen | `bfl-flux-3-image` | flux-3-image（参照なし） | `BFL_API_KEY` | 1k $0.048、1.5k $0.07、2k $0.10、4k $0.607 |
| image-gen | `xai-grok-imagine-image-2.0` | grok-imagine-image-2.0（参照なし） | `XAI_API_KEY` | 1k low $0.04 / medium $0.06、2k $0.06 / $0.08 |
| tts | **`elevenlabs-eleven-v4`** | eleven_v4（文字ごとのタイムスタンプも書く） | `ELEVENLABS_API_KEY`（声は `voice` か `ELEVENLABS_VOICE_ID`） | $0.08/1000 字。1 万字まで |
| tts | `elevenlabs-eleven-v4-turbo` | eleven_v4_turbo | 同上 | $0.04/1000 字 |
| tts | `google-gemini-3.8-flash-tts` | gemini-3.8-flash-tts | `GEMINI_API_KEY` | 出力 $9/100万トークン（25 トークン/秒）。上限は出力 16,384 と入力 8,192 トークンの全額。2027-01-01 から倍額で計算する |
| tts | `google-gemini-3.8-flash-lite-tts` | gemini-3.8-flash-lite-tts | `GEMINI_API_KEY` | 出力 $6/100万トークン。同上 |

既定の選び方は `routes.md` の意見に従った。B ロールはまず安い Grok 1.5 lite で、V2V は出力を自分のものとして扱える Runway Aleph 2.0、画像は Nano Banana 2.1、声はテロップの同期に使えるタイムスタンプを返す ElevenLabs にしている。

### 入れなかったもの

| 何 | 理由 |
| --- | --- |
| OpenAI Sora 2 | API が 2026-09-24 に停止 |
| Gemini API の Veo 3.1 Preview | 2026-10-22 に停止 |
| Agent Platform の Veo 3.1（GA） | モデルページが従量課金を Not supported と表示。Google Cloud の認証も要る |
| Gemini Omni Flash | 現役だが、動画の送り方（エンドポイント、ジョブの形）が調べのメモに無い |
| Kling 3.0 / O1 | Kling 4.0 は API 未提供。3.0 は認証とジョブの形が未確認 |
| gpt-image-2.5 | 1 枚あたりのトークン数が公開されておらず、上限つきの見積もりが出せない |
| Midjourney | API が無く、規約が自動化を禁止 |
| Decart、Luma、MiniMax、PixVerse、Wan 3.0、Seedance、Vidu、Recraft、Ideogram、Seedream、Qwen | 送り方が未確認か、商用条件が未確認。足すときは `_lib/providers/` に一つ書き、`_lib/registry.py` に並べる |

## 確かめていないこと

- どのプロバイダにも実際には送っていない。リクエストとレスポンスの形は公開ドキュメントと既知の API の形から書き、偽の HTTP 応答でだけ試した。最初の実送信は一番安い呼び出し（例: Grok 1.5 lite の 1 秒、FLUX 3 Klein の 1 枚）にして、出力と請求を確かめてから playbook のルートの `status` を `tested` にする。
- xAI の参照画像の欄（`reference_images`）と動画編集の入力（data URI の `video.url`）は推測が混じる。
- Gemini の画像とテキストの入力単価は調べのメモに無いので、上限には Nano Banana Pro の画像入力単価（$2/100万トークン）を仮定して足した。
- ElevenLabs v4 Turbo の 1 回の字数の上限は公開されていないので、v4 と同じ 1 万字で止める。

## テスト

```bash
python3 -m unittest discover -s skills/sasaru-make/adapters/tests -t skills/sasaru-make/adapters/tests
```

課金しない見積もりと、偽の HTTP 応答だけで試す。ネットワークに出ない（出ようとするとテストが落ちる）。鍵、顔、声、参照動画はリポジトリに置かない。テストの入力ファイルは一時フォルダに作って捨てる。
