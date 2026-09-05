# CONTEXTO-SIAO · el contexto vivo del proyecto

**Creado:** 2026-09-05
**Última actualización:** 2026-09-05 (tercera del día: FALSADOR-001 cerrado en VERDE)

Este archivo es lo primero que se lee antes de trabajar en SIAO, y se actualiza en
el mismo turno en que algo cambia.

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

## 3. Estado medido

- **Repo:** `gatehot59-star/siao`, id `1358498188`, privado.
- **FALSADOR-001: A VERDE, B VERDE**, medido en aarch64 nativo de Actions.
  - A: 146 ELF de openKylin 3.0 huanghe arm64, `p_align 65536` en todos, cruzado
    con un job x64 que dio el mismo número con el mismo md5 de instrumento.
  - B: `bash 5.3.9 aarch64` de openKylin corriendo en `chroot` y leyendo su propio
    `/etc/os-release`: `NAME="openKylin" VERSION="3.0 (huanghe)"`.
  - Evidencia cruda: `mediciones/falsador-001/` en la rama
    `titan/falsador-userland-arm64`, commiteada por el propio runner.
- **CI:** existe `.github/workflows/falsador-userland-arm64.yml`. Tres corridas,
  seis jobs, seis exitosos.
- **Código de producto:** cero. No hay kernel compilado, ni HAL hablado, ni
  dispositivo elegido.

## 4. NO MEDIDO

- **Un kernel de páginas de 16 KB.** El runner tiene `pagesize 4096`: lo medido es
  que la alineación es compatible, no que cargue en un kernel de 16 KB.
- **El userland completo:** 12 paquetes y un shell, no `systemd`, UKUI, Wayland,
  AI SDK ni KylinBot.
- **El ISO Embedded ARM64 (2,29 GiB, Beta).** El falsador midió el repo `apt`, que
  es otro sujeto.
- La ruta real de `uname` en el `coreutils` de openKylin (dio 127 en `/usr/bin`).
- Todo lo del teléfono: GKI, `/vendor`, binder, HALs, AppFunctions en un device.
- La deprecación de NNAPI y el estado de QNN / NeuroPilot: vienen del documento
  fuente, **no verificados**.
- Los números de HarmonyOS NEXT, HyperOS y BlueOS son **hallazgos ajenos**.
- Si SIAO comparte código o infraestructura con MUDH o `icca-engine`.

## 5. Cementerio de hipótesis

| # | Hipótesis | Cómo murió |
|---|---|---|
| H-001 | "Virtualizar Android completo (host/guest) sobre el OS base" | Descartada en ADR-001: en SoC móvil no hay passthrough de GPU/ISP/módem con IOMMU usable por terceros; el guest necesita el kernel del vendor y el host queda sin hardware |
| H-002 | "La I de SIAO es de inferencia activa (Friston)" | Apuesta perdida de BRAIN, refutada por Abraham: es **Inteligencia Artificial** |
| H-003 | "openKylin era un nombre de relleno arrastrado de un paper asiático" | **Falsa, medida en vivo.** openKylin 3.0 existe y salió el 2026-08-28 |
| H-004 | "El userland arm64 de openKylin NO ejecuta fuera de su ISO" (mi propio v1 del falsador la afirmó con un ROJO) | **Falsa, y el ROJO era MÍO:** faltaba el `PT_INTERP`, no el binario. El v3 lo ejecutó: `bash 5.3.9 aarch64` leyendo `os-release`. Y mi control negativo no discriminaba corrupto de inexistente |
| H-005 | "El runner arm64 no va a nacer porque el repo es privado" | **Falsa.** `runner_id 1000002018`, labels `['ubuntu-24.04-arm']`, seis jobs con runner real. Apliqué un hallazgo de otro repo y otra semana como propiedad de la cuenta |
| H-006 | "Hay que compilar la variante ARM64 con alineación 16K desde el día 1" (tarea del roadmap del ADR-001) | **Innecesaria:** los binarios ya vienen a 65536, múltiplo de 16384 |
