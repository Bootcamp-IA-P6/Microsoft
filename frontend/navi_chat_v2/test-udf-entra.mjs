// test-udf-entra.mjs
// Script aislado para probar autenticación contra Fabric User Data Function vía Entra ID
// con device code flow y una llamada POST de ejemplo.

import { PublicClientApplication } from '@azure/msal-node';

// Scope confirmado en docs Microsoft Learn:
// "Tutorial: Invoke user data functions from a Python application"
// https://learn.microsoft.com/en-us/fabric/data-engineering/user-data-functions/tutorial-invoke-from-python-app
// El tutorial usa InteractiveBrowserCredential con scope
// "https://analysis.windows.net/powerbi/api/user_impersonation"
// que corresponde al permiso delegado UserDataFunction.Execute.All (Power BI Service).
const SCOPES = ['https://analysis.windows.net/powerbi/api/UserDataFunction.Execute.All'];

async function main() {
  const clientId = process.env.UDF_TEST_CLIENT_ID;
  const tenantId = process.env.UDF_TEST_TENANT_ID;
  const udfUrl = process.env.UDF_PUBLIC_URL;

  if (!clientId || !tenantId || !udfUrl) {
    throw new Error(
      'Faltan variables de entorno. Setear: UDF_TEST_CLIENT_ID, UDF_TEST_TENANT_ID, UDF_PUBLIC_URL'
    );
  }

  const pca = new PublicClientApplication({
    auth: {
      clientId,
      authority: `https://login.microsoftonline.com/${tenantId}`,
    },
  });

  // --- Paso 1: Obtener token via device code ---
  const authResult = await pca.acquireTokenByDeviceCode({
    scopes: SCOPES,
    deviceCodeCallback: (response) => {
      console.log(response.message);
    },
  });

  const token = authResult.accessToken;

  // --- Paso 2: Llamar al UDF ---
  const response = await fetch(udfUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question: 'Cuanto tarda la linea 5 en llegar a la parada 5907',
      language: 'es',
    }),
  });

  const body = await response.text();

  if (!response.ok) {
    throw new Error(
      `UDF respondió con status ${response.status}\nBody:\n${body}`
    );
  }

  console.log(body);
}

main().catch((err) => {
  // Mensaje de error completo
  console.error('Error:', err.message ?? err);

  // Si es error de MSAL, imprime el errorCode específico
  if (err.errorCode) {
    console.error('MSAL errorCode:', err.errorCode);
  }
  if (err.errorMessage) {
    console.error('MSAL errorMessage:', err.errorMessage);
  }

  process.exit(1);
});

/*
Variables de entorno requeridas:

  UDF_TEST_CLIENT_ID   — Application (client) ID de la app registration "navi-udf-test-client"
  UDF_TEST_TENANT_ID   — Directory (tenant) ID del tenant (Contoso)
  UDF_PUBLIC_URL       — Public URL del UDF (ej. https://<fabric-endpoint>/api/...)
*/
