# SIAO

Proyecto de **Jorge Abraham Mendieta**. Repositorio creado el **2026-09-05**.

## Estado real, hoy

**El alcance de SIAO NO esta declarado en este repo.** No hay codigo, no hay
decision de stack y no hay medicion de nada. Este commit crea el andamio del
metodo y nada mas: cualquier afirmacion sobre que hace SIAO tiene que entrar
con su fuente, no con una suposicion.

Lo unico que se sabe y se puede escribir sin inventar: SIAO es una de las tres
lineas de producto del ecosistema (junto a MUDH y AURA), o sea que existe para
ser **entregable y cedible**, no para quedar como proyecto abierto.

## Donde vive cada cosa

| Que | Donde |
|---|---|
| Contexto vivo del proyecto | `docs/agents/CONTEXTO-SIAO.md` |
| Bitacora de entregas y evidencia | `docs/agents/respuestas/` |
| Reglas de trabajo para agentes | `AGENTS.md` |
| Inventario de maquinas (canonico, otro repo) | [`00-ENTORNOS-Y-CAPACIDADES.md`](https://github.com/gatehot59-star/mudh-mobile/blob/main/00-ENTORNOS-Y-CAPACIDADES.md) |

## Visibilidad

Este repo es **privado**. Consecuencia medida y ya documentada en el inventario:
en privado, GitHub Actions consume la cuota del plan y el runner es la mitad de
maquina (2 vCPU / 8 GB contra 4 vCPU / 16 GB del publico, que es gratis e
ilimitado). Si SIAO va a usar la fabrica en serio, pasarlo a publico es la
decision correcta, y es de Abraham.
