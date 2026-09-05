# ADR-003 · Resolución de la segunda auditoría (F-001 y ADR-002)

**Fecha:** 2026-09-05 · **Estado:** aceptada · **Enmienda a:** ADR-001, ADR-002
**Máquina:** `brain-env` (gateway, servicio `build`) para todas las lecturas, más
búsqueda web contra fuente primaria. **Cero compilación y cero QEMU.**

---

## 0. Marcador

| # | Punto del auditor | Resultado |
|---|---|---|
| §1.3 | `IPC_NS` ausente porque `SYSVIPC` está apagado | **CONFIRMADO, medido** |
| §1.2 | Mezclé los rojos de LXC con los de SIAO | **Acepto** |
| §1.7 | AppArmor vs SELinux | **Confirmado, y más barato de lo que creía** |
| §2.4 | `yangtze` no es 2.0 | **Pierdo. Es V1.0** |
| §3.4 / A9 | 64K es el default de GNU `ld` | **Pierdo, y mi VERDE valdría menos** |
| §3.2 | AOSP no se compila en Actions | **Acepto, con número al ADR** |
| §2.3 | "chrootless es la causa raíz del ENOENT" | **REFUTADO, medido** |
| §1.4 / F-004 | `stgdiff` contra `android/abi_gki_aarch64.stg` | **No corrible en la rama que importa** |
| §1.4 | "añadir es KMI-compatible" | **Correcto en espíritu, le falta el mecanismo real** |

---

## 1. Su hallazgo grande: CONFIRMADO

```plain
CONFIG_SYSVIPC                 APAGADO
CONFIG_SYSVIPC_SYSCTL          AUSENTE del .config
CONFIG_POSIX_MQUEUE            APAGADO
CONFIG_POSIX_MQUEUE_SYSCTL     AUSENTE del .config
CONFIG_IPC_NS                  AUSENTE del .config
```

**Tenía razón:** `IPC_NS` no está ausente por olvido, está ausente porque su
dependencia Kconfig (`SYSVIPC || POSIX_MQUEUE`) está apagada. Yo lo había
reportado como tres datos independientes y es **uno con dos consecuencias**.

**Y su regla general entra al método, porque es la misma clase de error que ya me
cobré dos veces:** *"ausente" se resuelve contra las dependencias de Kconfig
ANTES de interpretarlo*, igual que un símbolo mal tipeado siempre da ausente.

**Lo que agrega y él no dijo:** esto deja de ser un tema de contenedores y pasa a
ser de **compatibilidad de userland Linux**. `shmget`, `semget` y `mq_open` no
existen. Cualquier cosa del escritorio que los asuma falla, y falla en silencio.

---

## 2. Los cinco que pierdo

### 2.1 `yangtze (2.0)` es falso · quinto defecto del mismo patrón

Medido en los `Release` de los mirrors y en `build.openkylin.top`:

```plain
Suite: nile    | Version: 2.0 | Codename: nile
Yangtze V1.0 (1.0) : linux package : openKylin
Huanghe V3.0 | release | main | linux-meta 7.0.0.ok2.0
```

**Yangtze = V1.0 (2023), Nile = V2.0 (2024), Huanghe = V3.0.** Escribí "yangtze
(2.0)" con confianza y sin fuente. **Quinto defecto del patrón A2 en dos
jornadas**, y el auditor lo cazió declarando explícitamente que no lo había
verificado. Eso es mejor método que el mío en ese punto.

### 2.2 Mi "A VERDE" de FALSADOR-001 valía menos de lo que lo vendí

Acepto sin pelear: **65536 es el `max-page-size` por defecto de GNU `ld` en
aarch64**. Los 146 ELF a `p_align 65536` no son una virtud del build de openKylin:
son lo esperable de cualquier binario aarch64 linkeado con `ld`. El verde era
**real y banal**, y yo lo presenté como hallazgo con una tabla y un título.

**Lo que sobrevive de ese falsador:** el brazo B, que **ejecutó** el `bash 5.3.9`
de openKylin en un aarch64 ajeno. Eso sigue siendo la premisa base y sigue verde.

**Corregido donde se publicó**, como corresponde.

### 2.3, 2.4 y 2.5

- **Mezclé los rojos de `lxc-checkconfig` con los de SIAO.** `CGROUP_DEVICE` y
  checkpoint/restore son **falsos rojos** heredados de cgroup v1: en v2 el control
  de dispositivos lo hace BPF y `CONFIG_CGROUP_BPF=y` ya está.
- **`USER_NS` no es bloqueador de Fase 1:** Waydroid corre como contenedor
  privilegiado. Es endurecimiento de Fase 3.
- **Su roadmap de falsadores es mejor que el mío** y se adopta con una corrección
  (ver §4).

---

## 3. Los tres que le refuto, con medición

### 3.1 "chrootless es la causa raíz del ENOENT" · REFUTADO

Dice que un cambio de flag elimina dos de mis tres defectos, porque el ENOENT
vendría de `--mode=chrootless` y fakechroot. **Mi propia salida cruda commiteada
lo desmiente:**

```plain
$ mmdebstrap --architectures=arm64 --variant=important ...   (sin --mode)
  MM | I: automatically chosen mode: root
  MM | I: installing essential packages...
  MM | chroot: failed to run command 'dpkg': No such file or directory
```

**El ENOENT apareció en `--mode=root`**, que es el que él propone como solución.
El de `mawk` también fue sin `--mode`, o sea root por defecto. `chrootless`
apareció después, como **segunda vía**, y falló por otra cosa. Así que su
diagnóstico es plausible y **falso para este caso**.

### 3.2 F-004 como lo especificó NO es corrible en la rama que importa

```plain
rama android16-6.12 -> listado de android/: 404
rama android15-6.6  -> listado de android/: 200, y contiene:
    abi_gki_aarch64        abi_gki_aarch64.stg     abi_gki_aarch64.stg.allowed_breaks
    abi_gki_aarch64_qcom   abi_gki_aarch64_pixel   abi_gki_aarch64_mtk
    abi_gki_aarch64_xiaomi ... (38 listas por vendor)
```

**En `android16-6.12` el directorio `android/` da 404.** El `.stg` de referencia
que su F-004 necesita **sólo existe en `android15-6.6`**. Antes de comprometer un
build de 1-3 h hay que decidir: o F-004 corre sobre `android15-6.6`, o hay que
encontrar dónde 6.12 guarda su referencia de ABI. **Queda NO MEDIDO.**

**Y un regalo de ese listado que refuerza su propio argumento:** Google mantiene
**38 listas de símbolos por vendor** (`_qcom`, `_pixel`, `_mtk`, `_xiaomi`,
`_exynos`...). O sea que **el KMI ya se estira por vendor en el árbol oficial**:
la idea de un fragmento por dispositivo no es hereje, es lo que hace Google.

### 3.3 Su §1.4 acierta en espíritu y se pierde el mecanismo real

Argumenta que "añadir es compatible" y que el KMI prohíbe "quitar o cambiar". La
conclusión es correcta, pero el mecanismo **no es una convención**: son tres
símbolos que medí en el `.config` real.

```plain
CONFIG_MODVERSIONS                 =y
CONFIG_TRIM_UNUSED_KSYMS           =y
CONFIG_UNUSED_KSYMS_WHITELIST      ="abi_symbollist.raw"
CONFIG_MODULE_SIG                  =y
CONFIG_MODULE_SIG_FORCE            APAGADO      <-- la puerta
```

1. **`MODVERSIONS=y` es el enforcer real:** los CRC de símbolo se verifican al
   cargar. Un cambio de layout **no da un error de `stgdiff`, da un módulo que no
   carga.** Es más duro y más temprano de lo que su argumento supone.
2. **`TRIM_UNUSED_KSYMS` + `UNUSED_KSYMS_WHITELIST="abi_symbollist.raw"`** hacen
   que el conjunto exportado sea **exactamente la whitelist**. Eso **respalda** su
   "añadir no rompe": agregar features no agrega exports.
3. **Y su salida GPL sale más fuerte con un número: `MODULE_SIG_FORCE` está
   APAGADO.** O sea que un DLKM recompilado por nosotros **carga sin la llave de
   Google**. Su red de seguridad no depende de conseguir una firma: depende de
   tener la fuente, que es GPL.

---

## 4. La causa raíz de los cuatro ENOENT no era sólo mi torpeza: es empaquetado

```plain
base-files 14-ok3 (59.988 B)
  symlinks que trae: ./etc/os-release -> ../usr/lib/os-release
                     + tres licencias. NADA MAS.
  directorios top-level: bin boot dev etc home lib proc root run sbin sys tmp usr var
  hay ./lib? True | hay ./bin? True   <-- DIRECTORIOS REALES, no symlinks
  VEREDICTO: base-files NO trae los symlinks de merged-usr

usrmerge       presente en el repo
usr-is-merged  presente en el repo
```

**El `PT_INTERP` de los binarios de openKylin apunta a `/lib/ld-linux-aarch64.so.1`
y el loader se instala en `/usr/lib/`.** El puente lo traen `usrmerge` /
`usr-is-merged`, que son **paquetes separados** y no entran en el conjunto
esencial. Por eso **toda** construcción por extracción se rompe igual, con
`dpkg`, con un `postinst` o con un `chroot`.

**Fix de F-002, y no es un parche a mano:** `--include=usr-is-merged` (o el hook
merged-usr de mmdebstrap). Mis tres defectos de scripting siguen siendo míos,
pero **la clase entera de error tiene causa en el empaquetado de openKylin**, y
eso hay que saberlo antes de escribir el sexto workaround.

---

## 5. LSM: confirmado, y más barato de lo que él creía

```plain
CONFIG_SECURITY                    =y
CONFIG_SECURITY_SELINUX            =y
CONFIG_SECURITY_APPARMOR           APAGADO
CONFIG_SECURITY_PATH               =y        <-- prerequisito de AppArmor, YA ESTA
CONFIG_LSM                         ="landlock,lockdown,yama,loadpin,safesetid,selinux,smack,tomoyo,apparmor,ipe,bpf"
CONFIG_AUDIT                       =y
```

Su §1.7 acierta. **Dos datos que lo abaratan:** `SECURITY_PATH=y` ya está (es lo
que AppArmor necesita del kernel) y **el string de `CONFIG_LSM` ya lista
`apparmor`**, así que habilitarlo es un símbolo, no una reestructuración. Sigue
faltando medir el impacto en KMI.

---

## 6. Y A2 no se puede cerrar, contra los dos

| Fuente | Fecha |
|---|---|
| `Release` del repo apt `huanghe` | **Fri, 28 Aug 2026 3:58:34 UTC** |
| Índice de releases (`autoindex`) | 27 y 28-Aug-2026 |
| Nota oficial, **snapshot del buscador** | **2026-08-28 07:57:17** |
| Nota oficial, **mi lectura en vivo de hoy** | **2026-08-31 17:05:48** |

**El timestamp de la propia página cambió** entre el snapshot y mi lectura. Así
que mi "28" probablemente salió de un estado real anterior de esa página, y no de
la nada. **Igual pierdo el punto de método**, que es el que importa: afirmé desde
un extracto y corregí a alguien que tenía el dato bien. Y **el sujeto no se
cierra**: la fecha exacta de publicación queda NO MEDIDA, ahora con la razón
medida de por qué.

---

## 7. El fragmento de kernel, corregido con lo medido

```bash
# siao-A.fragment - HOST (systemd de openKylin arranca)
CONFIG_DEVTMPFS=y            # medido APAGADO
CONFIG_DEVTMPFS_MOUNT=y      # medido AUSENTE
CONFIG_FHANDLE=y             # medido APAGADO (el pedia "verificar": ya esta verificado)
CONFIG_SYSVIPC=y             # medido APAGADO -> habilita IPC_NS
CONFIG_POSIX_MQUEUE=y        # medido APAGADO
CONFIG_TMPFS_XATTR=y         # medido APAGADO
CONFIG_AUTOFS_FS=y           # medido APAGADO
CONFIG_VT=y                  # medido APAGADO (seats de logind) - NO MEDIDO si hace falta sin consola

# siao-B.fragment - CONTENEDOR DE APPS (LXC privilegiado, estilo Waydroid)
CONFIG_PID_NS=y              # medido APAGADO. EL bloqueador, sin rodeo
CONFIG_IPC_NS=y              # sale gratis con SYSVIPC
CONFIG_CGROUP_PIDS=y         # medido APAGADO. TasksMax de systemd

# siao-C.fragment - ENDURECIMIENTO (Fase 3)
CONFIG_USER_NS=y
CONFIG_SECURITY_APPARMOR=y   # SECURITY_PATH ya esta en y

# siao-D.fragment - SOLO ARNES QEMU, no va al dispositivo
CONFIG_VIRTIO_BLK=y CONFIG_VIRTIO_PCI=y CONFIG_VIRTIO_CONSOLE=y
```

**Lo que NO entra:** `CGROUP_DEVICE` ni checkpoint/restore. Son falsos rojos de
cgroup v1, como él dijo.

---

## 8. Roadmap de falsadores, adoptado con dos correcciones

| ID | Pregunta | Dónde | Estado |
|---|---|---|---|
| **F-002** | rootfs con `--mode=root` **+ `usr-is-merged`** + pin de UN paquete de `-proposed`, con `apt-cache policy` como segundo criterio | Actions arm64 | listo para relanzar, y ahora con la causa raíz identificada |
| **F-004** | ¿el fragmento cambia el KMI? | Actions arm64 | **corregido: sobre `android15-6.6`, porque en 6.12 el `android/` da 404.** Y `MODVERSIONS` es un testigo más barato que `stgdiff`: si un módulo del vendor carga, el CRC coincidió |
| **F-001-S1** | ¿arranca `systemd` sobre ACK + A/B/D? | Actions arm64 + QEMU | la pregunta real. Va después de F-004 |
| **F-001-S0** | el prebuilt | ídem | **degradado a control negativo**, como él propuso |
| **F-003** | ¿funciona con `ARM64_16K_PAGES=y`? | mismo arnés, kernel 16K | **redefinido**: `readelf` ya no es la prueba |
| **F-005** | ¿Agent Bridge en `priv-app` + allowlist invoca AppFunctions? | emulador x86 / Cuttlefish | nuevo, y es el que **puede matar media razón de ser** del contenedor arm64 |
| **F-006** | AppArmor + SELinux sin romper KMI | se cuelga de F-004 | nuevo |

**Su O-01 es correcto y lo acepto:** correr S1 antes de F-004 es apostar a ciegas.

---

## 9. NO MEDIDO, actualizado

- **Dónde vive la referencia de ABI de `android16-6.12`** (el `android/` da 404).
- Si los símbolos del fragmento pasan `MODVERSIONS` sin romper los DLKM.
- Si `usr-is-merged` cierra la clase entera de ENOENT: **identificado, no probado**.
- Si `huanghe-proposed` cierra la cadena de `systemd` con pin de un solo paquete.
- Si `VT=n` rompe `logind` en un arranque sin consola.
- **El costo del servidor de build de AOSP.** Acepto su §3.2: el runner de 2 vCPU
  no compila AOSP ni parcialmente, y **eso es la línea de presupuesto más grande
  del proyecto hasta Fase 2**. Entra al ADR-001 con número cuando se cotice.
- Su afirmación de que Halium mantiene `check-kernel-config`: **hallazgo ajeno**,
  no lo verifiqué. Si existe, `diff(halium, gki-6.12)` es el atajo correcto.

---

--- METODO PROMETEO ---
**Máquina:** `brain-env` por el gateway (servicio `build`, tool `run`) para todas
las lecturas de `.config`, índices `apt` y `googlesource`, más búsqueda web contra
fuente primaria. **Cero compilación, cero QEMU, cero kernel construido.**
**Artefacto 1 (git):** este ADR + `docs/agents/respuestas/2026-09-05-06-*`
**Artefacto 2 (ClickUp):** Doc del turno.
