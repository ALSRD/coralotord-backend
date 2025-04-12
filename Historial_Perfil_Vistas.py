
# Historial Perfil Vistas - Backend Flask + Admin
from flask import Flask, request, jsonify, session, redirect, url_for
from functools import wraps
import sqlite3
import os
import unittest

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave-secreta')
DATABASE = 'coraloto.db'

# --- Docker-ready Configuration ---
@app.before_request
def set_session_permanent():
    session.permanent = True

# --- DB CONNECTION ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- MIDDLEWARES ---
def login_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorado

def admin_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if 'nivel_acceso' not in session or session['nivel_acceso'] != 'admin':
            return jsonify({'error': 'Acceso restringido al panel admin'}), 403
        return f(*args, **kwargs)
    return decorado

# --- ENDPOINTS ADMIN ---
@app.route('/admin/usuarios', methods=['GET'])
@admin_requerido
def listar_usuarios():
    conn = get_db_connection()
    usuarios = conn.execute('SELECT id_usuario, nombre, email, nivel_acceso FROM usuarios').fetchall()
    return jsonify([dict(u) for u in usuarios])

@app.route('/admin/usuarios/<int:id>/nivel', methods=['PUT'])
@admin_requerido
def cambiar_nivel(id):
    nuevo_nivel = request.json.get('nivel_acceso')
    conn = get_db_connection()
    conn.execute('UPDATE usuarios SET nivel_acceso = ? WHERE id_usuario = ?', (nuevo_nivel, id))
    conn.commit()
    return jsonify({'mensaje': 'Nivel actualizado correctamente'})

@app.route('/admin/usuarios/<int:id>', methods=['DELETE'])
@admin_requerido
def eliminar_usuario(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM usuarios WHERE id_usuario = ?', (id,))
    conn.commit()
    return jsonify({'mensaje': 'Usuario eliminado'})

@app.route('/admin/loterias', methods=['GET'])
@admin_requerido
def obtener_loterias():
    conn = get_db_connection()
    loterias = conn.execute('SELECT nombre FROM loterias').fetchall()
    return jsonify([dict(row) for row in loterias])

@app.route('/admin/loterias', methods=['POST'])
@admin_requerido
def crear_loteria():
    data = request.json
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400
    conn = get_db_connection()
    conn.execute('INSERT INTO loterias (nombre) VALUES (?)', (nombre,))
    conn.commit()
    return jsonify({'mensaje': 'Lotería creada correctamente'})

# --- TEST UNITARIOS ---
class TestAdminEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        with self.app.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['nivel_acceso'] = 'admin'

    def test_listar_usuarios(self):
        res = self.app.get('/admin/usuarios')
        self.assertEqual(res.status_code, 200)

    def test_cambiar_nivel(self):
        res = self.app.put('/admin/usuarios/1/nivel', json={'nivel_acceso': 'vip'})
        self.assertIn(res.status_code, [200, 404])

    def test_eliminar_usuario(self):
        res = self.app.delete('/admin/usuarios/99')
        self.assertIn(res.status_code, [200, 404])

    def test_crear_loteria(self):
        res = self.app.post('/admin/loterias', json={'nombre': 'Loto Test'})
        self.assertEqual(res.status_code, 200)

# --- DEPLOY READY ---
if __name__ == '__main__':
    modo = os.environ.get('FLASK_ENV')
    if modo == 'testing':
        unittest.main()
    else:
        host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_RUN_PORT', 5000))
        app.run(debug=False, host=host, port=port)
