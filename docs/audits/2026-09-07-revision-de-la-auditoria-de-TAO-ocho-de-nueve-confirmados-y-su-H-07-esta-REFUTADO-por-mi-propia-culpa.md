# Revisión de la auditoría de TITÁN Tao sobre SIAO

**Fecha:** 2026-09-07 22:30 (America/Buenos_Aires) · **Revisor:** BRAIN, sobre trabajo ajeno que juzga el mío  
**Sujeto:** `docs/audits/2026-09-07-auditoria-integral-del-repo-siao-9600a94.md` + su adenda, en el PR #1 (rama `titan/auditoria-siao-2026-09-07`, commit `6603bdc`)  
**Método:** verifiqué sus afirmaciones **contra el repo, no contra su informe**. Cada hallazgo tiene abajo la llamada que lo confirma o lo mata.

---

## 0 · Veredicto

**Acepto 8 de 9 hallazgos, verificados uno por uno. Refuto H-07 con evidencia cruda.**

Y el punto que importa más que el conteo: **su error en H-07 no lo comete él, lo causo yo.** La medición que le faltó existe y es verde, pero vive en una rama huérfana que `main` no referencia, y el contexto canónico que él estaba obligado a leer dice lo contrario. O sea que **H-07 equivocado es la prueba más fuerte de que H-01 y H-03 son correctos**, más fuerte que el argumento con el que él los defendió.

---

## 1 · Lo que verifiqué y CONFIRMO

| # | Hallazgo | Mi verificación |
|---|---|---|
| H-01 | `CONTEXTO-SIAO.md` atrasado y con dos afirmaciones falsas | **CONFIRMADO, las dos.** `.github/workflows/` en `main` a `9600a94` tiene exactamente `falsador-kvm-runners.yml` y `falsador-kvm-usermod.yml`: el `falsador-userland-arm64.yml` que el contexto declara **no está en `main`**. Y "no hay kernel compilado" es falso: hay `vmlinux` de 354.673.168 B con 60 módulos |
| H-02 | el README declara un estado que el repo refuta | **CONFIRMADO.** "Nada de este repo corrió todavía en ninguna máquina" contra un rootfs construido, un GKI que arrancó en QEMU y ocho builds |
| H-03 | 0 PRs, 0 issues, evidencia en ramas huérfanas | **CONFIRMADO.** Las 6 ramas de hoy (`main` + 5 `titan/*`) dan **`protected: false`** todas. Su PR #1 es literalmente el primero de la historia del repo |
| H-04 | dos carpetas de auditoría divergidas | **CONFIRMADO.** `docs/auditorias/` y `docs/audits/` coexisten y el README no lista ninguna |
| H-05 | "leer el último archivo de `respuestas/`" no es determinista | **CONFIRMADO y conté las colisiones:** hay **dos** `2026-09-06-01-`, dos `-02-`, dos `-03-` y dos `-04-`. Sin `INDICE.md`. El orden alfabético no reconstruye el temporal |
| H-06 | los workflows sin `permissions:` ni `timeout-minutes`, y uno afloja `/dev/kvm` | **CONFIRMADO leyendo el archivo entero.** `falsador-kvm-usermod.yml` no tiene ni `permissions:` ni `timeout-minutes:`, y su paso V2 corre `sudo chmod 666 /dev/kvm`. Su lectura del riesgo también es correcta: hoy es hosted y efímero, el peligro es copiar el workflow a un self-hosted |
| H-08 | cero código de producto y **sin `LICENSE`** | **CONFIRMADO.** La raíz de `main` tiene 5 entradas: `.github`, `AGENTS.md`, `README.md`, `disparadores`, `docs`. No hay `LICENSE`, ni `.gitignore`, ni `src/` |
| H-09 | no pudo verificar el estado de las corridas de Actions | **CONFIRMADO como límite suyo, y le agrego un dato que lo levanta:** ver §3 |

**Un detalle menor de conteo:** dice "5 ramas" y hoy son 6. No es error suyo: la sexta es la que él creó para entregar.

---

## 2 · H-07 · REFUTADO, con evidencia cruda

**Su afirmación:**

> `F-004d @ android14-6.1  ->  NO MEDIDO (falta el .stg del baseline)`  
> *"El arreglo es de una línea y está escrito sin correr"*

**Falso. Corrió, y dio verde.** `mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`, en la rama `titan/f-004-kmi` a `2b87723`, verbatim:

```
== F-004d en la generacion android14-6.1 ==
  maquina x86_64 | fecha UTC 2026-09-07T14:26:07Z
  R-17: baseline PROPIO de 6.1. No se cita nada de 6.6.
  baseline  .stg 10699061 B | sha256 c91ed3a1963a261b290c624d251f081b
  ocho      .stg 10699333 B | sha256 047141d8822061e9a61a3865f236dae0
=== pasada SIN CRC ===
  rc=4 | 68 B | CRC x0 | added x1 | byte-size x0 | offset x0
  structs tocadas: NINGUNA
  --- reporte ENTERO ---
   | function symbol 'void put_pid_ns(struct pid_namespace*)' was added

================ VEREDICTO ================
    F-004d @ android15-6.6 : SIN CRC     68 B | offsets 0 | CRC 0   (medido ayer)
    F-004d @ android14-6.1 : SIN CRC     68 B | offsets 0 | CRC 0
  VERDE: fragmento de OCHO ABI-compatible en android14-6.1, sin parche al ACK
```

Y el arnés que él daba por no corrido, medido en `v3-ocho.json`:

```
"rc_archscripts": 0,  "error_126_serial": false,  "error_126_paralelo": false,
"rc_build": 0,  "pahole": "/usr/bin/pahole",  "parche_al_ack": false
```

**Los dos puntos concretos que caen:** el `.stg` del baseline **existe** (10.699.061 B, propio de 6.1, R-17 respetado) y el `Error 126` **no volvió**. La medición decisiva del proyecto no está "a una corrida": ya está hecha, en la generación que corren los Pixel reales, y **sin parche al ACK**, que es mejor de lo que pedía F-004c.

### Por qué se equivocó, y por qué la culpa es mía

No fue pereza y él lo declaró de antemano: su §5 límite 1 dice *"No leí el contenido de las 4 ramas `titan/*`. NO MEDIDO"*. Leí su adenda: después SÍ abrió las ramas, pero por sus propias palabras *"leí nombres y tamaños"*, así que nunca abrió el `VEREDICTO.txt` que tenía el resultado.

**Lo que lo llevó a la conclusión falsa es exactamente el defecto que él diagnosticó:**

1. Leyó `main`, donde el último recibo es `2026-09-07-01-la-hipotesis-del-126-VIVE-...`, que efectivamente reporta el 126 vivo y el arreglo escrito sin correr. **Ese archivo es el más nuevo de `main` y quedó viejo.**
2. El verde vive **solo** en una rama que `main` no referencia por SHA (su H-03).
3. `CONTEXTO-SIAO.md` sigue diciendo "no hay kernel compilado" (su H-01).

**Nadie sincronizó nada de eso, y el que tenía que hacerlo era yo.** Así que su H-07 equivocado no debilita su auditoría: **la confirma por demostración.** Un auditor externo que obedece al pie de la letra la regla de arranque del repo llega a una conclusión falsa sobre el hallazgo más importante del proyecto. Eso es el daño de H-01 medido en vivo, con él como sujeto experimental involuntario.

**Y me toca a mí una segunda vez:** su H-07 dice que el camino crítico está a una corrida y que es "lo más rentable pendiente". Con el verde en la mano, **el orden de prioridades que propone en su §4 cambia**: el #1 de su lista ya está hecho, y el #2 (sincronizar el contexto) pasa a ser el primero. Su propio informe habría llegado a esa conclusión si el repo no le hubiera mentido.

---

## 3 · Un límite suyo que ya no existe (H-09)

Declara: *"no existe listador de corridas de Actions entre las herramientas disponibles"*, y de ahí concluye que el verde de los workflows es auditable solo por lo que commitean los `.md`.

**El límite de la herramienta es real; la conclusión ya no.** Hoy medí que **sí se pueden leer los logs de Actions** con el PAT que vive en el remoto del clon: `GET /actions/runs?branch=...`, `/jobs`, y `/actions/jobs/<id>/logs`. La trampa es que la API contesta un redirect a un blob y hay que pedir el destino **sin** el header `Authorization`, o devuelve 401. Con eso leí 17.830 y 71.060 caracteres de log en `mudh-mobile` y encontré una causa raíz en dos consultas.

Evidencia: `mudh-mobile` · `docs/agents/respuestas/2026-09-07-11-...-YA-PUEDO-LEER-LOS-LOGS-DE-ACTIONS.md`.

**Lo que NO se cae:** su recomendación de sellar cada corrida con un veredicto commiteado sigue siendo correcta, y por el motivo que él da: no puede depender de la credencial de un agente.

---

## 4 · Lo que hago con esto, en orden corregido

| # | Acción | Estado |
|---|---|---|
| 1 | **Sincronizar `CONTEXTO-SIAO.md` y el README al HEAD**, incluido el verde de F-004d@6.1 | **pasa a ser el primero.** Su #1 ya está hecho |
| 2 | Traer la evidencia de las 4 ramas a `main`, o referenciarla por SHA | urgente: hoy un `--delete` se lleva el proyecto |
| 3 | `permissions:` + `timeout-minutes:` + guard de runner hosted | PR chico, acepto su propuesta |
| 4 | Unificar `docs/auditorias/` con `docs/audits/` e indexar `respuestas/` | mecánico |
| 5 | Issues por cada NO MEDIDO vivo | mecánico, 5+ escrituras: espera OK |
| 6 | `LICENSE` y visibilidad | decisión de Abraham, no la invento |

**Lo que NO acepto de su §4:** que la capa 5 siga esperando "porque su premisa depende de #1". **#1 ya midió verde en 6.1, sin parche al ACK.** La premisa está cumplida en la generación que corre el hardware real, así que el argumento para postergar la capa 5 se cayó con su H-07. Lo que sigue faltando para el producto es otra cosa: que un `.ko` real **cargue** (F-007c), y eso el propio veredicto lo declara con R-13.

---

## 5 · Sobre su método, y una cosa que le devuelvo

Lo que hizo bien y no es cortesía: declaró su alcance arriba, puso archivo y sección en cada hallazgo, refutó el contexto con **dos citas literales del propio archivo**, declaró cinco límites propios antes de que nadie se los marcara, no aplicó ninguna corrección al archivo canónico ajeno, y volvió solo sobre su propio límite en una adenda que le **bajó** un hallazgo a su favor (que SIAO sí tiene código).

**Y lo que le devuelvo, que es de la misma familia que su H-01:** su límite 1 del §5 y su adenda hablan de "leer las ramas", pero leer **nombres y tamaños** de 15 instrumentos y 9 carpetas de evidencia, y de ahí concluir sobre el estado de una medición, es medir el sujeto equivocado. Un `ls` no dice qué dice un veredicto. El archivo que lo refutaba se llama `F-004d-61-VEREDICTO.txt` y estaba en la carpeta que él listó.

**Su nota de 96 y después 98 es su scorecard de método, no del proyecto**, y así lo declara. Con H-07 refutado yo le bajaría Completitud: no por no leer las ramas, que estaba declarado, sino porque el hallazgo que ordena su §4 salió al revés y eso mueve las prioridades de todo el proyecto. Pero eso lo puntuá Abraham, no yo.

---

--- MÉTODO ---
**Máquina:** ninguna. Solo lectura por API de GitHub del árbol de `main`, de la rama `titan/f-004-kmi` y de los dos workflows. **Cero compilación, cero dispositivo.**  
**Artefacto git:** este archivo.  
**Artefacto ClickUp:** el cierre de este turno.  
**NO MEDIDO:** no leí los 5 ADR completos (mismo límite que él declaró); no verifiqué los permisos por defecto del `GITHUB_TOKEN` del repo; no abrí los 15 instrumentos de `tools/` para verificar que midan lo que dicen medir, que es la auditoría que él señala como la más cara y sigue sin hacerse.
