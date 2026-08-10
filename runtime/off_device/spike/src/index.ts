import { getWorkspace } from "@cloudflare/computer";
import { BroccoliWorkspace } from "./broccoli_workspace";

export { BroccoliWorkspace };

export interface Env {
  BROCCOLI_WORKSPACE: DurableObjectNamespace;
}

type TaskStatus =
  | "queued"
  | "running"
  | "needs_user"
  | "done"
  | "failed"
  | "cancelled";

interface Task {
  id: string;
  goal: string;
  domain: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  artifacts?: { path: string; kind?: string; bytes?: number }[];
  receipt?: { summary?: string; github_ref?: string; notified?: boolean };
  notes?: string;
}

function stub(env: Env, id = "default") {
  return env.BROCCOLI_WORKSPACE.get(env.BROCCOLI_WORKSPACE.idFromName(id));
}

async function withWs<T>(
  env: Env,
  fn: (ws: Awaited<ReturnType<typeof getWorkspace>>) => Promise<T>
): Promise<T> {
  using ws = await getWorkspace(stub(env));
  return await fn(ws);
}

function now() {
  return new Date().toISOString();
}

function taskPath(id: string) {
  return `/workspace/tasks/${id}.json`;
}

function receiptPath(id: string) {
  return `/workspace/receipts/${id}.json`;
}

async function ensureTree(ws: Awaited<ReturnType<typeof getWorkspace>>) {
  await ws.fs.mkdir("/workspace/tasks", { recursive: true });
  await ws.fs.mkdir("/workspace/receipts", { recursive: true });
}

async function writeJson(
  ws: Awaited<ReturnType<typeof getWorkspace>>,
  path: string,
  obj: unknown
) {
  const parent = path.replace(/\/[^/]+$/, "") || "/workspace";
  await ws.fs.mkdir(parent, { recursive: true });
  await ws.fs.writeFile(path, JSON.stringify(obj, null, 2) + "\n");
}

async function readJson(
  ws: Awaited<ReturnType<typeof getWorkspace>>,
  path: string
) {
  const content = await ws.fs.readFile(path, "utf8");
  return JSON.parse(content as string);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    try {
      if (request.method === "GET" && url.pathname === "/") {
        return Response.json({
          ok: true,
          service: "broccoli-do-spike",
          phase: "C1",
          endpoints: [
            "POST /write",
            "GET /read?path=",
            "GET /ls?path=",
            "POST /task",
            "GET /task?id=",
            "GET /tasks",
            "PATCH /task",
            "POST /receipt",
          ],
        });
      }

      if (request.method === "POST" && url.pathname === "/write") {
        const body = (await request.json()) as { path?: string; content?: string };
        if (!body.path || body.content === undefined) {
          return Response.json({ ok: false, error: "path and content required" }, { status: 400 });
        }
        const full = body.path.startsWith("/") ? body.path : `/workspace/${body.path}`;
        await withWs(env, async (ws) => {
          const parent = full.replace(/\/[^/]+$/, "") || "/workspace";
          await ws.fs.mkdir(parent, { recursive: true });
          await ws.fs.writeFile(full, body.content as string);
        });
        return Response.json({ ok: true, path: full, bytes: body.content.length });
      }

      if (request.method === "GET" && url.pathname === "/read") {
        const path = url.searchParams.get("path");
        if (!path) {
          return Response.json({ ok: false, error: "path query required" }, { status: 400 });
        }
        const full = path.startsWith("/") ? path : `/workspace/${path}`;
        const content = await withWs(env, (ws) => ws.fs.readFile(full, "utf8"));
        return Response.json({ ok: true, path: full, content });
      }

      if (request.method === "GET" && url.pathname === "/ls") {
        const path = url.searchParams.get("path") || "/workspace";
        const entries = await withWs(env, async (ws) => {
          try {
            await ws.fs.mkdir(path, { recursive: true });
            return await ws.fs.readdir(path);
          } catch {
            return [];
          }
        });
        const names = Array.isArray(entries)
          ? entries.map((e: unknown) =>
              typeof e === "string" ? e : (e as { name?: string })?.name ?? String(e)
            )
          : entries;
        return Response.json({ ok: true, path, entries: names });
      }

      if (request.method === "POST" && url.pathname === "/task") {
        const body = (await request.json()) as Partial<Task>;
        if (!body.goal || !body.domain) {
          return Response.json({ ok: false, error: "goal and domain required" }, { status: 400 });
        }
        const t: Task = {
          id: body.id || crypto.randomUUID(),
          goal: body.goal,
          domain: body.domain,
          status: body.status || "queued",
          created_at: now(),
          updated_at: now(),
          artifacts: body.artifacts || [],
          notes: body.notes || "",
        };
        await withWs(env, async (ws) => {
          await ensureTree(ws);
          await writeJson(ws, taskPath(t.id), t);
        });
        return Response.json({ ok: true, task: t });
      }

      if (request.method === "GET" && url.pathname === "/task") {
        const id = url.searchParams.get("id");
        if (!id) {
          return Response.json({ ok: false, error: "id query required" }, { status: 400 });
        }
        const task = await withWs(env, (ws) => readJson(ws, taskPath(id)));
        return Response.json({ ok: true, task });
      }

      if (request.method === "GET" && url.pathname === "/tasks") {
        const tasks = await withWs(env, async (ws) => {
          await ensureTree(ws);
          const entries = await ws.fs.readdir("/workspace/tasks");
          const names = Array.isArray(entries)
            ? entries.map((e: unknown) =>
                typeof e === "string" ? e : (e as { name?: string })?.name ?? ""
              )
            : [];
          const out: Task[] = [];
          for (const name of names) {
            if (!String(name).endsWith(".json")) continue;
            try {
              out.push(await readJson(ws, `/workspace/tasks/${name}`));
            } catch {
              /* skip */
            }
          }
          return out;
        });
        return Response.json({ ok: true, tasks });
      }

      if (request.method === "PATCH" && url.pathname === "/task") {
        const body = (await request.json()) as Partial<Task> & { id?: string };
        if (!body.id) {
          return Response.json({ ok: false, error: "id required" }, { status: 400 });
        }
        const task = await withWs(env, async (ws) => {
          const cur = (await readJson(ws, taskPath(body.id as string))) as Task;
          const next: Task = {
            ...cur,
            status: (body.status as TaskStatus) || cur.status,
            goal: body.goal || cur.goal,
            domain: body.domain || cur.domain,
            notes: body.notes !== undefined ? body.notes : cur.notes,
            artifacts: body.artifacts || cur.artifacts,
            receipt: body.receipt ? { ...cur.receipt, ...body.receipt } : cur.receipt,
            updated_at: now(),
          };
          await writeJson(ws, taskPath(next.id), next);
          return next;
        });
        return Response.json({ ok: true, task });
      }

      if (request.method === "POST" && url.pathname === "/receipt") {
        const body = (await request.json()) as {
          id?: string;
          summary?: string;
          github_ref?: string;
        };
        if (!body.id || !body.summary) {
          return Response.json({ ok: false, error: "id and summary required" }, { status: 400 });
        }
        const result = await withWs(env, async (ws) => {
          const cur = (await readJson(ws, taskPath(body.id as string))) as Task;
          const receipt = {
            task_id: cur.id,
            summary: body.summary,
            github_ref: body.github_ref || null,
            created_at: now(),
          };
          await writeJson(ws, receiptPath(cur.id), receipt);
          const next: Task = {
            ...cur,
            status: cur.status === "running" ? "done" : cur.status,
            updated_at: now(),
            receipt: {
              summary: body.summary,
              github_ref: body.github_ref,
              notified: false,
            },
            artifacts: [
              ...(cur.artifacts || []),
              { path: receiptPath(cur.id), kind: "receipt" },
            ],
          };
          await writeJson(ws, taskPath(next.id), next);
          return { task: next, receipt };
        });
        return Response.json({ ok: true, ...result });
      }

      return Response.json({ ok: false, error: "not found" }, { status: 404 });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return Response.json({ ok: false, error: message }, { status: 500 });
    }
  },
};
