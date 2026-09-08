# AGENTS.md · SIAO

Antes de escribir una linea en este repo:

1. **Leer `docs/agents/CONTEXTO-SIAO.md`.** Responder de memoria sobre este
   proyecto es un error de metodo, no un atajo.
2. **Leer `docs/agents/MAPA-DE-LA-EVIDENCIA.md`.** Dice en que RAMA, en que SHA
   y en que ARCHIVO exacto vive el veredicto de cada falsador. Hace falta porque
   la evidencia cruda de F-001, F-002, F-004 y FALSADOR-001 **no esta en `main`**:
   vive en cuatro ramas `titan/*` que `main` no referencia. Sin ese mapa, leer
   `main` de punta a punta y con metodo lleva igual a una conclusion falsa, y ya
   paso: una auditoria externa declaro `NO MEDIDO` el hallazgo que ordena el
   proyecto entero (F-004d@6.1) cuando estaba VERDE ese mismo dia.
   **Desempate:** si el mapa y el CONTEXTO se contradicen, gana el mapa, porque
   cada linea del mapa se verifica contra un SHA. Si el mapa y el repo se
   contradicen, gana el repo: el mapa tambien se escribe a mano.
3. **Leer el ultimo archivo de `docs/agents/respuestas/`** para saber que se
   hizo recien. **Ojo:** la numeracion colisiona (hay dos `2026-09-06-01-`, dos
   `-02-`, dos `-03-` y dos `-04-`), asi que el orden alfabetico NO reconstruye
   el orden temporal. Ordenar por fecha de commit, no por nombre.
4. **Antes de declarar un limite del entorno, abrir el inventario canonico:**
   <https://github.com/gatehot59-star/mudh-mobile/blob/main/00-ENTORNOS-Y-CAPACIDADES.md>
   Son tres maquinas (`brain-env`, GitHub Actions x64/arm64, Kaggle), no una, y
   el inventario **se re-mide, no se recuerda**.

## Como leer una rama sin clonarla

La API de GitHub acepta el nombre de rama en `ref`, asi que la evidencia de las
cuatro ramas es legible sin checkout. **Pero listar un directorio devuelve
nombres y tamaños, no contenido:** un `ls` de `mediciones/f-004d-61/` muestra 46
archivos y no dice que dice ninguno. El veredicto esta ADENTRO del archivo que se
llama `VEREDICTO`. Concluir un estado desde el listado es medir el sujeto
equivocado, y es exactamente como se produjo el error de arriba.

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
- **Si una medicion queda en una rama, su linea en el MAPA va a `main` en el
  mismo turno.** Es la regla que faltaba: sin ella la evidencia existe y nadie
  la encuentra, que para un auditor es indistinguible de que no exista.
- **Ningun script se commitea sin haberlo ejecutado**, y la salida cruda se
  commitea verbatim: un "lo corri y da verde" sin salida es un no-recibo.
- Tres estados posibles, siempre: **bien, mal y NO MEDIDO**.
- Cada entrega sustancial produce **dos** artefactos: el archivo en
  `docs/agents/respuestas/` y un Doc de ClickUp, y el cierre linkea los dos.
- Nada de binarios commiteados: se compila desde fuente.
