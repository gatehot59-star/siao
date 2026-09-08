# MANIFIESTO de binarios derivados NO commiteados

Los `.stg` son **binarios derivados**: los produce `stg` desde el `vmlinux`
de cada build. `AGENTS.md` prohibe commitear binarios, asi que **no entran a
`main`**: se referencian aca por sha256, tamano, rama y SHA de rama.

**Y la cadena ya estaba cortada mas arriba:** el `vmlinux` del que salen pesa
354.673.168 B y nunca se commiteo en ninguna rama. Asi que recomputar un
veredicto desde cero exige rebuildear el kernel, no tener el `.stg`. Lo que
este manifiesto conserva es la **identidad** del intermedio, para poder decir si
un `.stg` futuro es o no el mismo que produjo el veredicto de entonces.

| Archivo | Bytes | sha256 | Rama | SHA de rama |
|---|---|---|---|---|
| `mediciones/f-004-v3/baseline.stg` | 11317742 | `440f48ed6759f80e7f97eabcc09efc6ff90565889103c380805d0fcfd82d34b4` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004-v3/siao.stg` | 11319347 | `7d91aa2b9f9dc46224958b238be943b79a01803375d20bbf3b71cdcbae0118fe` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004b/baseline.stg` | 11317742 | `440f48ed6759f80e7f97eabcc09efc6ff90565889103c380805d0fcfd82d34b4` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004b/kabi.stg` | 11319678 | `ce3743b1f3b4cc0b26ffd8f076e46298fe1887e6c7ecf1612017976d2bb3cd7c` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004c/kabi.stg` | 11319319 | `c66fd3fcb6c6f8078ffa35ef729e2b7c6ab67bc2d0ca8affda39cc38365a6ec8` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004d-61/baseline-android14-6.1.stg` | 10699061 | `c91ed3a1963a261b290c624d251f081b7ecd698cb06013d5012af8ae69ee1e32` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004d-61/ocho-android14-6.1.stg` | 10699333 | `047141d8822061e9a61a3865f236dae0473bf8269d14cdfa30b9d77dee9e4464` | `titan/f-004-kmi` | `2b877236` |
| `mediciones/f-004d/ocho.stg` | 11318014 | `448b83907b14639b4d538f5cf7cc625185f8a327d92c019ceceff98e56a7ffe1` | `titan/f-004-kmi` | `2b877236` |

## Como recuperar uno

```
git fetch origin <rama>
git show origin/<rama>:<ruta> > <destino>
sha256sum <destino>   # tiene que coincidir con la tabla
```

**Si la rama se borra, estos ocho archivos se pierden y esta tabla solo va a
servir para saber QUE se perdio.** Es la deuda de durabilidad que el mapa
declara y que este manifiesto NO cierra.
