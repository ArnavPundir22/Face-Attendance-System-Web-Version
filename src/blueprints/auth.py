"""
Authentication Blueprint (Supabase Auth).

Routes: /login, /logout, /register, /forgot_password
"""

from flask import Blueprint, redirect, render_template, request, session, url_for
from src.utils.db import supabase, supabase_admin, is_valid_email
from supabase import AuthApiError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            return render_template('login.html', error="Email and password required")

        try:
            # Authenticate with Supabase Auth
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            user = auth_response.user
            
            # Check if user is admin via metadata
            metadata = user.user_metadata or {}
            is_admin = metadata.get('is_admin', False)
            username = metadata.get('username', email.split('@')[0])
            
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = is_admin
            session['user_id'] = user.id
            session['access_token'] = auth_response.session.access_token

            return redirect(url_for('attendance.index'))
            
        except Exception as e:
            error_message = str(e)
            if "AuthApiError" in error_message or hasattr(e, 'message'):
                error_message = getattr(e, 'message', str(e))
            else:
                error_message = "Invalid email or password"
            return render_template('login.html', error=error_message)

    error = request.args.get('error')
    info = request.args.get('info')
    return render_template('login.html', error=error, info=info)


@auth_bp.route('/logout')
def logout():
    try:
        # If we have an access token, we can sign out from Supabase as well
        if 'access_token' in session:
            supabase.auth.sign_out()
    except Exception:
        pass
    
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Admin-only user-creation route."""
    if not session.get('is_admin'):
        return render_template('login.html', error="Admin access required to create new users")

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email    = request.form.get('email', '').strip()

        if not username or not password or not email:
            return render_template('register.html', error="All fields are required")

        if not is_valid_email(email):
            return render_template('register.html', error="Invalid email format")

        if len(password) < 8:
            return render_template('register.html', error="Password must be at least 8 characters")

        try:
            # Create user using Supabase Admin API
            # This allows creating a user without auto-signing them in
            response = supabase_admin.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True, # Auto confirm since it's created by admin
                "user_metadata": {
                    "username": username,
                    "is_admin": False
                }
            })
            
            return render_template('register.html', success=f"User {username} successfully created.")
            
        except AuthApiError as e:
            return render_template('register.html', error=str(e.message))
        except Exception as e:
            return render_template('register.html', error="An error occurred while creating the user.")

    return render_template('register.html')


@auth_bp.route('/login/oauth/<provider>')
def oauth_login(provider):
    """Initiate OAuth sign-in flow."""
    # Maps 'linkedin' to 'linkedin_oidc' if needed by Supabase
    prov = 'linkedin_oidc' if provider == 'linkedin' else provider
    redirect_url = url_for('auth.callback', _external=True)
    try:
        res = supabase.auth.sign_in_with_oauth({
            "provider": prov,
            "options": {
                "redirect_to": redirect_url
            }
        })
        # Save code_verifier to Flask session for multi-process Gunicorn worker support (PKCE flow)
        storage_key = getattr(supabase.auth, "_storage_key", "supabase.auth.token")
        code_verifier = supabase.auth._storage.get_item(f"{storage_key}-code-verifier")
        if code_verifier:
            session['code_verifier'] = code_verifier
        return redirect(res.url)
    except Exception as e:
        return redirect(url_for('auth.login', error=str(e)))


@auth_bp.route('/auth/callback')
def callback():
    """Handle OAuth callback and session exchange."""
    code = request.args.get('code')
    error_description = request.args.get('error_description')
    
    if error_description:
        return redirect(url_for('auth.login', error=error_description))
        
    if code:
        try:
            code_verifier = session.pop('code_verifier', None)
            exchange_params = {"auth_code": code}
            if code_verifier:
                exchange_params["code_verifier"] = code_verifier

            res = supabase.auth.exchange_code_for_session(exchange_params)
            user = res.user
            metadata = user.user_metadata or {}

            # If 'username' is absent in metadata, this user was NOT pre-registered by admin.
            # Admin always sets 'username' in metadata via /register. Delete & block.
            if 'username' not in metadata:
                try:
                    supabase_admin.auth.admin.delete_user(user.id)
                except Exception:
                    pass
                return redirect(url_for('auth.login', error="Access denied. Your account is not registered in this system."))

            is_admin = metadata.get('is_admin', False)
            username = metadata.get('username', user.email.split('@')[0])

            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = is_admin
            session['user_id'] = user.id
            session['access_token'] = res.session.access_token
            return redirect(url_for('attendance.index'))
        except Exception as e:
            return redirect(url_for('auth.login', error=f"Auth exchange failed: {e}"))

    return redirect(url_for('auth.login', error="No authentication code received"))




