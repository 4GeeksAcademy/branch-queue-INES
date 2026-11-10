import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from branch_queue import BranchQueue, BranchQueueCLI


class TestBranchQueue(unittest.TestCase):
    def setUp(self):
        self.bq = BranchQueue()

    def test_numeros_globalmente_secuenciales(self):
        # Servicios distintos: ningún número se repite y no hay saltos.
        tickets = [
            self.bq.issue_ticket("Ana", "deposito"),
            self.bq.issue_ticket("Luis", "retiro"),
            self.bq.issue_ticket("Marta", "gestion_cuenta"),
            self.bq.issue_ticket("Pedro", "deposito"),
        ]
        self.assertEqual([t.number for t in tickets], [1, 2, 3, 4])

    def test_orden_de_llegada_dentro_de_un_servicio(self):
        self.bq.issue_ticket("Ana", "deposito")
        self.bq.issue_ticket("Luis", "retiro")  # intercalado a propósito
        self.bq.issue_ticket("Pedro", "deposito")
        self.bq.issue_ticket("Eva", "deposito")
        orden = [self.bq.call_next("deposito").client_name for _ in range(3)]
        self.assertEqual(orden, ["Ana", "Pedro", "Eva"])

    def test_un_agente_no_llama_a_otra_cola(self):
        self.bq.issue_ticket("Luis", "retiro")
        with self.assertRaises(IndexError):
            self.bq.call_next("deposito")
        self.assertEqual(self.bq.stats()["retiro"], 1)  # Luis sigue esperando

    def test_call_next_vacio_da_error_descriptivo(self):
        with self.assertRaisesRegex(IndexError, "No hay clientes"):
            self.bq.call_next("retiro")

    def test_peek_next_vacio_no_rompe(self):
        self.assertIsNone(self.bq.peek_next("retiro"))

    def test_peek_no_retira_al_cliente(self):
        self.bq.issue_ticket("Ana", "deposito")
        self.bq.peek_next("deposito")
        self.assertEqual(self.bq.stats()["deposito"], 1)

    def test_servicio_invalido_se_rechaza_con_mensaje_claro(self):
        with self.assertRaisesRegex(ValueError, "Servicio desconocido"):
            self.bq.issue_ticket("Ana", "hipoteca")

    def test_ticket_rechazado_no_consume_numero(self):
        with self.assertRaises(ValueError):
            self.bq.issue_ticket("Ana", "hipoteca")
        ticket = self.bq.issue_ticket("Ana", "deposito")
        self.assertEqual(ticket.number, 1)

    def test_stats_incluye_total(self):
        self.bq.issue_ticket("Ana", "deposito")
        self.bq.issue_ticket("Luis", "retiro")
        self.assertEqual(
            self.bq.stats(),
            {"deposito": 1, "retiro": 1, "gestion_cuenta": 0, "total": 2},
        )

    def test_list_waiting_agrupa_por_servicio_en_orden_de_atencion(self):
        self.bq.issue_ticket("Ana", "deposito")
        self.bq.issue_ticket("Luis", "retiro")
        self.bq.issue_ticket("Pedro", "deposito")
        self.bq.issue_ticket("Marta", "gestion_cuenta")
        self.bq.issue_ticket("Sofia", "retiro")
        waiting = self.bq.list_waiting()
        self.assertEqual(
            list(waiting), ["deposito", "retiro", "gestion_cuenta"]
        )
        nombres = {
            servicio: [t.client_name for t in tickets]
            for servicio, tickets in waiting.items()
        }
        self.assertEqual(
            nombres,
            {
                "deposito": ["Ana", "Pedro"],
                "retiro": ["Luis", "Sofia"],
                "gestion_cuenta": ["Marta"],
            },
        )

    def test_list_waiting_vacio_y_no_expone_la_cola_interna(self):
        self.assertEqual(
            self.bq.list_waiting(),
            {"deposito": [], "retiro": [], "gestion_cuenta": []},
        )
        self.bq.issue_ticket("Ana", "deposito")
        self.bq.list_waiting()["deposito"].clear()  # modificar la copia...
        self.assertEqual(self.bq.stats()["deposito"], 1)  # ...no afecta a la cola

    def test_ticket_guarda_nombre_servicio_y_momento_de_llegada(self):
        ticket = self.bq.issue_ticket("Ana", "retiro")
        self.assertEqual(ticket.client_name, "Ana")
        self.assertEqual(ticket.service_type, "retiro")
        self.assertIsNotNone(ticket.issued_at)


class TestCLI(unittest.TestCase):
    def ejecutar(self, entradas):
        """Ejecuta el menú con teclas simuladas; devuelve (salida, cli)."""
        cli = BranchQueueCLI()
        salida = io.StringIO()
        with patch("builtins.input", side_effect=entradas), redirect_stdout(salida):
            cli.run()
        return salida.getvalue(), cli

    def test_flujo_completo(self):
        salida, cli = self.ejecutar(
            ["1", "Ana", "deposito", "1", "Luis", "retiro", "3", "2", "deposito",
             "4", "5"]
        )
        self.assertIn("Ticket emitido: #1 Ana", salida)
        self.assertIn("Llamando a: #1 Ana", salida)
        self.assertIn("total: 1", salida)
        self.assertEqual(cli.queue.stats()["retiro"], 1)

    def test_opcion_invalida_no_rompe(self):
        salida, _ = self.ejecutar(["9", "abc", "", "5"])
        self.assertEqual(salida.count("Opción no válida."), 3)
        self.assertIn("¡Hasta luego!", salida)

    def test_servicio_invalido_muestra_error_y_sigue(self):
        salida, cli = self.ejecutar(["1", "Ana", "hipoteca", "5"])
        self.assertIn("Error: Servicio desconocido", salida)
        self.assertEqual(cli.queue.stats()["total"], 0)

    def test_llamar_con_cola_vacia_muestra_error_y_sigue(self):
        salida, _ = self.ejecutar(["2", "retiro", "5"])
        self.assertIn("Error: No hay clientes esperando", salida)
        self.assertIn("¡Hasta luego!", salida)

    def test_nombre_vacio_se_rechaza(self):
        salida, cli = self.ejecutar(["1", "   ", "5"])
        self.assertIn("El nombre no puede estar vacío.", salida)
        self.assertEqual(cli.queue.stats()["total"], 0)

    def test_servicio_en_mayusculas_se_acepta(self):
        _, cli = self.ejecutar(["1", "Ana", "  DEPOSITO ", "5"])
        self.assertEqual(cli.queue.stats()["deposito"], 1)

    def test_ctrl_d_sale_limpiamente(self):
        salida, _ = self.ejecutar(EOFError())
        self.assertIn("¡Hasta luego!", salida)

    def test_ctrl_c_en_mitad_de_una_opcion_sale_limpiamente(self):
        salida, _ = self.ejecutar(["1", KeyboardInterrupt()])
        self.assertIn("¡Hasta luego!", salida)


if __name__ == "__main__":
    unittest.main()
