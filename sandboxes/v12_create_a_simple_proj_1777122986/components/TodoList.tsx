'use client';
import { useState, useEffect } from 'react';

interface Task { id: number; text: string; status: string; }

export default function TodoList() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTask, setNewTask] = useState('');

  useEffect(() => {
    fetch('/api/tasks').then(r => r.json()).then(data => setTasks(data.rows || []));
  }, []);

  const addTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: newTask })
    });
    if (res.ok) {
      const saved = await res.json();
      setTasks(prev => [{ id: saved.id, text: newTask, status: 'pending' }, ...prev]);
      setNewTask('');
    }
  };

  const toggleTask = async (id: number) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    const newStatus = task.status === 'pending' ? 'done' : 'pending';
    await fetch(`/api/tasks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    setTasks(prev => prev.map(t => t.id === id ? { ...t, status: newStatus } : t));
  };

  const deleteTask = async (id: number) => {
    await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
    setTasks(prev => prev.filter(t => t.id !== id));
  };

  return (
    <div>
      <form onSubmit={addTask} className="flex gap-2 mb-4">
        <input type="text" value={newTask} onChange={(e) => setNewTask(e.target.value)}
          placeholder="Add a new task..." className="border p-2 flex-grow rounded" />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Add</button>
      </form>
      <ul className="space-y-2">
        {tasks.map(task => (
          <li key={task.id} className="p-3 border rounded flex justify-between items-center">
            <span className={task.status === 'done' ? 'line-through text-gray-400' : ''}>{task.text}</span>
            <div className="flex gap-2">
              <button onClick={() => toggleTask(task.id)} className="text-sm px-2 py-1 rounded bg-green-100 hover:bg-green-200">
                {task.status === 'done' ? 'Undo' : 'Done'}
              </button>
              <button onClick={() => deleteTask(task.id)} className="text-sm px-2 py-1 rounded bg-red-100 hover:bg-red-200">
                Delete
              </button>
            </div>
          </li>
        ))}
        {tasks.length === 0 && <li className="text-gray-500 text-center py-4">No tasks yet. Add one above!</li>}
      </ul>
    </div>
  );
}
