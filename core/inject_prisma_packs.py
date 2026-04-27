"""
Prisma-based feature packs for full-stack development.
Register complete, production-grade packs with proper ORM integration.
"""
from core.vector_store import HypervectorDB
from core import config


def register_prisma_packs(brain=None, save=True, verbose=True):
    """Register this module's built-in feature packs into the provided brain."""
    if brain is None:
        brain = HypervectorDB(filename=config.BRAIN_STORAGE_PATH)

    # â”€â”€â”€ PRISMA TODO APP PACK (Complete Full-Stack) â”€â”€â”€
    brain.register_feature_pack("prisma_todo", {
        "feature": "prisma_todo",
        "stack": "nextjs-app-router|prisma|typescript",
        "critical_files": [
            "app/layout.tsx",
            "app/page.tsx",
            "components/TodoList.tsx",
            "components/TodoItem.tsx",
            "app/api/tasks/route.ts",
            "app/api/tasks/[id]/route.ts",
            "lib/db.ts",
            "prisma/schema.prisma",
            "globals.css"
        ],
        "files": [
            {
                "path": "prisma/schema.prisma",
                "content": """// This is your Prisma schema file,
    // learn more about it in the docs: https://pris.ly/d/prisma-schema

    generator client {
      provider = "prisma-client-js"
    }

    datasource db {
      provider = "sqlite"
      url      = env("DATABASE_URL")
    }

    model Task {
      id        Int     @id @default(autoincrement())
      text      String
      status    String  @default("pending")
      createdAt DateTime @default(now())
      updatedAt DateTime @updatedAt
    }
    """
            },
            {
                "path": "lib/db.ts",
                "content": """import { PrismaClient } from '@prisma/client';

    declare global {
      var prisma: PrismaClient | undefined;
    }

    export const prisma =
      global.prisma ||
      new PrismaClient({
        log: ['warn'],
      });

    if (process.env.NODE_ENV !== 'production') {
      global.prisma = prisma;
    }

    export async function getTasks() {
      return prisma.task.findMany({
        orderBy: { createdAt: 'desc' }
      });
    }

    export async function createTask(text: string) {
      return prisma.task.create({
        data: { text }
      });
    }

    export async function updateTask(id: number, status: string) {
      return prisma.task.update({
        where: { id },
        data: { status }
      });
    }

    export async function deleteTask(id: number) {
      return prisma.task.delete({
        where: { id }
      });
    }
    """
            },
            {
                "path": "app/layout.tsx",
                "content": """import type { Metadata } from 'next';
    import './globals.css';

    export const metadata: Metadata = {
      title: 'Task Manager',
      description: 'A full-stack todo app built with Next.js and Prisma',
    };

    export default function RootLayout({ children }: { children: React.ReactNode }) {
      return (
        <html lang="en">
          <body className="bg-gray-50 min-h-screen">{children}</body>
        </html>
      );
    }
    """
            },
            {
                "path": "app/page.tsx",
                "content": """import TodoList from '@/components/TodoList';

    export default function Page() {
      return (
        <main className="p-8 max-w-2xl mx-auto">
          <h1 className="text-4xl font-bold mb-8 text-gray-900">Task Manager</h1>
          <TodoList />
        </main>
      );
    }
    """
            },
            {
                "path": "components/TodoList.tsx",
                "content": """'use client';
    import { useState, useEffect } from 'react';
    import TodoItem from './TodoItem';

    interface Task {
      id: number;
      text: string;
      status: string;
      createdAt: string;
    }

    export default function TodoList() {
      const [tasks, setTasks] = useState<Task[]>([]);
      const [newTask, setNewTask] = useState('');
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);

      useEffect(() => {
        fetchTasks();
      }, []);

      const fetchTasks = async () => {
        try {
          setLoading(true);
          const res = await fetch('/api/tasks');
          if (!res.ok) throw new Error('Failed to fetch tasks');
          const data = await res.json();
          setTasks(data.tasks || []);
          setError(null);
        } catch (err: any) {
          setError(err.message);
          setTasks([]);
        } finally {
          setLoading(false);
        }
      };

      const addTask = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTask.trim()) return;

        try {
          const res = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: newTask })
          });

          if (!res.ok) throw new Error('Failed to create task');
          const { task } = await res.json();
          setTasks(prev => [task, ...prev]);
          setNewTask('');
          setError(null);
        } catch (err: any) {
          setError(err.message);
        }
      };

      const updateTaskStatus = async (id: number, status: string) => {
        try {
          const res = await fetch(`/api/tasks/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
          });

          if (!res.ok) throw new Error('Failed to update task');
          setTasks(prev => prev.map(t => 
            t.id === id ? { ...t, status } : t
          ));
          setError(null);
        } catch (err: any) {
          setError(err.message);
        }
      };

      const removeTask = async (id: number) => {
        try {
          const res = await fetch(`/api/tasks/${id}`, {
            method: 'DELETE'
          });

          if (!res.ok) throw new Error('Failed to delete task');
          setTasks(prev => prev.filter(t => t.id !== id));
          setError(null);
        } catch (err: any) {
          setError(err.message);
        }
      };

      return (
        <div className="space-y-6">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={addTask} className="flex gap-2">
            <input
              type="text"
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
              placeholder="Add a new task..."
              className="flex-1 border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={!newTask.trim()}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Add
            </button>
          </form>

          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading tasks...</div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No tasks yet. Add one above!</div>
          ) : (
            <ul className="space-y-2">
              {tasks.map(task => (
                <TodoItem
                  key={task.id}
                  task={task}
                  onToggle={() => updateTaskStatus(task.id, task.status === 'done' ? 'pending' : 'done')}
                  onDelete={() => removeTask(task.id)}
                />
              ))}
            </ul>
          )}
        </div>
      );
    }
    """
            },
            {
                "path": "components/TodoItem.tsx",
                "content": """'use client';

    interface Task {
      id: number;
      text: string;
      status: string;
      createdAt: string;
    }

    interface TodoItemProps {
      task: Task;
      onToggle: () => void;
      onDelete: () => void;
    }

    export default function TodoItem({ task, onToggle, onDelete }: TodoItemProps) {
      const isDone = task.status === 'done';

      return (
        <li className="p-4 border border-gray-200 rounded-lg flex justify-between items-center hover:shadow-md transition bg-white">
          <div className="flex-1">
            <span className={`text-lg ${isDone ? 'line-through text-gray-400' : 'text-gray-900'}`}>
              {task.text}
            </span>
            <p className="text-xs text-gray-500 mt-1">
              {new Date(task.createdAt).toLocaleDateString()}
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={onToggle}
              className={`text-sm px-3 py-1 rounded transition ${
                isDone
                  ? 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                  : 'bg-green-100 hover:bg-green-200 text-green-700'
              }`}
            >
              {isDone ? 'Undo' : 'Done'}
            </button>
            <button
              onClick={onDelete}
              className="text-sm px-3 py-1 rounded bg-red-100 hover:bg-red-200 text-red-700 transition"
            >
              Delete
            </button>
          </div>
        </li>
      );
    }
    """
            },
            {
                "path": "app/api/tasks/route.ts",
                "content": """import { NextResponse } from 'next/server';
    import { getTasks, createTask } from '@/lib/db';

    export async function GET() {
      try {
        const tasks = await getTasks();
        return NextResponse.json({ success: true, tasks });
      } catch (error: any) {
        console.error('Failed to fetch tasks:', error);
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }
    }

    export async function POST(request: Request) {
      try {
        const { text } = await request.json();

        if (!text || !text.trim()) {
          return NextResponse.json(
            { success: false, error: 'Task text is required' },
            { status: 400 }
          );
        }

        const task = await createTask(text.trim());
        return NextResponse.json({ success: true, task }, { status: 201 });
      } catch (error: any) {
        console.error('Failed to create task:', error);
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }
    }
    """
            },
            {
                "path": "app/api/tasks/[id]/route.ts",
                "content": """import { NextResponse } from 'next/server';
    import { updateTask, deleteTask } from '@/lib/db';

    export async function PATCH(
      request: Request,
      { params }: { params: { id: string } }
    ) {
      try {
        const { status } = await request.json();
        const id = parseInt(params.id, 10);

        if (isNaN(id)) {
          return NextResponse.json(
            { success: false, error: 'Invalid task ID' },
            { status: 400 }
          );
        }

        await updateTask(id, status);
        return NextResponse.json({ success: true });
      } catch (error: any) {
        console.error('Failed to update task:', error);
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }
    }

    export async function DELETE(
      _request: Request,
      { params }: { params: { id: string } }
    ) {
      try {
        const id = parseInt(params.id, 10);

        if (isNaN(id)) {
          return NextResponse.json(
            { success: false, error: 'Invalid task ID' },
            { status: 400 }
          );
        }

        await deleteTask(id);
        return NextResponse.json({ success: true });
      } catch (error: any) {
        console.error('Failed to delete task:', error);
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }
    }
    """
            },
            {
                "path": "globals.css",
                "content": """@tailwind base;
    @tailwind components;
    @tailwind utilities;

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
      background-color: rgb(249, 250, 251);
      color: rgb(17, 24, 39);
    }

    html {
      scroll-behavior: smooth;
    }

    @layer components {
      .btn-primary {
        @apply bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition;
      }

      .btn-secondary {
        @apply bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 transition;
      }

      .input-field {
        @apply border border-gray-300 p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500;
      }
    }
    """
            }
        ]
    })

    # â”€â”€â”€ PRISMA DATABASE UTILITIES PACK â”€â”€â”€
    brain.register_feature_pack("prisma", {
        "feature": "prisma",
        "stack": "nextjs-app-router|prisma|typescript",
        "files": [
            {
                "path": "prisma/schema.prisma",
                "content": """generator client {
      provider = "prisma-client-js"
    }

    datasource db {
      provider = "sqlite"
      url      = env("DATABASE_URL")
    }

    // Add your models here
    """
            },
            {
                "path": ".env.local",
                "content": """DATABASE_URL="file:./dev.db"
    """
            },
            {
                "path": "package.json.patch",
                "content": """// After running npm install, add these dependencies:
    // npm install @prisma/client
    // npm install -D prisma
    // Then run: npx prisma generate
    """
            }
        ]
    })

    # â”€â”€â”€ API ROUTES UTILITIES PACK â”€â”€â”€
    brain.register_feature_pack("api-routes", {
        "feature": "api-routes",
        "stack": "nextjs-app-router|typescript",
        "files": [
            {
                "path": "lib/api-utils.ts",
                "content": """import { NextResponse } from 'next/server';

    export function successResponse<T>(data: T, status = 200) {
      return NextResponse.json({ success: true, data }, { status });
    }

    export function errorResponse(error: string, status = 500) {
      return NextResponse.json({ success: false, error }, { status });
    }

    export function validateRequest(body: any, requiredFields: string[]): string | null {
      for (const field of requiredFields) {
        if (!(field in body) || !body[field]) {
          return `Missing required field: ${field}`;
        }
      }
      return null;
    }
    """
            }
        ]
    })

    # â”€â”€â”€ VALIDATION UTILITIES PACK â”€â”€â”€
    brain.register_feature_pack("validation", {
        "feature": "validation",
        "stack": "typescript",
        "files": [
            {
                "path": "lib/validators.ts",
                "content": """export function validateEmail(email: string): boolean {
      const regex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
      return regex.test(email);
    }

    export function validateString(str: string, minLength = 1, maxLength = 1000): boolean {
      return str && str.trim().length >= minLength && str.length <= maxLength;
    }

    export function validateNumber(num: any, min?: number, max?: number): boolean {
      const n = Number(num);
      if (isNaN(n)) return false;
      if (min !== undefined && n < min) return false;
      if (max !== undefined && n > max) return false;
      return true;
    }

    export function sanitizeString(str: string): string {
      return str.trim().replace(/[<>]/g, '');
    }
    """
            }
        ]
    })

    if save:
        brain.save()
    if verbose: print(f"\\n[+] All Prisma-based feature packs registered.")
    if verbose: print(f"    Packs: {list(brain.feature_packs.keys())}")

    # Verification
    for name in ['prisma_todo', 'prisma', 'api-routes', 'validation']:
        pack = brain.get_feature_pack(name)
        if pack:
            files_count = len(pack.get('files', []))
            if verbose: print(f"    OK {name}: {files_count} files")
        else:
            if verbose: print(f"    MISSING {name}: NOT FOUND")
    return brain


if __name__ == "__main__":
    register_prisma_packs()
