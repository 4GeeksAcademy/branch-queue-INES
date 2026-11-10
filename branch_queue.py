"""branch-queue: gestor de colas del Banco Meridional.

Idea clave: una cola FIFO (deque) por cada tipo de servicio.
Así, "llamar al siguiente" es O(1) sin importar cuánta gente espere.
Las razones de diseño están explicadas en DESIGN.md.

El archivo tiene tres partes con responsabilidades separadas:
    1. Ticket          -> los datos de un ticket.
    2. BranchQueue     -> la lógica de las colas (no usa input() ni print()).
    3. BranchQueueCLI  -> el menú de terminal (habla con el usuario).
"""

from collections import deque
from datetime import datetime

SERVICE_TYPES = ("deposito", "retiro", "gestion_cuenta")


# ---------------------------------------------------------------------------
# 1. Datos
# ---------------------------------------------------------------------------
class Ticket:
    def __init__(self, number, client_name, service_type, issued_at):
        self.number = number  # int, secuencial y global
        self.client_name = client_name  # str
        self.service_type = service_type  # "deposito" | "retiro" | "gestion_cuenta"
        self.issued_at = issued_at  # datetime del momento de llegada

    def __repr__(self):
        return (
            f"Ticket(number={self.number!r}, client_name={self.client_name!r}, "
            f"service_type={self.service_type!r}, issued_at={self.issued_at!r})"
        )

    def __str__(self):
        hora = self.issued_at.strftime("%H:%M:%S")
        return f"#{self.number} {self.client_name} ({self.service_type}, {hora})"


# ---------------------------------------------------------------------------
# 2. Lógica de colas
# ---------------------------------------------------------------------------
class BranchQueue:
    def __init__(self):
        # Una cola independiente por servicio.
        self._queues = {service: deque() for service in SERVICE_TYPES}
        # Contador global: se comparte entre todos los servicios.
        self._next_number = 1

    def _get_queue(self, service_type):
        if service_type not in self._queues:
            raise ValueError(
                f"Servicio desconocido: {service_type!r}. "
                f"Válidos: {', '.join(SERVICE_TYPES)}"
            )
        return self._queues[service_type]

    def issue_ticket(self, client_name, service_type):
        """Crea un ticket, lo encola en su servicio y lo devuelve."""
        queue = self._get_queue(service_type)  # valida antes de gastar un número
        ticket = Ticket(
            number=self._next_number,
            client_name=client_name,
            service_type=service_type,
            issued_at=datetime.now(),
        )
        self._next_number += 1
        queue.append(ticket)
        return ticket

    def call_next(self, service_type):
        """Desencola y devuelve al siguiente cliente; error si no hay nadie."""
        queue = self._get_queue(service_type)
        if not queue:
            raise IndexError(
                f"No hay clientes esperando para el servicio {service_type!r}"
            )
        return queue.popleft()

    def peek_next(self, service_type):
        """Devuelve al siguiente cliente sin retirarlo (None si no hay nadie)."""
        queue = self._get_queue(service_type)
        return queue[0] if queue else None

    def list_waiting(self):
        """Devuelve {service_type: [tickets]} en el orden de atención."""
        return {service: list(queue) for service, queue in self._queues.items()}

    def stats(self):
        """Devuelve clientes por servicio más la clave "total"."""
        result = {service: len(queue) for service, queue in self._queues.items()}
        result["total"] = sum(result.values())
        return result


# ---------------------------------------------------------------------------
# 3. Menú de terminal
# ---------------------------------------------------------------------------
class BranchQueueCLI:
    MENU = """
=== Banco Meridional ===
1. Emitir ticket
2. Llamar al siguiente
3. Ver lista de espera
4. Ver estadísticas
5. Salir
"""

    def __init__(self, queue=None):
        self.queue = BranchQueue() if queue is None else queue
        # Cada número del menú apunta a su método.
        self._actions = {
            "1": self._issue_ticket,
            "2": self._call_next,
            "3": self._show_waiting,
            "4": self._show_stats,
        }

    def run(self):
        """Bucle principal. Termina con la opción 5, Ctrl+D o Ctrl+C."""
        try:
            while True:
                print(self.MENU)
                option = input("Elige una opción: ").strip()
                if option == "5":
                    break
                action = self._actions.get(option)
                if action is None:
                    print("Opción no válida.")
                    continue
                try:
                    action()
                except (ValueError, IndexError) as error:
                    # Servicio inexistente o cola vacía: avisamos y seguimos.
                    print(f"Error: {error}")
        except (EOFError, KeyboardInterrupt):
            # Entrada cerrada (Ctrl+D) o interrumpida (Ctrl+C): salida limpia.
            print()
        print("¡Hasta luego!")

    def _ask_service(self):
        """Pide el servicio; BranchQueue es quien lo valida."""
        options = " / ".join(SERVICE_TYPES)
        return input(f"Tipo de servicio ({options}): ").strip().lower()

    def _issue_ticket(self):
        name = input("Nombre del cliente: ").strip()
        if not name:
            print("El nombre no puede estar vacío.")
            return
        ticket = self.queue.issue_ticket(name, self._ask_service())
        print(f"Ticket emitido: {ticket}")

    def _call_next(self):
        ticket = self.queue.call_next(self._ask_service())
        print(f"Llamando a: {ticket}")

    def _show_waiting(self):
        for service, tickets in self.queue.list_waiting().items():
            print(f"{service} ({len(tickets)}):")
            if not tickets:
                print("  (nadie esperando)")
            for ticket in tickets:
                print(f"  {ticket}")

    def _show_stats(self):
        for key, amount in self.queue.stats().items():
            print(f"{key}: {amount}")


def main():
    BranchQueueCLI().run()


if __name__ == "__main__":
    main()
