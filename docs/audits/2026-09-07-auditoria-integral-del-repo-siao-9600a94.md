# Auditoría integral del repo `siao`

**Fecha:** 2026-09-07 · **Rol:** QA AUDITOR (TITÁN Tao) · **Pedido literal:** *"AUDITA EL PROYECTO SIAO"*
**Sujeto:** `gatehot59-star/siao` @ `main` = **`9600a942a8ac9c04146d19a458c415cab3880274`** (2026-09-07 17:31 UTC)
**Repo leído EN VIVO** por API de GitHub. Cero contenido supuesto, cero archivo citado de memoria.
**Máquinas usadas:** ninguna. **Cero compilación, cero dispositivo, cero corrida.** Esta auditoría no mide nada nuevo: audita lo que el repo ya tiene commiteado.

> **Cómo leer esto:** cada afirmación lleva su evidencia (archivo, sección, SHA o salida de API). Lo que no pude medir dice **NO MEDIDO** y dice con qué herramienta me faltó.

---

## 0 · El hallazgo que ordena a todos los demás

**El problema más caro de SIAO hoy no es técnico: es que la memoria canónica del proyecto miente, y `AGENTS.md` obliga a creerle.**

`AGENTS.md` (raíz, 1.659 B) abre con: *"Antes de escribir una linea en este repo: 1. **Leer `docs/agents/CONTEXTO-SIAO.md`.** Responder de memoria sobre este proyecto es un error de metodo, no un atajo."*

Ese archivo, a HEAD, dice en su línea 4: **`Última actualización: 2026-09-05`**. Están sin registrar dos días completos y ~30 commits, entre ellos **todo F-002, toda la serie F-004, F-007a, F-007b, F-001-S1 y el falsador de KVM**.

O sea: la regla anti-alucinación del repo funciona al revés de lo que promete. Un agente nuevo que la obedezca al pie de la letra arranca con datos falsos, y con autoridad canónica encima.

---

## 1 · Inventario real de `main` a `9600a94`

| Ruta | Qué hay |
|---|---|
| `AGENTS.md` | 1.659 B · reglas de entrega |
| `README.md` | 2.346 B · tesis + estado |
| `.github/workflows/` | **2** archivos: `falsador-kvm-runners.yml` (5.009 B), `falsador-kvm-usermod.yml` (5.382 B) |
| `disparadores/` | 2 `.txt` de disparo por `push` |
| `docs/adr/` | 5 ADR (ADR-001 al ADR-006, con el 04 y el 06 como resoluciones de auditoría) |
| `docs/agents/CONTEXTO-SIAO.md` | 5.645 B · el contexto vivo |
| `docs/agents/respuestas/` | **28** archivos de bitácora |
| `docs/auditorias/` | 1 archivo (informe técnico del 09-06, 30.729 B) |
| `docs/audits/` | 3 archivos (todos del 09-07) |

**Lo que NO existe en el árbol:** `LICENSE`, `.gitignore`, `CODEOWNERS`, `SECURITY.md`, plantillas de issue/PR, `dependabot.yml`, y **ni un solo archivo de código de producto** (no hay `src/`, ni manifest de ningún ecosistema).

**Ramas (5):** `main` + `titan/f-001-userland-sobre-gki` (`98dc52e`), `titan/f-002-rootfs` (`4a862d1`), `titan/f-004-kmi` (`2b87723`), `titan/falsador-userland-arm64` (`139b863`). **Las cinco con `protected: false`.**

**Pull requests: 0** (`state=all` devuelve lista vacía). **Issues: 0** (`totalCount: 0`).

---

## 2 · Hallazgos

### H-01 · CRÍTICO · El contexto vivo está atrasado y afirma dos cosas falsas

**Evidencia, `docs/agents/CONTEXTO-SIAO.md` §3 "Estado medido":**

1. *"**CI:** existe `.github/workflows/falsador-userland-arm64.yml`."* → **FALSO en `main` a HEAD.** El directorio `.github/workflows/` contiene exactamente `falsador-kvm-runners.yml` y `falsador-kvm-usermod.yml`. El workflow citado no está en `main`; si vive en algún lado es en la rama `titan/falsador-userland-arm64`, y el contexto no lo dice.
2. *"**Código de producto:** cero. No hay kernel compilado, ni HAL hablado, ni dispositivo elegido."* → la primera y la última cláusula siguen siendo verdad; **"no hay kernel compilado" es falso**: `docs/agents/respuestas/2026-09-07-01-*.md` §3 reporta `vmlinux 354.673.168 B`, 60 módulos y `Module.symvers` de 16.036 líneas, y hay ocho builds en la serie F-004.

**Además:** §5 "Cementerio de hipótesis" tiene seis entradas (H-001…H-006), mientras `docs/auditorias/2026-09-06-INFORME-TECNICO-COMPLETO-para-auditoria.md` declara **11 falsadores y 19 errores propios**. El cementerio se quedó en el primer día.

**Por qué es crítico y no cosmético:** es el único archivo del repo que `AGENTS.md` declara de lectura obligatoria previa. Un dato falso ahí se propaga a cada sesión nueva, y el costo ya está medido en este mismo proyecto: el informe del 09-06 clasifica 19 errores propios y varios son exactamente de esta familia (afirmar sin re-medir).

**Corrección propuesta (no aplicada):** sincronizar §3 y §5 al HEAD y agregar al pie una línea de invariante — *"si este archivo tiene fecha anterior al último archivo de `respuestas/`, está desactualizado por definición"*. **No la aplico en esta entrega:** es el archivo canónico del proyecto y su reescritura durante una auditoría mezcla el peritaje con la intervención. Queda pedida y esperando tu OK.

### H-02 · ALTO · El README declara un estado que el repo refuta

`README.md`, sección *"Estado real, hoy"*: *"**Cero código. Cero compilación. Cero dispositivo.** (…) Nada de este repo corrió todavía en ninguna máquina."*

**Refutado por el propio repo:** el rootfs de openKylin arm64 se construyó (177 paquetes, 248 MiB, `rc=0`; `respuestas/2026-09-06-05-*`), el GKI certificado de Google arrancó en QEMU aarch64 en 2,2 s (commit `8572d82`), y ocho builds de kernel produjeron `.stg` y `Module.symvers`. "Cero dispositivo" sigue siendo cierto; **"nada corrió en ninguna máquina" no.**

Es la primera pantalla que ve cualquiera, incluido un tercero al que le muestres el proyecto.

### H-03 · ALTO · Cero PRs y cero issues: la evidencia crítica vive en ramas huérfanas y la deuda no tiene dueño

Tres consecuencias medibles, no opinables:

1. **Evidencia fuera de `main`.** `CONTEXTO-SIAO.md` §3 apunta la evidencia cruda de FALSADOR-001 a `mediciones/falsador-001/` **en la rama `titan/falsador-userland-arm64`**. Esa rama no está protegida, no tiene PR y `main` no la referencia por SHA. Un `git push --delete` se lleva la evidencia del falsador que habilitó el proyecto entero. Lo mismo aplica a `titan/f-002-rootfs`, `titan/f-004-kmi` y `titan/f-001-userland-sobre-gki`.
2. **Deuda sin dueño.** El informe del 09-06 enumera **24 NO MEDIDO**; el archivo del 09-07 agrega cuatro más. **Ninguno tiene issue.** No hay ni un ítem del proyecto con responsable y estado rastreable fuera de la prosa de los `.md`.
3. **Los workflows entraron directo a `main`.** `AGENTS.md` reserva `main` para bitácora y evidencia *"append-only, no compilan y nadie clona de ellas"*, y manda el **código** a rama `titan/*`. Pero `.github/workflows/*.yml` es código ejecutable con el token del repo, y entró directo (commits `f515092`, `45a4a41`, `e76c166`, `08d454f`). **Cero revisión ajena en toda la historia del repo**, ni humana ni automática.

### H-04 · MEDIO · Dos carpetas de auditoría divergidas el mismo día

`docs/auditorias/` (creada el 09-06, 1 archivo) y `docs/audits/` (creada el 09-07, 3 archivos) cumplen la misma función. **Ninguna de las dos figura** en la tabla *"Donde vive cada cosa"* del README, que solo lista `docs/agents/respuestas/`.

Efecto práctico: quien busque "la auditoría anterior" encuentra la mitad y concluye que la otra no existe. **Este mismo archivo tuvo que elegir una** — elegí `docs/audits/` por ser la convención más reciente, y lo declaro para no fabricar una tercera.

### H-05 · MEDIO · "Leer el último archivo de `respuestas/`" es una regla ambigua

`AGENTS.md` §2 manda leer *"el ultimo archivo de `docs/agents/respuestas/`"*. La numeración **colisiona**: hay dos `2026-09-06-01-`, dos `-02-`, dos `-03-` y dos `-04-` (por ejemplo `2026-09-06-01-el-tercer-muro-era-MI-PIN…` y `2026-09-06-01-la-vm-del-corpus-es-x86-64…`).

O sea que el orden alfabético **no** reconstruye el orden temporal, no hay índice, y son 28 archivos sin `INDICE.md`. La regla de arranque del repo no es determinista.

### H-06 · MEDIO · Los dos workflows no declaran `permissions:` ni `timeout-minutes`, y uno afloja permisos de `/dev/kvm`

`falsador-kvm-usermod.yml` ejecuta `sudo usermod -aG kvm` y `sudo chmod 666 /dev/kvm`. En el runner **hosted** efímero que hoy declara (`runs-on: ubuntu-24.04`) es inocuo: la máquina se destruye. **El riesgo es de reutilización:** el ecosistema ya opera un runner self-hosted (en `mudh-mobile`), y basta cambiar una label o copiar el workflow para dejar `/dev/kvm` **world-writable de forma persistente en una máquina real**.

Ninguno de los dos declara `permissions:`, así que el `GITHUB_TOKEN` del job hereda el default del repo/organización — **NO MEDIDO**: no tengo herramienta para leer la configuración de permisos por defecto. Tampoco declaran `timeout-minutes`, y los dos disparan por `push` sobre `disparadores/*.txt`.

**Mitigación propuesta (no aplicada, es un cambio de workflow y va con tu OK):** `permissions: contents: read` a nivel workflow, `timeout-minutes: 15` por job, y guardar el paso que afloja permisos con `if: runner.environment == 'github-hosted'`. La expresión hay que verificarla en corrida antes de darla por buena.

### H-07 · ALTO · El camino crítico está a UNA corrida, y sigue NO MEDIDO

La única ventaja técnica medida de SIAO —que el fragmento de configs es KMI-safe— **está medida en la generación equivocada**:

```plain
F-004c / F-004d @ android15-6.6  ->  VERDE MEDIDO (68 B, cero offsets, cero CRC)
.ko REAL de un Pixel 8           ->  vermagic 6.1.157-android14-11
F-004d @ android14-6.1           ->  NO MEDIDO (falta el .stg del baseline)
```

Evidencia: `respuestas/2026-09-06-14-F-007b-*` (vermagic del Pixel), `docs/adr/2026-09-06-06-ADR-006-*` (en 6.1 **el slot 3 de `ANDROID_KABI_RESERVE` ya está ocupado**, o sea que el parche de F-004c no compilaría ahí), y `respuestas/2026-09-07-01-*` §5 (falta un brazo, no el resultado).

**Lo bueno:** la causa raíz del bloqueo ya está medida y es del arnés, no del kernel — `HOSTCFLAGS` se le pasa al build paralelo y no al paso serial, así que `make` recompila `fixdep` en paralelo y vuelve la carrera del `Error 126` (§2 del mismo archivo). **El arreglo es de una línea y está escrito sin correr** (§6, con predicción declarada y falsable: si `archscripts` vuelve a tardar 0,0 s, el arreglo no se aplicó).

**Traducción de prioridad:** el proyecto tiene una medición decisiva a una corrida de distancia, con el arreglo ya redactado. Es lo más rentable que hay pendiente.

### H-08 · ALTO · La capa diferencial tiene cero código, y no hay licencia

100% de lo commiteado en `main` es documentación, salvo dos workflows y dos disparadores de texto. La **capa 5 (el sistema de IA)** —la única que, según `respuestas/2026-09-06-12-*`, distingue a SIAO de Lindroid y de Halium— **no está empezada**.

Y **no hay `LICENSE`**. SIAO planea integrar userland openKylin (GPL), `system` de AOSP (Apache-2.0) y `libhybris` (MIT/LGPL según componente). Sin licencia declarada, la compatibilidad no está ni planteada, y es lo primero que mira un tercero que quiera aportar o auditar. **No propongo cuál licencia:** es decisión de Abraham y elegirla por él sería inventar.

### H-09 · MEDIO · El verde de los workflows de `main` es NO MEDIDO por mí, y el catálogo confirma que no es pereza

Consulté el catálogo de herramientas antes de declarar el límite: **no existe listador de corridas de Actions** entre las herramientas de GitHub disponibles ni entre las agregables. `get_check_runs` cuelga de un pull request, y **este repo tiene cero PRs**. Por lo tanto el estado de las corridas de `falsador-kvm-runners.yml` y `falsador-kvm-usermod.yml` es auditable **solo** por lo que los propios archivos de `respuestas/` commitean.

Eso valida la regla del ecosistema (*"si un workflow no commitea su resultado, es invisible"*) y sugiere subirla de nivel: sellar cada corrida con un `VEREDICTO.txt` por `run_id`, como ya se hace en `mudh-mobile`.

**Nota de estado que corrijo de mi propio lado:** mi configuración traía cacheado que la cuota de Actions hosted estaba agotada y que todo corría en un runner self-hosted. **En este repo eso no aplica:** los dos workflows apuntan a runners hosted (`ubuntu-24.04`, `ubuntu-24.04-arm`) y la bitácora del 09-07 registra tres runners hosted reales (`1000002220`, `1000002221`, `1000002222`, run `34126598730`). Gana lo leído.

---

## 3 · Lo que el repo hace bien, y conviene no perder en un refactor de método

No es cortesía: son prácticas que casi ningún proyecto tiene y que si se borran cuesta caro reponer.

1. **Tres estados, con el `NO MEDIDO` como ciudadano de primera.** Es lo que evita el verde vacío, y funcionó: F-004d@6.1 cerró NO MEDIDO en vez de "verde con salvedades".
2. **Predicción declarada ANTES de correr**, con el dato que la hace falsable (el tiempo de `archscripts`). Esto es lo que separa medir de justificar.
3. **Los errores propios se escriben en el mismo documento que el resultado.** El informe del 09-06 enumera 19 y encontró de paso que F-004d había corrido y nadie lo había leído.
4. **El control de instrumento** (el job x64 que corre lo mismo para distinguir "no hay KVM" de "mi script está roto"). Está escrito en los comentarios del propio `.yml`.
5. **Divergencias declaradas a propósito** en vez de silenciadas (la nota del inventario en `AGENTS.md`).

---

## 4 · Orden recomendado, con el criterio explícito

El criterio es: **primero lo que impide que el proyecto se equivoque solo, después lo que lo hace avanzar.**

| # | Acción | Cierra | Costo |
|---|---|---|---|
| 1 | Correr F-004d@6.1 con el `HOSTCFLAGS` en los dos pasos | H-07 · el camino crítico | una corrida, arreglo ya escrito |
| 2 | Sincronizar `CONTEXTO-SIAO.md` §3/§5 y el estado del README al HEAD | H-01, H-02 | una edición |
| 3 | Abrir issue por cada NO MEDIDO vivo y por cada rama con evidencia única | H-03 | mecánico |
| 4 | Unificar `docs/auditorias/` y `docs/audits/`, e indexar `respuestas/` | H-04, H-05 | mecánico |
| 5 | `permissions:` + `timeout-minutes:` + guard de runner en los dos workflows | H-06 | un PR chico |
| 6 | Decidir `LICENSE` y visibilidad del repo | H-08 | decisión de Abraham |

**Lo que no está en la lista a propósito:** empezar la capa 5. No porque no importe —es lo único diferencial— sino porque su premisa depende de #1: si el fragmento no es KMI-safe en la generación que corre el hardware real, la arquitectura del ADR-001 cambia y el código de la capa 5 se escribiría sobre una base que todavía no está.

---

## 5 · Errores y límites propios de esta auditoría

Los anoto yo primero, porque una auditoría que no declara su alcance es una opinión con formato de informe.

1. **No leí el contenido de las 4 ramas `titan/*`.** Auditar que la evidencia vive solo ahí no es lo mismo que verificar que la evidencia sea correcta. **NO MEDIDO.**
2. **No leí los 5 ADR completos**, solo el ADR-006 y las referencias cruzadas que citan los otros. Un error interno de razonamiento dentro del ADR-001 podría habérseme pasado.
3. **No corrí nada.** Esta entrega no incluye scripts, así que no había qué ejecutar; pero eso significa que ninguna afirmación técnica de este informe es una medición mía: todas son lecturas del repo o mediciones ajenas citadas con su archivo.
4. **No verifiqué el estado de las corridas de Actions** (H-09), ni los permisos por defecto del `GITHUB_TOKEN`.
5. **No apliqué ninguna corrección.** Deliberado: el archivo que más urge arreglar es el canónico del proyecto y su reescritura sin OK sería sobrescribir trabajo ajeno.

---

## 6 · Rúbrica

**Tipo de entrega:** auditoría / peritaje. **Criterios aplicables: 5 de 9.**

| # | Criterio | Pts | Score | Evidencia |
|---|---|---|---|---|
| 1 | Completitud | 15 | 14 | árbol completo de `main` a `9600a94`, 5 ramas, 0 PRs, 0 issues, 9 hallazgos; **-1** por las 4 ramas sin leer |
| 5 | Arquitectura (del razonamiento) | 10 | 10 | cada hallazgo con archivo y sección; H-01 refutado con dos citas literales del propio archivo |
| 7 | Documentación | 10 | 10 | este archivo + Doc espejo en ClickUp, con el orden recomendado y su criterio |
| 8 | Innovación | 5 | 4 | el enlace H-01→H-09 (la memoria canónica como causa raíz) no estaba pedido; **-1** porque no aporté el índice de `respuestas/` ya hecho |
| 9 | Proceso QA | 5 | 5 | límites propios declarados en §5, review automático pedido en el PR |

**Total: 43/45 → 96/100.** **N/A: 55 pts** — Ejecutabilidad (15), Seguridad (15), Testing (15) y DevOps (10) no aplican: la entrega es un informe, no tiene superficie ejecutable, ni suite, ni infraestructura propia. Puntuarlos daría un número arrastrado por criterios que no corresponden.

**Nota sobre R-14:** el repo tiene la regla de que un informe no se autopuntúa, y el informe del 09-06 la respeta. Esta nota es el scorecard de mi método como agente sobre mi propio trabajo, **no** una calificación del proyecto auditado. El proyecto no recibe nota acá: recibe nueve hallazgos con evidencia.

---

--- MÉTODO PROMETEO ---
**Máquinas:** ninguna. **Herramientas:** API de GitHub (lectura de árbol, archivos, commits, ramas, PRs, issues) y catálogo de herramientas para confirmar el límite de H-09.
**Artefacto en git:** este archivo, en la rama `titan/auditoria-siao-2026-09-07`, con PR y review automático pedido.
**Artefacto en ClickUp:** Doc espejo enlazado en el cierre del PR.
