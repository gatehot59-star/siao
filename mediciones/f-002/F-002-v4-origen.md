# F-002 v4 - auditoria de ORIGEN del rootfs

**Fecha (UTC):** 2026-09-06T00:42:42Z
**Maquina:** `{"arch": "aarch64", "nproc": 2, "kernel": "6.17.0-1022-azure", "runner_arch": "ARM64", "run_id": "34001984348"}`

**Veredicto:** **NO MEDIDO**

los controles de instrumento no pasaron: el conteo no es confiable

| Metrica | Valor |
|---|---|
| paquetes instalados | 175 |
| SOLO de -proposed | **57** |
| KB instalados de -proposed | 104952 |
| identicos en main y proposed | 89 |
| solo en main | 18 |
| en ningun indice | 11 |
| rootfs | 357535564 B |

## Los paquetes que vienen SOLO de -proposed

| paquete | version | tamano | en main |
|---|---|---|---|
| info | 7.2-ok1 | 804 KB | main: 7.1-ok1 |
| init-system-helpers | 1.66-ok1 | 127 KB | main: 1.57-ok2 |
| install-info | 7.2-ok1 | 504 KB | main: 7.1-ok1 |
| less | 668-ok1 | 500 KB | main: 590-ok2 |
| libbpf1 | 1:1.6.3-ok1 | 618 KB | main: 1:1.3.0-ok2 |
| libbsd0 | 0.12.2-2build2ok1 | 181 KB | main: 0.11.7-4ok1 |
| libcap-ng0 | 0.8.5-4ok3 | 149 KB | main: 0.8.4-ok4 |
| libcap2 | 1:2.75-10ok2 | 156 KB | main: 1:2.69-1ok3 |
| libcap2-bin | 1:2.75-10ok2 | 299 KB | main: 1:2.69-1ok3 |
| libcrypt1 | 1:4.5.1-ok1 | 417 KB | main: 1:4.4.36-ok2 |
| libedit2 | 3.1-20251016-ok1 | 305 KB | main: 3.1-20230828-ok1 |
| libgcrypt20 | 1.12.1-ok1 | 2116 KB | main: 1.10.3-ok2 |
| libgpg-error0 | 1.59-ok1 | 302 KB | main: 1.47-ok1 |
| libidn2-0 | 2.3.8-4ok4 | 506 KB | main: 2.3.7-ok2 |
| liblz4-1 | 1.10.0-ok1 | 152 KB | main: 1.9.4-1ok1 |
| liblzma5 | 5.8.2-ok1 | 579 KB | main: 5.4.5-ok3 |
| libncursesw6 | 6.6+20251231-ok1 | 635 KB | main: 6.4+20240113-1ok1 |
| libnftables1 | 1.1.6-ok1 | 1300 KB | main: 1.0.9-ok1 |
| libnftnl11 | 1.3.1-ok1 | 302 KB | main: 1.2.6-ok3 |
| libpam-modules | 1.7.0-ok2 | 3226 KB | main: 1.5.3-ok8 |
| libpam-modules-bin | 1.7.0-ok2 | 569 KB | main: 1.5.3-ok8 |
| libpam-systemd | 259.5-ok1.2 | 5562 KB | main: 255.2-ok2.8 |
| libpam0g | 1.7.0-ok2 | 353 KB | main: 1.5.3-ok8 |
| libpcre2-8-0 | 10.46-1ok2 | 859 KB | main: 10.42-4ok2 |
| libpipeline1 | 1.5.8-ok1 | 151 KB | main: 1.5.7-ok1 |
| libseccomp2 | 2.6.0-ok1 | 219 KB | main: 2.5.5-1ok1.2 |
| libselinux1 | 3.9-ok3 | 295 KB | main: 3.5-ok2 |
| libsemanage2 | 3.9-ok2 | 420 KB | main: 3.5-ok1 |
| libsepol2 | 3.9-ok1 | 1119 KB | main: 3.5-ok1 |
| libssl3t64 | 3.5.5-ok6 | 9366 KB | main: 3.2.1-ok5 |
| libsystemd-shared | 259.5-ok1.2 | 10160 KB | main: 255.2-ok2.8 |
| libsystemd0 | 259.5-ok1.2 | 2830 KB | main: 255.2-ok2.8 |
| libtinfo6 | 6.6+20251231-ok1 | 674 KB | main: 6.4+20240113-1ok1 |
| libtirpc3t64 | 1.3.7-ok1 | 301 KB | main: 1.3.4+ds-ok1 |
| libudev1 | 259.5-ok1.2 | 1637 KB | main: 255.2-ok2.8 |
| libunistring5 | 1.3-2ok1 | 2258 KB | main: 1.1-ok1 |
| libxxhash0 | 0.8.3-ok1 | 85 KB | main: 0.8.2-ok1 |
| libzstd1 | 1.5.7+dfsg-ok1 | 1495 KB | main: 1.5.5-ok3 |
| login.defs | 1:4.17.4-ok1 | 93 KB | main: no esta en main |
| logrotate | 3.22.0-ok2 | 180 KB | main: 3.21.0-ok2.1 |
| man-db | 2.13.1-ok1 | 3543 KB | main: 2.12.0-ok1 |
| mawk | 1.3.4.20260129-ok1 | 365 KB | main: 1.3.4.20240123-ok1 |
| nano | 8.7.1-ok1 | 2974 KB | main: 7.2-ok1 |
| ncurses-bin | 6.6+20251231-ok1 | 984 KB | main: 6.4+20240113-1ok1 |
| nftables | 1.1.6-ok1 | 225 KB | main: 1.0.9-ok1 |
| openssl-provider-legacy | 3.5.5-ok6 | 471 KB | main: no esta en main |
| passwd | 1:4.17.4-ok1 | 5374 KB | main: 1:4.14.3-ok3.5 |
| rsyslog | 8.2512.0-ok3 | 3540 KB | main: 8.2312.0-ok2.1 |
| sed | 4.9-2ok2 | 1016 KB | main: 4.9-2ok1 |
| systemd | 259.5-ok1.2 | 15737 KB | main: 255.2-ok2.8 |
| systemd-resolved | 259.5-ok1.2 | 1112 KB | main: 255.2-ok2.8 |
| systemd-sysv | 259.5-ok1.2 | 42 KB | main: 255.2-ok2.8 |
| sysvinit-utils | 3.15-ok1 | 190 KB | main: 3.08-ok1 |
| tar | 1.35+dfsg-ok3 | 3068 KB | main: 1.35+dfsg-ok1 |
| tzdata | 2026a-ok2 | 1362 KB | main: 2024a-ok2 |
| udev | 259.5-ok1.2 | 11023 KB | main: 255.2-ok2.8 |
| vim-tiny | 2:9.1.2141-ok3 | 2122 KB | main: 2:9.1.0016-ok3 |

## Controles de instrumento

```json
{
  "C1_positivo_libdevmapper_de_proposed": false,
  "C2_negativo_bash_no_de_proposed": true,
  "C3_cruzado_solo_main": {
    "paquetes": 60,
    "atribuidos_a_proposed": 1,
    "discrimina": false,
    "lista": [
      [
        "init-system-helpers",
        "1.66-ok1"
      ]
    ]
  },
  "instrumento_validado": false
}
```

## Declarado antes de correr

El criterio (b) NO es binario y este script NO dice 'aprobado'. Reporta el numero, la lista completa y el tamano. Cuantos paquetes sin QA son tolerables en la base de un producto es decision de Abraham.

NO MEDIDO: nada

## Salida cruda, verbatim

```plain
== F-002 v4: auditoria de origen ==
maquina: {"arch": "aarch64", "nproc": 2, "kernel": "6.17.0-1022-azure", "runner_arch": "ARM64", "run_id": "34001984348"}
DECLARADO ANTES DE CORRER: El criterio (b) NO es binario y este script NO dice 'aprobado'. Reporta el numero, la lista completa y el tamano. Cuantos paquetes sin QA son tolerables en la base de un producto es decision de Abraham.
indices oficiales leidos: main=11837 paquetes | proposed=11370

==============================================================================
>>> construyendo SUJETO main+proposed
    fuente: deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe main
    fuente: deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe-proposed main
$ bash -c rm -rf /tmp/f002v4/sujeto && mkdir -p /tmp/f002v4/sujeto
$ mmdebstrap --mode=root --variant=important --architectures=arm64 --include=systemd,systemd-sysv,dbus,udev,iproute2,libpam-systemd --aptopt=Acquire::AllowInsecureRepositories "true" --aptopt=APT::Get::AllowUnauthenticated "true" --setup-hook=set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; ln -sfn "usr/$d" "$1/$d"; done; mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64" --skip=cleanup/apt/lists --skip=cleanup/apt/cache --verbose huanghe /tmp/f002v4/sujeto deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe main deb [trusted=yes] https://mirrors.dotsrc.org/mir
  mmdebstrap rc=0
  MM | Setting up systemd (259.5-ok1.2) ...
  systemd presente: True | rc: 0

--- AUDITORIA DE ORIGEN: main+proposed ---
$ bash -c dpkg-query --admindir=/tmp/f002v4/sujeto/var/lib/dpkg -W -f '${Package} ${Version} ${Installed-Size}\n' 2>/dev/null
  paquetes instalados: 175
  SOLO en -proposed (version exacta): 57
      info                               7.2-ok1                   804 KB   main: 7.1-ok1
      init-system-helpers                1.66-ok1                  127 KB   main: 1.57-ok2
      install-info                       7.2-ok1                   504 KB   main: 7.1-ok1
      less                               668-ok1                   500 KB   main: 590-ok2
      libbpf1                            1:1.6.3-ok1               618 KB   main: 1:1.3.0-ok2
      libbsd0                            0.12.2-2build2ok1         181 KB   main: 0.11.7-4ok1
      libcap-ng0                         0.8.5-4ok3                149 KB   main: 0.8.4-ok4
      libcap2                            1:2.75-10ok2              156 KB   main: 1:2.69-1ok3
      libcap2-bin                        1:2.75-10ok2              299 KB   main: 1:2.69-1ok3
      libcrypt1                          1:4.5.1-ok1               417 KB   main: 1:4.4.36-ok2
      libedit2                           3.1-20251016-ok1          305 KB   main: 3.1-20230828-ok1
      libgcrypt20                        1.12.1-ok1               2116 KB   main: 1.10.3-ok2
      libgpg-error0                      1.59-ok1                  302 KB   main: 1.47-ok1
      libidn2-0                          2.3.8-4ok4                506 KB   main: 2.3.7-ok2
      liblz4-1                           1.10.0-ok1                152 KB   main: 1.9.4-1ok1
      liblzma5                           5.8.2-ok1                 579 KB   main: 5.4.5-ok3
      libncursesw6                       6.6+20251231-ok1          635 KB   main: 6.4+20240113-1ok1
      libnftables1                       1.1.6-ok1                1300 KB   main: 1.0.9-ok1
      libnftnl11                         1.3.1-ok1                 302 KB   main: 1.2.6-ok3
      libpam-modules                     1.7.0-ok2                3226 KB   main: 1.5.3-ok8
      libpam-modules-bin                 1.7.0-ok2                 569 KB   main: 1.5.3-ok8
      libpam-systemd                     259.5-ok1.2              5562 KB   main: 255.2-ok2.8
      libpam0g                           1.7.0-ok2                 353 KB   main: 1.5.3-ok8
      libpcre2-8-0                       10.46-1ok2                859 KB   main: 10.42-4ok2
      libpipeline1                       1.5.8-ok1                 151 KB   main: 1.5.7-ok1
      libseccomp2                        2.6.0-ok1                 219 KB   main: 2.5.5-1ok1.2
      libselinux1                        3.9-ok3                   295 KB   main: 3.5-ok2
      libsemanage2                       3.9-ok2                   420 KB   main: 3.5-ok1
      libsepol2                          3.9-ok1                  1119 KB   main: 3.5-ok1
      libssl3t64                         3.5.5-ok6                9366 KB   main: 3.2.1-ok5
      libsystemd-shared                  259.5-ok1.2             10160 KB   main: 255.2-ok2.8
      libsystemd0                        259.5-ok1.2              2830 KB   main: 255.2-ok2.8
      libtinfo6                          6.6+20251231-ok1          674 KB   main: 6.4+20240113-1ok1
      libtirpc3t64                       1.3.7-ok1                 301 KB   main: 1.3.4+ds-ok1
      libudev1                           259.5-ok1.2              1637 KB   main: 255.2-ok2.8
      libunistring5                      1.3-2ok1                 2258 KB   main: 1.1-ok1
      libxxhash0                         0.8.3-ok1                  85 KB   main: 0.8.2-ok1
      libzstd1                           1.5.7+dfsg-ok1           1495 KB   main: 1.5.5-ok3
      login.defs                         1:4.17.4-ok1               93 KB   main: no esta en main
      logrotate                          3.22.0-ok2                180 KB   main: 3.21.0-ok2.1
      man-db                             2.13.1-ok1               3543 KB   main: 2.12.0-ok1
      mawk                               1.3.4.20260129-ok1        365 KB   main: 1.3.4.20240123-ok1
      nano                               8.7.1-ok1                2974 KB   main: 7.2-ok1
      ncurses-bin                        6.6+20251231-ok1          984 KB   main: 6.4+20240113-1ok1
      nftables                           1.1.6-ok1                 225 KB   main: 1.0.9-ok1
      openssl-provider-legacy            3.5.5-ok6                 471 KB   main: no esta en main
      passwd                             1:4.17.4-ok1             5374 KB   main: 1:4.14.3-ok3.5
      rsyslog                            8.2512.0-ok3             3540 KB   main: 8.2312.0-ok2.1
      sed                                4.9-2ok2                 1016 KB   main: 4.9-2ok1
      systemd                            259.5-ok1.2             15737 KB   main: 255.2-ok2.8
      systemd-resolved                   259.5-ok1.2              1112 KB   main: 255.2-ok2.8
      systemd-sysv                       259.5-ok1.2                42 KB   main: 255.2-ok2.8
      sysvinit-utils                     3.15-ok1                  190 KB   main: 3.08-ok1
      tar                                1.35+dfsg-ok3            3068 KB   main: 1.35+dfsg-ok1
      tzdata                             2026a-ok2                1362 KB   main: 2024a-ok2
      udev                               259.5-ok1.2             11023 KB   main: 255.2-ok2.8
      vim-tiny                           2:9.1.2141-ok3           2122 KB   main: 2:9.1.0016-ok3
  identica en main y en proposed (indistinguible): 89
  solo en main: 18
  en NINGUN indice (version no publicada): 11
      bsdmainutils                       12.1.8-ok2
      dbus-session-bus-common            1.16.2-ok1
      dbus-system-bus-common             1.16.2-ok1
      libaudit-common                    1:4.1.2-ok1
      libpam-runtime                     1.7.0-ok2
      libsemanage-common                 3.9-ok2
      libtirpc-common                    1.3.7-ok1
      lsb-base                           11.6-ok1
      ncurses-base                       6.6+20251231-ok1
      readline-common                    8.3-4ok1
      vim-common                         2:9.1.2141-ok3
$ bash -c du -sb /tmp/f002v4/sujeto | cut -f1
  rootfs total: 357535564 B (0.333 GiB) | de -proposed: ~104952 KB instalados
  sources.list escrito en el chroot:
   | deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe main
   | deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe-proposed main
$ bash -c chroot /tmp/f002v4/sujeto apt-get update -o Acquire::AllowInsecureRepositories=true -o APT::Get::AllowUnauthenticated=true -qq 2>&1 | tail -5
  apt-get update en el chroot rc=0
   | W: Failed to fetch https://mirrors.dotsrc.org/mirrors/pub/openkylin/dists/huanghe/InRelease  Temporary failure resolving 'mirrors.dotsrc.org'
   | W: Failed to fetch https://mirrors.dotsrc.org/mirrors/pub/openkylin/dists/huanghe-proposed/InRelease  Temporary failure resolving 'mirrors.dotsrc.org'
   | W: Failed to fetch http://ppa.build.openkylin.top/kylinsoft/anything2.0/openkylin/dists/nile/InRelease  Temporary failure resolving 'ppa.build.openkylin.top'
   | W: Some index files failed to download. They have been ignored, or old ones used instead.
$ bash -c chroot /tmp/f002v4/sujeto apt-cache policy 2>&1
  apt-cache policy (verbatim):
   POLICY | Package files:
   POLICY |  100 /var/lib/dpkg/status
   POLICY |      release a=now
   POLICY |  500 https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe-proposed/main arm64 Packages
   POLICY |      release v=3.0,o=openKylin,a=huanghe-proposed,n=huanghe,l=openKylin,c=main,b=arm64
   POLICY |      origin mirrors.dotsrc.org
   POLICY |  500 https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe/main arm64 Packages
   POLICY |      release v=3.0,o=openKylin,a=huanghe,n=huanghe,l=openKylin,c=main,b=arm64
   POLICY |      origin mirrors.dotsrc.org
   POLICY | Pinned packages:

C1 POSITIVO de instrumento: libdevmapper1.02.1 aparece como de -proposed? False
C2 NEGATIVO de instrumento: bash NO aparece como de -proposed? True

==============================================================================
>>> construyendo C3 solo-main (se espera que NO instale systemd)
    fuente: deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe main
$ bash -c rm -rf /tmp/f002v4/solo-main && mkdir -p /tmp/f002v4/solo-main
$ mmdebstrap --mode=root --variant=important --architectures=arm64 --include=systemd,systemd-sysv,dbus,udev,iproute2,libpam-systemd --aptopt=Acquire::AllowInsecureRepositories "true" --aptopt=APT::Get::AllowUnauthenticated "true" --setup-hook=set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; ln -sfn "usr/$d" "$1/$d"; done; mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64" --skip=cleanup/apt/lists --skip=cleanup/apt/cache --verbose huanghe /tmp/f002v4/solo-main deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe main
  mmdebstrap rc=25
  MM | The following packages have unmet dependencies:
  MM | E: Unable to correct problems, you have held broken packages.
  MM | E: setup failed: E: apt-get -o Dir::Bin::dpkg=env -o DPkg::Options::=--unset=TMPDIR -o DPkg::Options::=dpkg --yes install -oAPT::Status-Fd=<$fd> -oDpkg::Use-Pty=false systemd systemd-sysv dbus udev iproute2 libpam-systemd ?narrow(?or(?archive(^huanghe$),?coden
  MM | W: hooklistener errored out: E: received eof on socket
  MM | I: main() received signal PIPE: waiting for setup...
  MM | E: mmdebstrap failed to run
  systemd presente: False | rc: 25
$ bash -c dpkg-query --admindir=/tmp/f002v4/solo-main/var/lib/dpkg -W -f '${Package} ${Version} ${Installed-Size}\n' 2>/dev/null
  C3: paquetes extraidos aunque el build fallara: 60
  C3: paquetes atribuidos a -proposed en un rootfs SIN proposed: 1
      OJO: ('init-system-helpers', '1.66-ok1')
  C3: ROTO: el auditor ve proposed donde no hay proposed

VEREDICTO: NO MEDIDO - instrumento no validado
```
