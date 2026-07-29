process.env.DATA_AGENT_URL = 'https://api.fabric.microsoft.com/v1/mcp/workspaces/8bfdf6eb-bff5-4647-9484-daa63a5b7ff0/dataagents/52c51205-f10a-4a24-a306-ec5b27435405/agent';
process.env.NODE_ENV = 'production';
process.env.RAYFIN_ENV = 'production';

const { default: chat } = await import('./rayfin/functions/chat.ts');

const result = await chat({
  body: { question: '¿Cuánto tarda la línea 5 en llegar a la parada 5907?', language: 'es' }
});

console.log(JSON.stringify(result, null, 2));