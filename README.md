# Rustrans Stock

Публичная HTML-сводка наличия масел (склад МСК / в пути / уценка) на основе Google Sheets.

## Локальная сборка

```bash
python3 build.py
```

## Публикация

- **Хаб (то, что смотрят люди):** VPS `https://141-105-71-134.sslip.io/` → склад.
- GitHub Action `daily-update.yml` каждые **2 часа** с **10:10 до 19:10 МСК** (10:10, 12:10, 14:10, 16:10, 18:10, 19:10) пересобирает страницу из Google Sheets и пушит в `main` (GitHub Pages).
- На VPS таймер `rtl-stock.timer` в **:25** тех же часов забирает `index.html` + `data.json` с GitHub в webroot (не чаще). Без этого шага хаб остаётся со старым снимком, даже если CI уже обновил git.

Ручная выкладка с Mac:

```bash
rsync -az -e 'ssh -i ~/.ssh/rtl_hostkey_ed25519 -o IdentitiesOnly=yes' \
  index.html data.json \
  root@141.105.71.134:/var/www/rtl-view/stock/
rsync -az -e 'ssh -i ~/.ssh/rtl_hostkey_ed25519 -o IdentitiesOnly=yes' \
  index.html data.json \
  root@141.105.71.134:/var/www/rtl-view/Redx5imaAYtfi1/
```
