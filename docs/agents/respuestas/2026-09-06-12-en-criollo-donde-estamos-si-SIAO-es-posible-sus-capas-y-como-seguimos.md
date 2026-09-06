# En criollo: dónde estamos, si SIAO es posible, sus capas, y cómo seguimos

**Fecha:** 2026-09-06 · **Modo:** TITAN FULL · **Pedido literal:** *"EN CRIOLLO DONDE NOS ENCONTRAMOS, SIAO ES POSIBLE, CUALES SERIAN SUS PARTES Y CAPAS, QUE DOLORES RESUELVE, COMO SEGUIMOS"*.

**Este documento no mide nada nuevo.** Es síntesis de lo medido en las 24 horas de F-001 a F-004c. Cada afirmación dice si es **MEDIDO**, **DE TERCEROS** o **NO MEDIDO**.

---

## 1 · ¿SIAO es posible? Sí, y ya no es una opinión

**Es posible, y lo firmo con cuatro números:**

1. **El userland de openKylin corre fuera de su ISO.** Su `bash 5.3.9` arm64 ejecutó en un chroot ajeno y leyó su propio `os-release`. **MEDIDO.** Sin esto el proyecto no existía.
2. **El sistema base se construye:** `rc=0`, 177 paquetes, 248 MiB, con `systemd 255.2` del release oficial. **MEDIDO.**
3. **El kernel se puede preparar sin romper el contrato de Android.** 495 bytes de diferencia de ABI, cero offsets movidos, cero CRC. **MEDIDO.**
4. **La parte más difícil ya la resolvió otro y es código libre:** `libhybris`, 844 estrellas, activo. **DE TERCEROS.**

**Pero "posible" no es "hecho", y la brecha honesta es una sola:** todo lo anterior se midió en máquinas de GitHub. **NADIE ARRANCÓ ESTO EN UN TELÉFONO NI EN UN EMULADOR TODAVÍA.** Eso es F-001-S1 y es el siguiente paso.

---

## 2 · Las seis capas, de abajo para arriba

### Capa 0 · El fierro y sus drivers — **prestada, no se toca**

El chip, la pantalla, la cámara, el módem. Los drivers los escribió el fabricante (Qualcomm, MediaTek) y **no hay código fuente público de la mayoría**. La decisión del ADR-001 es no pelear esa batalla: **se usan sus binarios tal como vienen.**

### Capa 1 · El kernel — **la que nos dio trabajo, y quedó resuelta en el papel**

El kernel de Android (GKI) viene con nueve cosas apagadas que systemd y los contenedores necesitan. **MEDIDO.** Y prenderlas rompe el contrato binario (KMI), lo que dejaría de cargar los drivers del fabricante.

**La solución que encontramos y medimos:** Google dejó seis espacios vacíos reservados en la estructura crítica del kernel, y ahí entran los 24 bytes que necesita `SYSVIPC`. **Resultado: se puede prender todo lo necesario y los drivers del fabricante siguen cargando.** Cuesta resignar `CGROUP_PIDS`, que es un límite de procesos, no algo para arrancar.

**Estado: MEDIDO en ABI. NO MEDIDO en boot.**

### Capa 2 · El sistema base — **existe y pesa 248 MiB**

openKylin arm64 con `systemd`. La base oficial más **tres** paquetes parchados. **MEDIDO**, salvo la verificación de firmas, que sigue en rojo declarado.

### Capa 3 · El puente al hardware — **la escribió otro y funciona**

`libhybris`: deja que un sistema Linux normal hable con los drivers de Android. Es la pieza que hace que la cámara y la GPU anden. **DE TERCEROS, 844 estrellas, y probado en producción desde 2013.** No hay que escribirla.

### Capa 4 · El inquilino Android — **el corralito de las apps**

Un contenedor (LXC) con Android adentro para correr APKs, compartiendo el mismo kernel. Sin duplicar drivers ni RAM.

**Y acá está el hallazgo más incómodo de la jornada:** **Lindroid** (205 estrellas, activo) **ya construyó esta capa**, pero al revés: Android de casero y Linux de inquilino. **Su lista de nueve configs de kernel coincide en ocho con la nuestra, armada sin conocernos.** O sea que la maquinaria está probada; lo que cambia es **quién manda**.

**Estado: DE TERCEROS para la maquinaria. NO MEDIDO para la inversión de roles.**

### Capa 5 · El sistema de IA — **la razón de ser, y la que no está escrita**

El agente que es **dueño** del sistema: ve los archivos, la red, los sensores y las apps sin pedir permiso a una sandbox. No es un asistente adentro de una app: es el que decide.

**Estado: NO MEDIDO. NO EMPEZADO. Y es lo único que hace a SIAO distinto de Lindroid.**

---

## 3 · Qué dolores resuelve, en orden de qué tan creíble es cada uno

### Dolor 1 · La IA en el teléfono hoy es una app con las manos atadas — **el más fuerte**

Cualquier asistente en Android vive en una caja: no puede leer tus archivos, no puede operar tus apps, no puede tocar los sensores. **Y medimos que la vía oficial de Google para arreglarlo (AppFunctions) exige ser una app privilegiada del sistema.** O sea que **para que un agente sirva de verdad, tiene que ser dueño del sistema. No hay atajo.** Ese es el dolor que SIAO resuelve por construcción y no por parche.

### Dolor 2 · Un teléfono tiene la potencia de una PC y no te deja usarla — **real y ya validado por el mercado**

Enchufar el teléfono a un monitor y tener un escritorio de verdad. **Lindroid existe justamente para esto**, o sea que el dolor está confirmado por un proyecto activo con usuarios. La diferencia de SIAO: el escritorio no es una app que abrís, es el sistema.

### Dolor 3 · Tus datos son la moneda de otro

Con la IA en el dispositivo y el sistema en tus manos, el procesamiento no sale del teléfono. **Es un dolor real pero es el más difícil de cobrar:** la gente lo dice y no lo paga.

### Dolor 4 · Dependencia de un solo proveedor

openKylin es chino y abierto, con soporte de cuatro arquitecturas. Para ciertos mercados y ciertos Estados eso **es** el producto. **NO MEDIDO como demanda.**

### Y el dolor que SIAO NO resuelve, para no venderte humo

**No resuelve "quiero un teléfono que funcione perfecto mañana".** Halium, el ecosistema base de todo esto, tiene **229 issues abiertos**. Portar a cada modelo de teléfono es trabajo artesanal. Cualquier plan que asuma "soporta cualquier teléfono" es falso.

---

## 4 · Dónde estamos, sin maquillaje

| Pieza | Estado |
|---|---|
| El userland arranca fuera de su ISO | **VERDE medido** |
| El sistema base se construye (177 paquetes) | **VERDE medido** |
| Firmas del sistema base verificadas | **ROJO declarado** |
| El kernel se puede preparar sin romper drivers | **VERDE medido** (ABI) |
| El kernel parcheado ARRANCA | **NO MEDIDO** ← el que falta |
| El puente al hardware (`libhybris`) | **DE TERCEROS, existe** |
| El corralito de apps Android | **DE TERCEROS, existe invertido** |
| El sistema de IA | **NO EMPEZADO** |
| Un teléfono real | **NO COMPRADO, y así debe quedar** |

**Traducción:** en 24 horas SIAO pasó de un nombre a **un proyecto con los cimientos medidos y el techo sin construir**. Lo caro que venía por delante (kernel y drivers) está resuelto o prestado. Lo que falta es lo que nadie puede prestarnos: **la capa 5.**

---

## 5 · Cómo seguimos — el orden, con el criterio declarado (O-01)

**Criterio: primero lo que hace que el producto EXISTA. Segundo, lo que nadie más puede hacer por nosotros. Último, lo que endurece algo que todavía no arranca.**

### Paso 1 · **F-001-S1: arrancarlo en QEMU** — el gate de todo

Meter el rootfs de 248 MiB sobre el kernel parcheado y llegar a que `systemd` levante. **Es el único paso que convierte "medimos que se puede" en "lo vimos andar".** Sin esto, todo lo demás es papel.

**Y es también el gate para el hardware: no se compra un teléfono antes de este verde.**

### Paso 2 · **Leer Lindroid de verdad, no su README**

Son el 80% de las capas 3 y 4, escrito y probado. **Reescribirlo sería el error de prioridad más caro del proyecto.** Y hay que leer su licencia, que todavía no leí y para uso comercial importa.

### Paso 3 · **El prototipo de la capa 5, en la PC**

El agente que gobierna el sistema no necesita un teléfono para existir: se puede prototipar sobre el mismo rootfs en QEMU. **Es lo único que nadie más está haciendo**, y es la respuesta a la pregunta "¿por qué SIAO y no Lindroid?".

### Paso 4 · **Firmas del sistema base (F-002 c)**

Corto, y cubre riesgo de cadena de suministro. **No desbloquea nada**, por eso va cuarto y no primero.

### Lo que BAJA de prioridad, con su razón

- **F-005 (AppFunctions):** Lindroid integró red, audio, input y storage **sin** eso.
- **F-003 (páginas de 16K):** se mide cuando haya un dispositivo real.
- **F-006 (LSM/SELinux):** endurecimiento de algo que todavía no arranca.

---

## 6 · La decisión que espera tu firma

1. **Aceptar el fragmento de nueve símbolos** como el oficial de SIAO, con `CGROUP_PIDS` movido a Fase 3.
2. **Confirmar el orden de arriba**, en particular que **F-001-S1 va antes que todo** y que el hardware espera ese verde.
3. **Decidir si SIAO adopta Lindroid como base** de las capas 3 y 4 en vez de reimplementarlas.

---

## NO MEDIDO de este documento

- **Todos los dolores son hipótesis de producto, no mediciones.** No hay un solo usuario entrevistado.
- **La licencia de `vendor_lindroid`**: sin leer.
- **Si la capa 5 es viable en el hardware de un teléfono** (RAM, térmica, batería con un modelo corriendo): sin medir.
- **El costo en tiempo de cada paso**: no estimado, y estimarlo sin haber corrido F-001-S1 sería inventar.

---

## Scorecard QA (tipo: reporte / síntesis)

Aplicables: Completitud, Arquitectura del razonamiento, Documentación, Innovación, Proceso QA. **N/A: Ejecutabilidad, Seguridad, Testing, DevOps** (35 pts: no hay código ni infra en esta entrega).

| Criterio | Score | Evidencia |
|---|---|---|
| Completitud | 14/15 | seis capas con estado, cuatro dolores con su fuerza, orden con criterio. −1: sin estimación de tiempo |
| Arquitectura del razonamiento | 10/10 | cada capa marcada MEDIDO / DE TERCEROS / NO MEDIDO, y el gate de hardware explícito |
| Documentación | 10/10 | en criollo como se pidió, sin perder los números |
| Innovación | 4/5 | nombra el dolor 1 como consecuencia de una medición propia (AppFunctions privilegiado). −1: no propone cómo validar los dolores |
| Proceso QA | 5/5 | cuatro NO MEDIDO declarados, incluido que los dolores son hipótesis |

**Total: 43/45 → 96/100.** Aprobado.

--- METODO TITAN ---
Accion delicada: NO
Modo aplicado:   TITAN FULL
Rubrica:         43/45 -> 96/100
N/A declarados:  35 pts (Ejecutabilidad, Seguridad, Testing, DevOps: es sintesis, no codigo)
Review externo:  no aplica (sin PR)
Instrumento:     ninguno nuevo. Sintesis de F-001, F-002, F-004, F-004b y F-004c, cuya
                 evidencia cruda esta en mediciones/f-001, f-002, f-004-v3, f-004b y
                 f-004c de la rama titan/f-004-kmi.
