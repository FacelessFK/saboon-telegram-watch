# saboon-telegram-watch

Polls `https://saboon.net/api/finders` every 5 minutes with GitHub Actions and sends a Telegram message when:

- a new treasure-hunt round (or weekly challenge) opens
- a round is paused
- a new finder appears
- a round closes

It only reads the public status endpoint. It never interacts with the hall or the vault.

## Setup

Repository secrets (Settings → Secrets and variables → Actions):

- `TELEGRAM_BOT_TOKEN`: token from @BotFather
- `TELEGRAM_CHAT_ID`: your chat id

Then run the workflow manually with `test` checked to confirm messages arrive.

## Local testing

```bash
DRY_RUN=1 python3 watch.py           # print messages instead of sending
FINDERS_FILE=sample.json DRY_RUN=1 python3 watch.py
```

`state.json` holds the last seen status and is committed back by the workflow.
