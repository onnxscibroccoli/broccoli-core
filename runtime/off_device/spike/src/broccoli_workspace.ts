import { DurableObject } from "cloudflare:workers";
import { withWorkspace, getWorkspace } from "@cloudflare/computer";

// Minimal durable workspace: SQLite VFS only, no exec backend yet.
export class BroccoliWorkspace extends withWorkspace(
  class extends DurableObject {
    async ensureRoot() {
      const ws = getWorkspace(this);
      await ws.ready();
      await ws.fs.mkdir("/workspace", { recursive: true });
      return ws;
    }

    async writeFile(path: string, content: string) {
      const ws = await this.ensureRoot();
      const full = path.startsWith("/") ? path : `/workspace/${path}`;
      await ws.fs.mkdir(full.replace(/\/[^/]+$/, "") || "/workspace", {
        recursive: true,
      });
      await ws.fs.writeFile(full, content);
      return { ok: true, path: full, bytes: content.length };
    }

    async readFile(path: string) {
      const ws = await this.ensureRoot();
      const full = path.startsWith("/") ? path : `/workspace/${path}`;
      const content = await ws.fs.readFile(full, "utf8");
      return { ok: true, path: full, content };
    }

    async list(path = "/workspace") {
      const ws = await this.ensureRoot();
      const entries = await ws.fs.readdir(path);
      return { ok: true, path, entries };
    }
  }
) {}
