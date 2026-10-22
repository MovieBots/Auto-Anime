# Anime Telegram Bot (Koyeb-ready starter)

Features:
- Anime search, posters and metadata from AniList (official public GraphQL API)
- Manual admin upload of video/document/audio to Telegram using caption `Anime Name | 01`
- Admin can add a legal direct download URL using `/add Anime Name | 01 | https://...`
- List saved episode records with `/episodes`
- Dockerfile for Koyeb deployment

## Important limits
- AniList provides anime metadata, not video files. This bot does **not** scrape or automatically download copyrighted anime from third-party websites.
- “Automatic” in this starter means automatic anime metadata search. To auto-publish new episodes, connect a licensed source/API or a channel you own and have permission to forward from.
- SQLite on an ephemeral free container may be lost during replacement/redeployment. Use a persistent database/storage service if you need reliable long-term file records. Telegram `file_id`s only work with the same bot.
- Large file sending/receiving limits depend on Telegram Bot API and current Telegram restrictions.

## Setup
1. Create a bot with `@BotFather` and copy its token.
2. Get your Telegram numeric user ID from a trusted ID bot, then add it to `ADMIN_IDS`.
3. Push all repository files to a GitHub repository. Do not upload your real token or `.env`.
4. On Koyeb, create App > Service > GitHub, select the repo, choose Dockerfile builder, and deploy.
5. Add environment variables `BOT_TOKEN` and `ADMIN_IDS` in Koyeb service settings. Redeploy.
6. Open your bot and send `/start`.

## Admin commands
- `/add Anime Name | 01 | https://your-authorized-direct-link`
- `/delete Anime Name | 01`
- To upload a file, send video/document/audio to the bot with caption `Anime Name | 01`.

## User commands
- `/start`
- `/search Naruto` or simply send an anime title
- `/episodes`

## Koyeb
This is a long-running polling bot and has no web port. Deploy as a worker/background service if offered by the current Koyeb UI. If the selected Koyeb service requires an HTTP port, this polling-only starter may not pass web-service health checks; use a worker option or add a health web server. Free-instance availability/limits can change.
