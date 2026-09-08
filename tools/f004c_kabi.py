#!/usr/bin/env python3
"""
F-004c - El fragmento SIN CGROUP_PIDS es KMI-safe?

POR QUE ES UN WRAPPER Y NO UN INSTRUMENTO NUEVO, y esto es deliberado:
  el arnes de F-004b ya esta medido y corrido (dos brazos success, run 34030115053).
  Si escribo un instrumento nuevo, la diferencia observada podria ser del script y
  no del sujeto. Reusar el MISMO codigo deja UNA sola variable en juego:
  CONFIG_CGROUP_PIDS afuera del fragmento. El parche KABI queda IGUAL.

PREDICCION DECLARADA ANTES DE CORRER (falsable, firmada en el chat):
  el reporte de stgdiff --ignore linux_symbol_crc queda con SOLO las cinco lineas
  de la union de task_struct mas los simbolos aditivos, y CERO 'byte size changed'
  y CERO 'offset changed' en TODO el archivo. Si eso pasa, el fragmento de SIAO es
  KMI-safe y un DLKM binario de vendor sigue cargando.

DE DONDE SALE, medido en F-004b y no supuesto:
  con el parche KABI puesto, lo unico que quedaba en el reporte eran TRES structs
  de cgroup:
     struct cgroup      byte size 1920 -> 1984, subsys[7] -> subsys[8], 24 offsets
     struct cgroup_root byte size 6272 -> 6336
     struct css_set     byte size  424 ->  448, subsys[7] -> subsys[8], 22 offsets
  CGROUP_PIDS agrega un subsistema, asi que CGROUP_SUBSYS_COUNT pasa de 7 a 8 y
  los arrays crecen. Eso NO se arregla con padding: no agrega un miembro, cambia
  la dimension de un array derivada de un enum.

Y LO QUE ESTE FALSADOR TAMBIEN MIDE, aunque no sea su titulo:
  si al sacar CGROUP_PIDS el reporte queda limpio, queda AISLADO que CGROUP_PIDS
  era la causa de los tres structs. Eso convierte en MEDIDO el 'NO MEDIDO' que
  declare en F-004b, y es justo la suposicion que me hizo perder la prediccion
  anterior: ahi supuse cual era el rompedor sin aislarlo. Esta vez se aisla.

EL COSTO DE PRODUCTO, declarado: sin CGROUP_PIDS no se puede limitar la cantidad
de procesos del contenedor de apps. Es endurecimiento, no arranque, y Lindroid
(205 estrellas, en produccion) NO lo pide en su lista de configs.

MODO DE USO:  f004c_kabi.py build baseline|kabi
"""
import os
import sys

import f004b_kabi as m

# LA UNICA VARIABLE: el mismo fragmento del ADR-003, sin CONFIG_CGROUP_PIDS.
SIN = "CONFIG_CGROUP_PIDS=y"
if SIN not in m.FRAGMENTO:
    raise SystemExit("ABORTO: el fragmento de F-004b no tiene %s, algo cambio" % SIN)
m.FRAGMENTO = m.FRAGMENTO.replace(SIN + "\n", "")
if SIN in m.FRAGMENTO:
    raise SystemExit("ABORTO: no pude sacar %s del fragmento" % SIN)


def main():
    cual = sys.argv[2] if len(sys.argv) > 2 else "kabi"
    m.say("== F-004c: mismo arnes que F-004b, UNA variable menos ==")
    m.say("  instrumento reusado: tools/f004b_kabi.py (sin tocar)")
    m.say("  variable retirada:   %s" % SIN)
    m.say("  parche KABI:         IGUAL que en F-004b")
    m.say("  PREDICCION: reporte sin CRC con SOLO la union de task_struct y los")
    m.say("  simbolos aditivos; CERO 'byte size changed' y CERO 'offset changed'.")
    m.say("  --- el fragmento de este falsador, verbatim ---")
    for l in m.FRAGMENTO.strip().splitlines():
        m.say("   |", l)
    n = len([l for l in m.FRAGMENTO.splitlines() if l.startswith("CONFIG_")])
    m.say("  simbolos en el fragmento: %d (eran 10 en F-004b)" % n)
    if n != 9:
        m.say("  ABORTO: esperaba 9 simbolos y hay %d" % n)
        return 3
    return m.build(cual)


if __name__ == "__main__":
    sys.exit(main())
