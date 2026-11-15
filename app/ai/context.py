"""Bounded model context backed by a durable conversation journal."""
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from app.ai.response import has_readable_text


@dataclass
class ConversationMessage:
    role: str
    content: str


class ConversationContext:
    MAX_MESSAGES = 60

    def __init__(self, storage_path=None, max_turns=30, token_budget=6000):
        self.max_messages = max(10, int(max_turns)) * 2
        self.token_budget = max(512, int(token_budget))
        self.storage_path = Path(storage_path) if storage_path else None
        self.messages: list[ConversationMessage] = []
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as db:
                db.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)')
                rows = db.execute('SELECT role, content FROM messages ORDER BY id DESC LIMIT ?', (self.max_messages,)).fetchall()
            self.messages = [ConversationMessage(*row) for row in reversed(rows)]

    def _connect(self):
        return closing(sqlite3.connect(self.storage_path, isolation_level=None))

    @staticmethod
    def _plain_assistant(message):
        try:
            parsed = json.loads(message)
            if isinstance(parsed, dict) and isinstance(parsed.get('response'), str):
                return parsed['response']
        except (ValueError, TypeError):
            pass
        return message

    def _add(self, role, content):
        if role == 'assistant':
            content = self._plain_assistant(content)
        self.messages.append(ConversationMessage(role, content))
        if self.storage_path:
            with self._connect() as db:
                db.execute('INSERT INTO messages(role,content,created_at) VALUES(?,?,?)',
                           (role, content, datetime.now(timezone.utc).isoformat()))
        self.messages = self.messages[-self.max_messages:]

    def add_user_message(self, message):
        self._add('user', message)

    def add_assistant_message(self, message):
        self._add('assistant', message)

    def get_messages(self):
        messages = [{'role': m.role, 'content': m.content} for m in self.messages
                    if m.role != 'assistant' or has_readable_text(m.content)]
        if messages and messages[0]['role'] == 'assistant':
            messages.pop(0)
        # Only trim model input. Keep the entire history on disk.
        budget = self.token_budget * 3
        while len(messages) > 2 and sum(len(m['content'].encode('utf-8')) for m in messages) > budget:
            messages.pop(0)
            if messages and messages[0]['role'] == 'assistant':
                messages.pop(0)
        return messages

    def relevant_history(self, query, limit=4):
        if not self.storage_path:
            return ''
        stop = {'that', 'this', 'what', 'when', 'where', 'with', 'have', 'about', 'remember', 'please', 'your', 'from', 'would', 'could', 'were', 'there', 'which'}
        terms = {w for w in re.findall(r'\w+', query.lower()) if len(w) > 3} - stop
        if not terms:
            return ''
        with self._connect() as db:
            rows = db.execute('SELECT id, role, content FROM messages WHERE id <= COALESCE((SELECT MAX(id) FROM messages),0)-? ORDER BY id DESC LIMIT 2000', (len(self.get_messages()),)).fetchall()
            scores = []
            for row_id, role, content in rows:
                if role != 'user':
                    continue
                score = len(terms & set(re.findall(r'\w+', content.lower())))
                if score:
                    scores.append((score, row_id, content))
            excerpts = []
            for _, row_id, content in sorted(scores, reverse=True)[:limit]:
                reply = db.execute("SELECT content FROM messages WHERE id>? AND role='assistant' ORDER BY id LIMIT 1", (row_id,)).fetchone()
                excerpts.append(f'User: {content[:700]}\nHornet: {reply[0][:700] if reply else ""}')
        return '\n\n'.join(excerpts)[:5000]

    def clear(self):
        self.messages.clear()
        if self.storage_path:
            with self._connect() as db:
                db.execute('DELETE FROM messages')

    def checkpoint(self):
        if self.storage_path:
            with self._connect() as db:
                row_id = db.execute('SELECT COALESCE(MAX(id),0) FROM messages').fetchone()[0]
        else:
            row_id = 0
        return row_id, list(self.messages)

    def rollback(self, checkpoint):
        row_id, messages = checkpoint
        if self.storage_path:
            with self._connect() as db:
                db.execute('DELETE FROM messages WHERE id>?', (row_id,))
        self.messages = messages
