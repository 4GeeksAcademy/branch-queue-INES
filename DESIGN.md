# Notas de diseño: branch-queue

## 1. ¿Por qué una cola por tipo de servicio hace `call_next` más eficiente?

**Diseño elegido:** un diccionario con una cola FIFO (`collections.deque`) por servicio.

```
deposito        → [T1, T4, T5]
retiro          → [T2, T6]
gestion_cuenta  → [T3]
```

`call_next("deposito")` hace un `popleft()` sobre la cola de depósitos: el
primer elemento de esa cola es, por construcción, el cliente de depósitos que
lleva más tiempo esperando. Coste: **O(1)**, sin importar cuánta gente espere
en total ni cuánta haya en las otras colas.

**Alternativa descartada:** una única cola compartida con todos los clientes.
Para encontrar al primer cliente de depósitos habría que recorrer la lista
desde el principio saltando a los de retiros y gestión de cuenta hasta dar con
uno de depósitos, y luego eliminarlo del medio. Coste: **O(n)** en el peor caso
(por ejemplo, 500 clientes de retiros delante del único de depósitos), y crece
a medida que la sucursal se llena. Es justo el problema que describe la
responsable de operaciones.

Ventajas adicionales de separar las colas:

- **Independencia:** cada agente solo toca su cola. El agente de depósitos no
  se ve afectado por lo que haga el de retiros.
- **Orden gratis:** el orden de llegada ya lo da la cola; no hay que ordenar
  ni comparar horas.
- **Regla de negocio garantizada:** un agente no puede llamar a un cliente de
  otro servicio, porque ese cliente ni siquiera está en su cola.
- **Por qué `deque` y no `list`:** `list.pop(0)` desplaza todos los elementos
  (O(n)); `deque.popleft()` es O(1).

| Operación        | Cola por servicio | Cola única compartida |
|------------------|-------------------|-----------------------|
| `issue_ticket`   | O(1)              | O(1)                  |
| `call_next`      | O(1)              | O(n)                  |
| `peek_next`      | O(1)              | O(n)                  |
| `list_waiting`   | O(n)              | O(n)                  |

## 2. ¿Qué pasaría si dos agentes del mismo servicio llamasen a `call_next` a la vez?

**El riesgo:** que los dos agentes reciban al *mismo* cliente. Ocurre si la
operación se hace en dos pasos separados:

```
agente A: mira el primero  → T1
agente B: mira el primero  → T1   (A todavía no lo ha retirado)
agente A: lo retira        → atiende a T1
agente B: lo retira        → atiende a T1   ← el mismo cliente, llamado dos veces
```

**La mutación que debe ocurrir primero:** *retirar* al cliente de la cola.
Leer y retirar tienen que ser **un solo paso indivisible**. Por eso
`call_next` usa `popleft()`, que devuelve y elimina el elemento a la vez: quien
lo obtiene es el único que lo tiene, y el otro agente recibe al siguiente.
Nunca se debe hacer "mirar el primero, atenderlo y luego borrarlo".

**Estado del código actual:** el programa es de un solo hilo y el menú atiende
una acción a la vez, así que esta carrera no puede ocurrir hoy.

**Si se integrara en los quioscos con varios hilos o procesos:**

- En CPython, `append` y `popleft` de `deque` son atómicos, así que dos hilos
  nunca obtendrían el mismo ticket con un solo `popleft()`.
- Pero `call_next` hace antes `if not cola`: es un patrón *comprobar y luego
  actuar*. Con la cola de un solo cliente, ambos agentes pasan la comprobación
  y uno de los dos falla en `popleft()` con un `IndexError` de la propia
  `deque`, sin el mensaje descriptivo. Se resuelve capturando ese error, o
  protegiendo comprobación y `popleft()` con un `threading.Lock` (también de la
  biblioteca estándar).
- Con varios procesos o varios quioscos, un `Lock` en memoria no basta: haría
  falta un almacén central con operaciones atómicas (por ejemplo una base de
  datos con transacciones). Queda fuera del alcance de este modelo.

## Nota sobre dependencias

Para la lógica solo se usan `collections.deque` y `datetime`, tal como exige el
enunciado. `Ticket` es una clase normal (sin `dataclasses`). Los tests usan
`unittest`, que también es de la biblioteca estándar. No hay paquetes externos.
