# luvoMiniApp

## Configuration

- `DEBUG_TELEGRAM_BOT_TOKENS` — optional comma-separated list of Telegram bot tokens that are accepted *in addition* to `TELEGRAM_BOT_TOKEN` while validating WebApp init data. These extra tokens are only honored when `DEBUG=True`, which allows operators to temporarily test alternative bots without weakening production security.
