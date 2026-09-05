# AGENTS.md · SIAO

Antes de escribir una linea en este repo:

1. **Leer `docs/agents/CONTEXTO-SIAO.md`.** Responder de memoria sobre este
   proyecto es un error de metodo, no un atajo.
2. **Leer el ultimo archivo de `docs/agents/respuestas/`** para saber que se
   hizo recien.
3. **Antes de declarar un limite del entorno, abrir el inventario canonico:**
   <https://github.com/gatehot59-star/mudh-mobile/blob/main/00-ENTORNOS-Y-CAPACIDADES.md>
   Son tres maquinas (`brain-env`, GitHub Actions x64/arm64, Kaggle), no una, y
   el inventario **se re-mide, no se recuerda**.

## Nota de divergencia, declarada a proposito

El inventario de entornos afirma ser **identico en los cuatro repos** del
ecosistema. **Este es el quinto y NO tiene su copia**: se linkea la del repo
`mudh-mobile` en vez de duplicarla. Queda dicho aca para que nadie lea la
afirmacion "identico en los cuatro" como si incluyera a SIAO. Normalizar a
cinco copias o centralizarla en un solo lugar es una decision pendiente de
Abraham, no un olvido.

## Reglas de entrega en este repo

- El **codigo** va en rama `titan/<tema-corto>`, nunca directo a `main`.
- La **bitacora y la evidencia** SI van directo a `main`: son append-only, no
  compilan y nadie clona de ellas.
- **Ningun script se commitea sin haberlo ejecutado**, y la salida cruda se
  commitea verbatim: un "lo corri y da verde" sin salida es un no-recibo.
- Tres estados posibles, siempre: **bien, mal y NO MEDIDO**.
- Cada entrega sustancial produce **dos** artefactos: el archivo en
  `docs/agents/respuestas/` y un Doc de ClickUp, y el cierre linkea los dos.
- Nada de binarios commiteados: se compila desde fuente.
