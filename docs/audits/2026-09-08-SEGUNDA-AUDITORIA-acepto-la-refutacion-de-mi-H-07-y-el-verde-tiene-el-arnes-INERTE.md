# Segunda auditoría de SIAO · acepto la refutación de mi H-07, y el verde tiene el arnés inerte

**Fecha:** 2026-09-08 · **Rol:** QA AUDITOR (TITÁN Tao) · **Pedido literal:** *"REPITE LA AUDITORIA"*
**Sujeto:** `gatehot59-star/siao` @ `main` = **`86691e7e750954e04ebd1cfe9f4fb451eaae9b54`** (2026-09-08 01:40 UTC)
**Primera pasada:** `docs/audits/2026-09-07-auditoria-integral-del-repo-siao-9600a94.md` @ `9600a94` + su adenda.
**Repo leído en vivo.** Cero compilación, cero dispositivo, cero corrida. Ninguna afirmación técnica de acá es medición mía: son lecturas del repo.

> **Qué hice distinto en esta pasada, para que no sea una reimpresión:** re-verifiqué los 9 hallazgos contra el HEAD nuevo (el repo se movió 3 commits), **abrí los archivos de evidencia en vez de listarlos** —el defecto que me costó H-07— y **leí el ADR-001 completo**, que era el límite que declaré dos veces sin cerrar.

---

## 0 · Lo primero: mi H-07 estaba mal, y la medición gana

**Abrí `mediciones/f-004d-61/F-004d-61-VEREDICTO.txt` en la rama `titan/f-004-kmi` (`2b87723`) con mis propios ojos, no la transcripción de nadie.** Dice, verbatim:

```plain
== F-004d en la generacion android14-6.1 ==
  maquina x86_64 | fecha UTC 2026-09-07T14:26:07Z
  baseline  .stg 10699061 B | sha256 c91ed3a1963a261b290c624d251f081b
  ocho      .stg 10699333 B | sha256 047141d8822061e9a61a3865f236dae0
=== pasada SIN CRC ===
  rc=4 | 68 B | CRC x0 | added x1 | byte-size x0 | offset x0
  structs tocadas: NINGUNA
  VERDE: fragmento de OCHO ABI-compatible en android14-6.1, sin parche al ACK
  R-13: esto dice ABI-compatible. Que un .ko real CARGUE es F-007c.
```

**Escribí que F-004d@6.1 estaba NO MEDIDO y que el arreglo estaba "escrito sin correr". Las dos cosas son falsas.** El `.stg` del baseline existe, es propio de 6.1 (R-17 respetado), y la medición es del 2026-09-07 14:26 UTC — nueve horas antes de que yo auditara.

**La medición externa gana sobre mi score, siempre, incluso cuando lo contradice.** H-07 queda **REFUTADO** y con él cae el orden de prioridades de mi §4: mi punto #1 ya estaba hecho.

**Y no me escondo detrás de la causa.** Es verdad que el repo me mandó al lugar equivocado (mi propio H-01 y H-03, confirmados por demostración con mi cadáver). Pero **el archivo se llamaba `F-004d-61-VEREDICTO.txt` y estaba en la carpeta que yo mismo listé en la adenda.** Listé 46 archivos y no abrí el que decía VEREDICTO en el nombre. Eso es mío: **un `ls` no dice qué dice un veredicto**, y yo concluí un estado desde un listado, que es medir el sujeto equivocado.

---

## 1 · H-10 · ALTO · El verde es real, pero el arnés que lo explica está INERTE

**Esto no lo vio nadie: ni el recibo del 09-07, ni la revisión que me refutó.** Y sale del mismo archivo que se usó para refutarme.

`mediciones/f-004d-61/v3-ocho.json`, verbatim y **completo** en los campos que importan:

```json
"rc_archscripts": 0,
"segundos_archscripts": 0.02,
"archscripts_hizo_trabajo": false,
"error_126_serial": false,
"error_126_paralelo": false,
"rc_build": 0
```

Y `v3-ocho-archscripts.txt` muestra el comando **con el arreglo ya aplicado** y su salida entera:

```plain
make -C ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j1 archscripts
rc=0 | segundos 0.02
make[1]: Nothing to be done for 'archscripts'.
```

**El arreglo se aplicó al comando y el paso siguió sin hacer trabajo.** Y eso choca de frente con el falsador que el propio proyecto declaró **antes** de correr, en `docs/agents/respuestas/2026-09-07-01-*` §6:

> *"**Predicción declarada antes de correr:** `archscripts` va a tardar **más de 0 s** esta vez (porque ahora sí tiene trabajo). (…) **El dato que hace falsable la predicción es el tiempo de `archscripts`:** si vuelve a dar 0,0 s, **el arreglo no se aplicó y no hay que interpretar nada más.**"*

**Dio 0,02 s y `Nothing to be done`. La predicción falló.** Lo mismo en el brazo baseline (`v3-baseline.json`: `0.02`, `archscripts_hizo_trabajo: false`).

### Qué se sostiene y qué no

| Afirmación | Estado |
|---|---|
| El build completó y produjo `vmlinux` + `Module.symvers` | **MEDIDO.** `rc_build: 0`, 16.036 líneas, sha256 registrado |
| El fragmento de ocho es ABI-compatible en android14-6.1 | **MEDIDO.** 68 B, cero offsets, cero CRC, cero structs |
| **El `Error 126` está eliminado** | **NO MEDIDO.** El guard serial no hizo trabajo, así que no puede ser la causa de que no apareciera |

**Por qué importa y no es puntillismo:** el proyecto mismo estableció que el 126 es **intermitente** —*"mismo código, mismos flags, mismo runner: uno falla y el otro no… eso es la firma de una carrera"*—. Un verde con el guard inerte es **una carrera ganada, no una carrera cerrada.** El próximo build puede volver a romperse, y el proyecto lo daría por arreglado.

**Y es la tercera vez que el mismo patrón muerde:** el recibo del 09-07 escribió la lección con estas palabras — *"un paso de mitigación que tarda 0,0 segundos no mitigó nada"* — y un día después el mismo campo salió en `false`, se leyó el `rc=0` de al lado, y se declaró cerrado.

**Lo que haría falta para cerrarlo de verdad (no lo puedo correr yo, es `needs-runtime`):** N corridas del mismo brazo sin cambiar nada, contando cuántas dan 126. Si el guard es inerte, la tasa de fallo debería ser la misma de antes del arreglo. Ése es el experimento que discrimina, y cuesta una matriz, no un análisis.

---

## 2 · H-11 · MEDIO (de método) · La refutación citó el JSON sin los dos campos que la matizan

La revisión que me refutó cita `v3-ocho.json` así: `rc_archscripts: 0`, `error_126_serial: false`, `error_126_paralelo: false`, `rc_build: 0`, `pahole`, `parche_al_ack: false`.

**Omite `segundos_archscripts: 0.02` y `archscripts_hizo_trabajo: false`**, que son exactamente los dos campos que el falsador declarado del proyecto convierte en decisivos.

**No cambia el veredicto ABI —ése está bien medido y lo acepto—, cambia el alcance:** con los seis campos citados, el 126 parece resuelto; con los ocho, queda abierto. Es la misma familia del defecto que este proyecto tiene registrado como el más caro de su historia: **recortar la evidencia** (el `tail` que costó seis versiones en F-002). El campo estaba impreso, en el mismo archivo, dos líneas más arriba.

**Lo digo de mi lado también:** yo caí en la versión peor de ese defecto —no leí el archivo— y quien me refutó cayó en la versión sutil —lo leyó y citó un subconjunto—. **Las dos son el mismo error con distinto radio.**

---

## 3 · H-12 · MEDIO · El índice de mediciones se contradice a sí mismo, y es un gate

`mediciones/INDICE.md` en `titan/f-004-kmi`, **completo**:

```plain
# Indice de mediciones (R-15)
Un run sin linea aca esta NO LEIDO y bloquea el siguiente falsador.

| falsador | generacion | veredicto | evidencia |
| F-004d | android14-6.1 | NO MEDIDO | mediciones/f-004d-61/ |
| F-004d | android14-6.1 | VERDE: fragmento de OCHO ABI-compatible... | mediciones/f-004d-61/ |
```

**Dos filas, mismo falsador, misma generación, misma carpeta, veredictos opuestos.** La vieja no se borró al cerrar. Y su propio encabezado lo convierte en un **gate** que bloquea el falsador siguiente: **un gate que se contradice no gatea nada**, y quien lea la primera fila se lleva el dato viejo con autoridad de índice.

**Nota justa:** esto ya está señalado en `docs/agents/MAPA-DE-LA-EVIDENCIA.md` §3, escrito hoy. Lo confirmo de forma independiente y lo dejo en la lista porque **sigue sin corregirse en la rama**, que es donde el gate opera.

---

## 4 · Lo que salió de leer el ADR-001 completo (el límite que había declarado dos veces)

### H-13 · ALTO · El README promete que ande el banco; el ADR-001 declara que eso no tiene solución legal completa

`README.md`, primera pantalla del proyecto:

> *"Android baja de rango y pasa a ser un inquilino en un contenedor, con **una sola función en la vida**: que sigan andando **WhatsApp, el banco** y el resto de las APKs."*

`ADR-001` §8, tabla de riesgos:

> *"Sin Play Integrity → apps bancarias · Prob. **Alta** · Impacto **Alto en Occidente** · **No hay solución legal completa**"*

**La única función que el README le asigna a todo el runtime de Android es justo la que el ADR declara sin solución.** Los dos documentos son del mismo día y del mismo autor. No es que el riesgo esté escondido —está declarado y con honestidad—: es que **la promesa de portada y el riesgo del ADR nunca se cruzaron**, y quien lea solo el README compra algo que el ADR ya sabe que no se puede entregar completo en Occidente.

**No propongo cómo resolverlo** (la respuesta del ADR es de mercado: nichos sin GMS, empresa, gobierno, privacidad). Propongo que **el README diga lo que el ADR ya sabe**: WhatsApp sí, el banco depende de Play Integrity y no está resuelto.

### H-14 · MEDIO · El ADR-001 arrastra en su roadmap una tarea que el propio proyecto midió como innecesaria, y tenía escrita la generación correcta desde el día 1

**Dos cosas, las dos verificables en `ADR-001` §7:**

1. **Fase 1 sigue pidiendo:** *"Rootfs openKylin ARM64 **(16K aligned)** sobre GKI **recompilado**"*. Pero FALSADOR-001 midió que **no hace falta**: los 146 ELF vienen con `p_align 65536`, múltiplo de 16384. Está en el cementerio de `CONTEXTO-SIAO.md` como **H-006, muerta**. El ADR está en estado *"aceptada"* y su criterio de salida de Fase 1 incluye trabajo que el proyecto ya sabe que no corresponde.
2. **Fase 0 dice, textual: *"GKI 6.1/6.6"*, y lista *"Pixel 7/8"* como candidatos.** El informe del 09-06 llama *"el error más caro"* a que los 8 builds de F-004 estuvieran en `android15-6.6`, una generación que ningún Pixel corre (F-007b midió `6.1.157-android14-11` en un Pixel 8 real). **Ese error estaba prevenido en el propio ADR desde el día 1, en la línea que nombra 6.1 primero.**

**Y eso es el gemelo de H-01 en otra superficie:** el problema no es solo que la memoria canónica esté vieja, es que **la decisión de arquitectura que el proyecto ya escribió no se vuelve a leer.** Un ADR que no se relee es un documento de trámite.

### H-15 · MEDIO (seguridad) · El levantamiento de H-09 se apoya en un secreto sin rotar

La revisión levanta mi H-09 informando que **sí** se pueden leer los logs de Actions *"con el PAT que vive en el remoto del clon"*.

**El método es correcto y el hallazgo técnico es válido** (el redirect a blob hay que pedirlo sin el header `Authorization`). Pero el ecosistema tiene señalado, desde el 2026-09-05 y otra vez el 09-06, **un PAT de GitHub en texto plano en el remoto, y nadie lo rotó.** Apoyar una capacidad operativa en esa credencial la vuelve **más caro rotarla**, que es lo contrario de lo que hay que lograr.

**Rotar es decisión humana y no la toco.** Lo que sí digo: mientras esa credencial siga expuesta, *"puedo leer los logs"* no es una capacidad del proyecto, es una deuda con intereses. Y refuerza —no debilita— la recomendación que ya está aceptada: **sellar cada corrida con su veredicto commiteado**, precisamente para no depender de la credencial de ningún agente.

---

## 5 · Re-verificación de los 9 hallazgos originales al HEAD nuevo

| # | Estado hoy | Evidencia |
|---|---|---|
| **H-01** | **ABIERTO.** `CONTEXTO-SIAO.md` **no se tocó** en los 3 commits nuevos (solo `AGENTS.md`, más dos archivos añadidos). Sigue diciendo *"existe `falsador-userland-arm64.yml`"* y *"no hay kernel compilado"*. Y `AGENTS.md` paso 1 **sigue mandándolo a leer primero** | ✅ confirmado por el revisor, sin corregir |
| **H-02** | **ABIERTO.** `README.md` intacto: *"nada de este repo corrió todavía en ninguna máquina"* | ✅ confirmado, sin corregir |
| **H-03** | **MITIGADO A MEDIAS.** Nace `docs/agents/MAPA-DE-LA-EVIDENCIA.md` con rama, SHA y archivo por falsador: **resuelve el descubrimiento**. **NO resuelve la durabilidad**, y el propio mapa lo declara: anotar un SHA no protege los objetos. Las 6 ramas siguen `protected: false` y sigue habiendo 0 issues | mapa §0, §2 |
| **H-04** | **ABIERTO.** `docs/auditorias/` y `docs/audits/` siguen coexistiendo | árbol a HEAD |
| **H-05** | **MITIGADO.** `AGENTS.md` paso 3 ahora avisa de las colisiones y manda **ordenar por fecha de commit, no por nombre**. Sigue sin `INDICE.md` en `respuestas/` | `AGENTS.md` nuevo |
| **H-06** | **ABIERTO.** Los dos workflows sin `permissions:` ni `timeout-minutes`, y el `chmod 666 /dev/kvm` sin guard | árbol a HEAD |
| **H-07** | **REFUTADO.** Ver §0. Reemplazado por **H-10**, que es más chico y más preciso | `F-004d-61-VEREDICTO.txt` |
| **H-08** | **ABIERTO**, y con H-13 encima. Sin `LICENSE`, sin `.gitignore`, capa 5 sin empezar | árbol a HEAD |
| **H-09** | **LEVANTADO como límite, con la salvedad de H-15** | revisión §3 |

**Saldo de 24 horas:** 2 hallazgos mitigados, 1 refutado, **6 abiertos**, 6 nuevos. Y **los dos más baratos de todos (H-01 y H-02: editar cuatro líneas falsas) siguen sin hacerse**, mientras se escribieron dos documentos nuevos para compensar que están mal. Eso es el patrón que más me preocupa de esta segunda pasada: **el repo prefiere agregar un mapa antes que corregir el mapa viejo.** Un documento nuevo que explica por qué el viejo miente deja dos documentos que hay que leer en orden.

---

## 6 · Orden recomendado, corregido

| # | Acción | Cierra | Por qué en este lugar |
|---|---|---|---|
| 1 | Corregir las 4 líneas falsas de `CONTEXTO-SIAO.md` y `README.md` | H-01, H-02 | es lo más barato del repo y lo único que ya causó un error medido |
| 2 | Traer la evidencia a `main` o proteger las 6 ramas | H-03 durabilidad | hoy un `--delete` se lleva 15 instrumentos y toda la evidencia |
| 3 | Borrar la fila `NO MEDIDO` de `mediciones/INDICE.md` | H-12 | un gate que se contradice bloquea mal |
| 4 | Matriz de N corridas para el `Error 126` con el guard inerte | H-10 | `needs-runtime`; sin eso el 126 está dormido, no muerto |
| 5 | Alinear el README con el riesgo de Play Integrity del ADR-001 | H-13 | es la promesa de portada del proyecto |
| 6 | Purgar de `ADR-001` §7 la tarea de 16K y anotar 6.1 como generación de referencia | H-14 | el ADR es "aceptada" y arrastra trabajo muerto |
| 7 | `permissions:` + `timeout-minutes:` + guard de runner | H-06 | PR chico, ya aceptado |
| 8 | Rotar el PAT expuesto | H-15 | decisión humana, no la toco |
| 9 | Unificar carpetas de auditoría, indexar `respuestas/`, issues por NO MEDIDO | H-04, H-05, H-03 | mecánico |
| 10 | `LICENSE` y visibilidad | H-08 | decisión de Abraham |

**Sobre la capa 5:** acepto la corrección. Mi argumento para postergarla era *"su premisa depende de #1"*, y #1 midió verde en 6.1 sin parche al ACK. **La premisa de ABI-compatibilidad está cumplida.** Lo que sigue faltando es que un `.ko` real **cargue** (F-007c), y eso el propio veredicto lo declara con R-13. O sea: la capa 5 ya no está bloqueada por el KMI; está bloqueada por una medición distinta y más chica.

---

## 7 · Mis errores en esta auditoría y en la anterior

1. **El grande, ya dicho:** listé 46 archivos y no abrí el que se llamaba `VEREDICTO`. Concluí un estado desde un `ls`. Costó el hallazgo que ordenaba mi propio orden de prioridades.
2. **Mi adenda decía "leí las 4 ramas"** cuando había leído **nombres y tamaños**. La palabra "leí" era más grande que lo que hice, y eso es una afirmación sin verificar con forma de rigor.
3. **Mi rúbrica se movió en la dirección equivocada:** subí de 96 a 98 por la adenda, en el mismo movimiento en que dejaba sin abrir el archivo que refutaba mi hallazgo principal. **Un número que sube mientras la medición cae es un número decorativo.**
4. **Sigue NO MEDIDO:** los 5 ADR — leí el 001 completo y el 006 por referencia; faltan 002, 003 y 004. El contenido de los 15 instrumentos (no puedo afirmar que midan lo que dicen medir). El contenido completo de `mediciones/f-004/`, `f-004-v3/`, `f-004b/`, `f-004c/`, `f-004d/`. Los permisos por defecto del `GITHUB_TOKEN`.

---

## 8 · Rúbrica

**Tipo de entrega:** auditoría / peritaje. **Criterios aplicables: 5 de 9. N/A: 55 pts** (Ejecutabilidad, Seguridad, Testing, DevOps: no hay superficie ejecutable ni infra propia).

| Criterio | Pts | Score | Evidencia |
|---|---|---|---|
| Completitud | 15 | **12** | 6 hallazgos nuevos con archivo y línea, 9 re-verificados al HEAD nuevo, ADR-001 leído entero · **-3 porque mi hallazgo más consecuente de la primera pasada salió al revés y movió el orden de todo el proyecto**, y porque faltan 3 ADR |
| Arquitectura (del razonamiento) | 10 | 10 | H-10 sale de cruzar el JSON con la predicción declarada; H-13 de cruzar README con ADR §8 |
| Documentación | 10 | 10 | este archivo + Doc espejo + comentario en el PR, con el orden corregido |
| Innovación | 5 | 4 | H-10 y H-13 no los había visto nadie · **-1**: no aporté el diseño de la matriz de N corridas |
| Proceso QA | 5 | 5 | acepté la refutación primero, antes de exponer hallazgos nuevos; 4 límites propios declarados |

**Total: 41/45 → 91/100.** Aprobado por 1 punto sobre el umbral, y **baja desde el 98 que me había puesto**: es lo correcto. La medición externa gana sobre mi score incluso cuando lo contradice, y acá lo contradijo.

---

--- MÉTODO PROMETEO ---
**Máquinas:** ninguna. **Herramientas:** API de GitHub — árbol y archivos de `main` a `86691e7e`, contenido de 6 archivos de evidencia en `titan/f-004-kmi` a `2b87723`, los 3 commits nuevos con sus stats, reviews y check runs del PR #1 (`total_count: 0` en los dos).
**Artefacto git:** este archivo, en `titan/auditoria-siao-2026-09-07`, sobre el PR #1.
**Artefacto ClickUp:** página nueva en el Doc de la auditoría, linkeada en el PR.
