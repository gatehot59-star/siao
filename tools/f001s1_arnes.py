#!/usr/bin/env python3
"""
F-001-S1 paso 0: el ARNES de QEMU, medido antes de gastar un build de kernel.

DE DONDE SALE ESTE FALSADOR: del Doc de KVM que Abraham me paso, que mide tres
cosas que cambian el diseno de F-001-S1 y que yo NO habia medido:
     Actions x64   -> /dev/kvm USABLE con usermod -aG kvm (api 12, create_vm 4)
     Actions arm64 -> /dev/kvm NO EXISTE
     brain-env     -> /dev/kvm NO EXISTE

LA CONSECUENCIA QUE EL DOC NO SACA, y es la que me importa: el kernel de SIAO es
aarch64. KVM solo acelera cuando el HUESPED es de la MISMA ISA que el anfitrion.
En x64 hay KVM pero el huesped es arm64 -> no aplica. En arm64 el huesped si es de
la misma ISA pero NO HAY /dev/kvm. O sea que F-001-S1 va por TCG en las dos, y el
dato util del doc es el inverso del titular: sirve para NO perder tiempo buscando
aceleracion que para este caso no existe.

Y LA LECCION DE METODO, que aplico literal: el doc cuenta que un veredicto
'SIN_KVM' colapso tres estados (no existe / sin permiso / roto) y produjo una
conclusion falsa sobre una salida correcta. Aca el chequeo devuelve los TRES
estados separados, y ninguno se llama igual que otro.

DEFECTO MIO DEL PRIMER INTENTO (run de las 15:17 UTC, los DOS brazos):
     entradas del zip: ['boot-6.6.img']
  y mi filtro pedia n.endswith("boot.img"). 'boot-6.6.img' NO termina en
  'boot.img', asi que el arranque no se corrio y los dos brazos quedaron a mitad
  de camino, con rc=0 y sin veredicto. Es el patron del guard demasiado estrecho:
  no fallo, se salteo, y el exit code no lo delato. Ahora el filtro es .img y se
  imprime QUE entrada eligio.

QUE MIDE, en orden de lo que bloquea:
  1. /dev/kvm con sus tres estados, en la maquina donde corra.
  2. Si existe qemu-system-aarch64 y con que version.
  3. UN ARRANQUE REAL: baja el boot.img certificado de Google, le saca el Image,
     y lo arranca en QEMU SIN rootfs. Un kernel sano imprime su banner y despues
     entra en panico por 'No working init found'. Ese panico es el VERDE: prueba
     que el arnes ejecuta un kernel arm64 de verdad. Si no aparece el banner, el
     arnes esta roto y no tiene sentido compilar nada.

PREDICCION DECLARADA ANTES DE CORRER:
  el banner de Linux aparece y el kernel entra en panico por falta de init.
  O sea: arnes VERDE, y el unico rojo posible es de mi propio arnes.
"""
import json, os, re, shutil, struct, subprocess, sys, time, urllib.request, zipfile

OUT = os.environ.get("F001_OUT", "mediciones/f-001-s1")
WORK = os.environ.get("F001_WORK", "/tmp/f001s1")
log = []


def w(*a):
    s = " ".join(str(x) for x in a)
    log.append(s)
    print(s, flush=True)


def sh(cmd, t=1800, guardar=None):
    w("$", cmd[:280])
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "-c", "set -o pipefail; " + cmd],
                           capture_output=True, text=True, timeout=t)
        rc, o, e = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT tras %ss" % t
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:200]
    w("  rc=%d en %.1f s | out %d B | err %d B" % (rc, time.time() - t0, len(o), len(e)))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        open(guardar, "w").write("### comando\n%s\n\n### rc\n%d\n\n### stdout ENTERO\n%s\n\n"
                                 "### stderr ENTERO\n%s\n" % (cmd, rc, o, e))
        w("  guardado entero en", guardar.replace(OUT, "<out>"))
    return rc, o, e


def kvm_tres_estados():
    """El guard que el Doc de KVM ensena: tres estados, no uno."""
    p = "/dev/kvm"
    if not os.path.exists(p):
        return "NO_EXISTE", "el nodo no esta en el filesystem"
    try:
        fd = os.open(p, os.O_RDWR)
        os.close(fd)
        return "USABLE", "abre O_RDWR sin error"
    except PermissionError as e:
        return "SIN_PERMISO", "existe y NO abre: %s (esto NO es ausencia)" % e
    except Exception as e:
        return "EXISTE_PERO_ROTO", repr(e)[:120]


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    arch = os.uname().machine
    w("== F-001-S1 paso 0: el arnes de QEMU ==")
    w("  fecha UTC", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("  PREDICCION: aparece el banner de Linux y el kernel entra en panico por")
    w("  falta de init. Ese panico es el VERDE del arnes.")
    rc, o, _ = sh("uname -m; nproc; free -m | head -2; df -h / | tail -1")
    for l in o.splitlines():
        w("   |", l[:120])

    estado, razon = kvm_tres_estados()
    w("")
    w("  === /dev/kvm, con los TRES estados separados ===")
    w("  estado: %s" % estado)
    w("  razon : %s" % razon)
    w("  NOTA de diseno: el kernel de SIAO es aarch64 y KVM acelera solo si")
    w("  huesped y anfitrion comparten ISA.")
    if arch == "x86_64":
        w("  -> aca la ISA NO coincide (huesped arm64 sobre anfitrion x86_64):")
        w("     KVM es IRRELEVANTE para este falsador, aunque este USABLE.")
    else:
        w("  -> aca la ISA coincide, pero sin /dev/kvm tampoco hay aceleracion.")
    w("  CONCLUSION: F-001-S1 va por TCG (emulacion pura) en las dos maquinas.")

    w("")
    w("  === herramientas ===")
    for b in ("qemu-system-aarch64", "qemu-img", "unzip", "cpio", "zstd", "python3"):
        w("   %-22s %s" % (b, shutil.which(b) or "AUSENTE"))
    rc, o, _ = sh("qemu-system-aarch64 --version 2>&1 | head -2")
    for l in o.splitlines():
        w("   |", l[:120])

    w("")
    w("  === bajando el boot.img CERTIFICADO de Google y sacandole el Image ===")
    url = ("https://dl.google.com/android/gki/gki-certified-boot-android15-6.6"
           "-2025-01_r1.zip")
    z = WORK + "/gki.zip"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "siao-f001s1/1"})
        d = urllib.request.urlopen(req, timeout=600).read()
        open(z, "wb").write(d)
        w("  bajado %d B" % len(d))
    except Exception as e:
        w("  NO MEDIDO: no pude bajar el zip: %s" % repr(e)[:140])
        open(os.path.join(OUT, "f001s1-%s-bitacora.txt" % arch), "w").write("\n".join(log) + "\n")
        return

    zf = zipfile.ZipFile(z)
    nombres = zf.namelist()
    w("  entradas del zip: %s" % nombres)
    # FIX: el zip trae 'boot-6.6.img', no 'boot.img'. Filtro por .img y lo digo.
    cand = [n for n in nombres if n.endswith(".img")]
    if not cand:
        w("  ABORTO: no hay ninguna entrada .img en el zip")
        open(os.path.join(OUT, "f001s1-%s-bitacora.txt" % arch), "w").write("\n".join(log) + "\n")
        return
    elegida = cand[0]
    w("  entrada elegida: %s (de %d candidatas .img)" % (elegida, len(cand)))
    raw = zf.read(elegida)
    open(WORK + "/boot.img", "wb").write(raw)
    w("  boot.img: %d B | magic %r" % (len(raw), raw[:8]))
    hdr_v = struct.unpack("<I", raw[40:44])[0]
    ksz = struct.unpack("<I", raw[8:12])[0]
    w("  header_version=%d | kernel_size=%d" % (hdr_v, ksz))
    img = raw[4096:4096 + ksz]
    open(WORK + "/Image", "wb").write(img)
    w("  Image extraido: %d B | magic %r" % (len(img), img[:4]))
    k = WORK + "/Image"
    if img[:2] == b"\x1f\x8b":
        w("  el Image esta comprimido con gzip: lo descomprimo")
        rc, o, _ = sh("cd %s && gzip -dc Image > Image.raw && ls -la Image.raw" % WORK)
        for l in o.splitlines():
            w("   |", l[:120])
        if os.path.isfile(WORK + "/Image.raw"):
            k = WORK + "/Image.raw"

    w("")
    w("  === EL ARRANQUE: qemu-system-aarch64 SIN rootfs ===")
    w("  un kernel sano imprime su banner y despues entra en panico por")
    w("  'No working init found'. Ese panico ES el verde del arnes.")
    cmd = ("timeout 240 qemu-system-aarch64 -machine virt -cpu cortex-a57 "
           "-smp 2 -m 2048 -nographic -no-reboot "
           "-kernel %s -append 'console=ttyAMA0 panic=1 earlycon' 2>&1 | head -200" % k)
    rc, o, e = sh(cmd, 320, guardar=os.path.join(OUT, "f001s1-%s-boot.txt" % arch))
    todo = o + e
    m = re.search(r"Linux version ([^\s]+)", todo)
    hitos = {
        "banner_linux": bool(m),
        "version_leida": m.group(1) if m else None,
        "memoria_ok": "Memory:" in todo,
        "llego_a_init": ("No working init found" in todo
                         or "Kernel panic" in todo
                         or "Failed to execute" in todo),
        "bytes_de_salida": len(todo),
    }
    w("")
    w("  === HITOS DEL ARRANQUE ===")
    for kk, vv in hitos.items():
        w("   %-18s %s" % (kk, vv))
    w("  --- salida del kernel, primeras 45 lineas ---")
    for l in todo.splitlines()[:45]:
        w("   B|", l[:170])
    ver = ("ARNES VERDE: QEMU ejecuta un kernel arm64 REAL en esta maquina"
           if hitos["banner_linux"] else
           "ARNES ROJO o NO MEDIDO: no aparecio el banner de Linux")
    res = {"arch": arch, "kvm_estado": estado, "kvm_razon": razon,
           "qemu": shutil.which("qemu-system-aarch64"), "entrada_zip": elegida,
           "hitos": hitos, "rc_qemu": rc, "veredicto": ver,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(res, open(os.path.join(OUT, "f001s1-%s.json" % arch), "w"),
              indent=2, ensure_ascii=False)
    w("")
    w("  VEREDICTO: %s" % ver)
    open(os.path.join(OUT, "f001s1-%s-bitacora.txt" % arch), "w").write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
