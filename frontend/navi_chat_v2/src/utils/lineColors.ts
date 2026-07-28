// src/utils/lineColors.ts
// Colores oficiales EMT Madrid — extraídos de StopInfo.lines[].color en Bronze
// Generado: 2026-07-29

export interface LineColor {
  bg: string;
  fg: string;
}

export const lineColors: Record<string, LineColor> = {
  "001": { bg: "#00aecf", fg: "#ffffff" },
  "002": { bg: "#00aecf", fg: "#ffffff" },
  "1": { bg: "#0072ce", fg: "#ffffff" },
  "146": { bg: "#0072ce", fg: "#ffffff" },
  "147": { bg: "#0072ce", fg: "#ffffff" },
  "148": { bg: "#0072ce", fg: "#ffffff" },
  "15": { bg: "#0072ce", fg: "#ffffff" },
  "150": { bg: "#0072ce", fg: "#ffffff" },
  "17": { bg: "#0072ce", fg: "#ffffff" },
  "18": { bg: "#0072ce", fg: "#ffffff" },
  "2": { bg: "#0072ce", fg: "#ffffff" },
  "20": { bg: "#0072ce", fg: "#ffffff" },
  "23": { bg: "#0072ce", fg: "#ffffff" },
  "26": { bg: "#0072ce", fg: "#ffffff" },
  "3": { bg: "#0072ce", fg: "#ffffff" },
  "31": { bg: "#0072ce", fg: "#ffffff" },
  "32": { bg: "#0072ce", fg: "#ffffff" },
  "35": { bg: "#0072ce", fg: "#ffffff" },
  "46": { bg: "#0072ce", fg: "#ffffff" },
  "5": { bg: "#0072ce", fg: "#ffffff" },
  "50": { bg: "#0072ce", fg: "#ffffff" },
  "51": { bg: "#0072ce", fg: "#ffffff" },
  "52": { bg: "#0072ce", fg: "#ffffff" },
  "53": { bg: "#0072ce", fg: "#ffffff" },
  "6": { bg: "#0072ce", fg: "#ffffff" },
  "65": { bg: "#0072ce", fg: "#ffffff" },
  "74": { bg: "#0072ce", fg: "#ffffff" },
  "75": { bg: "#0072ce", fg: "#ffffff" },
  "9": { bg: "#0072ce", fg: "#ffffff" },
  "M1": { bg: "#0072ce", fg: "#ffffff" },
  "M3": { bg: "#0072ce", fg: "#ffffff" },
  "N16": { bg: "#050505", fg: "#f2fb02" },
  "N18": { bg: "#050505", fg: "#f2fb02" },
  "N19": { bg: "#050505", fg: "#f2fb02" },
  "N20": { bg: "#050505", fg: "#f2fb02" },
  "N21": { bg: "#050505", fg: "#f2fb02" },
  "N25": { bg: "#050505", fg: "#f2fb02" },
  "N26": { bg: "#050505", fg: "#f2fb02" },
};

export function getLineColor(label: string): LineColor {
  return lineColors[label] ?? { bg: "#6b7280", fg: "#ffffff" };
}
