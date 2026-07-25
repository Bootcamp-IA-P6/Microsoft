export const stopIdToName: Record<string, string> = {
  '5907': 'Sevilla',
};

export function getStopNameById(id: string): string | undefined {
  return stopIdToName[id];
}
