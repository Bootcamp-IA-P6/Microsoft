# Fase 1 — Fuente de datos: EMT Madrid

**Estado:** Cerrado (actualizado 2026-07-20 — refleja alcance ampliado de v4)
**Referencia completa:** [`data-source-contract-v4.md`](./data-source-contract-v4.md)

## Resumen

Se eligió la API de EMT Madrid (MobilityLabs, fuente S1) más el feed GTFS-Realtime de Service Alerts (fuente S2) y el catálogo estático GTFS (fuente S3) como origen de datos, porque expone tiempos de llegada en tiempo real vía API REST pública con autenticación simple (apikey/token), sin necesidad de acceso a hardware o convenios institucionales — viable para el equipo en el tiempo disponible. El sistema, acotado a la zona Sol/Gran Vía (52 paradas, radio 600m desde Puerta del Sol), responde:

- Tiempo estimado de llegada de una línea a una parada concreta, y qué autobuses llegan ahora (US-01/02)
- Qué líneas pasan por una parada, dada por nombre o código (US-03)
- **Incidencias activas por línea** (US-07) — activado desde v4, no estaba en el alcance original
- **Frecuencia observada por línea**, entre semana / fin de semana (US-08) — activado desde v4, calculado sobre historial real de polling, nunca desde horario teórico

Deliberadamente **fuera de alcance**: retraso habitual respecto a horario teórico (no hay forma confiable de enlazar el vehículo real con el viaje programado de GTFS — ver contrato v4 §3), ocupación de vehículos, tarifas, y otros consorcios de transporte (Metro, Cercanías).

## Riesgos conocidos

| Riesgo | Detalle | Mitigación / estado |
|---|---|---|
| **Rate limit de la API (S1)** | Límite: **250.000 llamadas/día**. Con 52 paradas a polling ~60s, el consumo estimado ronda ~75.000/día — margen amplio. **Nota:** la cadencia real de producción todavía no está confirmada (pendiente abierto en el contrato v4 §12), así que este número es una estimación, no un dato medido. El feed S2 (GTFS-RT Service Alerts) es una fuente separada de Mobility Database, no consume esta misma cuota. | Bajo control, pendiente de confirmar con el soak test de 30 min. |
| **Caídas de servicio de la API** | La API de EMT es de terceros; no hay SLA garantizado conocido por el equipo. Un corte deja de actualizar bronze hasta que el servicio vuelva. | Cubierto por la regla de frescura: si el último poll exitoso supera 3× el intervalo normal (180s), `is_stale = true` y el agente avisa "dato desactualizado" en vez de mostrar algo viejo como vigente. |
| **Datos incompletos en ciertas ventanas horarias** | Fuera de horario de servicio algunas líneas no circulan; puede haber paradas con baja frecuencia de reporte. | Distinguido explícitamente en el contrato v4: `has_upcoming_bus = false` ("sin buses ahora, pero la línea sí pasa por aquí") separado de "línea no existe en esa parada". Estado válido de la respuesta, no un fallo. |
| **Región / residencia de datos en Azure — antes `UNVERIFIED`, ahora con acción concreta** | El modelo de agentes elegido (Fabric Data Agent expuesto como servidor MCP) requiere explícitamente el tenant setting **"Cross-geo processing and cross-geo storing for AI"** habilitado (requisito documentado por Microsoft). Sin esto habilitado, el flujo Data Agent → MCP → Foundry no funciona, sin importar que el resto esté bien construido. | **Acción pendiente, bloqueante:** confirmar con un Fabric Admin del tenant si este setting está habilitado, antes de invertir más tiempo en la integración de agentes. |

## Referencias
- Contrato completo de datos: [`data-source-contract-v4.md`](./data-source-contract-v4.md)