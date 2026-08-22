---
name: ambiguous-calibration
description: Ambiguous 文字幅がターミナル依存であることの説明と、aacalibrate.py でのキャリブレーション手順
volta:
  version: 1
  namespace: aatable
  locality: repo
  applies_when: Ambiguous 幅の違いで表のズレに気づいたとき
  requires: []
  min_role: VIEWER
  export: allowed
---

# Ambiguous 文字幅のキャリブレーション

## いつ使う

Ambiguous 文字（①②③, αβγ, ♠♥♦♣, ☺ 等）の表示幅はターミナル依存です。
表のズレが Ambiguous 文字で起きているとき、`aacalibrate.py` で実機の幅を測定し、
プロファイルに保存できます。

## 手順

1. `python3 aacalibrate.py` をターミナルで実行（TTY 必須）
2. プローブが Ambiguous 文字の幅を測定（1 or 2）
3. `~/.aatable_profile.json` に保存される
4. `aatable.py` / `aafixwidth.py` は起動時にプロファイルを自動読み込み
5. MCP tool では `ambiguous_width` パラメータで明示指定可能

## 判断基準

- Windows系・WSL: 1 (narrow)
- macOS Terminal: 2 (wide)
- Linux 端末: 1 が多いが、フォント依存

## 注意

- `aacalibrate.py` はインタラクティブ TTY が必須。MCP tool には含めない。
- MCP 経由で呼ぶエージェントは `ambiguous_width` パラメータで明示する。
