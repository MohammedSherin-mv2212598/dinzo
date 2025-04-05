import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name="food_reels.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            shortcode TEXT,
            title TEXT,
            description TEXT,
            timestamp TEXT,
            account_name TEXT,
            account_followers INTEGER,
            account_category TEXT,
            is_video BOOLEAN,
            has_audio BOOLEAN,
            is_food_related BOOLEAN,
            transcription TEXT,
            processed_data TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        self.conn.commit()

    def post_exists(self, url):
        """Check if a post already exists in the database."""
        self.cursor.execute("SELECT id FROM posts WHERE url = ?", (url,))
        return self.cursor.fetchone() is not None

    def get_post(self, url):
        """Get post data if it exists."""
        self.cursor.execute("SELECT * FROM posts WHERE url = ?", (url,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
            
        # Convert to dictionary
        columns = [description[0] for description in self.cursor.description]
        post_dict = dict(zip(columns, row))
        
        # Parse processed_data JSON if it exists
        if post_dict.get('processed_data'):
            try:
                post_dict['processed_data'] = json.loads(post_dict['processed_data'])
            except:
                pass
                
        return post_dict

    def save_post(self, url, metadata, processed_data=None, is_food_related=None, transcription=None):
        """Save post metadata and processed data to the database."""
        current_time = datetime.now().isoformat()
        
        if self.post_exists(url):
            # Update existing post
            query = """
            UPDATE posts SET 
                title = ?,
                description = ?,
                timestamp = ?,
                account_name = ?,
                account_followers = ?,
                account_category = ?,
                is_video = ?,
                has_audio = ?,
                is_food_related = ?,
                transcription = ?,
                processed_data = ?,
                updated_at = ?
            WHERE url = ?
            """
            self.cursor.execute(query, (
                metadata.get('title', ''),
                metadata.get('description', ''),
                metadata.get('timestamp', ''),
                metadata.get('account_name', ''),
                metadata.get('account_followers', 0),
                metadata.get('account_category', ''),
                metadata.get('is_video', False),
                metadata.get('has_audio', False),
                is_food_related,
                transcription,
                json.dumps(processed_data) if processed_data else None,
                current_time,
                url
            ))
        else:
            # Insert new post
            query = """
            INSERT INTO posts (
                url, shortcode, title, description, timestamp, 
                account_name, account_followers, account_category,
                is_video, has_audio, is_food_related, transcription, processed_data, 
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.cursor.execute(query, (
                url,
                metadata.get('shortcode', ''),
                metadata.get('title', ''),
                metadata.get('description', ''),
                metadata.get('timestamp', ''),
                metadata.get('account_name', ''),
                metadata.get('account_followers', 0),
                metadata.get('account_category', ''),
                metadata.get('is_video', False),
                metadata.get('has_audio', False),
                is_food_related,
                transcription,
                json.dumps(processed_data) if processed_data else None,
                current_time,
                current_time
            ))
        
        self.conn.commit()
        return True

    def update_transcription(self, url, transcription, has_audio=True):
        """Update only the transcription data for a post."""
        if not self.post_exists(url):
            return False
            
        current_time = datetime.now().isoformat()
        
        query = """
        UPDATE posts SET 
            has_audio = ?,
            transcription = ?,
            updated_at = ?
        WHERE url = ?
        """
        
        self.cursor.execute(query, (
            has_audio,
            transcription,
            current_time,
            url
        ))
        
        self.conn.commit()
        return True

    def close(self):
        """Close the database connection."""
        self.conn.close()