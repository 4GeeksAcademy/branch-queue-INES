# branch-queue

Gestor de colas en terminal para las sucursales del Banco Meridional.

Los clientes toman un ticket numerado para un servicio (depósitos, retiros o
gestión de cuenta) y cada agente llama al siguiente cliente **de su propio
servicio** al instante, sin recorrer la sala de espera completa.

## Cómo ejecutarlo

Necesitas Python 3.8 o superior. No hay que instalar nada más.

```bash
python3 branch_queue.py
```

Aparece un menú:

```
1. Emitir ticket
2. Llamar al siguiente
3. Ver lista de espera
4. Ver estadísticas
5. Salir
```

Los tipos de servicio válidos son `deposito`, `retiro` y `gestion_cuenta`.

## Cómo ejecutar los tests

```bash
python3 -m unittest -v
```

## Cómo está organizado

| Archivo | Para qué sirve |
|---|---|
| [branch_queue.py](branch_queue.py) | El programa: `Ticket` (datos), `BranchQueue` (lógica de colas) y `BranchQueueCLI` (menú de terminal). |
| [test_branch_queue.py](test_branch_queue.py) | Tests automáticos de los requisitos. |
| [DESIGN.md](DESIGN.md) | Por qué se eligió esta estructura y qué pasa con llamadas simultáneas. |
| [APRENDIENDO_CON_LA_IA.md](APRENDIENDO_CON_LA_IA.md) | Diario de aprendizaje: decisiones, motivos y problemas resueltos. |

## Idea principal

Una cola FIFO (`collections.deque`) por cada tipo de servicio:

```
deposito        → [T1, T4, T5]
retiro          → [T2, T6]
gestion_cuenta  → [T3]
```

Llamar al siguiente es un `popleft()` sobre la cola del servicio: cuesta lo
mismo con 5 clientes que con 5.000, y un agente nunca ve a clientes de otro
servicio.

## Operaciones de `BranchQueue`

| Método | Qué hace |
|---|---|
| `issue_ticket(client_name, service_type)` | Crea y encola un ticket; devuelve el ticket. |
| `call_next(service_type)` | Desencola y devuelve al siguiente cliente; error descriptivo si no hay nadie. |
| `peek_next(service_type)` | Muestra al siguiente sin retirarlo (`None` si no hay nadie). |
| `list_waiting()` | Diccionario servicio → lista de tickets en orden de atención. |
| `stats()` | Clientes por servicio más la clave `"total"`. |

## Restricciones

Solo biblioteca estándar de Python: la lógica usa únicamente `collections.deque`
y `datetime`; los tests usan `unittest`. Sin paquetes externos. No incluye persistencia, autenticación ni
asignación de agentes.
