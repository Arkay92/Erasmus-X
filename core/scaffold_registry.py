import json
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class Scaffold:
    name: str
    stack: str
    files: dict[str, str]
    verification_commands: list[str] = field(default_factory=list)


class ScaffoldRegistry:
    """Capability-based project scaffolds selected by metadata, not exact benchmark prompts."""

    def __init__(self):
        self._entries: list[tuple[Callable[[str, dict], bool], Callable[[], Scaffold]]] = []
        self._register_defaults()

    def match(self, user_input: str, metadata: dict) -> Optional[Scaffold]:
        for predicate, factory in self._entries:
            if predicate(user_input, metadata):
                return factory()
        return None

    def register(self, predicate: Callable[[str, dict], bool], factory: Callable[[], Scaffold]) -> None:
        self._entries.append((predicate, factory))

    def _register_defaults(self) -> None:
        self.register(
            lambda text, meta: "nextjs-app-router" in meta.get("target_stack", "") and "prisma" in meta.get("target_stack", ""),
            _next_prisma_scaffold,
        )
        self.register(
            lambda text, meta: meta.get("target_stack") == "react|typescript" and "dashboard" in text.lower(),
            _react_dashboard_scaffold,
        )
        self.register(
            lambda text, meta: meta.get("target_stack") == "express|typescript" and "api" in text.lower(),
            _express_api_scaffold,
        )
        self.register(
            lambda text, meta: _is_booking_system_request(text),
            _booking_system_scaffold,
        )
        self.register(
            lambda text, meta: _is_plumber_booking_business_request(text),
            _plumber_booking_business_scaffold,
        )


def _next_prisma_scaffold() -> Scaffold:
    return Scaffold(
        name="nextjs_prisma_app",
        stack="nextjs-app-router|prisma|typescript",
        files={
            "PLAN.md": "# Next.js Prisma App\n\n- App Router UI\n- Prisma schema\n- API route\n",
            "package.json": json.dumps({
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "test": "vitest run", "prisma:generate": "prisma generate", "verify": "npm run prisma:generate && npm test && npm run build"},
                "dependencies": {"@prisma/client": "latest", "next": "latest", "prisma": "latest", "react": "latest", "react-dom": "latest"},
                "devDependencies": {"typescript": "latest", "vitest": "latest"}
            }, indent=2),
            "prisma/schema.prisma": "datasource db { provider = \"sqlite\" url = env(\"DATABASE_URL\") }\ngenerator client { provider = \"prisma-client-js\" }\nmodel Item { id Int @id @default(autoincrement()) title String completed Boolean @default(false) createdAt DateTime @default(now()) }\n",
            "lib/db.ts": "import { PrismaClient } from '@prisma/client';\n\nconst client = new PrismaClient();\nconst connectedAt = new Date().toISOString();\nconst status = { connectedAt };\nexport const prisma = client;\nexport const dbStatus = status;\n",
            "app/api/items/route.ts": "import { NextResponse } from 'next/server';\nimport { prisma } from '@/lib/db';\n\nexport async function GET() {\n  const items = await prisma.item.findMany();\n  return NextResponse.json(items);\n}\n\nexport async function POST(request: Request) {\n  const body = await request.json();\n  const item = await prisma.item.create({ data: { title: body.title ?? 'Untitled' } });\n  return NextResponse.json(item, { status: 201 });\n}\n",
            "app/page.tsx": "const features = ['Create records', 'List records', 'Persist with Prisma'];\n\nexport default function Home() {\n  const title = 'Project App';\n  const subtitle = 'Manage records with Prisma';\n  return <main><h1>{title}</h1><p>{subtitle}</p>{features.map(feature => <section key={feature}>{feature}</section>)}</main>;\n}\n",
            "lib/validation.ts": "export function normalizeTitle(input: unknown) {\n  const title = String(input ?? '').trim();\n  return title.length > 0 ? title : 'Untitled';\n}\n",
            "test/validation.test.ts": "import { describe, expect, it } from 'vitest';\nimport { normalizeTitle } from '../lib/validation';\n\ndescribe('normalizeTitle', () => {\n  it('keeps meaningful item titles', () => {\n    expect(normalizeTitle(' Ship tests ')).toBe('Ship tests');\n  });\n\n  it('falls back for blank titles', () => {\n    expect(normalizeTitle('   ')).toBe('Untitled');\n  });\n});\n",
        },
        verification_commands=["npm install", "npx prisma generate", "npm test", "npm run build"],
    )


def _react_dashboard_scaffold() -> Scaffold:
    return Scaffold(
        name="react_dashboard",
        stack="react|typescript",
        files={
            "PLAN.md": "# React Dashboard\n\n- Dashboard page\n- Chart data helper\n- Reusable layout\n",
            "package.json": json.dumps({
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "test": "vitest run", "prisma:generate": "prisma generate", "verify": "npm run prisma:generate && npm test && npm run build"},
                "dependencies": {"next": "latest", "react": "latest", "react-dom": "latest", "recharts": "latest"},
                "devDependencies": {"typescript": "latest", "vitest": "latest"}
            }, indent=2),
            "app/layout.tsx": "export default function RootLayout({ children }: { children: React.ReactNode }) {\n  return <html><body>{children}</body></html>;\n}\n",
            "lib/charts.ts": "export const chartData = [\n  { label: 'Jan', value: 42 },\n  { label: 'Feb', value: 58 },\n  { label: 'Mar', value: 73 },\n];\n",
            "app/dashboard/page.tsx": "import { chartData } from '@/lib/charts';\n\nexport default function DashboardPage() {\n  const total = chartData.reduce((sum, item) => sum + item.value, 0);\n  return <main><div><h1>Dashboard</h1><p>Total: {total}</p></div><div>{chartData.map(item => <section key={item.label}>{item.label}: {item.value}</section>)}</div></main>;\n}\n",
            "test/charts.test.ts": "import { describe, expect, it } from 'vitest';\nimport { chartData } from '../lib/charts';\n\ndescribe('chartData', () => {\n  it('ships populated numeric dashboard data', () => {\n    expect(chartData.length).toBeGreaterThan(0);\n    expect(chartData.every(item => item.label && Number.isFinite(item.value))).toBe(true);\n  });\n});\n",
        },
        verification_commands=["npm install", "npx prisma generate", "npm test", "npm run build"],
    )


def _express_api_scaffold() -> Scaffold:
    return Scaffold(
        name="express_api",
        stack="express|typescript",
        files={
            "PLAN.md": "# Express API\n\n- Express server\n- In-memory model\n- REST routes\n",
            "package.json": json.dumps({
                "scripts": {"dev": "ts-node src/index.ts", "build": "tsc", "start": "node dist/index.js", "test": "vitest run", "verify": "npm test && npm run build"},
                "dependencies": {"express": "latest"},
                "devDependencies": {"@types/express": "latest", "@types/node": "latest", "@types/supertest": "latest", "supertest": "latest", "ts-node": "latest", "typescript": "latest", "vitest": "latest"}
            }, indent=2),
            "tsconfig.json": json.dumps({
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "commonjs",
                    "moduleResolution": "node",
                    "esModuleInterop": True,
                    "strict": True,
                    "outDir": "dist"
                },
                "include": ["src/**/*.ts", "test/**/*.ts"]
            }, indent=2),
            "src/db/model.ts": "export interface RecordItem { id: number; title: string; body?: string; }\n\nconst records: RecordItem[] = [];\n\nexport function listRecords() { return records; }\nexport function createRecord(input: Omit<RecordItem, 'id'>): RecordItem {\n  const record = { id: records.length + 1, ...input };\n  records.push(record);\n  return record;\n}\n",
            "src/controllers/controller.ts": "import { Request, Response } from 'express';\nimport { createRecord, listRecords } from '../db/model';\n\nexport function getRecords(_req: Request, res: Response) { res.json(listRecords()); }\nexport function postRecord(req: Request, res: Response) { res.status(201).json(createRecord(req.body)); }\n",
            "src/routes/routes.ts": "import { Router } from 'express';\nimport { getRecords, postRecord } from '../controllers/controller';\n\nexport const routes = Router();\nconst recordsPath = '/records';\nroutes.get(recordsPath, getRecords);\nroutes.post(recordsPath, postRecord);\nroutes.get('/health', (_req, res) => res.json({ ok: true }));\n",
            "src/index.ts": "import express from 'express';\nimport { routes } from './routes/routes';\n\nexport const app = express();\napp.use(express.json());\napp.use('/api', routes);\n\nif (require.main === module) {\n  app.listen(3000, () => console.log('API listening on 3000'));\n}\n",
            "test/routes.test.ts": "import request from 'supertest';\nimport { describe, expect, it } from 'vitest';\nimport { app } from '../src/index';\n\ndescribe('records API', () => {\n  it('returns health status', async () => {\n    const response = await request(app).get('/api/health').expect(200);\n    expect(response.body).toEqual({ ok: true });\n  });\n\n  it('lists and creates records', async () => {\n    await request(app).get('/api/records').expect(200);\n    const created = await request(app).post('/api/records').send({ title: 'First post', body: 'Body' }).expect(201);\n    expect(created.body).toMatchObject({ id: expect.any(Number), title: 'First post' });\n    const listed = await request(app).get('/api/records').expect(200);\n    expect(listed.body.some((record: { title: string }) => record.title === 'First post')).toBe(true);\n  });\n});\n",
        },
        verification_commands=["npm install", "npm test", "npm run build"],
    )


def _is_booking_system_request(text: str) -> bool:
    lower = text.lower()
    return (
        "booking" in lower
        and any(term in lower for term in ("login", "register", "auth"))
        and any(term in lower for term in ("admin", "portal", "dashboard"))
    )


def _is_plumber_booking_business_request(text: str) -> bool:
    lower = text.lower()
    return (
        "plumber" in lower
        and any(term in lower for term in ("booking", "appointment", "business", "saas"))
    )


def _booking_system_scaffold() -> Scaffold:
    return Scaffold(
        name="booking_system_admin_portal",
        stack="nextjs-app-router|prisma|typescript",
        files={
            "PLAN.md": "# Booking System\n\n- Next.js App Router full-stack booking portal\n- Login and registration pages\n- Protected admin booking management\n- Prisma booking/user schema\n- API routes with validation\n",
            "package.json": json.dumps({
                "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "test": "vitest run", "verify": "npm test && npm run build"},
                "dependencies": {"@prisma/client": "latest", "next": "latest", "prisma": "latest", "react": "latest", "react-dom": "latest"},
                "devDependencies": {"typescript": "latest", "@types/node": "latest", "vitest": "latest"}
            }, indent=2),
            "prisma/schema.prisma": """datasource db { provider = \"sqlite\" url = env(\"DATABASE_URL\") }
generator client { provider = \"prisma-client-js\" }

model User {
  id Int @id @default(autoincrement())
  email String @unique
  passwordHash String
  role String @default(\"user\")
  createdAt DateTime @default(now())
  bookings Booking[]
}

model Booking {
  id Int @id @default(autoincrement())
  customerName String
  customerEmail String
  service String
  startsAt DateTime
  status String @default(\"pending\")
  notes String?
  userId Int?
  user User? @relation(fields: [userId], references: [id])
  createdAt DateTime @default(now())
}
""",
            "app/layout.tsx": """export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html><body><div data-app-shell=\"booking-system\">{children}</div></body></html>;
}
""",
            "lib/db.ts": """import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };
const existingClient = globalForPrisma.prisma;
const createdClient = existingClient ?? new PrismaClient();
if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = createdClient;
}
export const prisma = createdClient;
export function databaseReady() {
  const hasClient = Boolean(prisma);
  const readyState = hasClient ? 'ready' : 'missing';
  return { hasClient, readyState };
}
""",
            "lib/validation.ts": """export type ValidationResult = { ok: true } | { ok: false; error: string };

export function requireFields(body: Record<string, unknown>, fields: string[]): ValidationResult {
  for (const field of fields) {
    if (!body[field] || String(body[field]).trim().length === 0) return { ok: false, error: `${field} is required` };
  }
  return { ok: true };
}

export function isEmail(value: string) {
  return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(value);
}
""",
            "lib/auth.ts": """import { cookies } from 'next/headers';
import { createHmac, randomBytes, scryptSync, timingSafeEqual } from 'crypto';
import { prisma } from '@/lib/db';
import { isEmail, requireFields } from '@/lib/validation';

export type SessionUser = { id: number; email: string; role: string };

const SESSION_COOKIE = 'booking_admin_session';
const SESSION_SECRET = process.env.SESSION_SECRET ?? 'dev-session-secret-change-me';

export function hashPassword(password: string) {
  const salt = randomBytes(16).toString('hex');
  const hash = scryptSync(password, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}

export function verifyPassword(password: string, storedHash: string) {
  const [salt, hash] = storedHash.split(':');
  if (!salt || !hash) return false;
  const actual = Buffer.from(scryptSync(password, salt, 64).toString('hex'), 'hex');
  const expected = Buffer.from(hash, 'hex');
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

function sign(payload: string) {
  return createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
}

export function createSessionToken(user: SessionUser) {
  const payload = Buffer.from(JSON.stringify({ id: user.id, email: user.email, role: user.role })).toString('base64url');
  return `${payload}.${sign(payload)}`;
}

export function parseSessionToken(token?: string): SessionUser | null {
  if (!token) return null;
  const [payload, signature] = token.split('.');
  if (!payload || signature !== sign(payload)) return null;
  try {
    const decoded = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    return { id: Number(decoded.id), email: String(decoded.email), role: String(decoded.role) };
  } catch {
    return null;
  }
}

export function sessionCookieName() {
  return SESSION_COOKIE;
}

export async function getCurrentUser(): Promise<SessionUser | null> {
  const cookieStore = cookies();
  const parsed = parseSessionToken(cookieStore.get(SESSION_COOKIE)?.value);
  if (!parsed) return null;
  const user = await prisma.user.findUnique({ where: { id: parsed.id } });
  return user ? { id: user.id, email: user.email, role: user.role } : null;
}

export async function registerUser(body: Record<string, unknown>) {
  const validation = requireFields(body, ['email', 'password']);
  if (!validation.ok) return { ok: false, error: validation.error };
  const email = String(body.email).toLowerCase();
  if (!isEmail(email)) return { ok: false, error: 'Valid email is required' };
  const password = String(body.password);
  if (password.length < 8) return { ok: false, error: 'Password must be at least 8 characters' };
  const passwordHash = hashPassword(password);
  const user = await prisma.user.create({ data: { email, passwordHash, role: body.role === 'admin' ? 'admin' : 'user' } });
  return { ok: true, user: { id: user.id, email: user.email, role: user.role } };
}

export async function loginUser(body: Record<string, unknown>) {
  const validation = requireFields(body, ['email', 'password']);
  if (!validation.ok) return { ok: false, error: validation.error };
  const user = await prisma.user.findUnique({ where: { email: String(body.email).toLowerCase() } });
  if (!user || !verifyPassword(String(body.password), user.passwordHash)) return { ok: false, error: 'Invalid credentials' };
  return { ok: true, user: { id: user.id, email: user.email, role: user.role } };
}

export async function requireAdmin() {
  const user = await getCurrentUser();
  if (!user || user.role !== 'admin') return { ok: false, error: 'Admin access required' };
  return { ok: true, user };
}
""",
            "lib/bookings.ts": """import { prisma } from '@/lib/db';
import { isEmail, requireFields } from '@/lib/validation';

export async function listBookings() {
  return prisma.booking.findMany({ orderBy: { startsAt: 'asc' } });
}

export async function createBooking(body: Record<string, unknown>) {
  const validation = requireFields(body, ['customerName', 'customerEmail', 'service', 'startsAt']);
  if (!validation.ok) return { ok: false, error: validation.error };
  const customerEmail = String(body.customerEmail).toLowerCase();
  if (!isEmail(customerEmail)) return { ok: false, error: 'Valid customer email is required' };
  const booking = await prisma.booking.create({
    data: {
      customerName: String(body.customerName),
      customerEmail,
      service: String(body.service),
      startsAt: new Date(String(body.startsAt)),
      status: String(body.status ?? 'pending'),
      notes: body.notes ? String(body.notes) : null,
    },
  });
  return { ok: true, booking };
}

export async function updateBookingStatus(id: number, status: string) {
  const booking = await prisma.booking.update({ where: { id }, data: { status } });
  return { ok: true, booking };
}
""",
            "app/login/page.tsx": """'use client';
import { FormEvent, useState } from 'react';

export default function LoginPage() {
  const title = 'Admin Login';
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await fetch('/api/auth/login', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(Object.fromEntries(form)) });
    const payload = await response.json();
    if (!response.ok) setError(payload.error ?? 'Login failed');
    else window.location.href = payload.redirectTo;
  }
  return <main><h1>{title}</h1><form onSubmit={submit}><label>Email<input name=\"email\" type=\"email\" required /></label><label>Password<input name=\"password\" type=\"password\" required /></label><button type=\"submit\">Login</button></form>{error && <p role=\"alert\">{error}</p>}</main>;
}
""",
            "app/register/page.tsx": """'use client';
import { FormEvent, useState } from 'react';

export default function RegisterPage() {
  const title = 'Create Admin Account';
  const [message, setMessage] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await fetch('/api/auth/register', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(Object.fromEntries(form)) });
    const payload = await response.json();
    setMessage(response.ok ? 'Account created. You can now log in.' : payload.error ?? 'Registration failed');
  }
  return <main><h1>{title}</h1><form onSubmit={submit}><label>Email<input name=\"email\" type=\"email\" required /></label><label>Password<input name=\"password\" type=\"password\" required minLength={8} /></label><label>Admin<input name=\"role\" value=\"admin\" readOnly /></label><button type=\"submit\">Register</button></form>{message && <p>{message}</p>}</main>;
}
""",
            "app/admin/bookings/page.tsx": """import { redirect } from 'next/navigation';
import BookingCreateForm from '@/app/admin/bookings/CreateBookingForm';
import { requireAdmin } from '@/lib/auth';
import { listBookings } from '@/lib/bookings';

export default async function AdminBookingsPage() {
  const access = await requireAdmin();
  if (!access.ok) redirect('/login');
  const bookings = await listBookings();
  return <main><h1>Admin Booking Portal</h1><p>Signed in as {access.user.email}</p><BookingCreateForm /><section>{bookings.map(booking => <article key={booking.id}><h2>{booking.service}</h2><p>{booking.customerName} - {booking.customerEmail}</p><p>{booking.status}</p></article>)}</section></main>;
}
""",
            "app/admin/bookings/CreateBookingForm.tsx": """'use client';
import { FormEvent, useState } from 'react';

export default function BookingCreateForm() {
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await fetch('/api/bookings', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(Object.fromEntries(form)) });
    if (response.ok) window.location.reload();
    else {
      const payload = await response.json();
      setError(payload.error ?? 'Booking could not be created');
    }
  }
  return <form onSubmit={submit}><input name=\"customerName\" placeholder=\"Customer\" required /><input name=\"customerEmail\" type=\"email\" placeholder=\"Email\" required /><input name=\"service\" placeholder=\"Service\" required /><input name=\"startsAt\" type=\"datetime-local\" required /><button type=\"submit\">Create Booking</button>{error && <p role=\"alert\">{error}</p>}</form>;
}
""",
            "app/api/auth/login/route.ts": """import { NextResponse } from 'next/server';
import { createSessionToken, loginUser, sessionCookieName } from '@/lib/auth';

export async function POST(request: Request) {
  const result = await loginUser(await request.json());
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 401 });
  const response = NextResponse.json({ user: result.user, redirectTo: '/admin/bookings' });
  response.cookies.set(sessionCookieName(), createSessionToken(result.user), { httpOnly: true, sameSite: 'lax', path: '/' });
  return response;
}
""",
            "app/api/auth/register/route.ts": """import { NextResponse } from 'next/server';
import { registerUser } from '@/lib/auth';

export async function POST(request: Request) {
  const result = await registerUser(await request.json());
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  return NextResponse.json({ user: result.user }, { status: 201 });
}
""",
            "app/api/bookings/route.ts": """import { NextResponse } from 'next/server';
import { requireAdmin } from '@/lib/auth';
import { createBooking, listBookings } from '@/lib/bookings';

export async function GET() {
  const access = await requireAdmin();
  if (!access.ok) return NextResponse.json({ error: access.error }, { status: 403 });
  const bookings = await listBookings();
  return NextResponse.json(bookings);
}

export async function POST(request: Request) {
  const access = await requireAdmin();
  if (!access.ok) return NextResponse.json({ error: access.error }, { status: 403 });
  const result = await createBooking(await request.json());
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  return NextResponse.json(result.booking, { status: 201 });
}
""",
            "test/validation.test.ts": """import { describe, expect, it } from 'vitest';
import { isEmail, requireFields } from '../lib/validation';

describe('booking validation helpers', () => {
  it('requires configured fields', () => {
    expect(requireFields({ email: 'admin@example.com' }, ['email'])).toEqual({ ok: true });
    expect(requireFields({ email: '' }, ['email'])).toEqual({ ok: false, error: 'email is required' });
  });

  it('validates email shape', () => {
    expect(isEmail('admin@example.com')).toBe(true);
    expect(isEmail('not-an-email')).toBe(false);
  });
});
""",
            "test/auth.test.ts": """import { describe, expect, it } from 'vitest';
import { createSessionToken, hashPassword, parseSessionToken, verifyPassword } from '../lib/auth';

describe('auth helpers', () => {
  it('hashes and verifies passwords with a per-password salt', () => {
    const first = hashPassword('correct horse battery');
    const second = hashPassword('correct horse battery');
    expect(first).not.toBe(second);
    expect(verifyPassword('correct horse battery', first)).toBe(true);
    expect(verifyPassword('wrong password', first)).toBe(false);
  });

  it('round-trips signed session tokens', () => {
    const token = createSessionToken({ id: 1, email: 'admin@example.com', role: 'admin' });
    expect(parseSessionToken(token)).toEqual({ id: 1, email: 'admin@example.com', role: 'admin' });
    expect(parseSessionToken(`${token}tampered`)).toBeNull();
  });
});
""",
        },
        verification_commands=["npm install", "npm test", "npm run build"],
    )


def _plumber_booking_business_scaffold() -> Scaffold:
    scaffold = _booking_system_scaffold()
    files = dict(scaffold.files)
    files["PLAN.md"] = "# Plumber Booking Business\n\n- Public service pages for emergency plumbing, repairs, and quotes\n- Booking API and admin dashboard\n- Auth/session helpers\n- Email notification helper\n- Stripe checkout route skeleton with explicit environment validation\n- Deploy script and test suite\n"
    files["app/page.tsx"] = """const services = ['Emergency callouts', 'Leak repairs', 'Boiler servicing', 'Bathroom installs'];

export default function HomePage() {
  return <main><h1>Reliable Local Plumbing</h1><p>Book trusted plumbing appointments with clear availability and fast follow-up.</p><a href=\"/book\">Book a plumber</a><section>{services.map(service => <article key={service}><h2>{service}</h2><p>Professional service with transparent scheduling.</p></article>)}</section></main>;
}
"""
    files["app/book/page.tsx"] = """'use client';
import { FormEvent, useState } from 'react';

export default function BookingPage() {
  const [message, setMessage] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await fetch('/api/bookings/public', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(Object.fromEntries(form)) });
    const payload = await response.json();
    setMessage(response.ok ? `Booking requested for ${payload.service}` : payload.error ?? 'Booking failed');
  }
  return <main><h1>Book a Plumber</h1><form onSubmit={submit}><input name=\"customerName\" placeholder=\"Name\" required /><input name=\"customerEmail\" type=\"email\" placeholder=\"Email\" required /><select name=\"service\" required><option>Emergency callout</option><option>Leak repair</option><option>Boiler service</option></select><input name=\"startsAt\" type=\"datetime-local\" required /><textarea name=\"notes\" placeholder=\"Describe the issue\" /><button type=\"submit\">Request Booking</button></form>{message && <p>{message}</p>}</main>;
}
"""
    files["app/api/bookings/public/route.ts"] = """import { NextResponse } from 'next/server';
import { createBooking } from '@/lib/bookings';
import { buildBookingEmail } from '@/lib/email';

export async function POST(request: Request) {
  const result = await createBooking(await request.json());
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: 400 });
  const email = buildBookingEmail(result.booking.customerEmail, result.booking.service, result.booking.startsAt.toISOString());
  return NextResponse.json({ id: result.booking.id, service: result.booking.service, emailPreview: email.subject }, { status: 201 });
}
"""
    files["app/api/checkout/route.ts"] = """import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();
  const stripeKey = process.env.STRIPE_SECRET_KEY;
  if (!stripeKey) return NextResponse.json({ error: 'Stripe is not configured' }, { status: 503 });
  const service = String(body.service ?? 'plumbing appointment');
  return NextResponse.json({ checkoutMode: 'payment', service, status: 'ready' });
}
"""
    files["lib/email.ts"] = """export function buildBookingEmail(customerEmail: string, service: string, startsAt: string) {
  return {
    to: customerEmail,
    subject: `Booking request received for ${service}`,
    text: `Your plumbing booking for ${service} at ${startsAt} has been received. We will confirm shortly.`,
  };
}
"""
    files["lib/seo.ts"] = """export const seoPages = [
  { slug: 'emergency-plumber', title: 'Emergency Plumber', description: 'Fast response plumbing callouts.' },
  { slug: 'leak-repair', title: 'Leak Repair', description: 'Trace and fix leaks before damage spreads.' },
  { slug: 'boiler-service', title: 'Boiler Service', description: 'Schedule safe boiler servicing.' },
];
"""
    files["scripts/deploy.sh"] = """#!/usr/bin/env sh
set -eu
npm test
npm run build
echo \"Deploy with your Next.js host after DATABASE_URL, SESSION_SECRET, and STRIPE_SECRET_KEY are configured.\"
"""
    files["test/email.test.ts"] = """import { describe, expect, it } from 'vitest';
import { buildBookingEmail } from '../lib/email';

describe('buildBookingEmail', () => {
  it('creates a customer notification', () => {
    const email = buildBookingEmail('customer@example.com', 'Leak repair', '2026-05-01T10:00:00.000Z');
    expect(email.to).toBe('customer@example.com');
    expect(email.subject).toContain('Leak repair');
    expect(email.text).toContain('2026-05-01');
  });
});
"""
    files["test/seo.test.ts"] = """import { describe, expect, it } from 'vitest';
import { seoPages } from '../lib/seo';

describe('seoPages', () => {
  it('contains service landing pages', () => {
    expect(seoPages.map(page => page.slug)).toContain('emergency-plumber');
    expect(seoPages.every(page => page.title && page.description)).toBe(true);
  });
});
"""
    files["SWARM_PLAN.md"] = "# Swarm Plan\n\n- architect: booking SaaS routes, schema, and deployment boundaries\n- builder: Next.js, Prisma, API, admin, and public booking files\n- tester: validation, auth, email, SEO, and route behavior tests\n- critic: reject placeholders and schema drift\n- security: sessions, password hashing, validation, and secrets\n"
    return Scaffold(
        name="plumber_booking_business_pack",
        stack="nextjs-app-router|prisma|typescript|saas",
        files=files,
        verification_commands=["npm install", "npx prisma generate", "npm test", "npm run build"],
    )
