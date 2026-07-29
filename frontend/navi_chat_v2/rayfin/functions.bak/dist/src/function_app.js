import { UserDataFunctions } from '@microsoft/fabric-user-data-functions';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { DefaultAzureCredential } from '@azure/identity';
const udf = new UserDataFunctions();
function isLocalDev() {
    return (process.env.AZURE_FUNCTIONS_ENVIRONMENT === 'Development' ||
        !process.env.DATA_AGENT_URL);
}
async function callDataAgent(question, token) {
    const dataAgentUrl = process.env.DATA_AGENT_URL;
    const transport = new StreamableHTTPClientTransport(new URL(dataAgentUrl), {
        requestInit: {
            headers: { Authorization: `Bearer ${token}` },
        },
    });
    const client = new Client({ name: 'navi-chat', version: '1.0.0' }, { capabilities: {} });
    await client.connect(transport);
    const tools = await client.listTools();
    const chatTool = tools.tools.find((t) => t.name === 'get_answer');
    if (!chatTool) {
        throw new Error(`Data agent tool 'get_answer' not found`);
    }
    const result = await client.callTool({
        name: 'get_answer',
        arguments: { userQuestion: question },
    });
    await client.close();
    const content = result.content;
    if (result.isError) {
        throw new Error(`Data agent returned error: ${JSON.stringify(content)}`);
    }
    const textParts = content
        .filter((c) => c.type === 'text')
        .map((c) => c.text);
    const answerText = textParts.join('\n') || 'No se pudo obtener respuesta.';
    return answerText;
}
function mockAnswer(question, _language) {
    const q = question.toLowerCase();
    if (q.includes('cercanías') || q.includes('renfe')) {
        return { answerText: 'La estación de Cercanías más cercana es Sol. Puedes tomar la línea C-3 o C-4.' };
    }
    if (q.includes('autobús') || q.includes('bus')) {
        return { answerText: 'La parada de autobús más cercana es "Gran Vía - Montera" (líneas 51, 146).' };
    }
    if (q.includes('metro')) {
        return { answerText: 'La estación de Metro más cercana es Gran Vía (líneas 1, 5).' };
    }
    return { answerText: 'Madrid tiene una amplia red de transporte. ¿Qué tipo de transporte te interesa?' };
}
udf.func('chat', async (question, language) => {
    if (isLocalDev()) {
        return mockAnswer(question, language);
    }
    try {
        const credential = new DefaultAzureCredential();
        const token = await credential.getToken('https://api.fabric.microsoft.com/.default');
        const answerText = await callDataAgent(question, token.token);
        return { answerText };
    }
    catch (err) {
        console.error('Data agent call failed:', err);
        return mockAnswer(question, language);
    }
}, []);
export default udf;
//# sourceMappingURL=function_app.js.map