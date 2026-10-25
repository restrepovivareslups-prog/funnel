# FUNNEL MASTER

Plataforma educativa gamificada sobre embudos de ventas. Incluye dos interfaces conectadas al mismo backend y base de datos:

- **Juego:** `http://127.0.0.1:5000/`
- **Panel administrativo:** `http://127.0.0.1:5000/admin`
- **Estado de la API:** `http://127.0.0.1:5000/api/health`

## Funciones implementadas

### Juego
- Registro, inicio y cierre de sesión con contraseñas hasheadas.
- Perfil y personalización de personaje (4 bases, 5 colores y accesorios).
- Ocho misiones educativas iniciales con desbloqueo secuencial.
- Evaluación de respuestas en el servidor, explicación, intentos, XP y monedas.
- Recompensas únicas por misión: repetir una misión no duplica la recompensa.
- Progreso persistente en SQLite, estadísticas personales, competencias y clasificación.
- Diseño adaptable a móvil y escritorio, estados vacíos y mensajes de error.

### Panel administrativo
- Acceso separado en `/admin`, protegido por rol.
- Indicadores calculados con datos persistidos, filtros temporales y gráficos.
- Tabla de jugadores con búsqueda, filtros, paginación y ficha individual.
- Historial de intentos, actividad y recompensas.
- Suspensión/reactivación de cuentas, exportación CSV y auditoría administrativa.

### Seguridad básica incluida
- Hash de contraseñas de Werkzeug.
- Cookies de sesión HttpOnly y SameSite=Lax.
- Token CSRF ligado a la sesión para mutaciones.
- Control de roles en el servidor, consultas parametrizadas y cabeceras de seguridad.
- No se incluyen cuentas ni contraseñas administrativas predeterminadas.

## Requisitos

- Python 3.10 o posterior.
- Navegador moderno.
- No se requiere Node.js ni una API de terceros.

## Instalación en Windows

1. Extrae el ZIP.
2. Abre una terminal dentro de la carpeta `funnel-master`.
3. Crea un entorno virtual:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

4. Instala las dependencias:

   ```powershell
   pip install -r requirements.txt
   ```

5. Crea el primer administrador:

   ```powershell
   python app.py create-admin
   ```

   Escribe un nombre y una contraseña única de al menos 12 caracteres. La contraseña no se muestra al escribirla.

6. Inicia la aplicación:

   ```powershell
   python app.py
   ```

7. Abre `http://127.0.0.1:5000/` para jugar y `http://127.0.0.1:5000/admin` para el panel.

## Instalación en macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py create-admin
python app.py
```

## Cómo funciona el progreso compartido

El navegador envía las acciones al backend Flask. Flask valida cada respuesta y guarda usuarios, intentos, experiencia, monedas, recompensas y actividad en `instance/funnel_master.sqlite3`. El panel consulta esa misma base de datos; no utiliza números de demostración para los indicadores. Si un usuario inicia sesión en otro dispositivo contra el mismo servidor, su progreso guardado estará disponible allí.

Los datos locales de prueba se guardan en el archivo SQLite dentro de `instance/`. No borres ese archivo si deseas conservar el progreso.

## Publicar en Internet para celular y computador

El diseño usa reglas adaptables (responsive) y las páginas incluyen `viewport`, por lo que se ajustan a pantallas pequeñas y grandes. La publicación sí requiere una cuenta de hosting y una cuenta de GitHub del propietario; el proyecto todavía no tiene una dirección pública.

### Opción preparada: Render

Se incluyen `render.yaml` y `Procfile` para facilitar la publicación. La configuración de Render utiliza un disco persistente para que las cuentas, contraseñas cifradas, monedas y progreso no se borren al reiniciar o volver a publicar. **El disco persistente requiere un plan de pago de Render**; no publiques el juego con SQLite en un alojamiento efímero si vas a guardar progreso real. Los precios y condiciones pueden cambiar.

1. Crea una cuenta en GitHub y un repositorio privado para este proyecto. Sube el contenido de esta carpeta sin incluir `.env`, bases de datos ni contraseñas.
2. Crea una cuenta en Render y conecta el repositorio desde el panel de Render.
3. Render detectará `render.yaml`; revisa el plan y el disco persistente antes de confirmar la publicación.
4. Espera a que termine el despliegue y abre la dirección `https://...onrender.com` que Render asigne. Esa misma dirección funcionará en celular y computador.
5. Crea la cuenta administradora desde la consola del servicio ejecutando `python app.py create-admin` (si el plan no ofrece consola, habrá que crearla desde un entorno seguro apuntando a la misma base de datos; no expongas una ruta pública para crear administradores).
6. Abre `https://TU-DOMINIO.onrender.com/admin` para el panel privado y comparte la dirección principal `/` con las personas que jugarán.
7. Prueba registro, inicio de sesión, misiones y guardado de progreso desde un celular y un computador antes de anunciarlo públicamente.

Guía oficial de despliegue de Flask: https://render.com/docs/deploy-flask. Render explica el almacenamiento persistente aquí: https://render.com/docs/disks.

### Antes de abrirlo al público

- Genera y guarda una contraseña administrativa fuerte; no la compartas con los jugadores.
- Publica una política de privacidad y recoge solo los datos necesarios.
- Añade verificación y recuperación de correo, copias de seguridad y controles antiabuso antes de una comunidad grande.
- La configuración actual es para una instancia sencilla con SQLite y un proceso de servidor. Para muchos usuarios simultáneos, conviene migrar a PostgreSQL y revisar límites de intentos, registros y respaldos.
- Nunca subas `.env`, contraseñas ni archivos de base de datos al repositorio.

El servidor de desarrollo de Flask no debe exponerse directamente a Internet. El proyecto no implementa todavía un flujo de recuperación de contraseña por correo, verificación de correo, gestión completa de versiones de misiones desde el panel ni protección avanzada antiabuso; estas funciones deben añadirse antes de un lanzamiento público amplio.

## API principal

- `GET /api/health`
- `GET /api/csrf`
- `POST /api/register`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/me`
- `PATCH /api/profile`
- `GET /api/missions`
- `POST /api/missions/<id>/submit`
- `GET /api/my-stats`
- `GET /api/leaderboard`
- `GET /api/admin/summary?days=30`
- `GET /api/admin/players?page=1&q=...`
- `GET /api/admin/players/<id>`
- `POST /api/admin/players/<id>/status`
- `GET /api/admin/export.csv`
- `GET /api/admin/audit`

Las rutas administrativas requieren una sesión autenticada cuyo rol sea `admin`.

## Pruebas

Ejecuta las comprobaciones incluidas:

```bash
python -m unittest discover -s tests -v
```

## Archivos anteriores

Los archivos del juego original se conservan como `legacy-index.html`, `css/legacy-styles.css` y los scripts originales en `static/js/` para referencia. La aplicación integrada actual utiliza `templates/`, `static/css/app.css`, `static/js/game-app.js` y `static/js/admin-app.js`.
