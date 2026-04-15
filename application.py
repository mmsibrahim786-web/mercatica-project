from flask import Flask, render_template, request, redirect, session, url_for
from branding_utils import generate_branding_kit, safe_generate
import sqlite3
import os
from dotenv import load_dotenv

application = Flask(__name__)
application.secret_key = os.environ.get('SECRET_KEY', 'f84f02d2d0076d67d294bfece7269ab4a95277ef51429e4ec226c8f09ddbddde')

# -------------------- CONTEXT --------------------

@application.context_processor
def inject_theme():
    return dict(theme=session.get('theme', 'light'))

# -------------------- UTILS --------------------

def clean_text(text):
    lines = text.split('\n')
    cleaned = [line.strip().replace("**", "").replace("#", "") for line in lines if line.strip()]
    return '\n'.join(cleaned)

def extract_section_by_number(text, number):
    lines = text.split('\n')
    capture = False
    result = []

    for line in lines:
        if line.strip().startswith(f"{number}."):
            capture = True
            result.append(line.split(":", 1)[-1].strip())
        elif capture:
            if any(line.strip().startswith(f"{i}.") for i in range(1, 10)):
                break
            result.append(line.strip())

    return ' '.join(result).strip() if result else "Not found"

# -------------------- DATABASE INIT --------------------

def create_tables():
    conn = sqlite3.connect('branding.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS branding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            Domain TEXT,
            tagline TEXT,
            colors TEXT,
            logo_ideas TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS branding_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            brand TEXT,
            domain TEXT,
            font TEXT,
            colors TEXT,
            logo_prompt TEXT,
            domain_name TEXT,
            languages TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# -------------------- ROUTES --------------------

@application.route('/')
def home():
    return redirect('/login')

@application.route('/login', methods=['GET', 'POST'])
def login():
    message = request.args.get('message')
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email and password:
            session['user'] = email
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html', message=message)

@application.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('branding.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login', message='Account Created Successfully'))
    return render_template('signup.html')

@application.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    message = request.args.get('message')
    return render_template('dashboard.html', message=message)

@application.route('/toggle-theme')
def toggle_theme():
    current = session.get('theme', 'light')
    session['theme'] = 'dark' if current == 'light' else 'light'
    return redirect(request.referrer or url_for('dashboard'))

@application.route('/generate', methods=['POST'])
def generate():
    if 'user' not in session:
        return redirect('/login')

    store_name = request.form.get('store_name', '').strip()
    Domain = request.form.get('Domain', '').strip()
    if not store_name or not Domain:
        return render_template('result.html', branding={'tagline': 'Error', 'colors': 'Error', 'logo_ideas': 'Store name and domain required.'})

    branding = generate_branding_kit(store_name, Domain)
    branding = {k: clean_text(v) for k, v in branding.items()}

    conn = sqlite3.connect('branding.db')
    c = conn.cursor()
    c.execute("INSERT INTO branding (store_name, Domain, tagline, colors, logo_ideas) VALUES (?, ?, ?, ?, ?)",
              (store_name, Domain, branding['tagline'], branding['colors'], branding['logo_ideas']))
    conn.commit()
    conn.close()

    return render_template('result.html', branding=branding)

@application.route('/assistant', methods=['GET', 'POST'])
def branding_assistant():
    if 'user' not in session:
        return redirect('/login')

    suggestions = None

    if request.method == 'POST':
        brand = request.form.get('brand', '').strip()
        domain = request.form.get('domain', '').strip()
        if not brand or not domain:
            suggestions = {"font": "Error", "colors": "Error", "logo_prompt": "Error", "domain_name": "Error", "languages": "Brand and domain required."}
        else:
            prompt = f"""
        You are a branding expert. Provide branding suggestions for a brand named '{brand}' in the '{domain}' domain.

        Respond in exactly this format:
        1. Font Style & Size: [one-line suggestion]
        2. Color Palette: [one-line suggestion]
        3. Logo Prompt: [one-line suggestion]
        4. Suggested Domain Name Ideas: [one-line suggestion]
        5. Recommended Programming Languages and Technologies: [one-line suggestion]
        """

            text = safe_generate(prompt)
            text = clean_text(text)

            suggestions = {
                "font": clean_text(extract_section_by_number(text, "1")),
                "colors": clean_text(extract_section_by_number(text, "2")),
                "logo_prompt": clean_text(extract_section_by_number(text, "3")),
                "domain_name": clean_text(extract_section_by_number(text, "4")),
                "languages": clean_text(extract_section_by_number(text, "5"))
            }

        conn = sqlite3.connect('branding.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO branding_history (
                user, brand, domain, font, colors, logo_prompt, domain_name, languages
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user'], brand, domain or '', 
            suggestions['font'], suggestions['colors'],
            suggestions['logo_prompt'], suggestions['domain_name'],
            suggestions['languages']
        ))
        conn.commit()
        conn.close()

    return render_template('assistant.html', suggestions=suggestions)

@application.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('branding.db')
    c = conn.cursor()
    c.execute('''
        SELECT brand, domain, font, colors, logo_prompt, domain_name, languages, timestamp
        FROM branding_history
        WHERE user = ?
        ORDER BY timestamp DESC
    ''', (session['user'],))
    rows = c.fetchall()
    conn.close()

    return render_template('history.html', history=rows)

@application.route('/roadmap', methods=['GET', 'POST'])
def roadmap():
    if 'user' not in session:
        return redirect('/login')

    roadmap = None

    if request.method == 'POST':
        brand = request.form.get('brand', '').strip()
        domain = request.form.get('domain', '').strip()
        if not brand or not domain:
            roadmap = "Brand name and domain are required to generate a roadmap."
        else:
            prompt = f"""
        You are a branding strategist. Create a 30-day brand launch roadmap for a brand named '{brand}' in the '{domain}' domain.

        Break it into 4 weekly milestones. For each week, include:
        - Goal summary
        - Key tasks
        - Suggested tools or platforms
        - Optional tips or reminders
        """

            roadmap_text = safe_generate(prompt)
            roadmap = clean_text(roadmap_text)

    return render_template('roadmap.html', roadmap=roadmap)

@application.route('/personality', methods=['GET', 'POST'])
def personality():
    if 'user' not in session:
        return redirect('/login')

    profile = None

    if request.method == 'POST':
        brand = request.form.get('brand', '').strip()
        domain = request.form.get('domain', '').strip()
        if not brand or not domain:
            profile = "Brand name and domain are required."
        else:
            prompt = f"""
        You are a branding psychologist. Define the brand personality for a brand named '{brand}' in the '{domain}' domain.

        Include:
        - Emotional tone
        - Brand archetype
        - Suggested tone of voice
        - Ideal audience traits
        """

            profile_text = safe_generate(prompt)
            profile = clean_text(profile_text)

    return render_template('personality.html', profile=profile)

@application.route('/analyzer', methods=['GET', 'POST'])
def analyzer():
    if 'user' not in session:
        return redirect('/login')

    sentiment_data = {}
    persona_data = {}
    swot_data = {}

    if request.method == 'POST':
        brand = request.form.get('brand', '').strip()
        domain = request.form.get('domain', '').strip()
        if not brand or not domain:
            sentiment_data = {'Error': 'Brand and domain required'}
        else:
            # Sentiment
            prompt_sentiment = f"""
        Give emotional tone scores (0–100) for brand '{brand}' in '{domain}'.
        Include: Trust, Excitement, Elegance, Boldness, Friendliness.
        Format as: Trust: 85, Excitement: 70, ...
        """
            sentiment_text = clean_text(safe_generate(prompt_sentiment))
            for line in sentiment_text.split(','):
                if ':' in line:
                    key, val = line.strip().split(':')
                    try:
                        sentiment_data[key.strip()] = int(val.strip())
                    except ValueError:
                        sentiment_data[key.strip()] = 0

            # Persona
            prompt_persona = f"""
        Define audience persona for brand '{brand}' in '{domain}'.
        Include: Demographics, Psychographics, Motivations, Pain Points.
        Format as: Demographics: ..., Psychographics: ..., ...
        """
            persona_text = clean_text(safe_generate(prompt_persona))
            for line in persona_text.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    persona_data[key.strip()] = val.strip()

            # SWOT
            prompt_swot = f"""
        SWOT analysis for brand '{brand}' vs 2 competitors in '{domain}'.
        Format as: Strengths: ..., Weaknesses: ..., ...
        """
            swot_text = clean_text(safe_generate(prompt_swot))
            for line in swot_text.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    swot_data[key.strip()] = val.strip()

    return render_template('analyzer.html',
                           sentiment=sentiment_data,
                           persona=persona_data,
                           swot=swot_data)

@application.route('/about')
def about():
    if 'user' not in session:
        return redirect('/login')
    return render_template('about.html')

@application.route('/help')
def help():
    if 'user' not in session:
        return redirect('/login')
    return render_template('help.html')

@application.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        return redirect(url_for('dashboard', message='Thank you! Your message sent successfully.'))

    return render_template('contact.html')

@application.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------------------- MAIN --------------------

if __name__ == '__main__':
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
    create_tables()
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port, debug=False)
