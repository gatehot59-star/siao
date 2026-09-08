import urllib.request, urllib.error
# Sin Authorization: mide lo que puede bajar FABLE desde abacus.ai.
RAW = 'https://raw.githubusercontent.com/gatehot59-star/siao/main/'
H = {'User-Agent': 'fable-probe'}
paths = [
 'AGENTS.md',
 'docs/agents/MAPA-DE-LA-EVIDENCIA.md',
 'docs/agents/CONTEXTO-SIAO.md',
 'docs/agents/briefings/2026-09-08-BRIEFING-FABLE-51-para-disenar-F-001-S2.md',
 'docs/adr/2026-09-08-07-ADR-007-resolucion-de-la-auditoria-de-FABLE-51.md',
 'mediciones/f-001-s1/f001s1-aarch64.json',
 'mediciones/f-001-s1/f001s1-aarch64-boot.txt',
 'mediciones/f-002/F-002-v9.md',
 'mediciones/f-004d-61/F-004d-61-VEREDICTO.txt',
 'mediciones/f-004d-61/v3-ocho.json',
 'tools/f001s1_arnes.py',
 'tools/f004d61_build.py',
 'mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md',
]
print('=== RAW ANONIMO (lo que FABLE puede bajar con un GET) ===')
ok = 0
for p in paths:
    try:
        r = urllib.request.urlopen(urllib.request.Request(RAW + p, headers=H), timeout=30)
        n = len(r.read()); print('  rc=%-4s %8d B  %s' % (r.status, n, p)); ok += 1
    except urllib.error.HTTPError as e:
        print('  rc=%-4s        0 B  %s' % (e.code, p))
    except Exception as e:
        print('  %-12s      %s' % (type(e).__name__, p))
print('  --> %d/%d bajables' % (ok, len(paths)))
print()
print('=== CONTROL NEGATIVO 1: ruta inexistente en el MISMO repo publico ===')
try:
    urllib.request.urlopen(urllib.request.Request(RAW + 'NO-EXISTE-ESTE-ARCHIVO.md', headers=H), timeout=30)
    print('  rc=200  <-- LA SONDA NO DISCRIMINA')
except urllib.error.HTTPError as e:
    print('  rc=%s  ruta inexistente -> la sonda discrimina por ARCHIVO' % e.code)
print()
print('=== CONTROL NEGATIVO 2: repo PRIVADO por raw ===')
try:
    urllib.request.urlopen(urllib.request.Request('https://raw.githubusercontent.com/gatehot59-star/mudh-mobile/main/AGENTS.md', headers=H), timeout=30)
    print('  rc=200  <-- LA SONDA NO DISCRIMINA')
except urllib.error.HTTPError as e:
    print('  rc=%s  mudh-mobile privado -> la sonda discrimina por REPO' % e.code)
