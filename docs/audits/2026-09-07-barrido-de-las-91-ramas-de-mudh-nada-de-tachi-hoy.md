# Barrido de TODAS las ramas remotas de MUDH buscando algo de hoy

**Fecha:** 2026-09-07  
**Pedido:** barrer las 89 ramas de MUDH buscando algo de hoy.  
**Cierra el NO MEDIDO** declarado en `2026-09-07-apendice-el-cruce-de-tachi-es-del-06-y-difiere-en-un-punto.md`, que dijo textual: *"ramas remotas distintas de `main` no se barrieron archivo por archivo"*.

## 1. Instrumento y por qué este y no otro

`git fetch` desde `brain-env` **está roto hoy**, y no por red ausente sino por el mismo defecto que ya midió el recibo `2026-09-07-03`: el container recreado perdió `seccomp=unconfined` y no puede crear hilos.

```
cd /workspace/mudh && git fetch --all --prune
fatal: unable to access 'https://github.com/gatehot59-star/mudh-mobile.git/': getaddrinfo() thread failed to start
```

**Y ojo con el exit code, porque es una trampa ya conocida:** ese comando imprimó `fetch_rc=0`. El `0` es del `tail` del pipe, no del `git`. Misma familia que el `tail -40` que escondió el error real del kernel. El veredicto se toma por la línea `fatal:`, no por el código.

Así que el barrido se hizo con **dos instrumentos independientes**:

1. **GitHub API** (`list_branches`): nombre y SHA de cabeza de cada rama remota, estado de hoy.
2. **El clon local de `brain-env`** (`git for-each-ref refs/remotes/origin`, offline): fecha de commit de cada cabeza, sin red.

El cruce entre los dos es lo que da el resultado: la API dice **qué** SHA es la cabeza hoy, el clon dice **de cuándo** es ese SHA.

## 2. Corrección de conteo

No son 89 ramas: la API devuelve **91** ramas remotas (`main`, `audit2`, `evidencia/...` y 88 `titan/*`). El clon local tiene 92 refs bajo `refs/remotes/origin` porque incluye el alias `origin/HEAD`. El "89" viene del análisis cruzado del 2026-09-06, que contó antes de los últimos pushes.

## 3. Validación del instrumento offline (esto es lo que lo hace usable)

Se compararon los 91 SHA de cabeza de la API contra los del clon. **Coinciden 90 de 91.** El único desfase es `main`: la API da `f74cd8d` (2026-09-06 19:54 UTC) y el clon tiene `36b402f` (18:54 UTC), o sea que el último fetch local fue entre esas dos horas.

Eso importa porque acota el error del instrumento: el clon puede estar ciego solo a pushes posteriores a las ~19:00 del 06-sep, y **el único push posterior que existe es el de `main` que ya se leyó** (es justamente el cruce de Tachi). Ninguna otra rama cambió de cabeza. Si el clon estuviera ciego a un push de hoy, se vería como un SHA de la API ausente del clon, y no hay ninguno.

## 4. Resultado: UNA sola rama tiene commits de hoy

| Rama | Cabeza | Fecha de la cabeza |
|---|---|---|
| **`titan/quickjs-jni`** | `ddb7bc9` | **2026-09-07** |
| `main` | `f74cd8d` | 2026-09-06 |
| `titan/analisis-cruzado-mudh` | `226397f` | 2026-09-06 |
| `audit2` | `7fc2fdf` | 2026-09-05 |
| `titan/ab-ocr-ley007` | `c77daf3` | 2026-09-03 |
| las otras 86 | — | 2026-09-02 o anterior |

Los dos commits del 2026-09-07 en `titan/quickjs-jni`, verbatim de la API:

```
d0a25ef  2026-09-07T00:22:54Z  BRAIN <brain@mudh.local>
  medicion(boot): NO SUBE y la causa tiene nombre - com.android.os.statsd y
  com.android.resolv no activan, libstatspull/libnetd_resolv ausentes, netd+
  gpuservice+mediametrics mueren y el zygote cicla. 27 de los APEX SI montan:
  me refuto la hipotesis del container

ddb7bc9  2026-09-07T01:48:23Z  BRAIN <brain@mudh.local>
  medicion(boot): el -wipe-data ARREGLO los APEX (venian comprimidos y read-only
  impedia descomprimirlos): 0 CANNOT LINK, zygote 1 vez, pm CONTESTA. Y aparecio
  el techo duro: el Watchdog mata al system_server a los 100s y sin KVM el TCG
  no llega
```

**Los dos son míos (BRAIN) y ninguno habla de SIAO.** Son emulador, APEX, zygote, Watchdog y KVM.

## 5. Veredicto

**No existe en el remoto de MUDH ningún documento de Tachi con fecha de hoy, ni sobre SIAO ni sobre nada.** El último commit de Tachi en el repo es el cruce `docs/base/04-CRUCE-SIAO-MUDH-2026-09-06.md`, del 06-sep, y sigue siendo el documento correcto para esa pregunta.

## 6. Hallazgo lateral, y no es menor

El clon de `brain-env` tiene **trabajo de hoy que NO está en el remoto**, porque el push está roto por el mismo defecto de hilos:

```
2026-09-07 05:04:47  49f9baf  titan/quickjs-jni   <- 
local ADELANTE de ddb7bc9
```

Y los cinco recibos del día (`respuestas/2026-09-07-01` a `-05`, incluido el del emulador arrancado completo con el APK del runtime en el device) existen **solo en el clon**. Por la regla del proyecto, un resultado que no está commiteado y empujado es invisible: hoy hay cinco en ese estado, más una rama adelantada.

**Consecuencia:** arreglar `seccomp=unconfined` en `brain-env` no es higiene, es la condición para que el trabajo de hoy exista para cualquiera que no sea yo.

## 7. NO MEDIDO

- No se leyó el árbol completo de archivos de las 91 ramas: se fechó la **cabeza** de cada una. Un commit de hoy escondido en una rama cuya cabeza es del 20-ago es imposible (la cabeza sería ese commit), pero un archivo viejo con contenido nuevo no se detecta así.
- No se barrieron tags, PRs cerrados ni forks.
- No se revisó el repo `siao` con el mismo barrido en este turno.

---

**Máquina:** GitHub API (lectura) + `brain-env` (git offline sobre `/workspace/mudh`, solo lectura).  
**Artefacto git:** este archivo.  
**Artefacto ClickUp:** el Doc del audit MUDH → SIAO del mismo día.