# ADR-006 · Resolución de la quinta auditoría

**Fecha:** 2026-09-06 · **Máquina:** `brain-env` vía gateway (servicio `build`), **cero builds**. Evidencia cruda: `/workspace/PRE-61.txt`.

**Sin rúbrica (R-14).**

---

## 1 · Acepto las cuatro reglas y las cuatro decisiones

**R-15** (ningún run termina sin lectura; `VEREDICTO.md` + entrada en `mediciones/INDICE.md`), **R-16** (toda afirmación con clase, y sin clase se lee como NO MEDIDO), **R-17** (generación de KMI en el nombre del artifact, y nada se cita cruzado sin etiqueta "NO TRANSFERIBLE"), **R-18** (repo sin `LICENSE` legible = SOLO LECTURA antes de leer código).

**Las cuatro ya están implementadas**, no solo aceptadas: `tools/f004d61_stg.py` escribe `VEREDICTO.md` y agrega su línea al índice; el workflow renombra los artifacts a `*-android14-6.1-*`; y este ADR clasifica cada afirmación.

**D8, D9, D10, D11 firmadas.** F-004d es el fragmento oficial, F-004c el plan B medido, Pixel 8/8a el dispositivo de referencia, Lindroid SOLO LECTURA.

**Y acepto la corrección sobre el 33,2%:** entre generaciones **no hay compatibilidad prometida por Google**, así que ese número no dice "un tercio sirve", dice "cero sirve, como corresponde". **Queda reetiquetado como control negativo, no como hallazgo.** Lo que sí sobrevive es el dato fino: 275 símbolos conservan su CRC entre 6.1 y 6.6, lo que muestra que **el CRC cambia por firma real y no por número de versión** — el mismo mecanismo de F-004c visto desde afuera.

**Y sus dos observaciones que el informe no tenía, aceptadas las dos:**

- **`MODULE_SIG_FORCE` apagado es la puerta, no la única cerradura.** `dm-verity` + AVB siguen ahí, y el bootloader desbloqueable es **criterio de elección de dispositivo**, no de kernel. Refuerza D9 hacia Pixel.
- **F-004c y F-004d no son excluyentes en producto.** Uno oficial, otro plan B por dispositivo. **DE TERCEROS** (es su lectura) y la comparto.

---

## 2 · El pre-vuelo de 6.1 CONFIRMA su advertencia sobre los slots, y es un hallazgo

**MEDIDO** hoy, cero builds, en `include/linux/sched.h` de `android14-6.1`:

```plain
 1551| ANDROID_KABI_USE(1, unsigned int saved_state);
 1552| ANDROID_KABI_USE(2, struct task_dma_buf_info *dmabuf_info);
 1553| ANDROID_KABI_USE(3, struct {          <-- EL SLOT 3 YA ESTA USADO
 1557| ANDROID_KABI_RESERVE(4);
 1558| ANDROID_KABI_RESERVE(5);
 1559| ANDROID_KABI_RESERVE(6);
 1560| ANDROID_KABI_RESERVE(7);
 1561| ANDROID_KABI_RESERVE(8);
```

Contra `android15-6.6`, donde los libres eran **3 a 8** (seis) y los usados solo 1 y 2.

**Su advertencia de la cuarta auditoría era:** *"Google consume `ANDROID_KABI_RESERVE` de menor a mayor en sus backports LTS. Si en un `android15-6.6` futuro usa el 3, el parche SIAO colisiona. Corrección barata: mover a slots 6-7-8"*.

**No hay que esperar un futuro: en 6.1 ya pasó.** El parche de F-004c, escrito sobre los slots **3-4-5**, **no compilaría** en 6.1: el `_Static_assert` de `__ANDROID_KABI_CHECK_SIZE_ALIGN` lo rechazaría porque el 3 ya no está reservado.

**Dos consecuencias:**

1. **D5 queda validado con evidencia, no con prudencia:** los slots van a **6-7-8**. Y ahora se sabe **por qué** y no solo "por si acaso".
2. **F-004d es aún más superior de lo que parecía:** no toca ningún slot, así que **es inmune a esta clase de colisión por diseño**. El plan B (F-004c) hereda una fragilidad que el plan A no tiene, y eso es un argumento nuevo a favor de D8.

---

## 3 · Su riesgo sobre `POSIX_MQUEUE`: existe, y va A FAVOR

Usted escribió: *"Si falla, es porque 6.1 tiene distinto `POSIX_MQUEUE` default: verificable en el `.config` antes de compilar (R-05)"*. Lo verifiqué. **MEDIDO:**

```plain
android14-6.1  gki_defconfig -> CONFIG_POSIX_MQUEUE=y     YA PRENDIDO
android15-6.6  gki_defconfig -> CONFIG_POSIX_MQUEUE       ausente del defconfig
```

**El default SÍ difiere, y en la dirección buena.** En 6.1 `POSIX_MQUEUE` ya viene en `y`, así que `IPC_NS` (que depende de `SYSVIPC || POSIX_MQUEUE`) tiene **más** margen que en 6.6, no menos.

**INFERIDO, y lo digo como inferencia:** si `POSIX_MQUEUE=y` ya está en el defconfig de 6.1, es posible que `IPC_NS` también resuelva a `y` **sin que el fragmento lo pida**. Si eso pasa, el fragmento de SIAO en 6.1 podría ser de **siete** símbolos, no ocho. **NO MEDIDO** hasta que el `.config` resuelto lo diga, y el instrumento ya lo imprime.

**Su predicción (68 B) la firmo igual**, con la base corregida: no es "mismo resultado porque nada cambia", es "mismo resultado **porque el fragmento de ocho no prende ninguna de las dos causas medidas**, y el margen de `IPC_NS` es mayor".

---

## 4 · Dos datos más del pre-vuelo, para el tablero

**MEDIDO:**

```plain
android14-6.1: 37 listas de simbolos
  abi_gki_aarch64                    2 simbolos   (en 6.6 eran 3)
  abi_gki_aarch64_pixel          2.943 simbolos   (en 6.6 eran 3.375)
  abi_gki_aarch64_virtual_device  1.394 simbolos   (en 6.6 eran 1.491)
```

**El contrato de Pixel en su generación real es 2.943 símbolos**, no 3.375. Ese es el número que hay que usar de ahora en más, y es el que F-007c va a cruzar contra el `Module.symvers` de 6.1.

---

## 5 · Sus dos innovaciones: acepto una entera y a la otra le agrego un guard

### 5.1 `siao-probe` — acepto, y es el primer artefacto publicable del proyecto

El script ya existe (`f7e.py` a `f7j.py` en el taller). Empaquetarlo es trabajo de forma, no de investigación. **Y su argumento de por qué importa es el que me faltaba:** un proyecto sin código publicable tendría el suyo, con licencia, y el ecosistema Halium lo necesita.

**Un guard que su enunciado no tiene:** el parser de `__versions` que usé tenía **stride 72 en vez de 64** y leía nombres como CRC. `siao-probe` no se publica sin el control aritmético que lo cazó (`len(__versions) % stride == 0`) **y** sin el control de consistencia (cero CRC contradictorios entre módulos). Publicar una herramienta con ese bug sería peor que no publicarla.

### 5.2 F-008 — acepto, y le refuto la predicción

Su predicción: *"las tres funcionan sin AppFunctions, porque el host es root sobre el contenedor"*.

**Le refuto el mecanismo, no la conclusión.** Ser root en el host **no** alcanza para operar apps de Android: `am start` y `cmd` requieren que **el binder del contenedor** acepte al llamador, y Android chequea **UID y firma**, no privilegio del host. Un `lxc-attach` te pone adentro del contenedor, y ahí sí sos root **de ese Android**, que es distinto.

**Así que la predicción hay que partirla en tres, y las tres son falsables por separado:**

| Acción | Predicción mía | Por qué |
|---|---|---|
| abrir una app (`am start`) | **funciona** | `shell` puede lanzar activities |
| leer una notificación | **NO funciona sin permiso especial** | requiere `NotificationListenerService`, que es una app con permiso otorgado |
| cambiar un ajuste (`cmd settings put`) | **funciona para `global`/`system`, no para todo** | algunos requieren `WRITE_SECURE_SETTINGS` |

**Si sale como predigo, F-008 mide algo más útil que un verde:** mide **exactamente dónde** el contenedor deja de obedecer, y eso es el borde donde AppFunctions sí hace falta. F-005 no se redefine como "mejora de interfaz": se redefine como **"lo que hace falta para las acciones que el borde no cubre"**, y ese borde queda medido.

---

## 6 · Su protocolo de F-001-S1: acepto entero y agrego un guard

Sus G1 a G4 y el control con GKI de stock entran tal cual. **G3 cerrando S1b en la misma corrida es la mejor pieza de su diseño:** ahorra un falsador entero.

**El guard que agrego, y sale de un defecto propio:** `systemctl --failed` con cero líneas **no** prueba que `systemd` llegue a `multi-user.target`. Un `systemd` que muere en `initrd` también tiene cero unidades fallidas, porque no llegó a intentar ninguna. **G5: `systemctl is-system-running` tiene que devolver `running` o `degraded`, y su salida va commiteada.** Es exactamente el patrón del `grep -c` que devuelve `0`: un cero disfrazado de medición.

---

## 7 · Ya corriendo

**F-004d @ `android14-6.1`**, dos brazos en Actions arm64, con baseline **propio** de 6.1 (R-17: el `.stg` de 6.6 no es transferible). Workflow `.github/workflows/f-004d-61.yml`, comparador `tools/f004d61_stg.py`.

**Predicción firmada antes de correr: ~68 B, 0 CRC, 0 byte-size, 0 offsets, 0 structs.**

---

## NO MEDIDO después de este ADR

1. **F-004d en 6.1** (corriendo).
2. **Si `IPC_NS` resuelve a `y` solo en 6.1** → el fragmento podría ser de siete.
3. **`dm-verity`/AVB en Pixel:** su observación es correcta y **no la medí**.
4. **Si el parche de F-004c compila en 6.1** con los slots movidos a 6-7-8. Predicción: sí. Sin medir.
5. Todo lo del §9 del informe técnico que sigue abierto.

--- METODO TITAN ---
Accion delicada: NO
Modo aplicado:   TITAN FULL
Rubrica:         N/A por R-14
Review externo:  este ADR responde a un review externo
Instrumento:     brain-env por el gateway, cero builds. Evidencia: /workspace/PRE-61.txt
                 Lecturas de android.googlesource.com, ramas android14-6.1 y android15-6.6.
