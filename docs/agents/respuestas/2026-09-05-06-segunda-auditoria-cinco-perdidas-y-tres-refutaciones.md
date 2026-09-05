# 2026-09-05 · Segunda auditoría: pierdo cinco, refuto tres, y la causa raíz era empaquetado

## 1. Pedido literal

Una segunda auditoría, esta vez sobre F-001 y el ADR-002, que arranca reconociendo
tres pérdidas propias y sigue con nueve puntos técnicos.

**Contestado en el ADR-003:** `docs/adr/2026-09-05-03-resolucion-segunda-auditoria.md`

## 2. Marcador

**Su hallazgo grande, CONFIRMADO:** `SYSVIPC` y `POSIX_MQUEUE` apagados, y por eso
`IPC_NS` no aparece. Un dato, no tres.

**Pierdo cinco:** `yangtze` es V1.0 (no 2.0); mi "A VERDE" valía menos porque 64K
es el default de GNU `ld`; mezclé los rojos de LXC con los de SIAO; `USER_NS` no
es bloqueador de Fase 1; su roadmap es mejor.

**Le refuto tres:** el ENOENT apareció en `--mode=root`, no en chrootless; su
F-004 no es corrible en `android16-6.12` porque el `android/` da 404; y su
argumento de KMI se pierde el mecanismo real, que es `MODVERSIONS`.

## 3. Evidencia cruda, verbatim

```plain
CONFIG_SYSVIPC        APAGADO      CONFIG_POSIX_MQUEUE   APAGADO
CONFIG_IPC_NS         AUSENTE del .config
CONFIG_FHANDLE        APAGADO      CONFIG_VT             APAGADO
CONFIG_SECURITY_APPARMOR APAGADO   CONFIG_SECURITY_SELINUX =y
CONFIG_SECURITY_PATH  =y
CONFIG_LSM = "landlock,lockdown,yama,loadpin,safesetid,selinux,smack,tomoyo,apparmor,ipe,bpf"
CONFIG_MODVERSIONS    =y
CONFIG_TRIM_UNUSED_KSYMS =y   CONFIG_UNUSED_KSYMS_WHITELIST="abi_symbollist.raw"
CONFIG_MODULE_SIG     =y      CONFIG_MODULE_SIG_FORCE  APAGADO
apagados explicitos: 4141 | con valor: 2381
```

```plain
base-files 14-ok3: hay ./lib? True | hay ./bin? True  (DIRECTORIOS REALES)
  symlinks que trae: [os-release, GFDL, GPL, LGPL, FAQ]  <- y nada mas
usrmerge presente | usr-is-merged presente
```

```plain
rama android16-6.12 -> listado de android/: 404
rama android15-6.6  -> 200: abi_gki_aarch64.stg + 38 listas por vendor
```

```plain
Suite: nile | Version: 2.0        Yangtze V1.0 (1.0)      Huanghe V3.0
```

## 4. Lo que este turno NO hizo

**Cero compilación, cero QEMU, cero kernel.** Todo es lectura verificada. F-002 no
se relanzó y F-004 no se corrió.

## 5. Defectos propios acumulados de la jornada

| # | Defecto | Clase |
|---|---|---|
| 1 | "la fecha es el 28" desde un extracto de buscador | afirmar sin fuente primaria |
| 2 | "el Embedded sigue siendo Beta" | ídem |
| 3 | `CONFIG_BRIDE` por `CONFIG_BRIDGE` | símbolo mal tipeado da ausente |
| 4 | `rm -rf` del directorio padre | scripting |
| 5 | comilla que se come el `SUITE` en `su -c` | scripting |
| 6 | **`yangtze (2.0)`** | afirmar sin fuente primaria (tercera vez) |
| 7 | **vender el `p_align 65536` como hallazgo** cuando es el default del linker | interpretar sin conocer el default |
| 8 | mezclar los rojos de `lxc-checkconfig` con los de SIAO | E-01, sujetos distintos |

**Y el patrón de los cuatro ENOENT tiene ahora causa medida y no es sólo mía:**
`base-files` de openKylin no trae los symlinks de merged-usr que su propio
`PT_INTERP` necesita. Sigue siendo mi trabajo haberlo diagnosticado en el cuarto
intento y no en el primero.

## 6. Contrato de cierre

- **Archivos commiteados:** `docs/adr/2026-09-05-03-resolucion-segunda-auditoria.md`,
  este archivo, `docs/agents/CONTEXTO-SIAO.md`
- **Repo:** <https://github.com/gatehot59-star/siao>

--- METODO PROMETEO ---
**Máquina:** `brain-env` por el gateway para todas las lecturas, más búsqueda web
contra fuente primaria. **Cero cómputo de compilación.**
**Artefacto 2 (ClickUp):** Doc del turno con el marcador.
