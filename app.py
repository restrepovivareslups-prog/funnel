"""FUNNEL MASTER: juego educativo y panel administrativo.
Inicio local: python app.py. Crear administrador: python app.py create-admin.
"""
from __future__ import annotations
import csv, io, os, secrets, sqlite3
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("FUNNEL_DB_PATH", INSTANCE_DIR / "funnel_master.sqlite3"))
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("FUNNEL_SECRET_KEY") or "dev-only-change-this-secret-before-deploying",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FUNNEL_HTTPS", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=1_000_000,
)
IS_PRODUCTION = os.environ.get("FUNNEL_ENV", "development") == "production"

LOGIN_ATTEMPTS = {}

MISSIONS = [
 {"id":"m1","zone":1,"title":"La tienda invisible","category":"Atracción","difficulty":"Fácil","xp":100,"coins":20,"skill":"Atracción","description":"Una tienda de cuadernos artesanales necesita que más personas descubran sus productos.","question":"¿Qué acción ayuda primero a atraer posibles clientes que todavía no conocen la tienda?","options":["Publicar contenido útil para el público objetivo","Enviar una factura a personas desconocidas","Pedir reseñas a quienes nunca compraron"],"answer":0,"explanation":"El contenido útil permite llegar a personas interesadas y despertar su atención antes de intentar venderles.","scenario":"Una marca nueva de papelería quiere darse a conocer."},
 {"id":"m2","zone":1,"title":"El mensaje correcto","category":"Atracción","difficulty":"Fácil","xp":100,"coins":20,"skill":"Atracción","description":"Debes crear un anuncio que conecte con las personas adecuadas.","question":"¿Qué anuncio es más probable que atraiga al público correcto?","options":["Compra cualquier cosa, ya","Cuadernos duraderos para organizar tus ideas y proyectos","El mejor producto del universo, garantizado"],"answer":1,"explanation":"Un mensaje concreto y dirigido a una necesidad ayuda a que el público adecuado entienda el valor de la oferta.","scenario":"Una campaña tiene muchas impresiones, pero pocas visitas relevantes."},
 {"id":"m3","zone":2,"title":"Contacto con propósito","category":"Captación","difficulty":"Fácil","xp":120,"coins":25,"skill":"Captación","description":"La tienda quiere construir una lista de personas interesadas sin pedir información innecesaria.","question":"¿Cuál es una forma razonable de captar un lead?","options":["Exigir dirección, documento y teléfono para leer un artículo","Ofrecer una guía útil a cambio de un correo con consentimiento","Comprar una lista de correos sin permiso"],"answer":1,"explanation":"Una oferta útil y una solicitud proporcional de datos, con consentimiento, pueden captar contactos de forma responsable.","scenario":"El negocio quiere seguir compartiendo consejos con personas interesadas."},
 {"id":"m4","zone":3,"title":"Interés verdadero","category":"Interés","difficulty":"Media","xp":140,"coins":30,"skill":"Interés","description":"Hay contactos nuevos, pero muchos todavía no entienden por qué necesitan el producto.","question":"¿Qué ayuda a convertir la curiosidad en interés informado?","options":["Explicar beneficios y mostrar ejemplos relevantes","Mandar el mismo mensaje cada hora","Ocultar el precio hasta después de cobrar"],"answer":0,"explanation":"La información clara y los ejemplos relevantes permiten evaluar si la solución responde a una necesidad real.","scenario":"Los visitantes preguntan qué diferencia al producto de otras opciones."},
 {"id":"m5","zone":4,"title":"La fuga en la compra","category":"Conversión","difficulty":"Media","xp":160,"coins":35,"skill":"Conversión","description":"Muchos visitantes añaden un producto al carrito, pero pocos terminan la compra.","question":"¿Cuál es la mejor primera acción para entender el problema?","options":["Duplicar el precio inmediatamente","Revisar el proceso, los costos inesperados y los errores de compra","Afirmar que todos los clientes cambiaron de opinión"],"answer":1,"explanation":"Primero se investigan los datos y las barreras reales. Luego se prueban mejoras y se comparan los resultados.","scenario":"La tasa de conversión baja en el último paso del embudo."},
 {"id":"m6","zone":5,"title":"Números que hablan","category":"Métricas","difficulty":"Media","xp":180,"coins":40,"skill":"Métricas","description":"La campaña recibió 800 visitas y produjo 32 compras. Calcula su tasa de conversión.","question":"¿Cuál es la tasa de conversión de 32 compras entre 800 visitas?","options":["4 %","25 %","40 %"],"answer":0,"explanation":"Tasa de conversión = (compras ÷ visitas) × 100 = (32 ÷ 800) × 100 = 4 %.","scenario":"Debes presentar un indicador claro del rendimiento de una campaña."},
 {"id":"m7","zone":6,"title":"Que vuelvan por valor","category":"Retención","difficulty":"Media","xp":180,"coins":40,"skill":"Retención","description":"Una parte de los clientes compra una vez y no vuelve a interactuar con la marca.","question":"¿Qué estrategia responsable puede favorecer la retención?","options":["Dificultar la cancelación de mensajes","Ofrecer buen servicio, seguimiento útil y recomendaciones relevantes","Enviar mensajes sin límite aunque no respondan"],"answer":1,"explanation":"La retención se construye con valor continuo, servicio y comunicaciones pertinentes que respetan las preferencias del cliente.","scenario":"El negocio busca relaciones duraderas, no solamente ventas aisladas."},
 {"id":"m8","zone":8,"title":"El estratega del embudo","category":"Estrategia","difficulty":"Difícil","xp":250,"coins":60,"skill":"Estrategia","description":"Una tienda tuvo 1.000 visitas, 200 leads y 20 compras. La mayor oportunidad puede estar en comprender qué ocurre después de captar los contactos.","question":"¿Qué decisión inicial es más útil para mejorar el embudo?","options":["Cambiar todo al mismo tiempo","Medir cada etapa, investigar dónde se pierden contactos y probar una mejora","Aumentar el presupuesto sin analizar los resultados"],"answer":1,"explanation":"Medir cada etapa ayuda a localizar el cuello de botella. Después conviene probar cambios controlados y comparar resultados.","scenario":"Tu misión final es recomendar una mejora basada en evidencia."}
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 email TEXT UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'player',
 character_base TEXT NOT NULL DEFAULT 'nova', character_color TEXT NOT NULL DEFAULT '#7c5cff',
 character_accessory TEXT NOT NULL DEFAULT 'none', xp INTEGER NOT NULL DEFAULT 0,
 coins INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, last_active TEXT, status TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS missions (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, zone INTEGER NOT NULL, category TEXT NOT NULL,
 difficulty TEXT NOT NULL, xp INTEGER NOT NULL, coins INTEGER NOT NULL, skill TEXT NOT NULL,
 description TEXT NOT NULL, question TEXT NOT NULL, options_json TEXT NOT NULL, answer_index INTEGER NOT NULL,
 explanation TEXT NOT NULL, scenario TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), mission_id TEXT NOT NULL REFERENCES missions(id),
 attempt_number INTEGER NOT NULL, selected_index INTEGER NOT NULL, correct INTEGER NOT NULL, score INTEGER NOT NULL,
 created_at TEXT NOT NULL, mission_version INTEGER NOT NULL, UNIQUE(user_id, mission_id, attempt_number)
);
CREATE TABLE IF NOT EXISTS rewards (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), reward_key TEXT NOT NULL,
 reward_name TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id, reward_key)
);
CREATE TABLE IF NOT EXISTS activity (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), event_type TEXT NOT NULL,
 details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER REFERENCES users(id), action TEXT NOT NULL,
 target_type TEXT NOT NULL DEFAULT '', target_id TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity(created_at);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at);
"""

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect_db() as db:
        db.executescript(SCHEMA)
        for m in MISSIONS:
            db.execute("""INSERT OR IGNORE INTO missions(id,title,zone,category,difficulty,xp,coins,skill,description,question,options_json,answer_index,explanation,scenario,active,version)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,1)""", (m['id'],m['title'],m['zone'],m['category'],m['difficulty'],m['xp'],m['coins'],m['skill'],m['description'],m['question'],__import__('json').dumps(m['options'],ensure_ascii=False),m['answer'],m['explanation'],m['scenario']))
        db.commit()

@app.before_request
def setup_request():
    g.db = connect_db()
    if 'csrf' not in session: session['csrf'] = secrets.token_urlsafe(24)

@app.teardown_request
def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None: db.close()

@app.after_request
def security_headers(response):
    response.headers.setdefault('X-Content-Type-Options','nosniff')
    response.headers.setdefault('X-Frame-Options','DENY')
    response.headers.setdefault('Referrer-Policy','strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy','camera=(), microphone=(), geolocation=()')
    if IS_PRODUCTION:
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
    return response

def csrf_valid():
    token = request.headers.get('X-CSRF-Token') or (request.get_json(silent=True) or {}).get('_csrf') or request.form.get('_csrf')
    return bool(token and secrets.compare_digest(str(token), str(session.get('csrf',''))))

@app.before_request
def protect_mutations():
    if request.method in ('POST','PUT','PATCH','DELETE') and request.endpoint not in ('static',):
        # API requests and form actions require a session-bound CSRF token.
        if not csrf_valid(): return jsonify({'error':'La sesión del formulario expiró. Recarga la página e inténtalo de nuevo.'}), 400

def current_user():
    uid = session.get('user_id')
    if not uid: return None
    row = g.db.execute('SELECT * FROM users WHERE id=? AND status="active"',(uid,)).fetchone()
    return row

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user(): return jsonify({'error':'Debes iniciar sesión.'}), 401
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        u=current_user()
        if not u: return jsonify({'error':'Inicia sesión como administrador.'}), 401
        if u['role']!='admin': return jsonify({'error':'No tienes permiso para acceder a esta función.'}), 403
        return fn(*args, **kwargs)
    return wrapped

def log_activity(user_id, event, details=''):
    g.db.execute('INSERT INTO activity(user_id,event_type,details,created_at) VALUES(?,?,?,?)',(user_id,event,details[:180],now_iso()))

def audit(admin_id, action, target_type='', target_id=''):
    g.db.execute('INSERT INTO admin_audit(admin_id,action,target_type,target_id,created_at) VALUES(?,?,?,?,?)',(admin_id,action,target_type,str(target_id),now_iso()))

def player_progress(uid):
    total=g.db.execute('SELECT COUNT(*) FROM missions WHERE active=1').fetchone()[0]
    completed=g.db.execute('SELECT COUNT(DISTINCT mission_id) FROM attempts WHERE user_id=? AND correct=1',(uid,)).fetchone()[0]
    return {'total_missions':total,'completed_missions':completed,'progress':round(completed/total*100) if total else 0}

def safe_user(row):
    p=player_progress(row['id'])
    return {'id':row['id'],'username':row['username'],'role':row['role'],'character_base':row['character_base'],'character_color':row['character_color'],'character_accessory':row['character_accessory'],'xp':row['xp'],'coins':row['coins'],'level':1+row['xp']//300,'created_at':row['created_at'],'last_active':row['last_active'],'status':row['status'],**p}

@app.get('/')
def home(): return render_template('game.html')
@app.get('/admin')
def admin_page(): return render_template('admin.html')
@app.get('/api/health')
def health(): return jsonify({'status':'ok','service':'FUNNEL MASTER','database':'sqlite','production':IS_PRODUCTION})
@app.get('/api/csrf')
def csrf_token(): return jsonify({'csrf_token':session['csrf']})

@app.post('/api/register')
def register():
    data=request.get_json(silent=True) or {}; username=str(data.get('username','')).strip(); email=str(data.get('email','')).strip().lower(); password=str(data.get('password',''))
    if not 3<=len(username)<=24 or not all(c.isalnum() or c in ' _-' for c in username): return jsonify({'error':'El nombre debe tener entre 3 y 24 caracteres (letras, números, espacios, guion o guion bajo).'}),400
    if len(password)<10: return jsonify({'error':'La contraseña debe tener al menos 10 caracteres.'}),400
    if email and ('@' not in email or len(email)>254): return jsonify({'error':'Escribe un correo válido.'}),400
    if g.db.execute('SELECT 1 FROM users WHERE username=? COLLATE NOCASE',(username,)).fetchone(): return jsonify({'error':'Ese nombre de usuario ya existe.'}),409
    if email and g.db.execute('SELECT 1 FROM users WHERE email=? COLLATE NOCASE',(email,)).fetchone(): return jsonify({'error':'Ese correo ya está registrado.'}),409
    try:
        cur=g.db.execute('INSERT INTO users(username,email,password_hash,created_at,last_active) VALUES(?,?,?,?,?)',(username,email or None,generate_password_hash(password),now_iso(),now_iso()))
        uid=cur.lastrowid; log_activity(uid,'registro','Cuenta creada'); g.db.commit()
    except sqlite3.IntegrityError: return jsonify({'error':'No se pudo crear la cuenta con esos datos.'}),409
    session.clear(); session['user_id']=uid; session['csrf']=secrets.token_urlsafe(24); session.permanent=True
    return jsonify({'user':safe_user(g.db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()),'csrf_token':session['csrf']}),201

@app.post('/api/login')
def login():
    data=request.get_json(silent=True) or {}; username=str(data.get('username','')).strip(); password=str(data.get('password',''))
    # Rate limit básico por IP para frenar intentos repetidos en una sola instancia.
    ip=request.remote_addr or 'unknown'; now_ts=datetime.now(timezone.utc).timestamp(); history=[t for t in LOGIN_ATTEMPTS.get(ip,[]) if now_ts-t<900]
    if len(history)>=10: return jsonify({'error':'Demasiados intentos. Espera unos minutos antes de volver a intentarlo.'}),429
    row=g.db.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(username,)).fetchone()
    if not row or not check_password_hash(row['password_hash'],password) or row['status']!='active':
        history.append(now_ts); LOGIN_ATTEMPTS[ip]=history
        return jsonify({'error':'Usuario o contraseña incorrectos.'}),401
    LOGIN_ATTEMPTS.pop(ip,None)
    session.clear(); session['user_id']=row['id']; session['csrf']=secrets.token_urlsafe(24); session.permanent=True
    g.db.execute('UPDATE users SET last_active=? WHERE id=?',(now_iso(),row['id'])); log_activity(row['id'],'inicio_sesion','Inicio de sesión'); g.db.commit()
    row=g.db.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
    return jsonify({'user':safe_user(row),'csrf_token':session['csrf']})

@app.post('/api/logout')
@login_required
def logout():
    u=current_user(); log_activity(u['id'],'cierre_sesion','Cierre de sesión'); g.db.commit(); session.clear(); return jsonify({'ok':True})

@app.get('/api/me')
def me():
    u=current_user()
    if not u: return jsonify({'user':None})
    g.db.execute('UPDATE users SET last_active=? WHERE id=?',(now_iso(),u['id'])); g.db.commit()
    return jsonify({'user':safe_user(g.db.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()),'csrf_token':session['csrf']})

@app.patch('/api/profile')
@login_required
def update_profile():
    u=current_user(); data=request.get_json(silent=True) or {}; base=data.get('character_base','nova'); color=data.get('character_color','#7c5cff'); accessory=data.get('character_accessory','none')
    if base not in ('nova','atlas','luna','pixel'): return jsonify({'error':'Personaje no válido.'}),400
    if color not in ('#7c5cff','#22d3ee','#ffb84d','#ff6b9d','#6ee7a8'): return jsonify({'error':'Color no válido.'}),400
    if accessory not in ('none','glasses','crown','headphones'): return jsonify({'error':'Accesorio no válido.'}),400
    g.db.execute('UPDATE users SET character_base=?,character_color=?,character_accessory=?,last_active=? WHERE id=?',(base,color,accessory,now_iso(),u['id']))
    log_activity(u['id'],'perfil_actualizado','Personalización del personaje'); g.db.commit()
    return jsonify({'user':safe_user(g.db.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone())})

@app.get('/api/missions')
@login_required
def missions():
    u=current_user(); rows=g.db.execute('SELECT * FROM missions WHERE active=1 ORDER BY zone,id').fetchall(); completed={r['mission_id'] for r in g.db.execute('SELECT DISTINCT mission_id FROM attempts WHERE user_id=? AND correct=1',(u['id'],)).fetchall()}
    out=[]
    for m in rows:
        opts=__import__('json').loads(m['options_json']); zone_locked=m['zone']>1 and not any(x['zone']==m['zone']-1 and x['id'] in completed for x in MISSIONS)
        # Sequential progression: previous mission must be completed, with the first mission always open.
        idx=next((i for i,x in enumerate(MISSIONS) if x['id']==m['id']),0)
        locked=idx>0 and MISSIONS[idx-1]['id'] not in completed
        out.append({'id':m['id'],'title':m['title'],'zone':m['zone'],'category':m['category'],'difficulty':m['difficulty'],'xp':m['xp'],'coins':m['coins'],'skill':m['skill'],'description':m['description'],'scenario':m['scenario'],'question':m['question'],'options':opts,'explanation':m['explanation'],'completed':m['id'] in completed,'locked':locked,'attempts':g.db.execute('SELECT COUNT(*) FROM attempts WHERE user_id=? AND mission_id=?',(u['id'],m['id'])).fetchone()[0]})
    return jsonify({'missions':out,'progress':player_progress(u['id'])})

@app.post('/api/missions/<mission_id>/submit')
@login_required
def submit_mission(mission_id):
    u=current_user(); data=request.get_json(silent=True) or {}; selected=data.get('selected_index')
    if not isinstance(selected,int) or isinstance(selected,bool): return jsonify({'error':'Selecciona una respuesta válida.'}),400
    m=g.db.execute('SELECT * FROM missions WHERE id=? AND active=1',(mission_id,)).fetchone()
    if not m: return jsonify({'error':'La misión no existe o no está disponible.'}),404
    opts=__import__('json').loads(m['options_json'])
    if selected<0 or selected>=len(opts): return jsonify({'error':'La respuesta seleccionada no es válida.'}),400
    idx=next((i for i,x in enumerate(MISSIONS) if x['id']==mission_id),0)
    if idx>0 and not g.db.execute('SELECT 1 FROM attempts WHERE user_id=? AND mission_id=? AND correct=1',(u['id'],MISSIONS[idx-1]['id'])).fetchone(): return jsonify({'error':'Completa la misión anterior para desbloquear esta.'}),403
    attempt=g.db.execute('SELECT COUNT(*) FROM attempts WHERE user_id=? AND mission_id=?',(u['id'],mission_id)).fetchone()[0]+1
    correct=selected==m['answer_index']; score=100 if correct else 0
    g.db.execute('INSERT INTO attempts(user_id,mission_id,attempt_number,selected_index,correct,score,created_at,mission_version) VALUES(?,?,?,?,?,?,?,?)',(u['id'],mission_id,attempt,selected,int(correct),score,now_iso(),m['version']))
    xp_awarded=coins_awarded=0
    if correct:
        already=g.db.execute('SELECT 1 FROM rewards WHERE user_id=? AND reward_key=?',(u['id'],'mission:'+mission_id)).fetchone()
        if not already:
            xp_awarded=m['xp']; coins_awarded=m['coins']
            g.db.execute('UPDATE users SET xp=xp+?,coins=coins+?,last_active=? WHERE id=?',(xp_awarded,coins_awarded,now_iso(),u['id']))
            g.db.execute('INSERT INTO rewards(user_id,reward_key,reward_name,created_at) VALUES(?,?,?,?)',(u['id'],'mission:'+mission_id,'Misión: '+m['title'],now_iso()))
            log_activity(u['id'],'recompensa','Recompensa por '+m['title'])
        log_activity(u['id'],'mision_completada',m['title'])
    else: log_activity(u['id'],'intento_mision',m['title']+' (respuesta incorrecta)')
    g.db.commit(); updated=g.db.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
    return jsonify({'correct':correct,'correct_index':m['answer_index'],'explanation':m['explanation'],'xp_awarded':xp_awarded,'coins_awarded':coins_awarded,'user':safe_user(updated),'progress':player_progress(u['id']),'already_rewarded':bool(correct and not xp_awarded and not coins_awarded)})

@app.get('/api/my-stats')
@login_required
def my_stats():
    u=current_user(); prog=player_progress(u['id'])
    attempts=g.db.execute('SELECT a.*,m.title,m.skill FROM attempts a JOIN missions m ON m.id=a.mission_id WHERE a.user_id=? ORDER BY a.created_at DESC LIMIT 40',(u['id'],)).fetchall()
    skills=g.db.execute('SELECT m.skill,COUNT(DISTINCT CASE WHEN a.correct=1 THEN a.mission_id END) AS passed,COUNT(DISTINCT m.id) AS total FROM missions m LEFT JOIN attempts a ON a.mission_id=m.id AND a.user_id=? WHERE m.active=1 GROUP BY m.skill',(u['id'],)).fetchall()
    return jsonify({'progress':prog,'attempts':[{'mission':a['title'],'skill':a['skill'],'correct':bool(a['correct']),'score':a['score'],'created_at':a['created_at']} for a in attempts], 'skills':[{'name':s['skill'],'passed':s['passed'],'total':s['total'],'percent':round(s['passed']/s['total']*100) if s['total'] else 0} for s in skills]})

@app.get('/api/leaderboard')
def leaderboard():
    rows=g.db.execute('SELECT id,username,xp,coins,created_at,last_active,character_base,character_color FROM users WHERE role="player" AND status="active" ORDER BY xp DESC,created_at ASC LIMIT 20').fetchall()
    return jsonify({'players':[{'username':r['username'],'xp':r['xp'],'level':1+r['xp']//300,'character_base':r['character_base'],'character_color':r['character_color']} for r in rows]})

# Admin API
@app.get('/api/admin/summary')
@admin_required
def admin_summary():
    period=request.args.get('days','30')
    try: days=max(1,min(365,int(period)))
    except ValueError: days=30
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    total=g.db.execute('SELECT COUNT(*) FROM users WHERE role="player"').fetchone()[0]
    new=g.db.execute('SELECT COUNT(*) FROM users WHERE role="player" AND created_at>=?',(cutoff,)).fetchone()[0]
    active=g.db.execute('SELECT COUNT(DISTINCT user_id) FROM activity WHERE user_id IS NOT NULL AND created_at>=?',(cutoff,)).fetchone()[0]
    completed=g.db.execute('SELECT COUNT(*) FROM (SELECT user_id,mission_id FROM attempts WHERE correct=1 GROUP BY user_id,mission_id)').fetchone()[0]
    started=g.db.execute('SELECT COUNT(*) FROM (SELECT user_id,mission_id FROM attempts GROUP BY user_id,mission_id)').fetchone()[0]
    avg=g.db.execute('SELECT AVG(score) FROM attempts').fetchone()[0] or 0
    rewards=g.db.execute('SELECT COUNT(*) FROM rewards').fetchone()[0]
    daily=g.db.execute('SELECT substr(created_at,1,10) day,COUNT(*) count FROM users WHERE role="player" AND created_at>=? GROUP BY day ORDER BY day',(cutoff,)).fetchall()
    mission_rows=g.db.execute('SELECT m.id,m.title,COUNT(DISTINCT CASE WHEN a.correct=1 THEN a.user_id END) completed,COUNT(a.id) attempts FROM missions m LEFT JOIN attempts a ON a.mission_id=m.id WHERE m.active=1 GROUP BY m.id ORDER BY m.zone').fetchall()
    levels=g.db.execute('SELECT CASE WHEN xp<300 THEN 1 WHEN xp<700 THEN 2 WHEN xp<1200 THEN 3 WHEN xp<1800 THEN 4 ELSE 5 END level,COUNT(*) count FROM users WHERE role="player" GROUP BY level ORDER BY level').fetchall()
    return jsonify({'kpis':{'players':total,'new_players':new,'active_players':active,'unique_missions_completed':completed,'mission_starts':started,'completion_rate':round(completed/started*100,1) if started else 0,'average_score':round(avg,1),'rewards':rewards},'daily_users':[dict(x) for x in daily],'missions':[dict(x) for x in mission_rows],'levels':[dict(x) for x in levels],'days':days})

@app.get('/api/admin/players')
@admin_required
def admin_players():
    q=request.args.get('q','').strip()[:80]; page=max(1,int(request.args.get('page','1') or 1)); per=20; status=request.args.get('status','all')
    where=['role="player"']; args=[]
    if q: where.append('username LIKE ?'); args.append('%'+q.replace('%','\\%').replace('_','\\_')+'%')
    if status in ('active','suspended'): where.append('status=?'); args.append(status)
    clause=' AND '.join(where); total=g.db.execute('SELECT COUNT(*) FROM users WHERE '+clause,args).fetchone()[0]
    rows=g.db.execute('SELECT * FROM users WHERE '+clause+' ORDER BY created_at DESC LIMIT ? OFFSET ?',args+[per,(page-1)*per]).fetchall()
    return jsonify({'players':[safe_user(r) for r in rows],'total':total,'page':page,'pages':max(1,(total+per-1)//per)})

@app.get('/api/admin/players/<int:uid>')
@admin_required
def admin_player_detail(uid):
    row=g.db.execute('SELECT * FROM users WHERE id=? AND role="player"',(uid,)).fetchone()
    if not row: return jsonify({'error':'No se encontró el jugador.'}),404
    attempts=g.db.execute('SELECT a.*,m.title,m.skill FROM attempts a JOIN missions m ON m.id=a.mission_id WHERE a.user_id=? ORDER BY a.created_at DESC LIMIT 100',(uid,)).fetchall()
    rewards=g.db.execute('SELECT reward_name,created_at FROM rewards WHERE user_id=? ORDER BY created_at DESC',(uid,)).fetchall()
    activity=g.db.execute('SELECT event_type,details,created_at FROM activity WHERE user_id=? ORDER BY created_at DESC LIMIT 100',(uid,)).fetchall()
    return jsonify({'player':safe_user(row),'attempts':[{'mission':a['title'],'skill':a['skill'],'correct':bool(a['correct']),'score':a['score'],'attempt':a['attempt_number'],'created_at':a['created_at']} for a in attempts],'rewards':[dict(r) for r in rewards],'activity':[dict(a) for a in activity]})

@app.post('/api/admin/players/<int:uid>/status')
@admin_required
def admin_player_status(uid):
    admin=current_user(); data=request.get_json(silent=True) or {}; status=data.get('status')
    if status not in ('active','suspended'): return jsonify({'error':'Estado no válido.'}),400
    row=g.db.execute('SELECT id FROM users WHERE id=? AND role="player"',(uid,)).fetchone()
    if not row: return jsonify({'error':'No se encontró el jugador.'}),404
    g.db.execute('UPDATE users SET status=? WHERE id=?',(status,uid)); audit(admin['id'],'cambio_estado','player',uid); g.db.commit()
    return jsonify({'ok':True,'status':status})

@app.get('/api/admin/export.csv')
@admin_required
def admin_export():
    admin=current_user(); rows=g.db.execute('SELECT u.id,u.username,u.created_at,u.last_active,u.status,u.xp,u.coins,COUNT(DISTINCT CASE WHEN a.correct=1 THEN a.mission_id END) completed FROM users u LEFT JOIN attempts a ON a.user_id=u.id WHERE u.role="player" GROUP BY u.id ORDER BY u.created_at DESC').fetchall()
    buf=io.StringIO(); writer=csv.writer(buf); writer.writerow(['id','usuario','registro_utc','ultima_actividad_utc','estado','xp','monedas','misiones_completadas'])
    for r in rows: writer.writerow(list(r))
    audit(admin['id'],'exportacion_csv','players','all'); g.db.commit()
    response=make_response('\ufeff'+buf.getvalue()); response.headers['Content-Type']='text/csv; charset=utf-8'; response.headers['Content-Disposition']='attachment; filename=funnel-master-jugadores.csv'; return response

@app.get('/api/admin/audit')
@admin_required
def admin_audit_list():
    rows=g.db.execute('SELECT a.*,u.username admin_name FROM admin_audit a LEFT JOIN users u ON u.id=a.admin_id ORDER BY a.created_at DESC LIMIT 100').fetchall()
    return jsonify({'events':[dict(r) for r in rows]})

@app.errorhandler(500)
def internal_error(_e):
    if hasattr(g,'db') and g.db: g.db.rollback()
    return jsonify({'error':'Ocurrió un error interno. Inténtalo de nuevo.'}),500

def create_admin(username,password):
    init_db()
    with connect_db() as db:
        if db.execute('SELECT 1 FROM users WHERE role="admin"').fetchone(): raise SystemExit('Ya existe un administrador. No se creó otro.')
        if not 3<=len(username)<=24 or len(password)<12: raise SystemExit('Usa un nombre de 3–24 caracteres y una contraseña de al menos 12 caracteres.')
        db.execute('INSERT INTO users(username,password_hash,role,created_at,last_active) VALUES(?,?,?,?,?)',(username,generate_password_hash(password),'admin',now_iso(),now_iso()))
        db.commit()
    print('Administrador creado. Guarda tus credenciales en un lugar seguro.')

# La base se inicializa también al importar la aplicación para servidores WSGI.
init_db()

if __name__ == '__main__':
    import getpass, sys
    if len(sys.argv)>1 and sys.argv[1]=='create-admin':
        username=input('Nombre de administrador: ').strip(); password=getpass.getpass('Contraseña (mínimo 12 caracteres): '); confirm=getpass.getpass('Repite la contraseña: ')
        if password!=confirm: raise SystemExit('Las contraseñas no coinciden.')
        create_admin(username,password)
    else:
        if IS_PRODUCTION and app.config['SECRET_KEY']=='dev-only-change-this-secret-before-deploying': raise SystemExit('Configura FUNNEL_SECRET_KEY antes de iniciar en producción.')
        app.run(host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','5000')),debug=not IS_PRODUCTION)
