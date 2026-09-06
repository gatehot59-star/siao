# Tercera auditoría: gano dos, pierdo dos, y las cuatro están medidas

**Fecha:** 2026-09-06 · **Máquina:** `brain-env` vía gateway, lecturas contra `android.googlesource.com` (fuente primaria). **Cero compilación en este turno.**

**Pedido:** resolver la auditoría de las cinco entregas. Su punto más duro (§2.5: *"no se listan las cinco vías, sin eso no es auditable"*) es el que me hizo re-medir, y re-medir **destruyó mi propio NO MEDIDO**.

---

## 1 · PIERDO, y es la peor: **`stgdiff` EXISTE**, y como binario listo

Su sospecha era *"puede estar en `prebuilts/kernel-build-tools/linux-x86/bin/stg`"*. Casi: el repo se llama distinto. Re-medido hoy:

```plain
1 api.github.com/repos/google/stg                     -> 404
2 api.github.com/repos/google/stg/tags                -> 404
3 googlesource platform/external/stg (+refs)          -> 200, 126.990 B
4 kernel/prebuilts/build-tools .../linux-x86/bin      -> 200, listado completo
5 kernel/prebuilts/build-tools (+refs)                -> 200, 301.497 B

platform/external/stg CMakeLists.txt (main y master)  -> 200, 6.112 B
```

Y en el listado de la vía 4, **verbatim**:

```plain
100755 blob 51da615081a47755608702b0dec60f61b5590241	stg
100755 blob a84c44ef90c4f08354e62b8251d52f47d3b0d20b	stgdiff
```

**Mi "stgdiff NO MEDIDO por falta de instrumento" era FALSO.** Buscaba en `kernel/prebuilts/kernel-build-tools`, que no existe; el repo real es **`kernel/prebuilts/build-tools`**. Dos de mis cinco "vías fallidas" eran **la misma URL mal escrita, contada dos veces**, y las otras dos (`github.com/google/stg`) apuntaban al lugar equivocado porque el proyecto vive en googlesource, no en GitHub.

**El mecanismo del error, nombrado:** declaré NO MEDIDO por **carencia de instrumento** cuando lo que tenía era **una ruta mal tipeada**. Es el mismo patrón que `CONFIG_BRIDE` por `BRIDGE`: un símbolo mal escrito produce un `0` que parece un hallazgo. Y lo agravé contando cinco intentos como si fueran cinco hipótesis independientes.

**Consecuencia de plan, no cosmética:** **F-004 real vuelve a estar sobre la mesa.** No hay que degradarlo a F-004-lite por falta de herramienta. Pero su matiz manda: el binario es **`linux-x86`**, o sea que **no corre en el runner arm64**. La arquitectura correcta sale de ahí sola: **compilar en arm64, comparar en x86.** `stg` lee ELF, no necesita ejecutarlo, así que un job x86 puede leer un `vmlinux` aarch64 sin problema.

---

## 2 · LE REFUTO la vía A: `-DOPENSSL_NO_ENGINE` **no es la guarda de este bug**

Su diagnóstico dice que `key_pass` está guardado por `#ifndef OPENSSL_NO_ENGINE`. Leí el archivo. **No es esa guarda.** `certs/extract-cert.c` de `android15-6.6`, 3.976 B, líneas verbatim:

```plain
  59| #ifndef OPENSSL_IS_BORINGSSL
  69| #endif
  80| #ifdef USE_PKCS11_ENGINE
  81| static const char *key_pass;        <-- LA DECLARACION
  82| #endif
 114| #ifdef USE_PKCS11_ENGINE
 115| 	key_pass = getenv("KBUILD_SIGN_PIN");
 116| #endif
 131| #ifdef OPENSSL_IS_BORINGSSL
 134| #else
 152| 		if (key_pass)                  <-- EL USO
 153| 			ERR(!ENGINE_ctrl_cmd_string(e, "PIN", key_pass, 0), "Set PKCS#11 PIN");
 157| #endif
```

**El bug es de guardas asimétricas:** la **declaración** vive bajo `USE_PKCS11_ENGINE`, y el **uso** vive bajo el `#else` de `OPENSSL_IS_BORINGSSL`. O sea que con OpenSSL normal y sin `USE_PKCS11_ENGINE`, el uso se compila y la declaración no. Eso es exactamente el error.

**Por qué su vía A no solo no arregla, sino que empeora:** definir `OPENSSL_NO_ENGINE` hace que los headers de OpenSSL esconden la API `ENGINE_*`, y las líneas 152-153 **siguen compilándose** porque su guarda es otra. Predicción falsable: con `-DOPENSSL_NO_ENGINE` el error cambia de `key_pass` a **`ENGINE_ctrl_cmd_string` / `ENGINE` no declarados**, o sea más errores, no menos.

**La vía A corregida, que es la que voy a correr:** `HOSTCFLAGS=-DUSE_PKCS11_ENGINE`, que declara `key_pass` (línea 81) y lo inicializa desde `KBUILD_SIGN_PIN` (línea 115). **No toca ningún `CONFIG_*`**, así que su regla "un baseline modificado no es baseline" se respeta entera. Predicción: compila.

---

## 3 · LE REFUTO el motivo de §2.2, y le CONFIRMO la conclusión

Dice que `MODULE_SIG=n` cambia `struct module` **por el campo `sig_ok`**. En ACK eso es falso, y lo dice el propio kernel de Google, `include/linux/module.h` líneas 450-455 verbatim:

```plain
	/*
	 * Signature was verified. Unconditionally compiled in Android to
	 * preserve ABI compatibility between kernels without module
	 * signing enabled and signed modules.
	 */
	bool sig_ok;
```

**Google lo compiló incondicionalmente exactamente para que apagar `MODULE_SIG` no mueva el layout.** Así que el mecanismo que cita está blindado por diseño.

**Pero su conclusión se sostiene por otro lado**, y también medido: en el `#else` de `CONFIG_MODULE_SIG` (líneas 927-936) `is_module_sig_enforced()` y `module_sig_ok()` pasan a ser `static inline`, o sea que **dejan de existir como símbolos**. Eso sí puede mover `Module.symvers`. Y el `gki_defconfig` trae `CONFIG_MODULE_SIG=y` **más `CONFIG_MODULE_SIG_PROTECT=y`**, que es una extensión de Android:

```plain
CONFIG_MODVERSIONS=y
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_PROTECT=y
```

**Veredicto:** acepto la prohibición (`MODULE_SIG=n` **no** puede ser brazo, solo control de arnés), y corrijo la razón. Que la conclusión sea correcta con el mecanismo equivocado es peligroso: mantiene el hábito de razonar sobre el mapa.

---

## 4 · Le acepto, sin peros

- **R-08, R-09, R-10.** Las tres son mecanismos, no lecciones, y las tres nacen de defectos míos medidos. `tee` + `pipefail` + `rc` del comando; borrar el log del brazo cuyo código cambió; y **"CERRADO" solo con todos los criterios verdes**. F-002 pasa a **"VERDE a/b · ROJO c"** en el tablero y en el ADR.
- **Las dos llaves en un paso.** Tenía pensada la de openKylin y no la del overlay. Si (c) entra sin **clave SIAO** firmando el `Release` del overlay, apt rechaza los tres paquetes por el mismo motivo que rechazaría el resto. Es un bug futuro que se evita hoy.
- **`Module.symvers` es criba, no veredicto.** Correcto: no ve cambios de layout de structs que un DLKM use sin exportar. Queda **F-004-lite**, y con `stgdiff` disponible ya no es el plan A sino el filtro rápido.
- **Los 2 de 3 paquetes imprevistos.** `libgcrypt20` y `libgpg-error0` no estaban en ninguna hipótesis mía: entraron por el conjunto esencial vía `gpgv`. Congelar los tres con sha256 antes de que `-proposed` los mueva entra al snapshot.

---

## 5 · Lo que queda NO MEDIDO después de este turno

- Si `-DUSE_PKCS11_ENGINE` compila. **Predicción declarada antes de correr: sí.**
- Si el `stgdiff` x86 corre contra ELF aarch64. Plausible por diseño (lee ELF), **no medido**.
- Kleaf: si el toolchain cabe en el disco del runner. **No medido**, y ahora es menos urgente porque el prebuilt existe.
- El brazo `siao` de F-004: su log actual es del intento viejo (R-09 lo va a borrar).
- F-002 (c), F-001-S1, F-003, F-005, F-006: sin cambios.

---

## 6 · El orden que propongo, y en qué difiere del suyo

Su orden pone F-002 (c) primero. **Lo invierto, y digo por qué:** F-004 es el que **bloquea a F-001-S1 y al gate de hardware**, y ahora tiene las dos piezas que le faltaban (el fix del host tool medido y `stgdiff` localizado). F-002 (c) es corto pero no desbloquea nada: `trusted=yes` ya construyó el rootfs y el riesgo que cubre es de cadena de suministro, no de arquitectura.

1. **F-004 v3** en arm64 con R-08/R-09, `HOSTCFLAGS=-DUSE_PKCS11_ENGINE`, cero cambios de `CONFIG` en el baseline, los dos brazos re-medidos desde cero, `vmlinux` + módulos subidos como artifact.
2. **F-004 comparación en x86** con `stg` + `stgdiff` prebuilt de `kernel/prebuilts/build-tools`, contra el `.stg` de referencia de Google (8.014.732 B).
3. **F-002 (c)** con las dos llaves.

--- METODO PROMETEO ---
Máquina: `brain-env` vía gateway (lecturas de fuente primaria en `android.googlesource.com`).
Artefacto en git: este archivo.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
