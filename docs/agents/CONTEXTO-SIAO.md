# CONTEXTO-SIAO · el contexto vivo del proyecto

**Creado:** 2026-09-05
**Última actualización:** 2026-09-08 (corrección de H-01: el §3 afirmaba dos cosas falsas)

Este archivo es lo primero que se lee antes de trabajar en SIAO, y se actualiza en
el mismo turno en que algo cambia.

> **INVARIANTE, y nació de un error medido:** si la fecha de arriba es anterior al
> último archivo de `docs/agents/respuestas/`, **este archivo está desactualizado
> por definición** y hay que re-verificarlo contra el repo antes de citarlo.
>
> **Y la evidencia cruda NO vive acá:** está en cuatro ramas `titan/*` que `main`
> no referencia. El índice es `docs/agents/MAPA-DE-LA-EVIDENCIA.md`, que dice rama,
> SHA y archivo exacto por falsador. Sin ese mapa, leer `main` con método lleva
> igual a una conclusión falsa: ya pasó el 2026-09-07 con una auditoría externa.

---

## 1. Qué es SIAO — DECLARADO 2026-09-05

**SIAO = Sistema de Inteligencia Artificial Operativo.**

Un **sistema operativo móvil AI-first**: la IA es el sistema, no una app que corre
adentro del sistema. Android queda como **proveedor de hardware** (sus HALs de
`/vendor`) y como **contenedor de aplicaciones** (para que las APKs sigan andando),
pero deja de ser el sistema operativo.

**La idea madre es de Abraham**, y su formulación literal:

> "SIAO es el dueño de la casa. Android es el inquilino. Como SIAO está afuera y por
> encima, tiene poder absoluto: mete la mano en el corralito de Android, usa la app
> por vos, saca la información y te la entrega. Android ni se da cuenta."

**Por qué importa:** hoy la IA en un celular vive dentro de la jaula de permisos de
Android (Accessibility, Notification Listener, restricciones de background). Dar
vuelta el tablero es lo que destraba esa limitación.

**Nombre anterior descartado:** el documento de diseño se había titulado "AURA OS"
(Agent-Unified Runtime Architecture). Queda como nombre muerto. El proyecto es SIAO.

## 2. Decisiones tomadas

| Fecha | Decisión | Por qué |
|---|---|---|
| 2026-09-05 | El repo se llama `siao` en minúsculas | Convención de los otros cinco repos de la cuenta. El proyecto se sigue llamando SIAO |
| 2026-09-05 | Nace **privado** | Es la dirección reversible: pasar a público es un toggle, despublicar no |
| 2026-09-05 | El inventario de entornos **no se copia**, se linkea | Copiar 7.000 palabras a un repo más multiplica las copias a sincronizar. Divergencia declarada en `AGENTS.md` |
| 2026-09-05 | **Alcance declarado** (sección 1) | Abraham lo definió: Sistema de Inteligencia Artificial Operativo |
| 2026-09-05 | **Arquitectura: openKylin userland + contrato Treble + contenedor de apps sin vendor.** NO virtualización | ADR-001. En SoC móvil no hay passthrough de GPU/ISP/módem usable por terceros |
| 2026-09-05 | **openKylin SE QUEDA.** No era un nombre de relleno | Medido en vivo: existe, 3.0 del 2026-08-28, con agentes por MCP en el OS |
| 2026-09-05 | **NO hace falta recompilar el userland para páginas de 16 KB** | FALSADOR-001: los 146 ELF arm64 vienen con `p_align 65536`, que es múltiplo de 16384 |
| 2026-09-05 | **Actions arm64 sirve aunque el repo sea privado** | Medido: 6 jobs, 6 con runner real. Contradice mi propia predicción |
| 2026-09-06 | **La generación de referencia es `android14-6.1`**, no 6.6 | F-007b: el `.ko` real de un Pixel 8 tiene `vermagic 6.1.157-android14-11`. El ADR-001 §7 ya decía "GKI 6.1/6.6" desde el día 1 y no se releyó |

## 3. Estado medido

> **Las dos afirmaciones que este §3 tuvo mal desde el 09-05 hasta el 09-08**, y las
> dejo escritas en vez de borrarlas, porque un dato falso en el archivo de lectura
> obligatoria es el error más caro del repo y ya hizo fallar una auditoría externa:
>
> - Decía *"existe `.github/workflows/falsador-userland-arm64.yml`"*. **Falso en
>   `main`:** ahí hay exactamente `falsador-kvm-runners.yml` y
>   `falsador-kvm-usermod.yml`. Ese workflow vive en la rama, no en `main`.
> - Decía *"no hay kernel compilado"*. **Falso:** hay ocho builds.

- **Repo:** `gatehot59-star/siao`, id `1358498188`, privado. **Ramas sin protección
  (las seis, `main` incluida) y sin evidencia en `main`:** un `--delete` se lleva el
  trabajo técnico. Pendiente de decisión.
- **FALSADOR-001: A VERDE, B VERDE**, medido en aarch64 nativo de Actions.
  - A: 146 ELF de openKylin 3.0 huanghe arm64, `p_align 65536` en todos, cruzado
    con un job x64 que dio el mismo número con el mismo md5 de instrumento.
  - B: `bash 5.3.9 aarch64` de openKylin corriendo en `chroot` y leyendo su propio
    `/etc/os-release`: `NAME="openKylin" VERSION="3.0 (huanghe)"`.
  - Evidencia cruda: `mediciones/falsador-001/` en la rama
    `titan/falsador-userland-arm64`.
- **F-002 CERRADO:** rootfs `siao-base-s1`, 177 paquetes, 248 MiB, `rc=0`.
  Evidencia en `titan/f-002-rootfs`.
- **F-001-S1 VERDE:** el GKI certificado de Google arrancó en QEMU aarch64 en 2,2 s.
- **Kernel: OCHO builds**, no cero. El del 09-07 dio `vmlinux` de **354.673.168 B**,
  60 módulos y `Module.symvers` de 16.036 líneas.
- **F-004d @ android14-6.1: VERDE en ABI** — 68 B, cero offsets, cero CRC, ninguna
  struct tocada, baseline propio de 6.1 y **sin parche al ACK**. Es la generación que
  corren los Pixel reales.
  - **SALVEDAD 1 (R-13):** esto dice **ABI-compatible**. Que un `.ko` real **cargue**
    es F-007c y sigue **NO MEDIDO**.
  - **SALVEDAD 2:** el **`Error 126` NO está eliminado.** El guard serial salió
    inerte en los dos brazos (`segundos_archscripts: 0.02`,
    `archscripts_hizo_trabajo: false`, `Nothing to be done`), y el falsador declarado
    antes de correr decía que con 0,0 s no hay nada que interpretar. Es una carrera
    **ganada, no cerrada**, y el 126 está medido como intermitente.
- **CI en `main`:** dos workflows, `falsador-kvm-runners.yml` y
  `falsador-kvm-usermod.yml`. **Ninguno declara `permissions:` ni `timeout-minutes:`**
  y uno corre `chmod 666 /dev/kvm` sin guard de runner. Los 12 workflows de las
  mediciones viven en las ramas `titan/*`.
- **Código:** ~157 KB de Python, **todo instrumentos de medición**, y viven en
  `tools/` de las ramas. `main` no tiene `tools/`. **La capa 5 (el sistema de IA), que
  es lo único no prestable del proyecto, sigue sin empezar.**
- **Sin `LICENSE`**, con GPL (openKylin) + Apache-2.0 (AOSP) + libhybris en el plan.

**Dónde está cada medición:** `docs/agents/MAPA-DE-LA-EVIDENCIA.md`. No se citan
veredictos de memoria ni desde un `ls` de directorio.

## 4. NO MEDIDO

- **Un kernel de páginas de 16 KB.** El runner tiene `pagesize 4096`: lo medido es
  que la alineación es compatible, no que cargue en un kernel de 16 KB.
- **El userland completo:** 12 paquetes y un shell, no `systemd`, UKUI, Wayland,
  AI SDK ni KylinBot.
- **El ISO Embedded ARM64 (2,29 GiB, Beta).** El falsador midió el repo `apt`, que
  es otro sujeto.
- La ruta real de `uname` en el `coreutils` de openKylin (dio 127 en `/usr/bin`).
- Todo lo del teléfono: GKI, `/vendor`, binder, HALs, AppFunctions en un device.
- **F-007c: que un `.ko` real cargue.** Es lo que separa "ABI-compatible" de
  "funciona", y es lo único que hoy bloquea la capa 5.
- **Si el `Error 126` está muerto o dormido.** Necesita una matriz de N corridas del
  mismo brazo contando fallos: es `needs-runtime`.
- La deprecación de NNAPI y el estado de QNN / NeuroPilot: vienen del documento
  fuente, **no verificados**.
- Los números de HarmonyOS NEXT, HyperOS y BlueOS son **hallazgos ajenos**.
- Si SIAO comparte código o infraestructura con MUDH o `icca-engine`.
  → **Parcialmente medido el 09-07:** el audit MUDH→SIAO dice que pasa el control
  plane (Zod Gate, `IntentPlan`, `ValidatedCommand`) y que el runtime Android se
  adapta o se reemplaza. Está en `docs/audits/2026-09-07-auditoria-mudh-a-siao.md`.

## 5. Cementerio de hipótesis

> **Declarado y NO corregido en esta edición:** esta tabla se quedó en el primer día.
> El informe del 09-06 cuenta **11 falsadores y 19 errores propios**, y acá hay seis
> entradas. Ampliarla es otra entrega, no una corrección de línea, y por eso no la
> hago de paso: sería mezclar arreglar con escribir.

| # | Hipótesis | Cómo murió |
|---|---|---|
| H-001 | "Virtualizar Android completo (host/guest) sobre el OS base" | Descartada en ADR-001: en SoC móvil no hay passthrough de GPU/ISP/módem con IOMMU usable por terceros; el guest necesita el kernel del vendor y el host queda sin hardware |
| H-002 | "La I de SIAO es de inferencia activa (Friston)" | Apuesta perdida de BRAIN, refutada por Abraham: es **Inteligencia Artificial** |
| H-003 | "openKylin era un nombre de relleno arrastrado de un paper asiático" | **Falsa, medida en vivo.** openKylin 3.0 existe y salió el 2026-08-28 |
| H-004 | "El userland arm64 de openKylin NO ejecuta fuera de su ISO" (mi propio v1 del falsador la afirmó con un ROJO) | **Falsa, y el ROJO era MÍO:** faltaba el `PT_INTERP`, no el binario. El v3 lo ejecutó: `bash 5.3.9 aarch64` leyendo `os-release`. Y mi control negativo no discriminaba corrupto de inexistente |
| H-005 | "El runner arm64 no va a nacer porque el repo es privado" | **Falsa.** `runner_id 1000002018`, labels `['ubuntu-24.04-arm']`, seis jobs con runner real. Apliqué un hallazgo de otro repo y otra semana como propiedad de la cuenta |
| H-006 | "Hay que compilar la variante ARM64 con alineación 16K desde el día 1" (tarea del roadmap del ADR-001) | **Innecesaria:** los binarios ya vienen a 65536, múltiplo de 16384. **Y el ADR-001 §7 todavía la pide:** hay que purgarla de ahí |
