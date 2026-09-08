# La lectura de FABLE ya estaba abierta: lo medí SIN credencial y el control negativo da 404

**Fecha (UTC):** 2026-09-08 · **main:** `c69e9ec`

## 1 · Pedido

"Dale acceso de lectura a Fable y prepará su briefing."

## 2 · Herramientas y máquina declaradas

- `brain-env` (container aislado, gateway `build/run`): escritura en `/workspace`, lectura del worktree `/workspace/siao`.
- API pública de GitHub **sin header `Authorization`**, para medir lo que ve un tercero y no lo que veo yo.
- Escrituras: dos archivos nuevos commiteados a `main` (bitácora y evidencia, append-only). Cero runtime ajeno gastado.

## 3 · Qué se midió

| Sujeto | Instrumento | Resultado |
|---|---|---|
| lectura anónima de `siao` | `urllib` sin `Authorization`, 6 rutas | **6/6 rc=200** |
| control negativo | mismo script contra `mudh-mobile` (privado) | **rc=404** |
| identidad de la sonda | `md5sum` del script corrido | `2b08c0905f47e77da7955433431fe753`, igual al original |
| estado de `main` | `git fetch` + `rev-list` | 0 commits de diferencia en ambos sentidos |

**No hubo nada que otorgar:** el permiso de lectura ya estaba dado por la visibilidad pública del repo, activada ayer junto al ruleset. La acción pedida era un no-op y decirlo es el resultado.

## 4 · Evidencia cruda verbatim

```plain
$ md5sum anon.py && wc -c anon.py && python3 anon.py; echo "rc_real=$?"
2b08c0905f47e77da7955433431fe753  anon.py
1290 anon.py
--- CORRIENDO ---
=== LO QUE VE UN TERCERO SIN CREDENCIAL ===
  rc=200       5274 B  metadata del repo
  rc=200      15286 B  el mapa
  rc=200      21593 B  los 26 instrumentos
  rc=200       2105 B  el JSON de los 8 simbolos
  rc=200      16574 B  los 15 workflows
  rc=200      39473 B  los PRs

=== CONTROL NEGATIVO: un repo que SIGUE privado ===
  rc=404    mudh-mobile (privado) -> si da 404, la sonda discrimina
rc_real=0
```

```plain
$ ls -l  (rutas literales, las diez que el briefing manda leer)
-rw-r--r--  3359 AGENTS.md
-rw-r--r-- 16062 docs/adr/2026-09-08-07-ADR-007-resolucion-de-la-auditoria-de-FABLE-51.md
-rw-r--r--  9588 docs/agents/CONTEXTO-SIAO.md
-rw-r--r-- 10406 docs/agents/MAPA-DE-LA-EVIDENCIA.md
-rw-r--r--  2293 mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md
-rw-r--r--  8359 mediciones/f-002/F-002-v9.md
-rw-r--r--  2484 mediciones/f-004d-61/F-004d-61-VEREDICTO.txt
-rw-r--r--   856 mediciones/f-004d-61/v3-ocho.json
-rw-r--r--  8272 tools/f001s1_arnes.py
-rw-r--r-- 15052 tools/f004d61_build.py
```

Las diez existen: cero FALTA. La primera pasada de este mismo inventario dio **10/10 "FALTA"** porque el gateway se comió `$f` del bucle y `wc -c` recibió el string vacío (`cannot open ""`); se repitió con rutas literales. Un bucle con variable no es un instrumento en este shell.

## 5 · Veredicto (conclusión, no medición)

**No había acceso que dar.** El repo es público, la lectura anónima está abierta en las seis rutas que importan y el control negativo discrimina. Lo que Fable no tiene es **escritura** y los **8 `.stg`** (no commiteados por la regla clean-room, referenciados por hash en el manifiesto).

## 6 · Archivos generados

- `docs/agents/briefings/2026-09-08-BRIEFING-FABLE-51-para-disenar-F-001-S2.md` (7.047 B, md5 `25c0f799c93f1722baaecc62f72865c3`)
- `docs/agents/respuestas/2026-09-08-04-la-lectura-de-FABLE-ya-estaba-abierta-lo-medi-sin-credencial.md` (este archivo)

## 7 · NO MEDIDO, declarado

- **El handle de GitHub de Fable.** Sin él no puedo agregarlo como colaborador ni darle escritura. No lo inventé.
- **Si Fable efectivamente leyó el repo.** Medí que *se puede* leer, no que leyó. Son cosas distintas y confundirlas sería E-01.
- **F-001-S2 en sí:** sigue sin correrse. Este turno entrega el briefing, no la medición de G0.

--- METODO PROMETEO ---
Máquina: brain-env (container) + API pública de GitHub sin credencial.
Artefactos: los dos archivos del §6, commiteados a `main` antes de redactar el chat.
