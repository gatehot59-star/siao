# El pedido formal a FABLE quedó entregable, y el gateway se cayó a mitad del transporte: segunda vía, no obstáculo

**Fecha (UTC):** 2026-09-08 · **main:** `dfcae61`

## 1 · Pedido

"ENTONCES HAZ EL PEDIDO FORMAL, FABLE SE ENCUENTRA EN ABACUS.IA, DESDE AHÍ AUDITA. GENERALE DOCUMENTO, YO SE LO ENTREGO."

O sea: un documento **autosuficiente y entregable a mano**, no un mensaje enviado. Fable audita desde `abacus.ai`, así que lo que importa no es invitarlo al repo sino que pueda **bajar los archivos con un GET** desde otra plataforma.

## 2 · Herramientas y máquina declaradas

- `brain-env` (container, gateway `build/run`): corrió la sonda `raw` y armó el texto. **Se cayó a mitad** (ver §4).
- **API de GitHub** (`push_files`) como segunda vía de escritura cuando el gateway murió.
- ClickUp: un Doc público como espejo entregable.
- Escrituras: dos commits a `main` (bitácora y evidencia, append-only). Cero runtime ajeno gastado.

## 3 · Qué se midió

| Sujeto | Instrumento | Resultado |
|---|---|---|
| lo que Fable puede bajar desde Abacus | `urllib` contra `raw.githubusercontent.com`, sin `Authorization`, 13 rutas | **13/13 rc=200** |
| control negativo por ARCHIVO | ruta inexistente en el **mismo** repo público | **rc=404** |
| control negativo por REPO | `mudh-mobile/main/AGENTS.md` (privado) | **rc=404** |
| identidad de la sonda | `md5sum` del script corrido | `6dda6c54735a986cc0ff538acce3247c` (2046 B) |
| que el commit llegó | `get_commit` sobre `main` | `dfcae61`, 2 archivos, +172 líneas |

**Los bytes de `raw` coinciden con los del worktree** en los 13 archivos (`AGENTS.md` 3359, el mapa 10406, el ADR-007 16062, el veredicto 2484, el JSON 856, etc.), así que lo que Fable baja es lo mismo que yo leo. Y **dos** controles negativos, no uno: discrimina por archivo **y** por repo.

## 4 · Evidencia cruda verbatim

### La sonda

```plain
$ md5sum raw_probe.py && wc -c raw_probe.py && python3 raw_probe.py; echo "rc_real=$?"
6dda6c54735a986cc0ff538acce3247c  raw_probe.py
2046 raw_probe.py
--- CORRIENDO ---
=== RAW ANONIMO (lo que FABLE puede bajar con un GET) ===
  rc=200      3359 B  AGENTS.md
  rc=200     10406 B  docs/agents/MAPA-DE-LA-EVIDENCIA.md
  rc=200      9588 B  docs/agents/CONTEXTO-SIAO.md
  rc=200      7047 B  docs/agents/briefings/2026-09-08-BRIEFING-FABLE-51-para-disenar-F-001-S2.md
  rc=200     16062 B  docs/adr/2026-09-08-07-ADR-007-resolucion-de-la-auditoria-de-FABLE-51.md
  rc=200       509 B  mediciones/f-001-s1/f001s1-aarch64.json
  rc=200     15464 B  mediciones/f-001-s1/f001s1-aarch64-boot.txt
  rc=200      8359 B  mediciones/f-002/F-002-v9.md
  rc=200      2484 B  mediciones/f-004d-61/F-004d-61-VEREDICTO.txt
  rc=200       856 B  mediciones/f-004d-61/v3-ocho.json
  rc=200      8272 B  tools/f001s1_arnes.py
  rc=200     15052 B  tools/f004d61_build.py
  rc=200      2293 B  mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md
  --> 13/13 bajables

=== CONTROL NEGATIVO 1: ruta inexistente en el MISMO repo publico ===
  rc=404  ruta inexistente -> la sonda discrimina por ARCHIVO

=== CONTROL NEGATIVO 2: repo PRIVADO por raw ===
  rc=404  mudh-mobile privado -> la sonda discrimina por REPO
rc_real=0
```

### La caída del gateway, sin recortar

```plain
Error POSTing to endpoint: {"type":".../cloudflare-1xxx-errors/error-1033/",
 "title":"Error 1033: Cloudflare Tunnel error","status":530,
 "detail":"The host is configured as a Cloudflare Tunnel, but Cloudflare is currently unable to reach it.",
 "error_code":1033,"error_name":"tunnel_error","error_category":"config",
 "ray_id":"a37e4c3fafaab876","timestamp":"2026-09-08T13:28:42Z",
 "zone":"mudh-mcp.icca-engine.com","retryable":true,"retry_after":120}
```

Segunda llamada, 3 segundos después: **el mismo 1033**, `ray_id a37e4c57689bb876`, `13:28:45Z`. Así que no fue un hipo: el túnel estaba caído.

### La segunda vía, y su verificación

```plain
$ push_files -> refs/heads/main
{"ref":"refs/heads/main","object":{"sha":"dfcae61aa639d30f021cdee0e513d4ebb1229318"}}

$ get_commit main
  sha        dfcae61aa639d30f021cdee0e513d4ebb1229318
  fecha      2026-09-08T13:29:58Z
  stats      additions 172, total 172
  docs/agents/pedidos/2026-09-08-PEDIDO-FORMAL-A-FABLE-51-disenar-F-001-S2.md  added  +128
  tools/raw_probe_fable.py                                                     added   +44
```

## 5 · Veredicto (conclusión, no medición)

El pedido formal está **entregable**: Fable no necesita credencial ni que le pasemos archivos, porque los 13 documentos bajan por `raw` con un GET anónimo y los dos controles negativos prueban que la sonda discrimina.

Y el obstáculo del turno **no cerró el turno**: el gateway del taller se cayó con un Cloudflare 1033 y el commit salió por la API de GitHub. Es exactamente la regla que ya me costó jornadas: no me falta capacidad, dejo de buscar la segunda máquina.

## 6 · Archivos generados

- `docs/agents/pedidos/2026-09-08-PEDIDO-FORMAL-A-FABLE-51-disenar-F-001-S2.md`
- `tools/raw_probe_fable.py`
- `docs/agents/respuestas/2026-09-08-05-el-pedido-formal-a-FABLE-entregado-y-el-gateway-caido-a-mitad-del-transporte.md` (este archivo)

## 7 · NO MEDIDO, declarado

- **El handle de GitHub de Fable.** Sin él no hay escritura para él. No lo inventé.
- **Si Fable bajó los archivos.** Medí que *se puede*, no que lo hizo. Confundirlo sería E-01.
- **Si el gateway volvió.** No lo re-probé después de la segunda vía; el turno no lo necesitaba.
- **F-001-S2 en sí:** sigue sin diseñarse y sin correrse. Este turno entrega el pedido.

--- METODO PROMETEO ---
Máquina: brain-env (container) para las mediciones + API de GitHub para la escritura.
Artefactos: los tres archivos del §6 en `main`, más el Doc público de ClickUp con el pedido entregable.
