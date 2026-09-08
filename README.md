# SIAO

**Sistema de Inteligencia Artificial Operativo.** Un sistema operativo móvil donde
la IA no es una app: **es el dueño del sistema**. Android baja de rango y pasa a ser
un inquilino en un contenedor, con una sola función en la vida: **que sigan andando
las APKs.**

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

## Qué APKs van a andar, y cuáles no — dicho en la portada

La versión anterior de este README prometía que anduvieran *"WhatsApp, **el banco** y
el resto de las APKs"*. **El propio `ADR-001` §8 declara lo contrario** y hay que
leerlo antes de comprar la promesa:

> *"Sin Play Integrity → apps bancarias · Prob. **Alta** · Impacto **Alto en
> Occidente** · **No hay solución legal completa**"*

Así que:

- **Deberían andar:** las APKs que no exigen atestación de integridad del dispositivo.
  WhatsApp entra acá. **NO MEDIDO todavía:** no hay contenedor de apps corriendo.
- **No van a andar completas:** las que exigen **Play Integrity**, banca en primer
  lugar. Un bootloader desbloqueado y un `system` que no es de Google no pasan la
  atestación, y eso **no tiene solución técnica legal**: es una decisión de Google,
  no un problema de ingeniería.
- **La respuesta del ADR es de mercado, no técnica:** mercados sin GMS, empresa,
  gobierno y nichos de privacidad.

Se dice acá, en la primera pantalla, porque el riesgo estaba declarado con honestidad
en el ADR desde el día 1 y **la portada prometía justo lo contrario**. Los dos
documentos son del mismo día y del mismo autor, y nunca se habían cruzado.

## Estado real, hoy · 2026-09-08

**Cero dispositivo. Cero producto. Pero ya no es "cero corrido":** la versión
anterior de esta sección decía *"nada de este repo corrió todavía en ninguna
máquina"*, y era falso.

| Pieza | Estado |
|---|---|
| userland openKylin arm64 fuera de su ISO | **VERDE medido** (FALSADOR-001) |
| sistema base `siao-base-s1` (177 paquetes, 248 MiB) | **VERDE medido** (F-002 cerrado) |
| GKI certificado de Google en QEMU aarch64 | **VERDE**, arrancó en 2,2 s |
| kernel compilado | **ocho builds**; el último, `vmlinux` de 354.673.168 B |
| fragmento de configs ABI-compatible en `android14-6.1` | **VERDE**, 68 B, cero offsets, cero CRC, sin parche al ACK |
| que un `.ko` real **CARGUE** (F-007c) | **NO MEDIDO** ← es lo que hoy bloquea todo |
| `Error 126` del arnés de build | **carrera ganada, no cerrada**: el guard salió inerte |
| contenedor de apps, HALs, dispositivo | **NO EMPEZADO** |
| **la capa 5: el sistema de IA** | **NO EMPEZADO**, y es lo único que nadie puede prestar |

**Lo commiteado es documentación más ~157 KB de Python, y ese Python son
instrumentos de medición, no producto.** Vive en `tools/` de las ramas `titan/*`.

## Donde vive cada cosa

| Qué | Dónde |
|---|---|
| **Dónde está cada medición (rama, SHA y archivo)** | **`docs/agents/MAPA-DE-LA-EVIDENCIA.md`** ← empezá por acá |
| Contexto vivo del proyecto | `docs/agents/CONTEXTO-SIAO.md` |
| Decisión de arquitectura (ADR-001) | `docs/adr/2026-09-05-01-arquitectura-siao-openkylin-sobre-treble.md` |
| Bitácora de entregas | `docs/agents/respuestas/` (la numeración colisiona: ordenar por fecha de commit) |
| Auditorías | `docs/audits/` y `docs/auditorias/` — **dos carpetas divergidas, sin unificar** |
| Reglas de trabajo para agentes | `AGENTS.md` |
| Inventario de máquinas (canónico, otro repo) | [`00-ENTORNOS-Y-CAPACIDADES.md`](https://github.com/gatehot59-star/mudh-mobile/blob/main/00-ENTORNOS-Y-CAPACIDADES.md) |

**La evidencia cruda NO está en `main`:** vive en cuatro ramas `titan/*` sin
protección que `main` no referencia por SHA. Hoy un `--delete` se lleva el trabajo
técnico del proyecto. Es la deuda más urgente y está sin resolver.

## Visibilidad y licencia

Este repo es **privado**. En privado, GitHub Actions come cuota del plan y el runner
es la mitad de máquina (2 vCPU / 8 GB contra 4 vCPU / 16 GB gratis e ilimitado en
público). Si SIAO va a usar la fábrica en serio, pasarlo a público es la decisión
correcta, y es de Abraham.

**No hay `LICENSE`**, y el plan integra openKylin (GPL), `system` de AOSP
(Apache-2.0) y libhybris. La compatibilidad de licencias no está ni planteada, y
elegirla es decisión de Abraham.
