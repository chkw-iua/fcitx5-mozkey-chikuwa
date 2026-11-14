# fcitx5-mozkey-chikuwa

[![Platform](https://img.shields.io/badge/platform-Ubuntu%2026.04%20%7C%2024.04-orange.svg)](https://ubuntu.com/)
[![Display](https://img.shields.io/badge/display-Wayland%20%7C%20X11-blue.svg)](https://wayland.freedesktop.org/)
[![Framework](https://img.shields.io/badge/framework-Fcitx5-green.svg)](https://fcitx-im.org/)
[![License](https://img.shields.io/badge/license-BSD%203--Clause%20%2F%20LGPL--2.1%2B%20%2F%20MIT-informational.svg)](LICENSE)

**fcitx5-mozkey-chikuwa** は、Windows 向け高機能日本語 IME [koyasi777/mozkey](https://github.com/koyasi777/mozkey)（`v1.1.0`）を Ubuntu (Wayland / X11 / Fcitx5) 向けに移植した非公式ビルド・パッケージングプロジェクトです。

キーを入力した瞬間にリアルタイムで漢字仮名変換が行われる**「遅延ライブ変換」**と、軽量ローカル LLM による文脈推論を行う**「Zenz AI 文脈補正」**を、Ubuntu デスクトップ環境でシームレスに利用できます。

---

## 目次

1. [主な特徴](#主な特徴)
2. [動作要件](#動作要件)
3. [クイックスタート (.deb の導入と初期設定)](#クイックスタート-deb-の導入と初期設定)
4. [設定と活用ガイド](#設定と活用ガイド)
5. [トラブルシューティング / よくある質問 (FAQ)](#トラブルシューティング--よくある質問-faq)
6. [ソースコードからのビルド (開発者・上級者向け)](#ソースコードからのビルド-開発者上級者向け)
7. [アーキテクチャと安全設計](#アーキテクチャと安全設計)
8. [ライセンス・著作権表示・謝辞](#ライセンス著作権表示謝辞)

---

## 主な特徴

- ⚡ **遅延ライブ変換**: ローマ字入力と同時にリアルタイムで適切な漢字仮名変換を実行します。適度な遅延バッファにより、画面のチラつきを抑えた自然で軽快なタイピング体験を提供します。
- 🤖 **ローカル AI 文脈補正 (Zenz)**: バックグラウンドで動作する推論エンジン（`llama.cpp` + `zenz-v3.2-small-Q5_K_M.gguf`）が入力前後の文脈を自動判別し、「同音異義語」の誤変換（例: 「きしゃのきしゃがきしゃできしゃした」→「貴社の記者が汽車で帰社した」など）を高精度に補正します。推論はすべて PC 内で完結し、外部クラウド通信は一切行いません。
- 🛡️ **既存 Mozc と安全に共存**: ソケット名前空間（`@tmp/.mozkey.*`）、設定ディレクトリ（`~/.config/mozkey`）、バイナリ配置先（`/usr/lib/mozkey`）を完全に分離。Ubuntu 標準の `fcitx5-mozc` や `mozc-server` の設定・辞書データを破壊することなく、安全に併用・切り替えが可能です。
- ⚙️ **Qt6 GUI 設定ツール (`mozc_tool`) 完備**: プロパティ設定、単語登録ダイアログ、辞書ツールなど、従来の Mozc と同等の使い慣れた GUI 管理画面を提供します。
- 🔒 **AppArmor セキュリティプロファイル対応**: `/etc/apparmor.d/abstractions/mozc.d/mozkey` を同梱し、Snap 版ブラウザ（Firefox や Chromium 等）などのサンドボックス環境からも安全に接続できます。

---

## 動作要件

| 項目 | 要件 |
|---|---|
| **対象 OS** | Ubuntu 26.04 LTS, Ubuntu 24.04 LTS (x86_64 / amd64) |
| **ディスプレイサーバー** | Wayland / X11 |
| **入力フレームワーク** | Fcitx5 (`fcitx5`, `fcitx5-configtool` または `fcitx5-config-qt`) |
| **ハードウェア要件** | 空きメモリ: 約 150MB 以上（Zenz モデルフットプリント: 約 74MB）<br>CPU: x86_64（AVX2 対応 CPU 推奨） |

---

## クイックスタート (.deb の導入と初期設定)

配布されているビルド済み `.deb` パッケージ（[Releases](https://github.com/chkw-iua/fcitx5-mozkey-chikuwa/releases) 等から入手、または下記の「[ソースコードからのビルド](#ソースコードからのビルド-開発者上級者向け)」で生成）を使用してセットアップします。

### 前提: Fcitx5 の準備（Ubuntu 標準 IBus から切り替える場合）

Ubuntu 標準の IBus を利用している場合は、あらかじめ Fcitx5 をインストールして既定の入力フレームワークに設定してください：

```bash
sudo apt update
sudo apt install -y fcitx5 fcitx5-config-qt
im-config -n fcitx5
```
※ `im-config` 実行後、設定を反映するために一度ログアウトして再ログイン（またはシステム再起動）してください。

### Step 1: パッケージのインストール

入手した `.deb` パッケージを `apt` 経由で依存パッケージとともにインストールし、Fcitx5 デーモンを再起動します（ダウンロードしたファイル名・パスに合わせて読み替えてください）：

```bash
# 例: ダウンロードした .deb ファイルがあるディレクトリで実行
sudo apt update
sudo apt install ./fcitx5-mozkey-chikuwa_<version>_amd64.deb

# Fcitx5 を再起動してアドオンを認識させる
fcitx5 -r -d
```

> ソースコードから自分でビルドした場合は、生成先である `packaging/out/` 配下の `.deb` ファイル（例: `./packaging/out/fcitx5-mozkey-chikuwa_*_amd64.deb`）を指定してください。

### Step 2: Fcitx5 への Mozkey の追加

1. **Fcitx5 設定画面を開く**:
   - システムトレイのキーボードアイコンを右クリックして「設定」を開くか、端末で `fcitx5-configtool` を実行します。
2. **Mozkey を追加する**:
   - 「入力メソッド」タブを選択します。
   - 画面中央付近にある **「現在の言語のみ表示」のチェックを外します**。
   - 検索入力欄に `Mozkey` と入力します。
   - リストに表示された **「Mozkey」** を選択し、**追加ボタン（`>`）** をクリックして現在の入力メソッド一覧に追加します。
   - 推奨の並び順（リストの上から順）：
     1. キーボード - 英語 (US) または キーボード - 日本語
     2. **Mozkey**
3. **「適用」をクリック** して設定を保存します。

### Step 3: 入力の切り替えとタイピング

- **`Ctrl + Space`** または **`半角/全角`** キーを押して Mozkey に切り替えます。
- システムトレイのインジケーターが **「あ」** になっていれば入力準備完了です。
- テキストエディタやブラウザ等でそのままローマ字を入力してください。タイピングに合わせてリアルタイムに漢字仮名変換が行われます。

---

## 設定と活用ガイド

### 1. GUI 設定ツール (`mozc_tool`)

Mozkey には専用の Qt6 GUI 設定ツールが同梱されています。トレイアイコンのメニューから起動するか、端末から以下のコマンドで呼び出すことができます：

```bash
# プロパティ設定（ライブ変換の有効/無効、遅延ミリ秒数、Zenz AI の有効/無効、キー設定など）
/usr/lib/mozkey/mozc_tool --mode=config_dialog

# 辞書ツール（ユーザー辞書の編集・インポート・エクスポート）
/usr/lib/mozkey/mozc_tool --mode=dictionary_tool

# 単語登録ダイアログ（新しい単語と読みの登録）
/usr/lib/mozkey/mozc_tool --mode=word_register_dialog

# バージョン情報ダイアログ
/usr/lib/mozkey/mozc_tool --mode=about_dialog
```

### 2. 日常のタイピング操作

- **ライブ変換**: 文字を入力すると自動的に文脈に合わせた漢字に変換されます。スペースキーを押す必要はなく、そのまま続けて入力し、**`Enter`** キーで確定できます。
- **候補選択**: 別の変換候補を選びたい場合は、**`Space`** キーまたは矢印キーを押して候補ウィンドウを表示し、目的の単語を選択します。
- **再変換・編集**: 直前に確定した単語や未確定部分の文字は、**`Backspace`** キーで取り消し・再編集が可能です。
- **ローカルプライバシー保護**: Zenz AI の推論はすべて PC 内部の `127.0.0.1` ループバック通信のみで行われます。入力内容やキーストロークが外部サーバーに送信されることは一切ありません。また、URL、アクセストークン、パスワード、長大な数字列などの機密情報はコンテキストから自動的に除外・サニタイズされます。

### 3. 設定ファイルおよび個人辞書の保存場所

Mozkey の設定や学習データは、Ubuntu 標準の Mozc とは完全に分離されています：

- **Mozkey 設定・辞書**: `~/.config/mozkey/`
- **標準 Mozc 設定・辞書**: `~/.config/mozc/`（Mozkey の影響を一切受けません）

---

## トラブルシューティング / よくある質問 (FAQ)

### Q1: Fcitx5 設定の候補一覧に「Mozkey」が表示されない
- Fcitx5 設定ダイアログで **「現在の言語のみ表示」のチェックが外れているか** 確認してください。
- Fcitx5 デーモンが新しいプラグインを読み込めていない場合があります。端末で `fcitx5 -r -d` を実行して再起動してください。
- プラグインおよび設定ファイルが正しくインストールされているか確認してください：
  - `/usr/lib/x86_64-linux-gnu/fcitx5/fcitx5-mozkey.so`
  - `/usr/share/fcitx5/addon/mozkey.conf`
  - `/usr/share/fcitx5/inputmethod/mozkey.conf`

### Q2: Mozkey に切り替えても日本語変換が動かない / Snap 版アプリ（Firefox 等）で入力できない
- AppArmor のプロファイル反映が必要な場合があります。以下のコマンドで AppArmor を再読み込みしてください：
  ```bash
  sudo systemctl reload apparmor
  ```
- Mozkey サーバープロセスが正常に起動しているか確認してください：
  ```bash
  pgrep -a mozc_server
  # 出力例: /usr/lib/mozkey/mozc_server
  ```

### Q3: Zenz AI による文脈補正が動作していない
- Zenz 推論サーバー（`llama-server`）およびスコアラーが動作しているか確認してください：
  ```bash
  pgrep -a llama-server
  pgrep -a mozc_zenz_scorer
  ```
- AI モデルファイルが存在しているか確認してください：
  ```bash
  ls -lh /usr/lib/mozkey/ZenzRuntime/models/zenz-v3.2-small-Q5_K_M.gguf
  ```
- 実行ユーザー用の IPC ソケットが作成されているか確認してください：
  ```bash
  ls -l /tmp/mozc_zenz_${UID}/scorer.sock
  ```

### Q4: アンインストール手順
Mozkey をアンインストールしてシステムをクリーンに戻すには、以下のコマンドを実行します：

```bash
# パッケージの完全削除（設定ファイル含む）
sudo apt purge fcitx5-mozkey-chikuwa

# Fcitx5 を再起動
fcitx5 -r -d
```
※ ユーザー設定や個人辞書（`~/.config/mozkey/`）を残したい場合は `sudo apt remove fcitx5-mozkey-chikuwa` を使用してください。

---

## ソースコードからのビルド (開発者・上級者向け)

本リポジトリのソースコードからコンポーネントをコンパイルし、`.deb` パッケージを新規生成する手順です。

### 1. ビルド前提パッケージのインストール

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build git python3 pkg-config \
  libfcitx5core-dev libfcitx5config-dev libfcitx5utils-dev \
  qt6-base-dev libqt6core6t64 libqt6gui6 libqt6widgets6 libqt6dbus6 \
  libssl-dev dpkg-dev

# Bazelisk の準備（PATH の通った場所に配置）
# https://github.com/bazelbuild/bazelisk/releases からダウンロードし、
# 例: ~/.local/bin/bazelisk に配置して実行権限を付与します。
```

### 2. ソースコードのチェックアウトとパッチ適用

```bash
# 上流 Mozkey リポジトリのクローンと Linux 向けパッチ適用
git clone --depth 1 --branch v1.1.0 https://github.com/koyasi777/mozkey.git upstream
git -C upstream apply ../packaging/patches/upstream-linux-port.patch
cp -a unix/fcitx5 upstream/src/unix/fcitx5

# llama.cpp のクローンと監視パイプ・文字トークナイザーパッチ適用
git init llama.cpp
git -C llama.cpp remote add origin https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp fetch --depth 1 origin 620d2225cc436ab0b001e3200e590e3b286ef9ab
git -C llama.cpp checkout --detach FETCH_HEAD
git -C llama.cpp apply ../packaging/patches/llama-cpp-linux-mozkey.patch

# llama-server のビルド (-ffile-prefix-map でビルド環境の絶対パス焼き付きを防止)
cmake -B llama.cpp/build -S llama.cpp -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_CURL=OFF \
  -DCMAKE_C_FLAGS="-ffile-prefix-map=${PWD}/llama.cpp=." \
  -DCMAKE_CXX_FLAGS="-ffile-prefix-map=${PWD}/llama.cpp=."
cmake --build llama.cpp/build --target llama-server -j"$(nproc)"
```

### 3. Bazel ビルドと .deb パッケージ作成

#### (A) 既定（sample 辞書）でビルドする場合
```bash
cd upstream/src
ANDROID_NDK_HOME= bazelisk build --config=no_sframe \
  //server:mozc_server //gui/tool:mozc_tool \
  //zenz_scorer:mozc_zenz_scorer //zenz_scorer:mozc_zenz_guard \
  //unix/fcitx5:fcitx5-mozkey.so
cd ../..

# .deb パッケージ生成（packaging/out/ に出力されます）
./packaging/build_deb.sh
```

#### (B) オプション: `daily` 辞書を組み込む場合
外部辞書（`merge-ut`、`dic-nico-intersection-pixiv`、`mozcdic-ut-personal-names`、Wikipedia 見出しインデックス）を SHA-256 検証付きで取得・生成して組み込みます（`daily` 有効時は `DICTIONARY_NOTICES.md` および `SudachiDict-LEGAL.txt` が `/usr/share/doc/fcitx5-mozkey-chikuwa/` に自動同梱されます）：

```bash
# daily 辞書のダウンロードとビルド設定
python3 packaging/prepare_daily_dictionary_linux.py

cd upstream/src
ANDROID_NDK_HOME= bazelisk build --config=no_sframe \
  //server:mozc_server //gui/tool:mozc_tool \
  //zenz_scorer:mozc_zenz_scorer //zenz_scorer:mozc_zenz_guard \
  //unix/fcitx5:fcitx5-mozkey.so
cd ../..
./packaging/build_deb.sh

# 辞書構成をリポジトリ既定 (sample) に戻す場合
python3 packaging/prepare_daily_dictionary_linux.py --switch-only --profile sample
```

### 4. ローカルステージング環境でのテスト (`start_local_mozkey.sh`)

システムにインストールせず、`~/.local` 配下に成果物を展開してローカルテストを行う場合は以下のスクリプトを利用できます：

```bash
./start_local_mozkey.sh --restart-server
```

---

## アーキテクチャと安全設計

本プロジェクトは、システム標準の `fcitx5-mozc` やデスクトップ環境と衝突しないよう、徹底したプロセス分離とリソースの独立性を確保して設計されています。

```text
[ GUI アプリケーション ] (ブラウザ、エディタ、端末など)
       │ (Wayland / X11)
       ▼
[ Fcitx5 デーモン ] ── (In-Process / dlopen) ──▶ [ fcitx5-mozkey.so ] (LGPL-2.1+ / LGPL-3.0+)
                                                       │
                                 Linux 抽象名前空間ソケット (@tmp/.mozkey.*)
                                                       ▼
                                              [ mozc_server ] (BSD-3-Clause)
                                                       │
                                     POSIX ドメインソケット (/tmp/mozc_zenz_<UID>/scorer.sock)
                                                       ▼
                                           [ mozc_zenz_scorer ] (BSD-3-Clause)
                                                       │
                                              ローカル HTTP (127.0.0.1) / パイプ監視
                                                       ▼
                                             [ llama-server ] (MIT License)
                                                       │
                                             [ zenz-v3.2 GGUF ] (Apache-2.0 / CC BY-SA 4.0)
```

### IPC 境界によるコピーレフト隔離

各コンポーネントは独立したプロセス空間で動作し、標準的なプロセス間通信（IPC）でのみ疎結合されています：
1. `fcitx5-mozkey.so` と `mozc_server`: Linux カーネルの抽象 Unix ドメインソケット（`@tmp/.mozkey.*`）を介して Google Protobuf メッセージにより通信。
2. `mozc_server` と `mozc_zenz_scorer`: POSIX ドメインソケット（`/tmp/mozc_zenz_<UID>/scorer.sock`）経由で通信。
3. `mozc_zenz_scorer` と `llama-server`: `posix_spawn` で起動された子プロセスであり、ファイルディスクリプタ（23, 24）による親死活監視とローカル HTTP ループバック（`127.0.0.1:<port>`）経由で通信。

著作権法およびオープンソースライセンスの標準的解釈に基づき、独立したアドレス空間で IPC により通信するプロセス群は相互に「派生物（Derivative Work）」とはみなされません。そのため、`fcitx5-mozkey.so` に適用される LGPL のコピーレフト義務が `mozc_server`（BSD-3-Clause）や `llama-server`（MIT License）へ波及（感染）することはありません。

### マルチユーザー・安全性設計

- **UID ごとの一時ディレクトリ分離**: Zenz プロセス用の一時ディレクトリ（`/tmp/mozc_zenz_<UID>/`）は `0700` 権限で動的生成され、同一マシン上の他ユーザーからの干渉や情報漏洩を遮断します。
- **ゾンビプロセスの防止**: `mozc_zenz_scorer` が異常終了した場合でも、`llama.cpp` に適用したパッチにより監視パイプを通じて `llama-server` が安全にフェイルクローズ（自動終了）します。

---

## ライセンス・著作権表示・謝辞

### 1. コンポーネント別ライセンス対応表

本リポジトリおよび生成されるパッケージは、複数のオープンソースプロジェクトの成果に基づいています。各コンポーネントの著作権者およびライセンスは以下の通りです：

| コンポーネント / パス | 著作権者 (Copyright Holders) | ライセンス | 配布条件・備考 |
|---|---|---|---|
| **本リポジトリ独自コード**<br>`packaging/*.sh`, `patches/`, `start_local_mozkey.sh` | 2026 chikuwa (fcitx5-mozkey-chikuwa contributors) | **BSD-3-Clause** | 本リポジトリのルート [LICENSE](LICENSE) を適用 |
| **Fcitx5 フロントエンド中核**<br>`unix/fcitx5/mozc_engine.*`, `mozc_engine_factory.cc`, `i18nwrapper.h` | 2017-2020 CSSlayer / Weng Xuetian (`<wengxt@gmail.com>`) | **LGPL-2.1-or-later** | [fcitx/mozc](https://github.com/fcitx/mozc) 由来（4ファイル） |
| **Fcitx5 フロントエンド共通部**<br>`unix/fcitx5/` (上記以外の C++ ソース 13 ファイル) | 2010-2013 Google Inc.<br>2012-2023 Weng Xuetian | **BSD-3-Clause** | 状態管理、キーバインド処理等 |
| **フロントエンド共有ライブラリ成果物**<br>`fcitx5-mozkey.so` | Google Inc., Weng Xuetian, chikuwa | **LGPL-2.1+ / LGPL-3.0+** | LGPL コード、Mozc コア（BSD-3）、Abseil（Apache-2.0）の静的結合成果物 |
| **上流 Mozc コア**<br>`upstream/src/` (Mozc エンジン部) | 2010-2024 Google Inc. | **BSD-3-Clause** | 日本語入力エンジン基盤 |
| **上流 Mozkey 拡張**<br>`upstream/src/` (遅延ライブ変換・Zenz 連携) | 2024-2026 koyasi777 | **BSD-3-Clause** | [koyasi777/mozkey](https://github.com/koyasi777/mozkey) 由来 |
| **サーバーデーモン & 設定 GUI**<br>`mozc_server`, `mozc_tool` | 2010-2024 Google Inc.<br>2024-2026 koyasi777 | **BSD-3-Clause** | `mozc_tool` はシステム Qt6（LGPLv3）と動的リンク |
| **Zenz スコアラー & ガード**<br>`mozc_zenz_scorer`, `mozc_zenz_guard` | 2024-2026 koyasi777, 2026 chikuwa | **BSD-3-Clause** | Zenz 連携・推論監視デーモン |
| **推論サーバー**<br>`llama.cpp/`, `llama-server` バイナリ | 2023-2026 Georgi Gerganov and llama.cpp contributors | **MIT License** | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) 由来 |
| **Zenz AI モデル**<br>`zenz-v3.2-small-Q5_K_M.gguf` | 2024 三輪 敬太 (Keita Miwa)<br>2023 京都大学 KU-NLP (黒橋・河原・村脇研究室) | **Apache-2.0** (ファインチューン)<br>**CC BY-SA 4.0** (基底モデル) | 二重出自（Dual-lineage Attribution）。商用利用可能（Non-Commercial 制限なし） |
| **内蔵標準辞書データ** | 2000-2003 NAIST, 1992-1995 ICOT, Google Inc. | **NAIST-ICOT-Mozc** | IPAdic / ICOT 辞書許諾条件に準拠 |
| **daily 外部辞書 (オプション)** | Works Applications, UniDic Consortium, Toshinori Sato, utuhiro78, Wikipedia 執筆者 | **Apache-2.0 / BSD-3 / CC BY-SA 4.0** | 生成時に `DICTIONARY_NOTICES.md` および `SudachiDict-LEGAL.txt` を自動同梱 |

### 2. AI モデルおよび辞書データの権利関係

- **Zenz AI モデルの二重出自 (Dual-lineage Attribution)**:
  同梱されているモデルファイル `zenz-v3.2-small-Q5_K_M.gguf` は、[三輪敬太 氏](https://huggingface.co/Miwa-Keita/zenz-v3.2-small-gguf)（Apache License 2.0）がファインチューニングおよび GGUF 量子化を行ったモデルです。バイナリヘッダーに含まれるメタデータの通り、基底の事前学習モデルは [京都大学 黒橋・河原・村脇研究室 / KU-NLP](https://huggingface.co/ku-nlp/gpt2-small-japanese-char) が公開している `ku-nlp/gpt2-small-japanese-char`（CC BY-SA 4.0）に基づいています。CC BY-SA 4.0 および Apache-2.0 のいずれにも非商用制限（NC）は課されていないため、商用利用を含めて自由に利用可能です。
- **パッケージ内のライセンス文書**:
  Debian パッケージ（`.deb`）には、Debian Policy Manual (§12.5) および DEP-5 形式に準拠した完全な著作権・ライセンス情報が `/usr/share/doc/fcitx5-mozkey-chikuwa/copyright` として同梱されます。

### 3. 免責事項 (Disclaimer & Non-Affiliation)

- **非公式コミュニティプロジェクト**:
  本ソフトウェアは有志による独立した移植成果物であり、Google LLC、Fcitx プロジェクトチーム、京都大学、または koyasi777 氏とは一切提携、承認、後援、または公認関係にありません。
- **無保証 (AS IS)**:
  本ソフトウェアは、明示・黙示を問わず、商品性や特定目的への適合性の保証を含め、いかなる保証もなしに「現状のまま（AS IS）」で提供されます。本ソフトウェアの使用または使用不能によって生じたいかなる損害についても、作者および貢献者は一切の責任を負いません。
