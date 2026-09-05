# CONTEXTO-SIAO · el contexto vivo del proyecto

**Creado:** 2026-09-05
**Ultima actualizacion:** 2026-09-05

Este archivo es lo primero que se lee antes de trabajar en SIAO, y se actualiza
en el mismo turno en que algo cambia.

---

## 1. Que es SIAO

**NO DECLARADO.** El pedido que abrio el repo fue literal: *"nuevo proyecto,
genera otro repositorio en git, se llamara SIAO"*. No hubo definicion de
alcance, ni de producto, ni de stack, y **no se inventa ninguna**.

Lo unico que consta fuera de este repo es que SIAO es una de las tres lineas de
producto del ecosistema, junto a MUDH y AURA: son **el medio** (existen para
generar ingresos y poder cederse a un aprendiz), no el fin.

**Lo que falta para cerrar esta seccion, en una linea de Abraham:** que hace
SIAO, para quien, y que significa la sigla.

## 2. Decisiones tomadas

| Fecha | Decision | Por que |
|---|---|---|
| 2026-09-05 | El repo se llama `siao` en minusculas | Convencion de los otros cinco repos de la cuenta (`mudh-mobile`, `dualbrain`, `icca-engine`, `corpus-legal-tarija`, `drosophila-fep-connectome`). El proyecto se sigue llamando SIAO |
| 2026-09-05 | Nace **privado** | Es la direccion reversible: pasar a publico es un toggle, despublicar lo que ya se publico no |
| 2026-09-05 | El inventario de entornos **no se copia**, se linkea | Copiar 7.000 palabras a un quinto repo multiplica las copias que hay que mantener sincronizadas. La divergencia queda declarada en `AGENTS.md` |

## 3. Estado medido

- **Repo creado:** si, `gatehot59-star/siao`, id `1358498188`.
- **Codigo:** cero archivos de codigo. No hay stack elegido.
- **CI:** no hay `.github/workflows/`. **Ningun workflow corrio nunca aca.**
- **Nada de este repo se ejecuto en ninguna de las tres maquinas.** La creacion
  y este commit son escrituras por la API de GitHub, sin computo.

## 4. NO MEDIDO

- Todo lo tecnico: no hay nada que medir todavia.
- Si SIAO comparte codigo, corpus o infraestructura con MUDH, AURA o
  `icca-engine`. Se pregunta, no se supone.
- Si conviene privado o publico: depende de si SIAO va a usar Actions, y eso
  depende del alcance, que esta sin declarar.

## 5. Cementerio de hipotesis

Vacio. Cuando una hipotesis de este proyecto muera medida, va aca con su
numero y la salida que la mato.
