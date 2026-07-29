import { describe, it, expect } from 'vitest';
import { hasIncident } from '../BusCard';

describe('hasIncident', () => {
  it('returns false when "no hay incidencias activas" is present', () => {
    const result = hasIncident(
      'El próximo bus de la línea 5 está llegando en este momento a la parada 5907 (Sol - Sevilla). Además, la línea 5 sí pasa por esta parada y no hay incidencias activas para esta línea.'
    );
    expect(result).toBe(false);
  });

  it('returns false when no incident is mentioned at all', () => {
    const result = hasIncident(
      'El próximo autobús de la línea 5 en la parada 5907 (Sol - Sevilla) está llegando en este momento. Si ves otro resultado sin tiempo de espera (y el dato está desactualizado), puede que no haya más buses próximamente, pero la línea sí para aquí.'
    );
    expect(result).toBe(false);
  });

  it('returns true when an active incident is described', () => {
    const result = hasIncident(
      'El próximo bus de la línea 5 está llegando en este momento a la parada 5907 (Sol - Sevilla). Además, hay una incidencia activa: por desmontaje de infraestructura en la zona de Cibeles —25 líneas de EMT están afectadas.'
    );
    expect(result).toBe(true);
  });

  it('returns true when incident is mentioned at the start of a sentence', () => {
    const result = hasIncident(
      'Afectado por incidencia: Desmontaje de infraestructura en zona Cibeles. Afectadas 25 líneas de EMT.'
    );
    expect(result).toBe(true);
  });

  it('returns false when no incident-related words appear', () => {
    const result = hasIncident(
      'El próximo bus de la línea 5 llega en 3 minutos a Sol - Sevilla.'
    );
    expect(result).toBe(false);
  });
});
