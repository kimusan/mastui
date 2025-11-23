import sqlite3
import json
from pathlib import Path
import logging
from datetime import datetime, timezone, timedelta
import os

log = logging.getLogger(__name__)

class CustomJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle datetime objects.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class Cache:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.initialize_database()

    def _get_conn(self):
        """Get a new database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            log.error(f"Database connection failed: {e}", exc_info=True)
            return None

    def initialize_database(self):
        """Create tables if they don't exist. Called once at startup."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    timeline_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    unread INTEGER NOT NULL,
                    last_status_id TEXT,
                    data TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_id ON posts (timeline_id, id)")
            conn.commit()
        except sqlite3.Error as e:
            log.error(f"Failed to create tables: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    def get_conversations(self):
        """Get all conversations from the database."""
        conn = self._get_conn()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM conversations")
            rows = cursor.fetchall()
            # Manually set 'unread' to a boolean, as it's stored as an integer
            conversations = []
            for row in rows:
                conv = json.loads(row['data'])
                conv['unread'] = bool(conv.get('unread'))
                # Parse created_at back to datetime for consistency
                if conv.get('last_status') and conv['last_status'].get('created_at'):
                    ts_str = conv['last_status']['created_at']
                    if isinstance(ts_str, str):
                        conv['last_status']['created_at'] = datetime.fromisoformat(ts_str)
                conversations.append(conv)
            return conversations
        except sqlite3.Error as e:
            log.error(f"Failed to get conversations: {e}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()

    def bulk_insert_conversations(self, conversations: list):
        """Bulk insert conversations into the database."""
        if not conversations:
            return
        conn = self._get_conn()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            convos_to_insert = []
            for convo in conversations:
                last_status = convo.get('last_status')
                convos_to_insert.append((
                    convo['id'],
                    1 if convo.get('unread') else 0,
                    last_status['id'] if last_status else None,
                    json.dumps(convo, cls=CustomJsonEncoder)
                ))
            
            cursor.executemany(
                "INSERT OR REPLACE INTO conversations (id, unread, last_status_id, data) VALUES (?, ?, ?, ?)",
                convos_to_insert
            )
            conn.commit()
            log.info(f"Inserted/updated {len(convos_to_insert)} conversations")
        except sqlite3.Error as e:
            log.error(f"Failed to bulk insert conversations: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    def mark_conversation_as_read(self, conversation_id: str):
        """Mark a conversation as read in the database."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE conversations SET unread = 0 WHERE id = ?", (conversation_id,))
            conn.commit()
            log.info(f"Marked conversation {conversation_id} as read in cache.")
        except sqlite3.Error as e:
            log.error(f"Failed to mark conversation as read: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    def bulk_insert_posts(self, timeline_id: str, posts: list):
        """Bulk insert posts into the database."""
        if not posts:
            return
        conn = self._get_conn()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            posts_to_insert = []
            for post in posts:
                created_at_str = (post.get('reblog') or post).get('created_at')
                if not created_at_str:
                    log.warning(f"Post {post.get('id')} has no created_at timestamp. Skipping.")
                    continue

                if isinstance(created_at_str, datetime):
                    created_at = created_at_str
                else:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                
                posts_to_insert.append((
                    post['id'],
                    timeline_id,
                    created_at.isoformat(),
                    json.dumps(post, cls=CustomJsonEncoder)
                ))
            
            cursor.executemany(
                "INSERT OR REPLACE INTO posts (id, timeline_id, created_at, data) VALUES (?, ?, ?, ?)",
                posts_to_insert
            )
            conn.commit()
            log.info(f"Inserted/updated {len(posts_to_insert)} posts for timeline '{timeline_id}'")
        except sqlite3.Error as e:
            log.error(f"Failed to bulk insert posts: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    def get_latest_post_timestamp(self, timeline_id: str) -> datetime | None:
        """Get the timestamp of the latest post in the cache for a timeline."""
        conn = self._get_conn()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(created_at) FROM posts WHERE timeline_id = ?", (timeline_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return datetime.fromisoformat(row[0])
            return None
        except sqlite3.Error as e:
            log.error(f"Failed to get latest post timestamp: {e}", exc_info=True)
            return None
        finally:
            if conn:
                conn.close()

    def get_posts(self, timeline_id: str, limit: int = 20, max_id: str = None):
        """Get posts from the database, ordered by ID."""
        conn = self._get_conn()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            query = "SELECT data FROM posts WHERE timeline_id = ?"
            params = [timeline_id]

            if max_id:
                query += " AND id < ?"
                params.append(max_id)

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [json.loads(row['data']) for row in rows]
        except sqlite3.Error as e:
            log.error(f"Failed to get posts: {e}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()

    def delete_post(self, post_id: str):
        """Remove a post from all timelines in the cache."""
        conn = self._get_conn()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()
            log.info(f"Deleted post {post_id} from cache.")
        except sqlite3.Error as e:
            log.error(f"Failed to delete post {post_id} from cache: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    def prune_image_cache(self, days: int = 30) -> int:
        """Prune the image cache of files older than a certain number of days."""
        count = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        image_cache_dir = self.db_path.parent / "image_cache"
        if not image_cache_dir.exists():
            return 0

        for filename in os.listdir(image_cache_dir):
            file_path = image_cache_dir / filename
            try:
                if file_path.is_file():
                    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                    if modified_time < cutoff:
                        file_path.unlink()
                        count += 1
            except Exception as e:
                log.error(f"Error pruning cache file {file_path}: {e}", exc_info=True)
        
        log.info(f"Pruned {count} items from the image cache.")
        return count
