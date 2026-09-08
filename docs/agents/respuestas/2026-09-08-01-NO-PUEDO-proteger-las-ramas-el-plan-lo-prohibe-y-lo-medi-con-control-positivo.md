# NO puedo proteger las ramas, y el límite no es mío ni del token: es del plan

**Fecha:** 2026-09-08 07:30 (America/Buenos_Aires) · **Autor:** BRAIN  
**Orden de Abraham:** proteger `main` y las cuatro ramas.  
**Resultado: NO SE PUDO.** Y está medido con control positivo, no supuesto.

---

## 1 · Las DOS vías, las dos medidas

No me quedé en el primer obstáculo: probé los **dos** mecanismos que GitHub ofrece, que son endpoints distintos.

**Vía 1 · Ruleset** (el moderno, una regla para las cinco ramas):

```
POST /repos/gatehot59-star/siao/rulesets  ->  rc=403
{"message":"Upgrade to GitHub Pro or make this repository public to enable
this feature."}
```

**Vía 2 · Branch protection clásica** (otro endpoint, una llamada por rama):

```
PUT /branches/main/protection                             -> rc=403
PUT /branches/titan/f-004-kmi/protection                  -> rc=403
PUT /branches/titan/f-002-rootfs/protection               -> rc=403
PUT /branches/titan/f-001-userland-sobre-gki/protection    -> rc=403
PUT /branches/titan/falsador-userland-arm64/protection     -> rc=403
```

Las cinco con el **mismo mensaje textual**: *"Upgrade to GitHub Pro or make this repository public to enable this feature."*

## 2 · El control positivo, que es lo que hace válido el veredicto

Un 403 solo no distingue **"el token no puede"** de **"el plan no lo permite"**, y confundir esas dos cosas ya costó diagnósticos en este ecosistema. Así que medí si el mismo token puede escribir configuración del repo:

```
PATCH /repos/gatehot59-star/siao   {"has_issues": true}   ->  rc=200
GET   /repos/...  ->  private=True   permissions.admin=True
```

**El token escribe config del repo y tiene admin.** Así que el 403 **no es de permisos: es del plan.** GitHub Free no ofrece protección de ramas en repositorios **privados**.

**Y es exactamente la clase de error que este proyecto tiene registrado:** declarar "no puedo" sin separar ausencia de permiso denegado. Acá quedó separado.

## 3 · Las tres vías reales, con su costo

| # | Vía | Costo | Qué habilita |
|---|---|---|---|
| **1** | **Pasar el repo a público** | **$0** | Protección de ramas y rulesets **gratis**. Y de paso el runner pasa de 2 vCPU / 8 GB a **4 vCPU / 16 GB, gratis e ilimitado** |
| 2 | GitHub Pro | pago mensual | lo mismo, sin publicar |
| 3 | Un workflow que **avise** de borrados | $0 | **no previene, solo detecta.** Un aviso después del `--delete` llega tarde |

**La vía 1 es la que recomiendo, y no la elijo yo.** El propio `README.md` ya dice, desde antes de esta medición, que *"si SIAO va a usar la fábrica en serio, pasarlo a público es la decisión correcta, y es de Abraham"*. Esta medición le agrega un segundo motivo: **es también la única forma gratuita de proteger la evidencia.**

**Lo que hay que mirar antes de publicar, y no lo decido yo:** el repo no tiene `LICENSE`, y publicar sin licencia deja el código sin términos de uso declarados. Son dos decisiones que conviene tomar juntas.

## 4 · Por qué el riesgo ya es MENOR que hace una hora

La consolidación de hoy cambió la magnitud del daño, aunque no elimine la causa:

| | Antes de hoy | Ahora |
|---|---|---|
| borrar una rama se lleva | **todo el trabajo técnico**: 177 archivos, 15 instrumentos, 15 workflows | **solo los 8 `.stg`** (89,3 MB de binario derivado) |
| dónde está la evidencia de texto | 4 ramas huérfanas | **`main`** |

Así que el `--delete` pasó de **catastrófico** a **acotado**. Sigue siendo una pérdida real, y el manifiesto lo dice: *"si la rama se borra, estos ocho archivos se pierden y esta tabla solo va a servir para saber QUÉ se perdió"*.

## 5 · Una cuarta vía para los `.stg`, medida a medias

`GET /releases` da **rc=200** con 0 releases: los **release assets existen y son accesibles** en este plan. Un asset de release **no vive en el árbol de git**, así que subir los 8 `.stg` ahí:

- no viola la regla de `AGENTS.md` (nada de binarios **commiteados**),
- y **sobrevive al borrado de una rama**.

**NO LO HICE**, por dos motivos que declaro en vez de decidir solo: son **89,3 MB** de subida, y elegir dónde vive un binario derivado del proyecto es una decisión de arquitectura de almacenamiento, no un trámite. **Queda propuesta y esperando OK.**

## 6 · Efecto colateral que produje y hay que saber

El control positivo fue `has_issues: true`. **El repo tenía los issues habilitados ya**, así que no cambió nada observable, pero **fue una escritura real sobre la configuración** y no un `GET`. Lo elegí porque es el cambio reversible más chico que encontré; usar un `PATCH` destructivo como control habría sido peor que no medir.

## 7 · NO MEDIDO

- Si al pasar el repo a público la protección se aplica sin más pasos: **es esperable, no medido**.
- Si los 8 `.stg` caben en un release sin problemas de cuota.
- El plan exacto de la cuenta: `GET /user` no devolvió el campo `plan`, así que el nombre del plan es **NO MEDIDO**. Lo que sí está medido es la **consecuencia**: los dos endpoints responden que hace falta Pro.
