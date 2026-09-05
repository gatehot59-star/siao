# SIAO

**Sistema de Inteligencia Artificial Operativo.** Un sistema operativo móvil donde
la IA no es una app: **es el dueño del sistema**. Android baja de rango y pasa a ser
un inquilino en un contenedor, con una sola función en la vida: que sigan andando
WhatsApp, el banco y el resto de las APKs.

Proyecto de **Jorge Abraham Mendieta**. Repositorio creado el 2026-09-05.

## La tesis en tres líneas

1. **SIAO es dueño de la casa.** Corre nativo sobre el fierro: kernel, batería,
   cámara, sensores, micrófono, radio. Los agentes viven acá, con acceso directo a
   binder y D-Bus, sin hipervisor en el medio.
2. **Android es el inquilino.** Un contenedor LXC (no una VM) con solo el `system` de
   AOSP, sin `vendor` propio: reutiliza los HALs del host. Sirve para correr APKs.
3. **SIAO es el titiritero.** Mete la mano en el corralito, usa la app, saca el dato
   y lo devuelve. La app no se enteró.

## Lo que NO es

- **No es virtualización.** Ver `docs/adr/2026-09-05-01-*`: en SoC móvil no hay
  passthrough de GPU/ISP/módem usable, y el host se queda sin hardware.
- **No es ingeniería inversa de drivers.** Se honra el contrato Treble (AIDL sobre
  binder) desde un userland distinto. Es el modelo Halium/Sailfish, en producción
  desde 2013.

## Estado real, hoy

**Cero código. Cero compilación. Cero dispositivo.** Lo que existe es el alcance
declarado y la decisión de arquitectura, con las cuatro correcciones medidas al
documento fuente. Nada de este repo corrió todavía en ninguna máquina.

## Donde vive cada cosa

| Qué | Dónde |
|---|---|
| Contexto vivo del proyecto | `docs/agents/CONTEXTO-SIAO.md` |
| Decisión de arquitectura (ADR-001) | `docs/adr/2026-09-05-01-arquitectura-siao-openkylin-sobre-treble.md` |
| Bitácora de entregas y evidencia | `docs/agents/respuestas/` |
| Reglas de trabajo para agentes | `AGENTS.md` |
| Inventario de máquinas (canónico, otro repo) | [`00-ENTORNOS-Y-CAPACIDADES.md`](https://github.com/gatehot59-star/mudh-mobile/blob/main/00-ENTORNOS-Y-CAPACIDADES.md) |

## Visibilidad

Este repo es **privado**. En privado, GitHub Actions come cuota del plan y el runner
es la mitad de máquina (2 vCPU / 8 GB contra 4 vCPU / 16 GB gratis e ilimitado en
público). Si SIAO va a usar la fábrica en serio, pasarlo a público es la decisión
correcta, y es de Abraham.
