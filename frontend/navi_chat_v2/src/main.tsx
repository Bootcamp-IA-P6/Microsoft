import { createRoot } from 'react-dom/client';
import App from '@/App';
import { PublicClientApplication } from '@azure/msal-browser';
import { setMsalInstance } from '@/services/udfAuth';

const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_UDF_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_UDF_TENANT_ID}`,
    redirectUri: window.location.origin,
    navigateToLoginRequestUrl: true,
  },
  system: {
    allowNativeBroker: false,
  },
} as unknown as import('@azure/msal-browser').Configuration;

const msalInstance = new PublicClientApplication(msalConfig);

async function startApp() {
  await msalInstance.initialize();

  try {
    const response = await msalInstance.handleRedirectPromise();
    if (response) {
      msalInstance.setActiveAccount(response.account);
    } else {
      const currentAccounts = msalInstance.getAllAccounts();
      if (currentAccounts.length > 0) {
        msalInstance.setActiveAccount(currentAccounts[0]);
      }
    }
  } catch (error) {
    console.error('Error al procesar redirect de MSAL:', error);
  }

  setMsalInstance(msalInstance);

  createRoot(document.getElementById('root')!).render(<App />);
}

startApp();
