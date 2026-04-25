import json
from core.vector_store import HypervectorDB

brain = HypervectorDB()

todo_pack = {
    "feature": "todo",
    "stack": "nextjs-app-router",
    "files": [
        {
            "path": "app/page.tsx",
            "content": "import TodoList from '@/components/TodoList';\n\nexport default function Page() {\n  return (\n    <main className=\"p-8 max-w-2xl mx-auto\">\n      <h1 className=\"text-3xl font-bold mb-6\">Task Manager</h1>\n      <TodoList />\n    </main>\n  )\n}\n"
        },
        {
            "path": "components/TodoList.tsx",
            "content": "'use client';\nimport { useState, useEffect } from 'react';\n\ninterface Task { id: number; text: string; status: string; }\n\nexport default function TodoList() {\n  const [tasks, setTasks] = useState<Task[]>([]);\n  const [newTask, setNewTask] = useState('');\n\n  useEffect(() => {\n    fetch('/api/tasks').then(r => r.json()).then(data => setTasks(data.rows || []));\n  }, []);\n\n  const addTask = async (e: React.FormEvent) => {\n    e.preventDefault();\n    if (!newTask.trim()) return;\n    const res = await fetch('/api/tasks', {\n      method: 'POST',\n      headers: { 'Content-Type': 'application/json' },\n      body: JSON.stringify({ text: newTask })\n    });\n    if (res.ok) {\n      const saved = await res.json();\n      setTasks(prev => [{ id: saved.id, text: newTask, status: 'pending' }, ...prev]);\n      setNewTask('');\n    }\n  };\n\n  const toggleTask = async (id: number) => {\n    const task = tasks.find(t => t.id === id);\n    if (!task) return;\n    const newStatus = task.status === 'pending' ? 'done' : 'pending';\n    await fetch(`/api/tasks/${id}`, {\n      method: 'PATCH',\n      headers: { 'Content-Type': 'application/json' },\n      body: JSON.stringify({ status: newStatus })\n    });\n    setTasks(prev => prev.map(t => t.id === id ? { ...t, status: newStatus } : t));\n  };\n\n  const deleteTask = async (id: number) => {\n    await fetch(`/api/tasks/${id}`, { method: 'DELETE' });\n    setTasks(prev => prev.filter(t => t.id !== id));\n  };\n\n  return (\n    <div>\n      <form onSubmit={addTask} className=\"flex gap-2 mb-4\">\n        <input\n          type=\"text\"\n          value={newTask}\n          onChange={(e) => setNewTask(e.target.value)}\n          placeholder=\"Add a new task...\"\n          className=\"border p-2 flex-grow rounded\"\n        />\n        <button type=\"submit\" className=\"bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700\">Add</button>\n      </form>\n      <ul className=\"space-y-2\">\n        {tasks.map(task => (\n          <li key={task.id} className=\"p-3 border rounded flex justify-between items-center\">\n            <span className={task.status === 'done' ? 'line-through text-gray-400' : ''}>{task.text}</span>\n            <div className=\"flex gap-2\">\n              <button onClick={() => toggleTask(task.id)} className=\"text-sm px-2 py-1 rounded bg-green-100 hover:bg-green-200\">\n                {task.status === 'done' ? 'Undo' : 'Done'}\n              </button>\n              <button onClick={() => deleteTask(task.id)} className=\"text-sm px-2 py-1 rounded bg-red-100 hover:bg-red-200\">\n                Delete\n              </button>\n            </div>\n          </li>\n        ))}\n        {tasks.length === 0 && <li className=\"text-gray-500 text-center py-4\">No tasks yet. Add one above!</li>}\n      </ul>\n    </div>\n  );\n}\n"
        },
        {
            "path": "app/api/tasks/route.ts",
            "content": "import { NextResponse } from 'next/server';\nimport { query, execute } from '@/lib/db';\n\nconst ensureTable = async () => {\n  await execute(`CREATE TABLE IF NOT EXISTS tasks (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    text TEXT NOT NULL,\n    status TEXT DEFAULT 'pending',\n    created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n  )`);\n};\n\nexport async function GET() {\n  try {\n    await ensureTable();\n    const rows = await query('SELECT * FROM tasks ORDER BY id DESC');\n    return NextResponse.json({ success: true, rows });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n\nexport async function POST(request: Request) {\n  try {\n    await ensureTable();\n    const { text } = await request.json();\n    if (!text || !text.trim()) {\n      return NextResponse.json({ success: false, error: 'Task text is required' }, { status: 400 });\n    }\n    const result = await execute('INSERT INTO tasks (text) VALUES (?)', [text.trim()]) as any;\n    return NextResponse.json({ success: true, id: result.id });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n"
        },
        {
            "path": "app/api/tasks/[id]/route.ts",
            "content": "import { NextResponse } from 'next/server';\nimport { execute } from '@/lib/db';\n\nexport async function PATCH(request: Request, { params }: { params: { id: string } }) {\n  try {\n    const { status } = await request.json();\n    await execute('UPDATE tasks SET status = ? WHERE id = ?', [status, params.id]);\n    return NextResponse.json({ success: true });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n\nexport async function DELETE(_request: Request, { params }: { params: { id: string } }) {\n  try {\n    await execute('DELETE FROM tasks WHERE id = ?', [params.id]);\n    return NextResponse.json({ success: true });\n  } catch (error: any) {\n    return NextResponse.json({ success: false, error: error.message }, { status: 500 });\n  }\n}\n"
        },
        {
            "path": "lib/db.ts",
            "content": "import Database from 'better-sqlite3';\nimport path from 'path';\n\nconst dbPath = path.resolve(process.cwd(), 'data', 'tasks.db');\n\n// Ensure data directory exists\nimport fs from 'fs';\nfs.mkdirSync(path.dirname(dbPath), { recursive: true });\n\nconst db = new Database(dbPath);\ndb.pragma('journal_mode = WAL');\n\nexport const query = (sql: string, params: any[] = []): any[] => {\n  const stmt = db.prepare(sql);\n  return stmt.all(...params);\n};\n\nexport const execute = (sql: string, params: any[] = []): any => {\n  const stmt = db.prepare(sql);\n  const result = stmt.run(...params);\n  return { id: result.lastInsertRowid, changes: result.changes };\n};\n"
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
}

json_str = json.dumps(todo_pack)
doc = f"[FEATURE_PACK] FEATURE: todo CONTENT: {json_str}"
brain.add_document(doc)
brain.save()
print(f"Injected todo pack ({len(json_str)} chars). Brain saved.")

# Verify
results = brain.search("[FEATURE_PACK] FEATURE: todo", threshold=0.01, top_k=5)
for score, d in results:
    if "[FEATURE_PACK]" in d and "FEATURE: todo" in d:
        print(f"VERIFIED: Todo pack found at score {score:.4f}")
        break
else:
    print("WARNING: Todo pack NOT found after injection!")
