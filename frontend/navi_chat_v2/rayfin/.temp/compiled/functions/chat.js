const isLocalDev = () => !process.env.DATA_AGENT_URL ||
    process.env.RAYFIN_ENV === 'development' ||
    process.env.NODE_ENV === 'development';
function mockAnswer(_question, language) {
    return {
        answerText: language === 'es'
            ? `Modo Mock: La línea 027 llegará a la parada de Lavapiés en 3 minutos.`
            : `Mock Mode: Bus line 027 will arrive at Lavapiés stop in 3 minutes.`,
    };
}
async function callDataAgent(token, question, _language) {
    const dataAgentUrl = process.env.DATA_AGENT_URL;
    const { Client } = await import('@modelcontextprotocol/sdk/client/index.js');
    const { StreamableHTTPClientTransport } = await import('@modelcontextprotocol/sdk/client/streamableHttp.js');
    const transport = new StreamableHTTPClientTransport(new URL(dataAgentUrl), {
        requestInit: {
            headers: { Authorization: `Bearer ${token}` },
        },
    });
    const client = new Client({ name: 'navi-chat-v2', version: '2.0.0' });
    await client.connect(transport);
    const toolsResult = await client.listTools();
    if (!toolsResult.tools?.length) {
        throw new Error('Data Agent did not expose any tools via MCP');
    }
    const tool = toolsResult.tools[0];
    const result = await client.callTool({
        name: tool.name,
        arguments: { userQuestion: question },
    });
    const text = result.content?.find((c) => c.type === 'text')?.text ?? '';
    if (!text) {
        console.error('[chat function] MCP callTool result had no text content:', JSON.stringify(result, null, 2));
    }
    return text;
}
export default async function chat(request) {
    try {
        const { question, language } = request.body;
        if (!question) {
            return { status: 400, body: { answerText: 'Question is required' } };
        }
        if (isLocalDev()) {
            return { status: 200, body: mockAnswer(question, language ?? 'es') };
        }
        const { DefaultAzureCredential } = await import('@azure/identity');
        const credential = new DefaultAzureCredential();
        const tokenResponse = await credential.getToken('https://api.fabric.microsoft.com/.default');
        const answerText = await callDataAgent(tokenResponse.token, question, language ?? 'es');
        return { status: 200, body: { answerText } };
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        console.error('[chat function] Error completo:', error);
        return {
            status: 500,
            body: { answerText: `Error: ${message}` },
        };
    }
}
