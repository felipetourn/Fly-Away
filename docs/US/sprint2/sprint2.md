# Sprint 2 - Resumen

Objetivo del sprint: el flujo de compra de pasajes (reservar, pagar, confirmar la venta, ticket y factura). Rama: `feat/sprint2-pagos`.

## User stories implementadas

| US | Nombre | Story points | Horas estimadas | Horas reales | Estado | Ficha |
|---|---|---|---|---|---|---|
| US23 | Cerrar sesión | 1 | 5 | 1 | Terminada | [us23.md](us23.md) |
| US06 | Reservar pasajes | 3 | 22 | 5 | Terminada | [us06.md](us06.md) |
| US07 | Realizar pago de los pasajes reservados | 8 | 31 | 7 | Terminada | [us07.md](us07.md) |
| US08 | Corroborar transacción y finalizar la venta | 5 | 18 | 4 | Terminada | [us08.md](us08.md) |
| **Total** | | **17** | **76** | **17** | | |

Pendientes del sprint: **US09** ticket electrónico y **US10** factura por email.

## Aclaraciones generales

### Reservas de prueba (hasta que esté la US06)

La reserva de pasajes (US06) la desarrolla otro integrante. Para poder pagar mientras tanto, cada pasajero recibe **3 reservas de prueba** al entrar a **Reservas**: economy × 1, primera × 2 y economy × 9, en los próximos vuelos con lugar. Quedan fijas: una vez pagadas, no se regeneran. El contrato para reemplazarlas por las reservas reales está en [arquitectura.md](../../arquitectura.md#contrato-entre-reservas-us06-y-pagos-us07us08).

### Medios de pago

Hay dos, los dos en modo de prueba: no se mueve dinero real.

**1. Tarjeta (simulada).** Es una pasarela propia: valida los datos como una real (número, titular, vencimiento, CVV) y decide el resultado según el número. En la pantalla de pago, el botón **"Tarjetas de prueba"** abre la lista y completa el formulario con un clic. Para cualquiera de estas tarjetas sirven cualquier titular, cualquier vencimiento futuro y cualquier CVV de 3 dígitos.

| Resultado | Visa | Mastercard |
|---|---|---|
| Aprobada | `4242 4242 4242 4242` | `5555 5555 5555 4444` |
| Rechazada por el emisor | `4000 0000 0000 0002` | `5200 0000 0000 0007` |
| Fondos insuficientes | `4000 0000 0000 9995` | `5200 0000 0000 9990` |
| Error de procesamiento | `4000 0000 0000 0119` | `5200 0000 0000 0114` |

Cualquier otra tarjeta Visa, Mastercard o Amex válida se aprueba.

**2. Mercado Pago (sandbox).** Integramos la API de Orders de Checkout Pro: el pasajero va al checkout de Mercado Pago y vuelve a la pantalla de resultado. Para pagar hace falta:

1. **No tener una sesión real de Mercado Pago abierta** en el navegador (usar una ventana privada o cerrar sesión en mercadopago.com.ar). Si no, MP muestra "Una de las partes con la que intentás hacer el pago es de prueba".
2. Cuando MP lo pida, **iniciar sesión con el comprador de prueba**. Su usuario y contraseña **no están en el repo** (es público): se piden al equipo.
3. Pagar con una de estas tarjetas de prueba de Mercado Pago:

| Tarjeta | Número | Vencimiento | CVV | Titular |
|---|---|---|---|---|
| Mastercard | `5031 7557 3453 0604` | `11/30` | `123` | `APRO` → aprobada / `OTHE` → rechazada |
| Visa | `4509 9535 6623 3704` | `11/30` | `123` | `APRO` → aprobada / `OTHE` → rechazada |

Si pide documento: DNI `12345678`.

### Confirmación de la venta

Los asientos del vuelo se descuentan **solo cuando el pago se aprueba**; un pago rechazado no toca la disponibilidad. Si con Mercado Pago, entre ir al checkout y que se apruebe el pago, el vuelo se queda sin lugar o se cancela, la compra no se confirma y el pago queda marcado "corresponde devolución" (la devolución no se automatiza).

Sin webhook de Mercado Pago: un pago se confirma cuando el pasajero vuelve del checkout a la pantalla de resultado, o cuando intenta pagar de nuevo esa reserva.

### Dónde se ve cada cosa

- **Reservas:** las reservas de prueba, con el botón **Pagar** o el chip **Confirmada**.
- **Pantalla de pago:** resumen de la reserva, tarjeta o Mercado Pago. Al pagar con tarjeta, el avión cruza la línea mientras se valida.
- **Resultado del pago:** "¡Compra confirmada!", "Pago rechazado" (con el motivo) o "Pago pendiente".
- **Perfil > Mis pagos:** todos los pagos con medio, tarjeta o cuenta de MP, fecha, vuelo (al tocarlo abre su detalle), valor y estado.
- **Cerrar sesión:** botón del perfil; invalida la sesión también en el servidor.

### Correr en local

- Trabajar contra **SQLite** (`DATABASE_URL=` vacío en `backend/.env`), no contra Supabase. Supabase recibe las migraciones recién con el deploy.
- Este sprint agrega migraciones (`token_blacklist` de la US23 y `pagos` 0001 a 0003). Después de hacer pull: `DATABASE_URL= .venv/Scripts/python manage.py migrate` desde `backend/`. Sin eso, el login da error 500.
- Para Mercado Pago hace falta `MP_ACCESS_TOKEN` en `backend/.env` (el token de prueba también se pide al equipo). Sin token, el pago con MP avisa que no puede conectar y la tarjeta funciona igual.
- En Render (producción) hay que cargar `MP_ACCESS_TOKEN` y `FRONTEND_URL=https://fly-away-one.vercel.app`.
