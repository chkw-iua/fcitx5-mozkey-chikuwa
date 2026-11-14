# fcitx5-mozkey-chikuwa

Ubuntu 26.04 LTS (Wayland / Fcitx5) 向けに [koyasi777/mozkey](https://github.com/koyasi777/mozkey)（`v1.1.0`）を移植し、ライブ変換・Zenz ローカル AI 文脈補正・`mozc_tool` 設定 UI・`.deb` パッケージ化までをまとめた非公式ビルド・パッケージングリポジトリです。

## 主な特徴

- **既存 Mozc と安全に共存**: ソケット名前空間（`@tmp/.mozkey.*`）、設定ディレクトリ（`~/.config/mozkey`）、配置先（`/usr/lib/mozkey`）を分離し、Ubuntu 標準の `fcitx5-mozc` / `mozc-server` と競合しません。
- **Fcitx5 遅延ライブ変換 & Zenz 対応**: `upstream/src/unix/fcitx5/` にて `output.callback().delay_millisec()`、`Preedit::cursor` 位置補正、周辺テキスト（`zenz_preceding_text` / `zenz_following_text`）を実装しています。
- **Linux 版 Zenz ランタイム**: `mozc_zenz_scorer` / `mozc_zenz_guard` / `llama-server`（`zenz-v3.2-small-Q5_K_M.gguf`）を `/tmp/mozc_zenz_<UID>/scorer.sock` 経由で自動起動・連携します。
- **AppArmor 対応**: `/etc/apparmor.d/abstractions/mozc.d/mozkey` を同梱し、`@tmp/.mozkey.*` への接続を許可します。

## ディレクトリ構成

- `unix/fcitx5/` — Fcitx5 フロントエンド（`fcitx/mozc` ベース + 遅延ライブ変換 / `Preedit::cursor` / Zenz 周辺テキスト対応）
- `packaging/`
  - `build_deb.sh` — `.deb` パッケージ生成スクリプト
  - `prepare_daily_dictionary_linux.py` — Linux 用 `daily` 辞書取得・生成スクリプト（オプション）
  - `apparmor/mozkey`, `fcitx5/` — AppArmor drop-in および Fcitx5 設定
  - `patches/` — `koyasi777/mozkey` (`v1.1.0` / `7f8af6b`) および `ggml-org/llama.cpp` (`0.7.0` / `620d222`) 向け差分パッチ
- `start_local_mozkey.sh` — `~/.local` ステージング環境でのローカル起動用スクリプト
- `upstream/` / `llama.cpp/` — ローカルビルド用チェックアウト（`.gitignore` 対象）

## ゼロからのソース準備（別環境でビルドする場合）

```bash
git clone --depth 1 --branch v1.1.0 https://github.com/koyasi777/mozkey.git upstream
git -C upstream apply ../packaging/patches/upstream-linux-port.patch
cp -a unix/fcitx5 upstream/src/unix/fcitx5

git init llama.cpp
git -C llama.cpp remote add origin https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp fetch --depth 1 origin 620d2225cc436ab0b001e3200e590e3b286ef9ab
git -C llama.cpp checkout --detach FETCH_HEAD
git -C llama.cpp apply ../packaging/patches/llama-cpp-linux-mozkey.patch

# llama-server のビルド（ローカルパス焼き付き防止のため -ffile-prefix-map を付与）
cmake -B llama.cpp/build -S llama.cpp -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_CURL=OFF \
  -DCMAKE_C_FLAGS="-ffile-prefix-map=${PWD}/llama.cpp=." \
  -DCMAKE_CXX_FLAGS="-ffile-prefix-map=${PWD}/llama.cpp=."
cmake --build llama.cpp/build --target llama-server -j"$(nproc)"
```

## ビルド & パッケージ化手順

※ `bazelisk` は `PATH` が通った場所に配置してください（例: `~/.local/bin/bazelisk`）。

### 1. 既定（`mozcdic_ut_sample`）でビルドして `.deb` を作る

```bash
cd upstream/src
ANDROID_NDK_HOME= bazelisk build --config=no_sframe \
  //server:mozc_server //gui/tool:mozc_tool \
  //zenz_scorer:mozc_zenz_scorer //zenz_scorer:mozc_zenz_guard \
  //unix/fcitx5:fcitx5-mozkey.so
cd ../..
./packaging/build_deb.sh
```

※ `zenz-v3.2-small-Q5_K_M.gguf` は `MOZKEY_MODEL_PATH`、`upstream/src/win32/installer/zenz_runtime/models/`、`~/.local/lib/mozkey/ZenzRuntime/models/`、`/usr/lib/mozkey/ZenzRuntime/models/` の順に参照します。

### 2. オプション: `daily` 辞書を組み込んでローカル用 `.deb` を作る

外部辞書（`merge-ut`、`dic-nico-intersection-pixiv`、`mozcdic-ut-personal-names`、Wikipedia 見出しインデックス）を SHA-256 検証付きで取得・生成して組み込む場合（`daily` 有効時は `DICTIONARY_NOTICES.md` / `SudachiDict-LEGAL.txt` が `/usr/share/doc/fcitx5-mozkey-chikuwa/` に自動同梱されます）：

```bash
python3 packaging/prepare_daily_dictionary_linux.py

cd upstream/src
ANDROID_NDK_HOME= bazelisk build --config=no_sframe \
  //server:mozc_server //gui/tool:mozc_tool \
  //zenz_scorer:mozc_zenz_scorer //zenz_scorer:mozc_zenz_guard \
  //unix/fcitx5:fcitx5-mozkey.so
cd ../..
./packaging/build_deb.sh

# リポジトリ既定 (sample) に戻す
python3 packaging/prepare_daily_dictionary_linux.py --switch-only --profile sample
```

## インストール / アンインストール

```bash
# インストール
sudo apt install ./packaging/out/fcitx5-mozkey-chikuwa_0.1.0+git20261113_amd64.deb
fcitx5 -r -d

# アンインストール
sudo apt purge fcitx5-mozkey-chikuwa
fcitx5 -r -d
```

## ライセンス・謝辞

- 本リポジトリの独自スクリプト・パッチ・設定ファイルは [BSD-3-Clause](LICENSE) です。
- `unix/fcitx5/` は [fcitx/mozc](https://github.com/fcitx/mozc) に由来する複合ライセンスです：
  - `mozc_engine.*`, `mozc_engine_factory.cc`, `i18nwrapper.h` は **LGPL-2.1+**（CSSlayer / Weng Xuetian）
  - その他の C++ ファイルは **BSD-3-Clause**（Google Inc. / Weng Xuetian）
  - 生成される `fcitx5-mozkey.so` は **LGPL-2.1+**（Abseil 結合時は **LGPL-3.0+**）に従います。
- `llama-server` は [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)（MIT License）に従います。
- バンドルされる Zenz モデル（`zenz-v3.2-small-Q5_K_M.gguf`）は [三輪敬太 氏](https://huggingface.co/Miwa-Keita/zenz-v3.2-small-gguf)（Apache-2.0）および基底モデルを事前学習した [京都大学 黒橋・河原・村脇研究室 / KU-NLP](https://huggingface.co/ku-nlp/gpt2-small-japanese-char)（CC BY-SA 4.0）の成果に依拠しています。
- 上流 Mozkey は [koyasi777/mozkey](https://github.com/koyasi777/mozkey)（BSD-3-Clause / Google Inc.）に従います。

