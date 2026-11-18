"""Testes de integração: executar após instalar dependências com python -m unittest discover -s tests -v."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["DEMO_DATA"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as project  # noqa: E402


class DonationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        project.DB_PATH = Path(self.temp.name) / "test.sqlite3"
        project.app.config.update(TESTING=True, SECRET_KEY="test-key")
        project.init_database()
        self.client = project.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def token(self):
        with self.client.session_transaction() as sess:
            sess.setdefault("csrf", "test-csrf-token")
            return sess["csrf"]

    def register(self, name, email):
        response = self.client.post("/cadastrar", data={
            "csrf_token": self.token(), "name": name, "city": "Belém",
            "email": email, "password": "Forte@123",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def logout(self):
        self.client.post("/sair", data={"csrf_token": self.token()})

    def login(self, email):
        self.client.post("/entrar", data={
            "csrf_token": self.token(), "email": email, "password": "Forte@123",
        })

    def publish(self):
        r = self.client.post("/doacoes/nova", data={
            "csrf_token": self.token(), "title": "Mochila escolar",
            "description": "Mochila em bom estado e conservada.",
            "category": "Material escolar", "item_condition": "Bom estado",
            "city": "Belém", "state": "PA",
        })
        self.assertEqual(r.status_code, 302)
        with project.app.app_context():
            return project.one("SELECT id FROM donations ORDER BY id DESC LIMIT 1")["id"]

    def test_complete_donation_flow(self):
        self.register("Ana Oliveira", "ana@teste.local")
        item_id = self.publish()
        own_request = self.client.post(f"/doacoes/{item_id}/solicitar", data={"csrf_token": self.token()}, follow_redirects=True)
        self.assertIn("não pode solicitar seu próprio", own_request.get_data(as_text=True))
        self.logout()
        self.register("João Santos", "joao@teste.local")
        request_response = self.client.post(f"/doacoes/{item_id}/solicitar", data={"csrf_token": self.token()})
        self.assertEqual(request_response.status_code, 302)
        with project.app.app_context():
            req_id = project.one("SELECT id FROM requests WHERE donation_id=?", (item_id,))["id"]
        self.logout()
        self.login("ana@teste.local")
        approve = self.client.post(f"/solicitacoes/{req_id}/aprovar", data={"csrf_token": self.token()})
        self.assertEqual(approve.status_code, 302)
        with project.app.app_context():
            self.assertEqual(project.one("SELECT status FROM donations WHERE id=?", (item_id,))["status"], "reservado")
            self.assertEqual(project.one("SELECT status FROM requests WHERE id=?", (req_id,))["status"], "aprovada")
        complete = self.client.post(f"/doacoes/{item_id}/concluir", data={"csrf_token": self.token()})
        self.assertEqual(complete.status_code, 302)
        with project.app.app_context():
            self.assertEqual(project.one("SELECT status FROM donations WHERE id=?", (item_id,))["status"], "doado")
            self.assertEqual(project.one("SELECT status FROM requests WHERE id=?", (req_id,))["status"], "concluida")

    def test_private_routes_require_login(self):
        self.assertEqual(self.client.get("/painel").status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.register("Ana Oliveira", "ana@teste.local")
        self.assertEqual(self.client.get("/admin").status_code, 403)

    def test_post_rejects_invalid_csrf(self):
        self.assertEqual(self.client.post("/cadastrar", data={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
