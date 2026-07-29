/**
 * mi-test.ts — Azure Function (HTTP trigger)
 *
 * Valida que ManagedIdentityCredential pueda obtener un token
 * con scope https://api.fabric.microsoft.com/.default.
 *
 * Despliegue: func azure functionapp publish <app-name>
 * Requiere: npm install @azure/identity
 */

import { AzureFunction, Context, HttpRequest } from "@azure/functions";
import { ManagedIdentityCredential, DefaultAzureCredential } from "@azure/identity";

const FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default";

interface TestResult {
  success: boolean;
  credential: string;
  tokenLength?: number;
  error?: string;
  stack?: string;
}

async function tryCredential(cred, label: string): Promise<TestResult> {
  try {
    const token = await cred.getToken(FABRIC_SCOPE);
    return { success: true, credential: label, tokenLength: token.token.length };
  } catch (err: any) {
    return { success: false, credential: label, error: err.message ?? String(err), stack: err.stack };
  }
}

const httpTrigger: AzureFunction = async function (
  context: Context,
  req: HttpRequest
): Promise<void> {
  const results: TestResult[] = await Promise.all([
    tryCredential(new ManagedIdentityCredential(), "ManagedIdentityCredential"),
    tryCredential(new DefaultAzureCredential(), "DefaultAzureCredential"),
  ]);

  const anyOk = results.some((r) => r.success);
  context.res = {
    status: anyOk ? 200 : 503,
    body: { results },
  };
};

export default httpTrigger;