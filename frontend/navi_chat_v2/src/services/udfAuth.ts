import {
  PublicClientApplication,
  InteractionRequiredAuthError,
  type AccountInfo,
} from '@azure/msal-browser';

const SCOPES = ['https://analysis.windows.net/powerbi/api/UserDataFunction.Execute.All'];

let pca: PublicClientApplication | null = null;

export function setMsalInstance(instance: PublicClientApplication): void {
  pca = instance;
}

function ensurePca(): PublicClientApplication {
  if (!pca) throw new Error('MSAL no inicializado. startApp() debe ejecutarse primero.');
  return pca;
}

function getActiveAccount(accounts: AccountInfo[]): AccountInfo | null {
  return accounts.find((a) => a.tenantId === import.meta.env.VITE_UDF_TENANT_ID) ?? accounts[0] ?? null;
}

export async function acquireToken(): Promise<string> {
  const app = ensurePca();

  const accounts = app.getAllAccounts();
  const account = getActiveAccount(accounts);

  if (account) {
    try {
      const result = await app.acquireTokenSilent({ scopes: SCOPES, account });
      return result.accessToken;
    } catch (err) {
      if (!(err instanceof InteractionRequiredAuthError)) {
        throw err;
      }
    }
  }

  await app.loginRedirect({ scopes: SCOPES });
  throw new Error('Redirigiendo a Microsoft login...');
}
