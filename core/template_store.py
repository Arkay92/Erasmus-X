# Elite V10 Deterministic Template Store
import os
import json

PACKS_DIR = os.path.join(os.path.dirname(__file__), 'packs')

TEMPLATE_MAP = {
    "nextjs_layout": {
        "path": "app/layout.tsx",
        "content": """import './globals.css';\n\nexport default function RootLayout({\n  children,\n}: {\n  children: React.ReactNode\n}) {\n  return (\n    <html lang=\"en\">\n      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>\n    </html>\n  )\n}\n"""
    },
    "nextjs_page": {
        "path": "app/page.tsx",
        "content": """import Link from 'next/link';\n\nexport default function Home() {\n  return (\n    <main className=\"flex flex-col items-center justify-center min-h-screen p-24\">\n      <div className=\"z-10 w-full max-w-5xl items-center justify-between font-mono text-sm flex\">\n        <p className=\"fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl\">\n          Ready for Implementation&nbsp;\n        </p>\n      </div>\n      <div className=\"flex flex-col gap-4 mt-8 text-center\">\n        <h1 className=\"text-4xl font-bold\">Application Core</h1>\n        <p className=\"text-gray-600\">V17 Authoritative Logic Depth Active.</p>\n        <Link href=\"/login\" className=\"text-blue-500 hover:underline\">Get Started</Link>\n      </div>\n    </main>\n  )\n}\n"""
    },
    "python_init": {
        "path": "__init__.py",
        "content": "\"\"\"Package initialization.\"\"\"\n"
    },
    "node_package_json": {
        "path": "package.json",
        "content": """{
  "name": "project-generated",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "latest",
    "react": "latest",
    "react-dom": "latest"
  }
}
"""
    },
    "dockerfile_python": {
        "path": "Dockerfile",
        "content": """FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
"""
    },
    "docker_compose": {
        "path": "docker-compose.yml",
        "content": """version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: main
      POSTGRES_HOST_AUTH_METHOD: trust
"""
    },
     "sql_migration": {
        "path": "migrations/001_init.sql",
        "content": """-- Initial migration
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    },
    "rust_cargo": {
        "path": "Cargo.toml",
        "content": """[package]
name = "project-generated"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
    },
    "nextjs_generic_component": {
        "path": "",
        "content": """'use client';\nimport React from 'react';\n\nexport default function UIComponent() {\n  return (\n    <section className=\"p-8 bg-white rounded-lg shadow-md border\">\n      <h3 className=\"text-lg font-semibold mb-2\">Feature Interface</h3>\n      <p className=\"text-sm text-gray-600\">Implementation following Capability Contract assertions.</p>\n    </section>\n  )\n}\n"""
    },
    "nextjs_generic_api": {
        "path": "",
        "content": """import { NextResponse } from 'next/server';\n\nexport async function GET(request: Request) {\n  const data = { status: 'implemented', timestamp: new Date().toISOString() };\n  return NextResponse.json(data);\n}\n\nexport async function POST(request: Request) {\n  const body = await request.json();\n  return NextResponse.json({ received: true, ...body }, { status: 201 });\n}\n"""
    },
    "nextjs_generic_ts": {
        "path": "",
        "content": """// Logic Implementation Module\n// Deep functional logic required for contract compliance.\n\nexport interface SystemState {\n  active: boolean;\n  initializedAt: string;\n}\n\nexport function initializeState(): SystemState {\n  return {\n    active: true,\n    initializedAt: new Date().toISOString()\n  };\n}\n"""
    }
}

def get_template(key):
    return TEMPLATE_MAP.get(key)

def get_best_skeleton_from_brain(filename, brain, stack_context=""):
    """Elite V20: Deterministic feature pack lookup via brain registry."""
    fn_low = filename.lower()
    search_space = fn_low + " " + str(stack_context).lower()
    
    # 1. Map filename or contract signals to feature names
    feature_map = {
        'todo': 'todo', 'task': 'todo',
        'db': 'db', 'database': 'db',
        'dashboard': 'dashboard',
        'login': 'auth', 'auth': 'auth'
    }
    
    target_feature = None
    for signal, feat in feature_map.items():
        if signal in search_space:
            target_feature = feat
            break
            
    if not target_feature:
        return None
        
    # 2. Deterministic registry lookup (O(1), no HDC search needed)
    pack = brain.get_feature_pack(target_feature)
    if not pack:
        return None
    
    # 3. Find the specific file within the pack
    for f in pack.get('files', []):
        if f['path'].lower() in fn_low or fn_low in f['path'].lower():
            return f
    
    # 4. Fallback: return the first file's content as a generic seed
    if pack.get('files'):
        return {"content": pack['files'][0].get('content', '')}
    return None
                
def get_best_skeleton(filename, brain=None, stack_context=None):
    """Heuristic to find the best template for a given path, strictly using brain-based packs."""
    fn_low = filename.lower()
    
    # 1. Brain-based Feature Packs (Highest Fidelity Override)
    if brain:
        brain_skeleton = get_best_skeleton_from_brain(filename, brain, stack_context)
        if brain_skeleton:
            return brain_skeleton
    
    # 2. Standard Skeletons (Deterministic / Hardcoded)
    if 'layout' in fn_low and ('tsx' in fn_low or 'js' in fn_low): return TEMPLATE_MAP['nextjs_layout']
    if 'page' in fn_low and ('tsx' in fn_low or 'js' in fn_low): return TEMPLATE_MAP['nextjs_page']
    if 'package.json' in fn_low: return TEMPLATE_MAP['node_package_json']
    if 'dockerfile' in fn_low: return TEMPLATE_MAP['dockerfile_python']
    if 'docker-compose' in fn_low: return TEMPLATE_MAP['docker_compose']
    if 'cargo.toml' in fn_low: return TEMPLATE_MAP['rust_cargo']
    if filename.endswith('__init__.py'): return TEMPLATE_MAP['python_init']
    if filename.endswith('.sql'): return TEMPLATE_MAP['sql_migration']
    
    # Generic Fallbacks for Next.js Projects
    if 'route.ts' in fn_low or 'route.js' in fn_low or 'api/' in fn_low: return TEMPLATE_MAP['nextjs_generic_api']
    if fn_low.endswith('.tsx') or fn_low.endswith('.jsx'): return TEMPLATE_MAP['nextjs_generic_component']
    if fn_low.endswith('.ts') or fn_low.endswith('.js'): return TEMPLATE_MAP['nextjs_generic_ts']
    
    return None
