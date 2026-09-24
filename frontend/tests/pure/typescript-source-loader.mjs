"use strict";

import { resolve as resolvePath } from "node:path";
import { pathToFileURL } from "node:url";

const clientUrl = pathToFileURL(resolvePath("frontend/src/shared/api/client.ts")).href;
const generatedApiUrl = pathToFileURL(resolvePath("frontend/src/generated/api/index.ts")).href;

export async function resolve(specifier, context, nextResolve) {
  if (context.parentURL === clientUrl && specifier === "../../generated/api") {
    return { shortCircuit: true, url: generatedApiUrl };
  }
  return nextResolve(specifier, context);
}
