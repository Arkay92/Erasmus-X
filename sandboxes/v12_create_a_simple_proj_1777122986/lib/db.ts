import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const dbPath = path.resolve(process.cwd(), 'data', 'tasks.db');
fs.mkdirSync(path.dirname(dbPath), { recursive: true });

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');

export const query = (sql: string, params: any[] = []): any[] => {
  const stmt = db.prepare(sql);
  return stmt.all(...params);
};

export const execute = (sql: string, params: any[] = []): any => {
  const stmt = db.prepare(sql);
  const result = stmt.run(...params);
  return { id: result.lastInsertRowid, changes: result.changes };
};
