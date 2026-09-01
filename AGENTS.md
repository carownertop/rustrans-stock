# Rustrans Stock — вход для агента

Владелец ставит задачи по эффекту на странице склада, не по путям. Код ищи сам.

## Что это

Публичная HTML-сводка наличия масел (МСК / в пути / уценка) с данных Google Sheets → GitHub Pages.

## Карта

| Зона | Где |
|------|-----|
| UI | `index.html` |
| Сборка | `build.py` |
| Данные витрины | `data.json` |
| CI / Pages | `.github/` |

## Куда не лезть по умолчанию

- Тяжёлые бинарники/иконки без нужды; секреты если появятся
- Бэкапы: только `~/Backups/rustrans-stock/`, только по явной команде

## Якоря

- **Live хаб:** `https://141-105-71-134.sslip.io/` → плитка склада (slug), файлы на VPS `/var/www/rtl-view/stock/`
- GitHub Action `daily-update.yml` собирает Sheets → commit `main` каждые 2 ч с 10:10 до 19:10 МСК
- VPS копирует `main` в webroot в :25 тех же часов (`rtl-stock.timer`, `scripts/pull_github_to_webroot.sh`)
- Ручной rsync с Mac: `index.html` + `data.json` → `/var/www/rtl-view/stock/` **и** slug `Redx5imaAYtfi1`
