"""Register all deterministic feature packs into the brain's registry."""
from core.vector_store import HypervectorDB
from core import config



def register_feature_packs(brain=None, save=True, verbose=True):
    """Register deterministic feature packs into the provided brain."""
    if brain is None:
        brain = HypervectorDB(filename=config.BRAIN_STORAGE_PATH)

    # â”€â”€â”€ Todo App Pack â”€â”€â”€
    brain.register_feature_pack("todo", {
        "feature": "todo",
        "stack": "nextjs-app-router",
        "files": [
            {
                "path": "app/page.tsx",
                "content": "import TodoList from '@/components/TodoList';\n\nexport default function Page() {\n  return (\n    <main className=\"p-8 max-w-2xl mx-auto\">\n      <h1 className=\"text-3xl font-bold mb-6\">Task Manager</h1>\n      <TodoList />\n    </main>\n  )\n}\n"
            },
            {
                "path": "components/TodoList.tsx",
                "content": "'use client';\nimport { useState, useEffect } from 'react';\n\ninterface Task { id: number; text: string; status: string; }\n\nexport default function TodoList() {\n  const [tasks, setTasks] = useState<Task[]>([]);\n  const [newTask, setNewTask] = useState('');\n\n  useEffect(() => {\n    fetch('/api/tasks').then(r => r.json()).then(data => setTasks(data.rows || []));\n  }, []);\n\n  const addTask = async (e: React.FormEvent) => {\n    e.preventDefault();\n    if (!newTask.trim()) return;\n    const res = await fetch('/api/tasks', {\n      method: 'POST',\n      headers: { 'Content-Type': 'application/json' },\n      body: JSON.stringify({ text: newTask })\n    });\n    if (res.ok) {\n      const saved = await res.json();\n      setTasks(prev => [{ id: saved.id, text: newTask, status: 'pending' }, ...prev]);\n      setNewTask('');\n    }\n  };\n\n  const toggleTask = async (id: number) => {\n    const task = tasks.find(t => t.id === id);\n    if (!task) return;\n    const newStatus = task.status === 'pending' ? 'done' : 'pending';\n    await fetch(`/api/tasks/${id}`, {\n      method: 'PATCH',\n      headers: { 'Content-Type': 'application/json' },\n      body: JSON.stringify({ status: newStatus })\n    });\n    setTasks(prev => prev.map(t => t.id === id ? { ...t, status: newStatus } : t));\n  };\n\n  const deleteTask = async (id: number) => {\n    await fetch(`/api/tasks/${id}`, { method: 'DELETE' });\n    setTasks(prev => prev.filter(t => t.id !== id));\n  };\n\n  return (\n    <div>\n      <form onSubmit={addTask} className=\"flex gap-2 mb-4\">\n        <input type=\"text\" value={newTask} onChange={(e) => setNewTask(e.target.value)}\n          placeholder=\"Add a new task...\" className=\"border p-2 flex-grow rounded\" />\n        <button type=\"submit\" className=\"bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700\">Add</button>\n      </form>\n      <ul className=\"space-y-2\">\n        {tasks.map(task => (\n          <li key={task.id} className=\"p-3 border rounded flex justify-between items-center\">\n            <span className={task.status === 'done' ? 'line-through text-gray-400' : ''}>{task.text}</span>\n            <div className=\"flex gap-2\">\n              <button onClick={() => toggleTask(task.id)} className=\"text-sm px-2 py-1 rounded bg-green-100 hover:bg-green-200\">\n                {task.status === 'done' ? 'Undo' : 'Done'}\n              </button>\n              <button onClick={() => deleteTask(task.id)} className=\"text-sm px-2 py-1 rounded bg-red-100 hover:bg-red-200\">\n                Delete\n              </button>\n            </div>\n          </li>\n        ))}\n        {tasks.length === 0 && <li className=\"text-gray-500 text-center py-4\">No tasks yet. Add one above!</li>}\n      </ul>\n    </div>\n  );\n}\n"
            },
            {
                "path": "app/api/tasks/route.ts",
                "content": "import { NextResponse } from 'next/server';\nimport { query, execute } from '@/lib/db';\n\nconst ensureTable = async () => {\n  await execute(`CREATE TABLE IF NOT EXISTS tasks (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    text TEXT NOT NULL,\n    status TEXT DEFAULT 'pending',\n    created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n  )`);\n};\n\nexport async function GET() {\n  try {\n    await ensureTable();\n    const rows = await query('SELECT * FROM tasks ORDER BY id DESC');\n    return NextResponse.json({ success: true, rows });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n\nexport async function POST(request: Request) {\n  try {\n    await ensureTable();\n    const { text } = await request.json();\n    if (!text || !text.trim()) {\n      return NextResponse.json({ success: false, error: 'Task text required' }, { status: 400 });\n    }\n    const result = await execute('INSERT INTO tasks (text) VALUES (?)', [text.trim()]) as any;\n    return NextResponse.json({ success: true, id: result.id });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n"
            },
            {
                "path": "app/api/tasks/[id]/route.ts",
                "content": "import { NextResponse } from 'next/server';\nimport { execute } from '@/lib/db';\n\nexport async function PATCH(request: Request, { params }: { params: { id: string } }) {\n  try {\n    const { status } = await request.json();\n    await execute('UPDATE tasks SET status = ? WHERE id = ?', [status, params.id]);\n    return NextResponse.json({ success: true });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n\nexport async function DELETE(_request: Request, { params }: { params: { id: string } }) {\n  try {\n    await execute('DELETE FROM tasks WHERE id = ?', [params.id]);\n    return NextResponse.json({ success: true });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n"
            },
            {
                "path": "lib/db.ts",
                "content": "import Database from 'better-sqlite3';\nimport path from 'path';\nimport fs from 'fs';\n\nconst dbPath = path.resolve(process.cwd(), 'data', 'tasks.db');\nfs.mkdirSync(path.dirname(dbPath), { recursive: true });\n\nconst db = new Database(dbPath);\ndb.pragma('journal_mode = WAL');\n\nexport const query = (sql: string, params: any[] = []): any[] => {\n  const stmt = db.prepare(sql);\n  return stmt.all(...params);\n};\n\nexport const execute = (sql: string, params: any[] = []): any => {\n  const stmt = db.prepare(sql);\n  const result = stmt.run(...params);\n  return { id: result.lastInsertRowid, changes: result.changes };\n};\n"
            },
            {
                "path": "app/layout.tsx",
                "content": "import type { Metadata } from 'next';\nimport './globals.css';\n\nexport const metadata: Metadata = {\n  title: 'Task Manager',\n  description: 'A simple todo list application built with Next.js',\n};\n\nexport default function RootLayout({ children }: { children: React.ReactNode }) {\n  return (\n    <html lang=\"en\">\n      <body className=\"bg-gray-50 min-h-screen\">{children}</body>\n    </html>\n  );\n}\n"
            },
            {
                "path": "globals.css",
                "content": "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n\nbody {\n  font-family: 'Inter', system-ui, -apple-system, sans-serif;\n}\n"
            }
        ]
    })

    # â”€â”€â”€ DB Pack â”€â”€â”€
    brain.register_feature_pack("db", {
        "feature": "db",
        "stack": "nextjs-app-router",
        "files": [
            {
                "path": "lib/db.ts",
                "content": "import Database from 'better-sqlite3';\nimport path from 'path';\nimport fs from 'fs';\n\nconst dbPath = path.resolve(process.cwd(), 'data', 'app.db');\nfs.mkdirSync(path.dirname(dbPath), { recursive: true });\n\nconst db = new Database(dbPath);\ndb.pragma('journal_mode = WAL');\n\nexport const query = (sql: string, params: any[] = []): any[] => {\n  const stmt = db.prepare(sql);\n  return stmt.all(...params);\n};\n\nexport const execute = (sql: string, params: any[] = []): any => {\n  const stmt = db.prepare(sql);\n  const result = stmt.run(...params);\n  return { id: result.lastInsertRowid, changes: result.changes };\n};\n"
            }
        ]
    })

    # â”€â”€â”€ Dashboard Pack â”€â”€â”€
    brain.register_feature_pack("dashboard", {
        "feature": "dashboard",
        "stack": "nextjs-app-router",
        "files": [
            {
                "path": "app/dashboard/page.tsx",
                "content": "import { query } from '@/lib/db';\n\nexport default async function DashboardPage() {\n  const stats = await query('SELECT count(*) as total FROM tasks') as any[];\n  const total = stats[0]?.total || 0;\n\n  return (\n    <div className=\"p-8\">\n      <h1 className=\"text-2xl font-bold mb-6\">Dashboard</h1>\n      <div className=\"grid grid-cols-1 md:grid-cols-3 gap-6\">\n        <div className=\"p-6 bg-blue-50 border border-blue-200 rounded-lg\">\n          <p className=\"text-blue-600 font-medium\">Total Tasks</p>\n          <p className=\"text-3xl font-bold\">{total}</p>\n        </div>\n      </div>\n    </div>\n  );\n}\n"
            }
        ]
    })

    # â”€â”€â”€ Auth Pack â”€â”€â”€
    brain.register_feature_pack("auth", {
        "feature": "auth",
        "stack": "nextjs-app-router",
        "files": [
            {
                "path": "app/api/auth/[...nextauth]/route.ts",
                "content": "import NextAuth from 'next-auth';\nimport CredentialsProvider from 'next-auth/providers/credentials';\nimport { query } from '@/lib/db';\n\nconst handler = NextAuth({\n  providers: [\n    CredentialsProvider({\n      name: 'Credentials',\n      credentials: {\n        username: { label: 'Username', type: 'text' },\n        password: { label: 'Password', type: 'password' }\n      },\n      async authorize(credentials) {\n        if (!credentials?.username) return null;\n        const users = await query('SELECT * FROM users WHERE username = ?', [credentials.username]) as any[];\n        if (users && users.length > 0) {\n          return { id: users[0].id.toString(), name: users[0].username };\n        }\n        return null;\n      }\n    })\n  ],\n  secret: process.env.NEXTAUTH_SECRET || 'dev-secret'\n});\n\nexport { handler as GET, handler as POST };\n"
            }
        ]
    })

    if save:
        brain.save()
    if verbose: print(f"\\n[+] All feature packs registered.")
    if verbose: print(f"    Packs: {list(brain.feature_packs.keys())}")

    # Verification
    for name in ['todo', 'db', 'dashboard', 'auth']:
        pack = brain.get_feature_pack(name)
        if pack:
            if verbose: print(f"    OK {name}: {len(pack.get('files', []))} files")
        else:
            if verbose: print(f"    MISSING {name}: NOT FOUND")


    return brain


if __name__ == "__main__":
    register_feature_packs()
