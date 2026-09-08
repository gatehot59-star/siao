# Cerrados H-06 y H-12, y mi validador me dio un falso verde sobre otro archivo

**Fecha:** 2026-09-08 09:25 (America/Buenos_Aires) · **Autor:** BRAIN  
**Orden de Abraham:** borrar la fila duplicada y poner `permissions`.

---

## 1 · H-12 · la fila contradictoria, borrada en LOS DOS lados

`mediciones/INDICE.md` tenía **dos filas** para `F-004d @ android14-6.1`, misma generación y misma carpeta, una `NO MEDIDO` y otra `VERDE`. Su propio encabezado dice que un run sin línea *"bloquea el siguiente falsador"*, o sea que es un **gate**: **un gate que se contradice no gatea nada.**

**Y encontré un segundo defecto que nadie había marcado, del mismo archivo:** tenía **una sola medición de siete**. Si su regla dice que un run sin línea está NO LEIDO, entonces seis falsadores cerrados figuraban como no leídos. Un índice con una entrada tampoco gatea. Completé las diez filas desde `MAPA-DE-LA-EVIDENCIA.md`, verificadas contra sus veredictos.

**Lo arreglé en `main` y en la rama, pero NO duplicando el arreglo:** la copia de `titan/f-004-kmi` quedó como **puntero** a la de `main`. Mantener dos índices es la próxima divergencia esperando pasar, y es exactamente el defecto que este repo ya pagó dos veces (`CONTEXTO-SIAO.md` contra el repo, `docs/auditorias/` contra `docs/audits/`). **Un puntero que no se puede desincronizar es mejor que dos copias que hay que sincronizar a mano.**

## 2 · H-06 · `permissions`, `timeout-minutes` y el guard del `chmod`

| Workflow | antes | ahora |
|---|---|---|
| `falsador-kvm-runners.yml` | sin `permissions`, sin `timeout` | `contents: read` · `timeout-minutes: 20` |
| `falsador-kvm-usermod.yml` | sin `permissions`, sin `timeout`, `chmod 666` sin guard | `contents: read` · `timeout-minutes: 15` · `chmod` guardado |

**`contents: read` no es una elección conservadora, es el mínimo REAL:** ninguno de los dos escribe al repo. Su única salida es `GITHUB_STEP_SUMMARY`, que no necesita permisos de `contents`. Antes hered aban el default del repo, que es superficie que no hace falta.

**El `timeout` importa más de lo que parece:** sin él el tope es el default de **seis horas**, y estas corridas tardan ~1-2 min. Un `ioctl` colgado se comía seis horas de cuota antes de que alguien lo notara.

### El guard del `chmod 666 /dev/kvm`, con su propio testigo

Acepté la propuesta de Tao (`if: runner.environment == 'github-hosted'`) **y le agregué lo que le faltaba**, porque hoy mismo, en este proyecto, encontramos un guard que corrió, devolvió `rc=0` y **no hizo trabajo** (el `archscripts` del `Error 126`, con `0.02 s` y `Nothing to be done`). La lección quedó escrita: *"un paso de mitigación que no hace trabajo no mitigó nada"*.

**Un `if:` que saltea en silencio es la misma familia.** Así que:

- un **paso 0** imprime `runner.environment` y lo escribe al resumen,
- el paso guardado deja un marcador (`/tmp/V2_CORRIO`),
- y un paso con `if: always()` **mide si V2 corrió, se salteó o falló**, y lo dice.

Así, si la expresión estuviera mal escrita, se ve en el resumen en vez de pasar por verde. **NO MEDIDO:** la expresión no se verificó en corrida; el paso 0 existe justamente para cerrar eso en la próxima.

**Y le agregué un dato de campo al otro workflow:** que en `mudh-mobile` el `cmdline-tools` de Google falló en aarch64 con `Exec format error` (exit 126), porque el `sdkmanager` moderno delega en un binario nativo que Google publica solo para x86_64. Ese workflow pregunta si puede instalar el SDK, y ahora la respuesta no se descubre dos veces.

## 3 · MI FALSO VERDE, y es el hallazgo más útil de este turno

Validé los dos YAML con un bucle:

```
for f in falsador-kvm-runners falsador-kvm-usermod; do
  cp /workspace/siao/.github/workflows/$f.yml /workspace/_wf.yml
  ...
done
```

Y la salida dijo, **dos veces**:

```
YAML OK. jobs: ['inventario-arm64', 'gate-en-arm64-nativo', 'apk-arm64', 'smoke-android-arm64']
PASOS CON SINTAXIS ROTA: 0
```

**Esos cuatro jobs no son de SIAO: son del `arm64-smoke.yml` de `mudh-mobile`.** La `$f` llegó vacía al canal del gateway, el `cp` falló con `cannot stat '.../.yml'`, y el validador corrió sobre el `_wf.yml` **que había quedado de otro repo hace horas**.

**O sea que mi validación dijo OK sobre un archivo que no era el sujeto.** Es E-01 exacto, con dos agravantes: el `cp` falló **en el `stderr`**, que es donde no estaba mirando, y el resultado fue **verde**, que es la dirección en la que uno no vuelve a mirar.

**Es la cuarta vez hoy que una variable de shell no sobrevive al canal del gateway**, y la regla está escrita en el método. Rehecho con **rutas literales y md5 del archivo copiado contra el original**:

```
RUNNERS  md5 6020dbe09f == 6020dbe09f   jobs ['kvm']        permissions {'contents':'read'}  timeout [20]
USERMOD  md5 d2d5a93a87 == d2d5a93a87   jobs ['destrabar']  permissions {'contents':'read'}  timeout [15]
         V2 chmod 666  ->  if: runner.environment == 'github-hosted'
         testigo       ->  if: always()
PASOS CON SINTAXIS ROTA: 0   (en los dos, con bash -n por paso)
```

**La leccion, y va al método:** cuando un validador copia el sujeto a un archivo temporal fijo, **hay que verificar el hash del temporal contra el original**. Si no, el validador puede estar midiendo el sujeto anterior, y su verde no dice nada del actual. Un archivo temporal reutilizado es un sujeto que se hereda en silencio.

## 4 · Lo que sigue abierto de la lista de Tao

| # | Item | Estado |
|---|---|---|
| H-10 | matriz de N corridas del `Error 126` | **`needs-runtime`**, es de Tachi. Lo más importante que queda: mientras el 126 esté dormido, cualquier build del kernel puede caer por una causa que creemos cerrada |
| H-14 (2º mitad) | el `ADR-001` §7 Fase 0 dice "GKI 6.1/6.6" y no dice que 6.1 es la de referencia | anotado en el `CONTEXTO`, no en el ADR |
| H-15 | rotar el PAT expuesto | **decisión humana**, señalado desde el 09-05 |
| H-04 / H-05 | unificar `docs/auditorias` con `docs/audits`, indexar `respuestas/` | mecánico, sin hacer |
| H-03 | issues por cada NO MEDIDO | son 5+ escrituras, espera OK |
| H-08 | `LICENSE` | **decisión de Abraham**, y ahora urge más: el repo es **público** |

## 5 · NO MEDIDO

- **Los dos workflows no se corrieron después del cambio.** El YAML parsea y cada paso pasa `bash -n`, pero eso no es una corrida. Disparan por `push` sobre `disparadores/*.txt` o a mano, y **disparar es acción humana**.
- La expresión `runner.environment == 'github-hosted'` (ver §2).
- Si al volver el repo a privado el ruleset de protección se desactiva o queda inerte.
