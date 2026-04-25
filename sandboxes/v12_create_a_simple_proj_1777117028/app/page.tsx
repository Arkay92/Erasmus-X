import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm flex">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl">
          Ready for Implementation&nbsp;
        </p>
      </div>
      <div className="flex flex-col gap-4 mt-8 text-center">
        <h1 className="text-4xl font-bold">Application Core</h1>
        <p className="text-gray-600">V17 Authoritative Logic Depth Active.</p>
        <Link href="/login" className="text-blue-500 hover:underline">Get Started</Link>
      </div>
    </main>
  )
}
