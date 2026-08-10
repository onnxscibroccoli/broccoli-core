import { DurableObject } from "cloudflare:workers";
import { withWorkspace } from "@cloudflare/computer";

// Workspace is mixed in via withWorkspace + storage factory.
// File ops happen from the Worker through getWorkspace(stub).
export class BroccoliWorkspace extends withWorkspace(
  class extends DurableObject {},
  (self) => ({ storage: self.ctx.storage })
) {}
