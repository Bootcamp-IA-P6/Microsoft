import type { BusInfo } from '@/utils/parseBusInfo';

export function hasIncident(raw: string): boolean {
  const match = raw.match(/incidencias?|desv[ií]os|corte|aver[ií]a/i);
  if (!match) return false;

  const sentenceStart = Math.max(
    raw.lastIndexOf('.', match.index),
    raw.lastIndexOf(',', match.index),
    raw.lastIndexOf(';', match.index)
  ) + 1;

  const clause = raw.slice(sentenceStart, match.index).toLowerCase();
  const negated = /\b(no|sin|ningun[ao]?)\b/.test(clause);

  return !negated;
}

interface BusCardProps {
  info: BusInfo;
  onFlyTo?: () => void;
}

export default function BusCard({ info, onFlyTo }: BusCardProps) {
  const hasIncidentFlag = hasIncident(info.raw);

  return (
    <div className="p-4 rounded-2xl bg-zinc-900/90 border border-zinc-800 shadow-md backdrop-blur-md flex flex-col gap-3 my-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="bg-emerald-500 text-zinc-950 font-extrabold text-xs px-2.5 py-1 rounded-lg shadow-sm tracking-wide">
            {info.line || '5'}
          </span>
          <span className="text-sm font-semibold text-zinc-100">
            {info.stopName || 'Parada 5907 (Sevilla)'}
          </span>
        </div>
        {hasIncidentFlag && (
          <span className="text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">
            ⚠️ Con desvíos
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3 mt-1">
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-black text-emerald-400">
            {info.firstBusMinutes != null ? info.firstBusMinutes : '5'}
          </span>
          <span className="text-xs font-bold text-emerald-400/90 uppercase tracking-wider">
            min
          </span>
        </div>

        {info.secondBusMinutes != null && (
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 pl-3 border-l border-zinc-800">
            <span className="text-zinc-500">Siguiente:</span>
            <span className="font-semibold text-zinc-300">{info.secondBusMinutes} min</span>
          </div>
        )}
      </div>

      {onFlyTo && (
        <button
          onClick={onFlyTo}
          className="self-start flex items-center gap-1.5 text-xs font-medium text-sky-400 hover:text-sky-300 transition-colors pt-1 cursor-pointer group"
        >
          <span>Ver ubicación en mapa 3D</span>
          <span className="group-hover:translate-x-0.5 transition-transform">→</span>
        </button>
      )}
    </div>
  );
}
