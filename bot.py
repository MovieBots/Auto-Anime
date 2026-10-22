import os
import logging
import sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv('BOT_TOKEN', '').strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()}
DB_PATH = os.getenv('DB_PATH', 'animebot.db')
SOURCE_CHANNEL_ID = os.getenv('SOURCE_CHANNEL_ID', '').strip()
TARGET_CHANNEL_ID = os.getenv('TARGET_CHANNEL_ID', '').strip()
ANILIST_URL = 'https://graphql.anilist.co'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('animebot')


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, title TEXT, PRIMARY KEY(user_id,title))')
    conn.execute('''CREATE TABLE IF NOT EXISTS anime (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, episode TEXT NOT NULL,
        file_id TEXT, file_type TEXT, download_url TEXT, source TEXT DEFAULT 'manual',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(title, episode))''')
    conn.commit()
    return conn


def anilist_search(query):
    gql = '''query ($search: String) { Page(page: 1, perPage: 6) { media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id title { romaji english native } coverImage { large } description(asHtml: false)
      episodes status seasonYear format averageScore siteUrl
    } } }'''
    body = json.dumps({'query': gql, 'variables': {'search': query}}).encode()
    req = Request(ANILIST_URL, data=body, headers={'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'AnimeTelegramBot/1.0'})
    with urlopen(req, timeout=15) as response:
        payload = json.loads(response.read().decode())
    return payload.get('data', {}).get('Page', {}).get('media', [])


def title_of(media):
    t = media.get('title') or {}
    return t.get('english') or t.get('romaji') or t.get('native') or 'Unknown anime'


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🔎 Search Anime', callback_data='search_help'), InlineKeyboardButton('📥 Episodes', callback_data='episodes')],
        [InlineKeyboardButton('ℹ️ Help', callback_data='help')]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    conn.execute('INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)', (update.effective_user.id, update.effective_user.username or ''))
    conn.commit(); conn.close()
    await update.effective_message.reply_text(
        '👋 Welcome to Anime God-style bot!\n\nAnime ka naam bhejkar search karein. Admin episode file ya legal download link bhi add kar sakta hai.\n\n⚠️ Anime info AniList se aati hai; video files automatically kisi third-party site se download nahi hoti.',
        reply_markup=main_menu())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ('Commands:\n/start — start bot\n/search Naruto — anime search\n/episodes — saved episodes\n'
            '/add Naruto | 01 | https://example.com/legal-video.mp4 — admin: legal direct link add karein\n'
            '/delete Naruto | 01 — admin: saved episode remove karein\n/stats — admin statistics\n/broadcast message — admin announcement\n/fav Naruto — favorite save karein\n/favorites — apne favorites dekhein\n\n'
            'Manual upload: admin bot ko video/document bheje, caption is format mein likhe: Naruto | 01')
    await update.effective_message.reply_text(text)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args).strip()
    if not query:
        await update.effective_message.reply_text('Search ke liye likhein: /search Naruto')
        return
    await update.effective_message.reply_text('🔎 Anime search ho raha hai...')
    try:
        results = anilist_search(query)
    except Exception as e:
        log.exception('AniList search failed')
        await update.effective_message.reply_text('Search abhi kaam nahi kar raha. Thodi der baad try karein.')
        return
    if not results:
        await update.effective_message.reply_text('Koi anime nahi mila. Naam dobara check karein.')
        return
    for m in results:
        title = title_of(m)
        description = (m.get('description') or 'Description available nahi hai.').replace('<br>', '\n')
        if len(description) > 550:
            description = description[:547] + '...'
        details = f"🎬 <b>{title}</b>\n📺 Episodes: {m.get('episodes') or 'Unknown'}\n📅 Year: {m.get('seasonYear') or 'Unknown'}\n⭐ Score: {m.get('averageScore') or 'N/A'}/100\n\n{description}\n\n<a href=\"{m.get('siteUrl', 'https://anilist.co')}\">AniList details</a>"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('📥 Available Episodes', callback_data='episodes')]])
        cover = (m.get('coverImage') or {}).get('large')
        try:
            if cover:
                await update.effective_message.reply_photo(cover, caption=details, parse_mode='HTML', reply_markup=keyboard)
            else:
                await update.effective_message.reply_text(details, parse_mode='HTML', reply_markup=keyboard, disable_web_page_preview=True)
        except Exception:
            await update.effective_message.reply_text(details, parse_mode='HTML', reply_markup=keyboard, disable_web_page_preview=True)


async def episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    rows = conn.execute('SELECT title, episode, file_id, file_type, download_url FROM anime ORDER BY title, episode LIMIT 30').fetchall()
    conn.close()
    if not rows:
        await update.effective_message.reply_text('Abhi koi episode add nahi hua hai. Admin episode upload ya /add se link add kar sakta hai.')
        return
    for r in rows:
        msg = f"🎬 {r['title']} — Episode {r['episode']}"
        if r['file_id']:
            try:
                if r['file_type'] == 'video':
                    await update.effective_message.reply_video(r['file_id'], caption=msg)
                elif r['file_type'] == 'audio':
                    await update.effective_message.reply_audio(r['file_id'], caption=msg)
                else:
                    await update.effective_message.reply_document(r['file_id'], caption=msg)
            except Exception:
                await update.effective_message.reply_text(msg + '\nSaved Telegram file send nahi ho payi.')
        elif r['download_url']:
            await update.effective_message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬇️ Direct Download', url=r['download_url'])]]))
        else:
            await update.effective_message.reply_text(msg + '\nDownload link abhi add nahi hai.')


async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.effective_message.reply_text('Ye command sirf bot admin use kar sakta hai.')
        return
    raw = ' '.join(context.args)
    parts = [p.strip() for p in raw.split('|')]
    if len(parts) != 3 or not parts[0] or not parts[1] or not parts[2].startswith(('https://', 'http://')):
        await update.effective_message.reply_text('Format: /add Anime Name | 01 | https://your-authorized-download-link')
        return
    conn = db()
    conn.execute('INSERT INTO anime(title, episode, download_url, source) VALUES(?,?,?,?) ON CONFLICT(title,episode) DO UPDATE SET download_url=excluded.download_url, source=excluded.source', (parts[0], parts[1], parts[2], 'manual-link'))
    conn.commit(); conn.close()
    await update.effective_message.reply_text(f'✅ Saved: {parts[0]} — Episode {parts[1]}')


async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.effective_message.reply_text('Ye command sirf bot admin use kar sakta hai.')
        return
    parts = [p.strip() for p in ' '.join(context.args).split('|')]
    if len(parts) != 2:
        await update.effective_message.reply_text('Format: /delete Anime Name | 01'); return
    conn = db(); cur = conn.execute('DELETE FROM anime WHERE title=? AND episode=?', (parts[0], parts[1])); conn.commit(); conn.close()
    await update.effective_message.reply_text('🗑️ Episode deleted.' if cur.rowcount else 'Episode nahi mila.')


async def admin_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if update.effective_user.id not in ADMIN_IDS:
        return
    caption = (msg.caption or '').strip()
    parts = [p.strip() for p in caption.split('|')]
    if len(parts) != 2 or not all(parts):
        await msg.reply_text('Video/document ke caption mein likhein: Anime Name | 01')
        return
    file_id = None; file_type = None
    if msg.video:
        file_id = msg.video.file_id; file_type = 'video'
    elif msg.document:
        file_id = msg.document.file_id; file_type = 'document'
    elif msg.audio:
        file_id = msg.audio.file_id; file_type = 'audio'
    if not file_id:
        await msg.reply_text('Video, document ya audio file bhejein.'); return
    conn = db()
    conn.execute('INSERT INTO anime(title, episode, file_id, file_type, source) VALUES(?,?,?,?,?) ON CONFLICT(title,episode) DO UPDATE SET file_id=excluded.file_id, file_type=excluded.file_type, source=excluded.source', (parts[0], parts[1], file_id, file_type, 'manual-upload'))
    conn.commit(); conn.close()
    await msg.reply_text(f'✅ File saved: {parts[0]} — Episode {parts[1]}')


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == 'search_help':
        await q.message.reply_text('Anime search ke liye likhein: /search Demon Slayer')
    elif q.data == 'episodes':
        await episodes(update, context)
    elif q.data == 'help':
        await help_cmd(update, context)


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and update.effective_user.id in ADMIN_IDS and (update.effective_message.video or update.effective_message.document):
        await admin_upload(update, context); return
    query = (update.effective_message.text or '').strip()
    if query and not query.startswith('/'):
        context.args = query.split()
        await search(update, context)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.effective_message.reply_text('Admin only.'); return
    conn = db()
    users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    episodes_count = conn.execute('SELECT COUNT(*) FROM anime').fetchone()[0]
    favorites_count = conn.execute('SELECT COUNT(*) FROM favorites').fetchone()[0]
    conn.close()
    await update.effective_message.reply_text(f'📊 Bot Stats\n👥 Users: {users}\n🎬 Episodes: {episodes_count}\n⭐ Favorites: {favorites_count}')

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.effective_message.reply_text('Admin only.'); return
    message = ' '.join(context.args).strip()
    if not message:
        await update.effective_message.reply_text('Format: /broadcast Your message'); return
    conn = db(); users = conn.execute('SELECT user_id FROM users').fetchall(); conn.close()
    sent = 0
    for row in users:
        try:
            await context.bot.send_message(chat_id=row['user_id'], text=message)
            sent += 1
        except Exception as e:
            log.warning('Broadcast failed for %s: %s', row['user_id'], e)
    await update.effective_message.reply_text(f'📣 Broadcast complete. Sent: {sent}/{len(users)}')

async def favorite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = ' '.join(context.args).strip()
    if not title:
        await update.effective_message.reply_text('Format: /fav Naruto'); return
    conn = db()
    conn.execute('INSERT OR IGNORE INTO favorites(user_id,title) VALUES(?,?)', (update.effective_user.id, title))
    conn.commit(); conn.close()
    await update.effective_message.reply_text(f'⭐ Favorite saved: {title}')

async def favorites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db(); rows = conn.execute('SELECT title FROM favorites WHERE user_id=? ORDER BY title', (update.effective_user.id,)).fetchall(); conn.close()
    if not rows:
        await update.effective_message.reply_text('Abhi favorites empty hain. /fav Naruto use karein.'); return
    await update.effective_message.reply_text('⭐ Your favorites:\n' + '\n'.join('• ' + r['title'] for r in rows))

async def source_channel_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg or not SOURCE_CHANNEL_ID or not TARGET_CHANNEL_ID:
        return
    if str(msg.chat_id) != SOURCE_CHANNEL_ID:
        return
    try:
        await context.bot.copy_message(chat_id=int(TARGET_CHANNEL_ID), from_chat_id=msg.chat_id, message_id=msg.message_id)
        log.info('Copied authorized source channel post %s', msg.message_id)
    except Exception:
        log.exception('Auto-forward failed; check bot admin permissions and channel IDs')


def main():
    if not TOKEN:
        raise RuntimeError('BOT_TOKEN environment variable is missing')
    db().close()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('search', search))
    app.add_handler(CommandHandler('episodes', episodes))
    app.add_handler(CommandHandler('add', add_link))
    app.add_handler(CommandHandler('delete', delete_episode))
    app.add_handler(CommandHandler('stats', stats_cmd))
    app.add_handler(CommandHandler('broadcast', broadcast_cmd))
    app.add_handler(CommandHandler('fav', favorite_cmd))
    app.add_handler(CommandHandler('favorites', favorites_cmd))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, source_channel_forward))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL | filters.AUDIO, admin_upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))
    log.info('Bot starting with polling')
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
