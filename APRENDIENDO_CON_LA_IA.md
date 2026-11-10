# Aprendiendo con la IA: diario de branch-queue

Este documento explica **qué se hizo, por qué y cómo se resolvieron los
problemas**, para que puedas aprender y repetirlo tú sola en otros proyectos.

## 1. Cómo se construyó, paso a paso

1. **Archivo de entrada** (`branch_queue.py`). Empezamos con un esqueleto mínimo
   y lo ejecutamos para comprobar que Python funcionaba.
2. **La estructura de datos.** Antes de escribir código, pensamos *cómo guardar
   los clientes*. Esa decisión es la más importante del proyecto (ver sección 2).
3. **Los nombres del enunciado.** Mi primera versión usaba nombres en español
   (`GestorColas`, `cliente`, `emitir_ticket`). Al leer tus instrucciones vimos
   que pedían nombres concretos (`BranchQueue`, `client_name`, `issue_ticket`).
   Los renombré.
4. **El menú de terminal.** Un bucle que muestra opciones y actúa según lo que
   elijas.
5. **Tests.** Escribí pruebas automáticas para demostrar que cada requisito se
   cumple, en vez de limitarme a decir "funciona".
6. **Notas de diseño** (`DESIGN.md`), `README.md` y este diario.
7. **Revisión final contra la rúbrica.** Comparé el proyecto punto por punto
   con los criterios de evaluación antes de entregar. Encontré tres cosas por
   mejorar (salida limpia con Ctrl+C/Ctrl+D, un test que faltaba para
   `list_waiting` y el orden del código) y las arreglé.
8. **Subida a GitHub** con un commit y un `.gitignore` para no subir archivos
   generados por Python (`__pycache__/`).

## 2. La decisión principal: una cola por servicio

**El problema:** el agente de depósitos no debe quedarse parado porque haya
clientes de retiros delante en la lista.

**Opción A (descartada): una lista única con todos los clientes.**
Para llamar al siguiente de depósitos habría que recorrer la lista saltándose
a los de otros servicios. Cuanta más gente, más lento.

**Opción B (elegida): un diccionario con una cola por servicio.**

```
deposito        → [T1, T4, T5]
retiro          → [T2, T6]
gestion_cuenta  → [T3]
```

El agente de depósitos solo mira su cola y toma el primero. Es rápido siempre y
el orden de llegada sale gratis.

**Concepto que aprendiste: FIFO** (*first in, first out*): el primero que entra
es el primero que sale, como una cola de supermercado.

**Por qué `deque` y no `list`:** `list.pop(0)` desplaza todos los elementos
para rellenar el hueco, así que se vuelve lento con muchos datos.
`deque.popleft()` siempre cuesta lo mismo.

## 3. Otras decisiones pequeñas y sus motivos

| Decisión | Motivo |
|---|---|
| `Ticket` como `dataclass` | Es una clase que solo guarda datos; Python escribe el constructor por ti. |
| Un único contador global de tickets | El enunciado pide números secuenciales entre *todos* los servicios. |
| Validar el servicio **antes** de gastar un número | Si un ticket falla, el siguiente no debe saltarse un número. Hay un test para esto. |
| `call_next` con cola vacía lanza `IndexError` | El enunciado pide un error descriptivo. `IndexError` es lo que Python usa al sacar de algo vacío. |
| `peek_next` con cola vacía devuelve `None` | Mirar no modifica nada y una cola vacía es normal. El enunciado no lo especificaba, fue decisión mía. |
| Servicio inexistente lanza `ValueError` | Así se distingue "ese servicio no existe" de "no hay nadie esperando". |
| El menú captura los errores con `try/except` | Un error del usuario no debe cerrar el programa. |
| Diccionario de acciones en el menú (`{"1": self._issue_ticket, ...}`) | Es más limpio que muchos `if/elif` y fácil de ampliar. |
| La lógica no se mezcla con `input()`/`print()` | `BranchQueue` solo gestiona colas; la clase `BranchQueueCLI` habla con el usuario. Así se puede probar la lógica sin teclado. |
| El menú es una clase (`BranchQueueCLI`) y no funciones sueltas | Cada parte del archivo tiene una responsabilidad: `Ticket` guarda datos, `BranchQueue` gestiona colas, `BranchQueueCLI` conversa con el usuario. |
| Nombres internos en inglés (`_queues`, `SERVICE_TYPES`) | Al principio mezclé español e inglés. Un solo idioma en el código es más fácil de leer. Los mensajes para el usuario siguen en español. |
| Ctrl+C y Ctrl+D salen con un mensaje, sin error | Cerrar la entrada lanza `EOFError` y Ctrl+C lanza `KeyboardInterrupt`. Se capturan para que el programa termine limpiamente. |

## 4. Problemas que aparecieron y cómo se resolvieron

**Problema 1: los nombres no coincidían con el enunciado.**
*Cómo se resolvió:* al recibir cada bloque de instrucciones, lo comparé con lo
que ya había escrito y renombré lo que no coincidía.
*Lección:* lee los requisitos con lupa; los nombres exactos importan,
sobre todo si algo los va a evaluar automáticamente.

**Problema 2: ¿qué hacer con una cola vacía?**
Primero `call_next` devolvía `None`. Luego el enunciado pidió un error
descriptivo, así que lo cambié.
*Lección:* devolver `None` y lanzar un error son dos formas de avisar de un
caso especial; se elige según lo que pida el requisito.

**Problema 3: ¿cómo saber que de verdad funciona?**
*Cómo se resolvió:* tests automáticos (`python3 -m unittest -v`), uno por
requisito. Además, probé el menú con una sesión simulada de teclas,
incluyendo entradas inválidas.
*Lección:* "me funciona" no es una prueba. Un test sí, y te avisa si más
adelante rompes algo.

**Problema 4: el programa se caía al cerrar la entrada.**
Una revisión mía encontró que con Ctrl+D o Ctrl+C el menú mostraba un error
largo de Python (`EOFError`). Lo comprobé ejecutando el programa con la entrada
cerrada antes de arreglarlo, y después de arreglarlo lo repetí.
*Cómo se resolvió:* se envolvió el bucle del menú en un `try/except
(EOFError, KeyboardInterrupt)` y se añadieron tests que simulan el teclado con
`unittest.mock`.
*Lección:* primero reproduce el fallo, luego arréglalo, y después comprueba que
el fallo ya no ocurre.

**Problema 5: dos agentes llamando a la vez.**
Si el código *mira* al primero y *después* lo retira, dos agentes podrían
atender al mismo cliente. La solución es que leer y retirar sean **un solo paso**
(`popleft()`). Está explicado a fondo en [DESIGN.md](DESIGN.md).
*Lección:* el orden de las operaciones importa cuando hay varios actores.

## 5. Conceptos nuevos para tu vocabulario

- **Cola FIFO:** el primero en llegar es el primero en salir.
- **O(1) y O(n):** cuánto crece el tiempo de una operación al crecer los datos.
  O(1) = siempre igual; O(n) = crece con la cantidad de datos.
- **Dataclass:** clase pensada solo para guardar datos.
- **Caso borde:** situación poco habitual (cola vacía, dato inválido) que hay
  que contemplar.
- **Test unitario:** código que comprueba automáticamente que otro código
  hace lo que debe.
- **Check-then-act:** comprobar algo y actuar después. Es peligroso si otro
  puede cambiar la situación entre ambos pasos.

## 6. Cómo practicar

1. Cambia el nombre de un servicio en `SERVICE_TYPES` y mira qué cambia en el menú.
2. Añade un cuarto servicio, por ejemplo `prestamos`. ¿Hay que tocar algo más?
3. Escribe un test nuevo: tras llamar a todos los clientes, `stats()["total"]`
   debe ser 0.
4. Intenta añadir una opción al menú que muestre al siguiente cliente con
   `peek_next`.
