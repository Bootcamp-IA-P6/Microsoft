export const stopIdToName: Record<string, string> = {
  '5907': 'Sevilla',
};

export const stopNameToId: Record<string, string> = {};
for (const [id, name] of Object.entries(stopIdToName)) {
  stopNameToId[name.toUpperCase()] = id;
}

export function getStopNameById(id: string): string | undefined {
  return stopIdToName[id];
}

export function getStopIdByName(name: string): string | undefined {
  return stopNameToId[name.toUpperCase().trim()];
}
