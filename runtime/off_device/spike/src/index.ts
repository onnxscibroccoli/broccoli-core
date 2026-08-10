import { getWorkspace } from "@cloudflare/computer";
import { BroccoliWorkspace } from "./broccoli_workspace";

export { BroccoliWorkspace };

export interface Env {
  BROCCOLI_WORKSPACE: DurableObjectNamespace;
}

function stub(env: Env, id = "default") {
  return env.BROCCOLI_WORKSPACE.get(env.BROCCOLI_WORKSPACE.idFromName(id));
}

async function withWs<T>(
  env: Env,
  fn: (ws: Awaited<ReturnType<typeof getWorkspace>>) => Promise<T>
): Promise<T> {
  // getWorkspace returns a disposable client over the DO stub
  using ws = await getWorkspace(stub(env));
  return await fn(ws);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    try {
      if (request.method === "POST" && url.pathname === "/write") {
        const body = (await request.json()) as {
          path?: string;
          content?: string;
        };
        if (!body.path || body.content === undefined) {
          return Response.json(
            { ok: false, error: "path and content required" },
            { status: 400 }
          );
        }
        const full = body.path.startsWith("/")
          ? body.path
          : `/workspace/${body.path}`;
        await withWs(env, async (ws) => {
          const parent = full.replace(/\/[^/]+$/, "") || "/workspace";
          await ws.fs.mkdir(parent, { recursive: true });
          await ws.fs.writeFile(full, body.content!);
        });
        return Response.json({
          ok: true,
          path: full,
          bytes: body.content.length,
        });
      }

      if (request.method === "GET" && url.pathname === "/read") {
        const path = url.searchParams.get("path");
        if (!path) {
          return Response.json(
            { ok: false, error: "path query required" },
            { status: 400 }
          );
        }
        const full = path.startsWith("/") ? path : `/workspace/${path}`;
        const content = await withWs(env, (ws) =>
          ws.fs.readFile(full, "utf8")
        );
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
              typeof e === "string"
                ? e
                : (e as { name?: string })?.name ?? String(e)
            )
          : entries;
        return Response.json({ ok: true, path, entries: names });
      }

      return Response.json({
        ok: true,
        service: "broccoli-do-spike",
        endpoints: ["POST /write", "GET /read?path=", "GET /ls?path="],
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return Response.json({ ok: false, error: message }, { status: 500 });
    }
  },
};
