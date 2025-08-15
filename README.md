# LOLMakeCustom

==================================================
       【LOLMakeCustom】Discord Bot for LoL
        自動チーム分け＆能力成長Bot
==================================================

📦 同梱物
--------------------------------------------------
- README.txt              ← この説明書
- requirements.txt        ← 使用ライブラリ一覧
- .env                    ← token登録用
- LOLMakeCustom_bot/
    ├─main.py            ← メインスクリプト
    ├─keep_alive.py      ← Replit用（Renderでは不要）
    └─data/
        ├─ abilities.json      ← プレイヤーの能力値保存
        ├─ history.json        ← 試合結果・戦績の保存
        └─ last_teams.json     ← 直近のチーム構成保存

🐍 必要環境
--------------------------------------------------
- Python 3.8以上
- Discord Developerアカウント
- DiscordサーバーへのBot追加権限
- 実行環境（Render推奨 / Replit可 / ローカルでもOK）

⚙️ セットアップ手順（Render向け）
--------------------------------------------------
① [Discord Developer Portal] でBotを作成
　→ https://discord.com/developers/applications

② Botの「トークン」を取得しておく（後で使う）

③ このプロジェクトをRenderにデプロイ
　手順参考: https://render.com/docs/deploy-python

⑤ 必要ライブラリをインストール（ローカルの場合）

⑥ main.py を実行すればBotが起動！

 ⚙️ セットアップ手順（Replit向け）
--------------------------------------------------
🧾 事前準備
✅ Replit アカウントを作成・ログイン
https://replit.com にアクセスしてアカウントを作成

🗂 プロジェクトのインポート
① このリポジトリを GitHub から Fork する
GitHub のリポジトリをフォーク（またはZIPを展開してGitHubにアップロード）

② Replit で新しいプロジェクトを作成
「Create Repl」をクリック

Python を選択

「Import from GitHub」タブで、自分のリポジトリURLを入力

「Create Repl」をクリック


📡 常時起動について（オプション）
--------------------------------------------------
- Renderを使えば常時稼働可能（無料枠あり）
- Replitを使う場合は keep_alive.py を使って UptimeRobot と連携

📝 よく使うコマンド（例）
--------------------------------------------------
- !hello：Botの起動確認
- !ability：能力値登録
- !join @user レーン1 レーン2：参加登録
- !make_teams：自動チーム編成
- !swap @user1 @user2：2人のレーン入れ替え
- !win A / !win B：勝敗報告 → 能力値自動更新
- !show_custom @user：カスタム戦績表示

※全コマンドは「!help_mc_detail」に記載！

🙋‍♂️ よくある質問（FAQ）
--------------------------------------------------
Q. Botが反応しません！
→ Botがサーバーに参加しているか、トークンが正しいか確認してください。

Q. JSONファイルが空です！
→ 最初は空でOKです。コマンドを使えば自動的にデータが追加されます。

Q. 導入方法がよく分かりません！
→ より一層詳しい説明をnoteに更新していく予定です。https://note.com/owsc

📬 サポート
--------------------------------------------------
不具合報告・カスタマイズ依頼は以下までご連絡ください。
📸 X（旧Twitter）: @deco39deco or @owsc_39
discord：@harapeko_o
https://discord.gg/Vjn4Gxys
note：https://note.com/owsc

--------------------------------------------------
Copyright © 2025 deco
このBotは非公式ファンツールであり、Riot Gamesとは無関係です。
--------------------------------------------------


