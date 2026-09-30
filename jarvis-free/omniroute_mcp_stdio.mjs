import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const packageRoot = resolve(
  process.env.OMNIROUTE_PACKAGE_ROOT || join(process.cwd(), "node_modules", "omniroute"),
);
const guardPath = join(packageRoot, "bin", "mcpStdioConsoleGuard.mjs");
const serverPath = join(packageRoot, "dist", "open-sse", "mcp-server", "server.js");

await import(pathToFileURL(guardPath).href);
const { startMcpStdio } = await import(pathToFileURL(serverPath).href);
await startMcpStdio();
