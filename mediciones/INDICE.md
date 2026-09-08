# Indice de mediciones · ESTA COPIA YA NO ES LA FUENTE

> **La fuente es `mediciones/INDICE.md` en `main`.** Este archivo quedó como puntero.

## Por qué

Esta copia era un **gate contradictorio**: tenía **dos filas** para
`F-004d @ android14-6.1`, misma generación y misma carpeta, una `NO MEDIDO` y otra
`VERDE`. La vieja no se borró al cerrar la medición, y su propio encabezado decía que
un run sin línea *"bloquea el siguiente falsador"*. **Un gate que se contradice no
gatea nada**, y quien leyera la primera fila se llevaba el dato viejo con autoridad
de índice. Es **H-12** de la segunda auditoría de Tao.

**Y no se arregló duplicando el arreglo.** El 2026-09-08 los 177 archivos de
`mediciones/` y `tools/` de las cuatro ramas se consolidaron en `main`, así que
mantener **dos** índices —uno acá y uno allá— es la próxima divergencia esperando
pasar: exactamente el defecto que este proyecto ya pagó con `CONTEXTO-SIAO.md`
contra el repo, y con `docs/auditorias/` contra `docs/audits/`.

**Un puntero que no se puede desincronizar es mejor que dos copias que hay que
sincronizar a mano.**

## Dónde está cada cosa ahora

| Qué | Dónde |
|---|---|
| El índice de mediciones, con las 10 filas y las salvedades | `mediciones/INDICE.md` en **`main`** |
| El mapa completo (rama, SHA y archivo por falsador) | `docs/agents/MAPA-DE-LA-EVIDENCIA.md` en **`main`** |
| Los 8 `.stg` (binario derivado, NO commiteados en `main`) | esta rama, referenciados por sha256 en `mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md` de `main` |

## Lo único que esta rama sigue teniendo en exclusiva

Los **8 archivos `.stg`** (89,3 MB). Son binarios derivados y `AGENTS.md` prohibe
commitearlos, así que no entraron a `main`. **Esta rama está protegida desde el
2026-09-08** contra borrado y force-push (ruleset `no-borrar-ni-forzar-la-evidencia`,
falsado intentando borrarla de verdad: dio `422 Cannot delete this branch`).
