import { BroccoliWorkspace } from "./broccoli_workspace";

export { BroccoliWorkspace };

export interface Env {
  BROCCOLI_WORKSPACE: DurableObjectNamespace;
}

function stub(env: Env, id = "default") {
  return env.BROCCOLI_WORKSPACE.get(env.BROCCOLI_WORKSPACE.idFromName(id));
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const doStub = stub(env);

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
        const result = await doStub.writeFile(body.path, body.content);
        return Response.json(result);
      }

      if (request.method === "GET" && url.pathname === "/read") {
        const path = url.searchParams.get("path");
        if (!path) {
          return Response.json(
            { ok: false, error: "path query required" },
            { status: 400 }
          );
        }
        const result = await doStub.readFile(path);
        return Response.json(result);
      }

      if (request.method === "GET" && url.pathname === "/ls") {
        const path = url.searchParams.get("path") || "/workspace";
        const result = await doStub.list(path);
        return Response.json(result);
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
