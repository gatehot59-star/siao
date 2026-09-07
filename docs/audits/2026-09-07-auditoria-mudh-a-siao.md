# Auditoría MUDH-Mobile → SIAO

**Fecha:** 2026-09-07  
**Sujeto:** `gatehot59-star/mudh-mobile`, rama `main`, HEAD observado `f74cd8d9ae43b082c7ffe37f3fc820195338af56`  
**Destino:** SIAO, ADR-001 vigente  
**Veredicto:** MUDH no pasa entero. Pasa el **control plane determinista**; el runtime Android pasa detrás de adaptadores; `proot` no pasa como arquitectura y se reemplaza por LXC; la capa de política propia de SIAO todavía hay que construirla.

## 1. Método y límites

Se leyeron en GitHub el README, AGENTS, el estado consolidado del 2026-09-06, el handoff, el bridge TypeScript completo, el router y ejecutores Kotlin, Shizuku, inferencia local, contenedor, contratos y health. También se revisaron los PR abiertos antes de fijar el audit. No se compiló ni se ejecutó MUDH en este turno. El estado de cada pieza es **portable**, **portable con adaptador**, **referencia**, o **reemplazar**, no una afirmación de que SIAO ya la tenga integrada.

## 2. Qué pasa directamente

### A. Contratos de intención y resultados: DIRECTAMENTE PORTABLE

`mudh-kernel/src/bridge/intentSchema.ts` define un vocabulario cerrado de nueve acciones, `IntentPlan` estricto, agente cerrado, UUID, presupuesto, `expectedOrigin`, límites de tamaño, coordenadas normalizadas y reglas por verbo. `UiSnapshot`, `UiNode`, `ActionOutcome` y `PlanVerdict` son exactamente el tipo de frontera que necesita el principio SIAO: el planner propone un `tool_call`, no toca hardware ni filesystem.

La ligadura `snapshotId` + `ref`, la huella del nodo y el corte fail-closed cuando cambia el paquete o el árbol son reutilizables como contrato conceptual y de datos. En SIAO, el contrato final debería vivir en Rust o generarse desde un schema común, no quedar duplicado a mano entre TypeScript y Kotlin.

### B. Ejecución secuencial y auditoría: DIRECTAMENTE PORTABLE

`intentBridge.ts` valida antes de despachar, registra `received/rejected/action_ok/action_fail/completed`, corta el plan en el primer fallo y devuelve un veredicto determinista. `BlindFlowExecutor` y `AuditSink` son las interfaces correctas para `siao-policyd`, `siao-capd` y `siao-auditd`.

La decisión clave pasa intacta: **un fallo no se tapa continuando sobre estado incierto**. El código está medido por lectura, pero el Gate de `main` no tiene llamador ni ejecución productiva observada.

### C. Allowlist tipada para comandos: DIRECTAMENTE PORTABLE

`ValidatedCommand.kt` convierte la promesa de “comando validado” en un tipo que el compilador exige. Separa `GUEST` de `PRIVILEGED`, usa specs cerradas y no `sh -c`. Este patrón debe reaparecer en SIAO como capabilities declarativas: `siao.files`, `siao.telephony`, `siao.camera`, etc., con scope, argumentos y consentimiento explícitos.

## 3. Qué pasa detrás de un adaptador SIAO

### D. `ExecutorRouter` y target guard: ADAPTADOR NECESARIO

`ExecutorRouter.kt` hace el guard antes y después, serializa con un `Mutex` y rechaza si el origen observado no coincide. La propiedad es valiosa, pero su sujeto es Android: `currentWebOrigin()` y `currentForegroundPackage()`.

En SIAO el router debe apuntar a `CapabilityServer`/`capd`; el origen deja de ser solo paquete o URL y pasa a ser una capability, dispositivo, tenant Android o recurso con scope. No copiar el router tal cual: conservar el algoritmo de doble comprobación y cambiar el modelo de autoridad.

### E. `MudhAccessibilityExecutor`: ADAPTADOR SIAO-UI

La observación acotada a 400 nodos, profundidad 40, huellas, refs ligados y consumo de snapshot es buena ingeniería de seguridad. Pero `AccessibilityNodeInfo`, `performAction` y `AccessibilityService` son Android-only. Su destino SIAO es `siao.ui` sobre AT-SPI2/Wayland para el host y un puente privilegiado separado para el tenant Android.

El modo legacy que busca el primer nodo por texto/viewId es ambiguo: en SIAO debe quedar deshabilitado para operaciones sensibles o encerrado en una capability con consentimiento.

### F. `MudhWebViewExecutor`: ADAPTADOR DEL TENANT, NO CORE

La allowlist de navegación, `WebOrigin`, bloqueo de file access y limpieza ante timeout son reutilizables como reglas. El ejecutor depende de `WebView`, JavaScript y DOM, por lo que no es la vía general de SIAO. Para APKs Android queda como backend del Agent Bridge; para el host SIAO conviene MCP/capability nativa y no scraping.

Tiene deuda declarada: `parseDomResult` acepta contenido no confiable como `readback` y no marca su procedencia. No llevar esa deuda al contrato central.

### G. `ShizukuGate`: ADAPTADOR TEMPORAL, NO ARQUITECTURA

La firma `runPrivileged(ValidatedCommand)`, scopes separados, timeout y fail-closed son reutilizables. Shizuku, reflexión sobre `newProcess` y el uid shell ADB son Android-specific y sobran en SIAO: el reemplazo es `siao-capd`/servicios privilegiados del propio OS, con capabilities y consentimiento.

### H. LLM e inferencia: ADAPTADOR DE BACKEND

`ILlmProvider`, `LlmRequest`, `LlmResponse` y `CascadingLlmProvider` sirven como interfaz. `LlamaCppLlmProvider` es el candidato más portable como backend on-device, sujeto a una integración nativa SIAO y a límites de memoria/energía. `NanoLlmProvider` depende de Google AICore/Gemini y es Android/Google-only. `CloudLlmProvider` no debe ser el camino por defecto: SIAO debe poder operar localmente y declarar presupuesto, consentimiento y salida de datos.

La cascada actual acumula gasto con `get` seguido de `put`; eso no es una contabilidad atómica. En SIAO-auditd el recibo de costo debe ser transaccional.

### I. Health, update, rollback y storage: ADAPTADOR FUERTE

La cadena TypeScript de firma Ed25519, política, hash, health, swap y rollback es la pieza operativa más transferible después del Gate. Debe aterrizar en `siao-updated` con A/B, AVB/firmware y recibos firmados. `EncryptedKeyValueStore`, `EncryptedQueueStore` y SQLCipher son ideas válidas, pero SIAO necesita una bóveda/servicio de secretos del OS, no una base cifrada dentro de una app.

## 4. Qué queda como referencia o se reemplaza

| Pieza | Clasificación | Decisión SIAO |
|---|---|---|
| `proot` + `ProotContainer` | **REEMPLAZAR** | No es el host/tenant de ADR-001. Android apps van en LXC; openKylin es el host. Conservar solo la disciplina de `ValidatedCommand`, checksum, límites y diagnóstico. |
| `ContainerFactory` / rootfs Ubuntu | **REFERENCIA** | Enseña extracción, integridad y fallos, pero no debe crear el runtime final. |
| `MudhNativeBootstrap` | **REFERENCIA DE CABLEADO** | Es un composition root útil, pero el estado consolidado dice que nadie lo instancia en `main`; no hay integración viva que transferir. |
| `LocalBridgeServer` HTTP loopback | **ADAPTADOR / REEMPLAZAR EN HOST** | En SIAO el transporte interno debe ser Unix socket, binder/libgbinder o IPC de capability. Loopback+token es útil para un prototipo, no como autoridad. |
| `MudhA11yService` | **REEMPLAZAR** | Android service; la autoridad pasa a `siao.ui` y al Agent Bridge privilegiado. |
| `NanoLlmProvider` | **REFERENCIA** | No portable fuera del stack Google/Android. |
| `OllamaLlmProvider` y cloud | **REFERENCIA** | Backend opcional, nunca la raíz de confianza. |
| patches/hooks de seccomp de proot | **REEMPLAZAR** | Pertenecen al plan B congelado de MUDH, no al diseño LXC de SIAO. |

## 5. Lo que MUDH agrega y SIAO debe absorber

MUDH ya trae una respuesta concreta a problemas que ADR-001 todavía deja como arquitectura: frontera tipada, plan limitado, origen esperado, snapshot vinculante, ejecución ciega, corte ante fallo, scopes de privilegio, resultados deterministas, health/update/rollback y disciplina clean-room. Esa es la transferencia de mayor valor.

Lo que MUDH **no** resuelve todavía y SIAO debe construir: identidad criptográfica de agente no autodeclarada, `siao-capd` con allowlist declarativa por capability, consentimiento/dry-run, política de tenant Android, transporte IPC real, integración del Gate en el camino vivo, y contrato único Rust/TypeScript/Kotlin.

## 6. Orden recomendado

1. Congelar el contrato portable: `IntentPlan`, capability call, snapshot, outcome y receipt.
2. Implementar `siao-policyd`/`siao-capd` en Rust, tomando `ValidatedCommand` como patrón, no como dependencia.
3. Cablear un único camino medible: planner → Gate → policy → adapter → receipt.
4. Hacer primero el backend host `siao.ui` y un capability no destructivo (`screen.describe` o `fs.search`).
5. Después adaptar el Agent Bridge Android para `app.launch`/AppFunctions; Accessibility queda fallback.
6. Reemplazar `proot` por LXC y no gastar más ingeniería en el plan B salvo que una prueba de SIAO lo exija.

## 7. Evidencia y no medido

**Medido por lectura de fuente:** contratos, Gate, bridge fail-closed, snapshot, router, ejecutores, Shizuku, inferencia, contenedor y estado de integración.  
**No medido en este audit:** ejecución de MUDH en este turno; integración real del Gate en SIAO; boot de SIAO; LXC; AT-SPI2; AppFunctions; firma/rollback en SIAO; rendimiento y consumo de llama.cpp en el host openKylin.

**Archivos de referencia:** `mudh-kernel/src/bridge/{intentSchema.ts,intentBridge.ts,wiring.ts,localServer.ts}`, `app/src/main/java/com/mudh/mobile/{exec,privilege,llm,container}`, `app/src/main/java/com/mudh/mobile/contracts/{Contracts.kt,ValidatedCommand.kt}`, `mudh-kernel/src/{health,update}`.

---

**Método:** GitHub MCP, lectura de `main` de MUDH y `main` de SIAO; cero compilación, cero device, cero runtime ajeno.  
**Artefacto git:** este archivo.  
**Artefacto ClickUp:** se crea en el mismo turno.