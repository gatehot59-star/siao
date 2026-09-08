import urllib.request as u
import urllib.error

# SIN header Authorization: mide lo que ve un tercero, no lo que veo yo.
B = 'https://api.github.com/repos/gatehot59-star/siao'
H = {'Accept': 'application/vnd.github+json', 'User-Agent': 'anon-probe'}


def anon(path=''):
    try:
        r = u.urlopen(urllib.request.Request(B + path, headers=H), timeout=30)
        return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception as e:
        return type(e).__name__, 0


import urllib.request
print('=== LO QUE VE UN TERCERO SIN CREDENCIAL ===')
for p, d in [('', 'metadata del repo'),
             ('/contents/docs/agents/MAPA-DE-LA-EVIDENCIA.md', 'el mapa'),
             ('/contents/tools', 'los 26 instrumentos'),
             ('/contents/mediciones/f-004d-61/v3-ocho.json', 'el JSON de los 8 simbolos'),
             ('/contents/docs/campo/workflows-de-las-ramas', 'los 15 workflows'),
             ('/pulls?state=all', 'los PRs')]:
    st, n = anon(p)
    print('  rc=%-5s %8s B  %s' % (st, n, d))

print()
print('=== CONTROL NEGATIVO: un repo que SIGUE privado ===')
B = 'https://api.github.com/repos/gatehot59-star/mudh-mobile'
st, n = anon('')
print('  rc=%-5s  mudh-mobile (privado) -> si da 404, la sonda discrimina' % st)
