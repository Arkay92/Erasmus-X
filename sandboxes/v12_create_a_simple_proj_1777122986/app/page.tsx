import TodoList from '@/components/TodoList';

export default function Page() {
  return (
    <main className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Task Manager</h1>
      <TodoList />
    </main>
  )
}