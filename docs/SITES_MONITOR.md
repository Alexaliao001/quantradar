# SITES_MONITOR — 日一次全站验收

> SX6-5 · 任务源 `GROK_GOAL_SITES_EXTREME.md`

## 手动

```bash
python3 ~/quantradar/scripts/sites_extreme_verify.py
# 期望末行 RESULT: PASS
```

日志可重定向：

```bash
mkdir -p ~/quantradar/logs
python3 ~/quantradar/scripts/sites_extreme_verify.py \
  | tee ~/quantradar/logs/sites_extreme_$(date +%Y%m%d).log
```

## cron（每日 09:00 本地）

```cron
0 9 * * * /usr/bin/python3 $HOME/quantradar/scripts/sites_extreme_verify.py >> $HOME/quantradar/logs/sites_extreme_cron.log 2>&1
```

`crontab -e` 粘贴上一行；先 `mkdir -p ~/quantradar/logs`。

## launchd（可选 · macOS）

`~/Library/LaunchAgents/one.quantradar.sites-extreme.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>one.quantradar.sites-extreme</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/rongjianliao/quantradar/scripts/sites_extreme_verify.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/rongjianliao/quantradar/logs/sites_extreme_launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/rongjianliao/quantradar/logs/sites_extreme_launchd.err</string>
</dict>
</plist>
```

```bash
mkdir -p ~/quantradar/logs
launchctl load ~/Library/LaunchAgents/one.quantradar.sites-extreme.plist
```

卸载：`launchctl unload ~/Library/LaunchAgents/one.quantradar.sites-extreme.plist`。

## 失败时

1. 打开当日 log，看哪个 `[FAIL]`
2. 对照 `docs/SITES_LIVE.md` / `docs/SITES_COST.md`
3. 禁止开 Manus agent；优先 GH Pages / Render 日志 / DNS
