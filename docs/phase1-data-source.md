# Fase 1 — Fuente de datos: EMT Madrid

**Estado:** Cerrado
**Referencia completa:** [`data-source-contract-v4.md`](./data-source-contract-v4.md)

## Resumen

Se eligió la API de EMT Madrid (MobilityLabs) como fuente de datos porque expone tiempos de llegada en tiempo real de autobuses vía API REST pública con autenticación simple (apikey/token), sin necesidad de acceso a hardware o convenios institucionales, lo cual la hace viable para el equipo en el tiempo establecido. El sistema, acotado a la zona Sol/Gran Vía (52 paradas, radio ~600m), responde preguntas sobre tiempo estimado de llegada de una línea a una parada concreta, qué autobuses llegan ahora a una parada, y qué líneas pasan por una parada dada por nombre o código — deliberadamente el MVP no cubre causas de retraso, incidencias, tarifas ni rutas a paradas intermedias (ver Matriz de Alcance Excluido en el contrato v3).

## Riesgos conocidos

| Riesgo | Detalle | Mitigación / estado |
|---|---|---|
| **Rate limit de la API** | Límite actualizado a **250.000 llamadas/día** (antes 150.000). Con 52 paradas y polling cada 60s, el consumo real es de ~75.000/día — margen de ~3.3x sobre el límite actual. | Bajo control. El límite anterior (150k) ya daba margen 2x; el aumento a 250k libera espacio si se decide ampliar la zona más adelante, aunque eso no está planeado para el MVP. |
| **Caídas de servicio de la API** | La API de EMT es de terceros; no hay SLA garantizado conocido por el equipo. Un corte deja de actualizar `bronze` hasta que el servicio vuelva. | Cubierto por la regla de frescura ya definida: si el último poll exitoso de una parada supera 3x el intervalo normal (~3 min), se marca `is_stale = true` y el agente avisa "dato desactualizado" en vez de mostrar un ETA viejo como si fuera vigente. |
| **Datos incompletos en ciertas ventanas horarias** | Fuera de horario de servicio (madrugada) algunas líneas no tienen buses circulando; también puede haber paradas con baja frecuencia de reporte. | Ya distinguido en el contrato v3: `has_upcoming_bus = false` ("sin buses ahora, pero la línea sí pasa por aquí") se separa explícitamente de "línea no existe en esa parada" (ver sección 4 del contrato). No se trata como fallo del sistema, es un estado válido de la respuesta. |
| **Cambios no anunciados en el catálogo GTFS** | El catálogo estático (paradas, líneas, cabeceras) se carga una vez (`catalog_loaded_at`); si CRTM actualiza el GTFS, el sistema no lo detecta automáticamente. | Fuera de alcance del MVP. Recarga manual si se detecta desalineación entre `silver_stop_lines` y la realidad. |

## Referencias
- Contrato completo de datos: [`data-source-contract-v4.md`](./data-source-contract-v4.md)
