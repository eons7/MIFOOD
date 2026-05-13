"""Тесты безопасности: политика паролей, rate limit, CSRF, admin_required,
session fixation, security headers."""
import os
import pytest

os.environ['FLASK_ENV'] = 'testing'

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402
from app.utils.security import validate_password  # noqa: E402


@pytest.fixture
def app():
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_with_csrf():
    """Отдельная фикстура с включённым CSRF — для проверки самого CSRF."""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    from werkzeug.security import generate_password_hash
    u = User(name='Admin', email='admin@x.x',
            password_hash=generate_password_hash('Admin123pwd'),
            is_admin=True)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def regular_user(app):
    from werkzeug.security import generate_password_hash
    u = User(name='User', email='u@x.x',
            password_hash=generate_password_hash('User123pwd'),
            is_admin=False)
    db.session.add(u)
    db.session.commit()
    return u


# ───────── Политика паролей ─────────

class TestPasswordPolicy:
    def test_too_short_rejected(self):
        assert validate_password('a1b') is not None
        assert validate_password('1234567') is not None  # 7 символов

    def test_only_digits_rejected(self):
        assert validate_password('12345678') is not None

    def test_only_letters_rejected(self):
        assert validate_password('abcdefgh') is not None
        assert validate_password('абвгдежз') is not None

    def test_valid_password_accepted(self):
        assert validate_password('Pass123word') is None
        assert validate_password('пароль123') is None
        assert validate_password('a1b2c3d4') is None

    def test_empty_rejected(self):
        assert validate_password('') is not None
        assert validate_password(None) is not None


# ───────── @admin_required ─────────

class TestAdminRequired:
    def test_anonymous_gets_401(self, client):
        r = client.get('/admin/orders')
        # Flask-Login по умолчанию редиректит на login → 302
        assert r.status_code in (302, 401)

    def test_regular_user_gets_403(self, client, regular_user):
        with client.session_transaction() as s:
            s['_user_id'] = str(regular_user.id)
            s['_fresh'] = True
        r = client.get('/admin/orders')
        assert r.status_code == 403

    def test_admin_passes(self, client, admin_user):
        with client.session_transaction() as s:
            s['_user_id'] = str(admin_user.id)
            s['_fresh'] = True
        r = client.get('/admin/orders')
        assert r.status_code == 200


# ───────── Rate limiting ─────────

class TestRateLimit:
    def test_login_rate_limit_kicks_in(self, client):
        codes = []
        for _ in range(15):
            r = client.post('/auth/login', data={'email': 'x@x.x', 'password': 'wrong'})
            codes.append(r.status_code)
        # До 10-го запроса включительно — 302 (редирект «неверный пароль»),
        # потом 429.
        assert 429 in codes, f'Ожидали 429 в {codes}'
        # Минимум 5 успешных перед лимитом
        non_429 = [c for c in codes if c != 429]
        assert len(non_429) >= 5


# ───────── CSRF ─────────

class TestCSRF:
    def test_post_without_token_rejected(self, app_with_csrf):
        c = app_with_csrf.test_client()
        r = c.post('/auth/login', data={'email': 'x@x.x', 'password': 'x'})
        # CSRFProtect возвращает 400 при отсутствии токена
        assert r.status_code == 400


# ───────── Security headers ─────────

class TestSecurityHeaders:
    def test_csp_present_in_response(self, client):
        r = client.get('/auth/login')
        csp = r.headers.get('Content-Security-Policy', '')
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        # самое важное: НЕТ unsafe-inline в script-src
        # ищем «script-src ...; » сегмент
        script_seg = next((s for s in csp.split(';') if s.strip().startswith('script-src')), '')
        assert "'unsafe-inline'" not in script_seg, f'unsafe-inline нашёлся в script-src: {script_seg}'

    def test_x_frame_options_present(self, client):
        r = client.get('/auth/login')
        assert r.headers.get('X-Frame-Options') in ('SAMEORIGIN', 'DENY')

    def test_referrer_policy_present(self, client):
        r = client.get('/auth/login')
        assert r.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_x_content_type_options(self, client):
        r = client.get('/auth/login')
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'


# ───────── Session fixation ─────────

class TestSessionFixation:
    def test_session_cleared_on_login(self, client, regular_user):
        with client.session_transaction() as s:
            s['attacker_planted'] = 'value'
        r = client.post('/auth/login',
                        data={'email': 'u@x.x', 'password': 'User123pwd'})
        assert r.status_code in (302, 200)
        with client.session_transaction() as s:
            assert 'attacker_planted' not in s


# ───────── security.txt ─────────

class TestSecurityTxt:
    def test_security_txt_served(self, client):
        r = client.get('/.well-known/security.txt')
        assert r.status_code == 200
        body = r.get_data(as_text=True)
        assert 'Contact:' in body
        assert 'Expires:' in body


# ───────── Регистрация требует валидный пароль ─────────

class TestRegistrationPasswordPolicy:
    def test_short_password_rejected_at_register(self, client):
        r = client.post('/auth/register', data={
            'name': 'X', 'email': 'new@x.x',
            'password': '123', 'password_confirm': '123',
        })
        # Форма ре-рендерится с введёнными данными — 200, не редирект.
        assert r.status_code == 200
        # Имя/email сохранились в форме (не очистились).
        body = r.get_data(as_text=True)
        assert 'new@x.x' in body
        # Юзер не создан.
        assert User.query.filter_by(email='new@x.x').count() == 0

    def test_valid_password_creates_user(self, client):
        r = client.post('/auth/register', data={
            'name': 'NewUser', 'email': 'new2@x.x',
            'password': 'Strong123', 'password_confirm': 'Strong123',
        })
        assert r.status_code == 302
        assert User.query.filter_by(email='new2@x.x').count() == 1
