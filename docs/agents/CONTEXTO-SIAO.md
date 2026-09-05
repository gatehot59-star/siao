# CONTEXTO-SIAO · el contexto vivo del proyecto

**Creado:** 2026-09-05
**Última actualización:** 2026-09-05 (segunda del día: se declara el alcance)

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
| 2026-09-05 | **openKylin SE QUEDA.** No era un nombre de relleno | Medido en vivo: existe, 3.0 del 2026-08-28, con agentes por MCP en el OS. Ver ADR-001 §Correcciones |

## 3. Estado medido

- **Repo creado:** sí, `gatehot59-star/siao`, id `1358498188`.
- **Código:** cero archivos de código. Cero compilación. Cero dispositivo.
- **CI:** no hay `.github/workflows/`. **Ningún workflow corrió nunca acá.**
- **Verificado en vivo el 2026-09-05:** la existencia y el contenido de openKylin 3.0,
  y el contrato de la API AppFunctions de Android. Evidencia cruda en la bitácora
  `docs/agents/respuestas/2026-09-05-02-*`.
- **Nada de este repo se ejecutó en ninguna de las tres máquinas.** Las escrituras
  son por la API de GitHub.

## 4. NO MEDIDO

- **Todo lo ejecutable.** No se arrancó un rootfs, no se compiló un kernel, no se
  habló un HAL por binder, no hay dispositivo elegido.
- Si el userland ARM64 de openKylin 3.0 arranca en un aarch64 ajeno. **Se puede
  medir gratis hoy** en Actions arm64 (4 vCPU, 16 GB, aarch64 nativo): es el
  falsador más barato del proyecto y todavía no se corrió.
- Alineación de páginas de 16 KB en los binarios de openKylin arm64: se lee con
  `readelf`, no se supone.
- Que NNAPI esté deprecado desde Android 15 y el estado de QNN/NeuroPilot: viene del
  documento fuente, **no lo verifiqué**.
- Todos los números de HarmonyOS NEXT, HyperOS y BlueOS del análisis competitivo son
  **hallazgos ajenos**, no mediciones propias.
- Si SIAO comparte código o infraestructura con MUDH, AURA (el proyecto, no el
  nombre muerto) o `icca-engine`.

## 5. Cementerio de hipótesis

| # | Hipótesis | Cómo murió |
|---|---|---|
| H-001 | "Virtualizar Android completo (host/guest) sobre el OS base" | Descartada en ADR-001: en SoC móvil no hay passthrough de GPU/ISP/módem con IOMMU usable por terceros; el guest necesita el kernel del vendor y el host queda sin hardware. Costo: 1,5–2,5 GB de RAM y batería. Es una demo |
| H-002 | "La I de SIAO es de inferencia activa (Friston)" | Apuesta perdida de BRAIN el 2026-09-05, refutada por Abraham en el turno siguiente: es **Inteligencia Artificial**. Se registra porque se apostó en público antes de saber |
| H-003 | "openKylin era un nombre de relleno que el análisis arrastró de un paper asiático" | **Falsa, medida en vivo.** openKylin 3.0 existe, salió el 2026-08-28 y es justamente un OS con agentes en la capa del sistema. Ver ADR-001 |
