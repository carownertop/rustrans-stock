# Rustrans Stock

Публичная HTML-сводка наличия масел (склад МСК / в пути / уценка) на основе Google Sheets.

## Локальная сборка

```bash
python3 build.py
```

## Публикация

Страница отдаётся через GitHub Pages из корня ветки `main`.

Ежедневное обновление: GitHub Action в `.github/workflows/daily-update.yml` (10:10 МСК) + ручной запуск `workflow_dispatch`.
