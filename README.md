# Anime Telegram Bot — Koyeb-ready starter

Features included:
- Anime search with poster, synopsis, year, episode count and AniList score (AniList metadata only).
- Search by `/search Naruto` or send an anime name as a message.
- Admin manual episode upload (video/document/audio) with caption `Anime Name | 01`.
- Admin direct-link catalog: `/add Anime Name | 01 | https://your-authorized-link`.
- Browse saved episodes using `/episodes`; remove with `/delete Anime Name | 01`.
- User registration, favorites (`/fav Naruto`, `/favorites`), admin stats (`/stats`) and announcements (`/broadcast message`).
- Optional auto-copy of new posts from a source Telegram channel to a target channel using `SOURCE_CHANNEL_ID` and `TARGET_CHANNEL_ID`.
- SQLite database and Dockerfile for deployment.

## Deploy
1. Create a Telegram bot with `@BotFather` and copy its token.
2. Upload this folder to a GitHub repository.
3. In Koyeb create an App from that GitHub repository. Use Dockerfile build/deployment.
4. Add environment variables: `BOT_TOKEN` and `ADMIN_IDS` (your numeric Telegram user ID). `DB_PATH` may be left as `animebot.db`.
5. For auto-copy, set `SOURCE_CHANNEL_ID` and `TARGET_CHANNEL_ID`; add the bot as an administrator in both channels, with permission to post in the target. Only configure channels you own or are authorized to manage.
6. Deploy and check logs.

## Commands
- `/start`, `/help`
- `/search One Piece` or just send `One Piece`
- `/episodes`
- `/fav One Piece`, `/favorites`
- Admin: `/add Title | 01 | https://authorized-link`, `/delete Title | 01`, `/stats`, `/broadcast Hello users`
- Admin uploads: send a video/document/audio with caption `Title | 01`.

## Important limitations
- This bot does **not** scrape or download copyrighted anime from third-party websites. AniList supplies metadata, not video files. Upload only files you own or have permission to distribute, and use authorized download links.
- Auto-copy forwards posts from a Telegram source channel you administer; it does not discover new anime episodes across the internet.
- SQLite storage on free hosting may be ephemeral and free-tier availability/limits can change. Use persistent storage or an external database for reliable long-term data.
