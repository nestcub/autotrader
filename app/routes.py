from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash
from flask_socketio import emit
from flask_dance.contrib.google import google, make_google_blueprint
from app.sockets import socketio
from app.stock_data import STOCKS, stock_data
from app.models import db, User, Portfolio, Holding, Transaction
from functools import wraps
from dotenv import load_dotenv  
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError  # Correct import for TokenExpiredError


load_dotenv()

main = Blueprint('main', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not google.authorized:
            flash('Please login to access this feature', 'warning')
            return redirect(url_for('google.login'))
        return f(*args, **kwargs)
    return decorated_function

@main.before_request
def make_session_permanent():
    session.permanent = True

@main.route('/')
def index():
    if google.authorized:
        try:
            resp = google.get("/oauth2/v2/userinfo")
            if resp.ok:
                email = resp.json()["email"]
                # Get or create user
                user = User.query.filter_by(email=email).first()
                if not user:
                    user = User(email=email)
                    portfolio = Portfolio(user=user)
                    db.session.add(user)
                    db.session.add(portfolio)
                    db.session.commit()
                    flash('Welcome! Your trading account has been created.', 'success')
                
                return render_template('index.html', 
                                    stocks=STOCKS,
                                    email=email,
                                    portfolio=user.portfolio)
        except TokenExpiredError:
            flash('Your session has expired. Please log in again.', 'warning')
            return redirect(url_for('google.login'))  # Redirect to login if token expired
        except Exception as e:
            print(f"Error fetching user info: {e}")
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('google.login'))
    
    return render_template('index.html', stocks=STOCKS)

@main.route('/trade', methods=['POST'])
@login_required
def trade():
    try:
        data = request.json
        action = data.get('action')
        symbol = data.get('symbol')
        quantity = int(data.get('quantity', 0))
        
        # Get user info
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return jsonify({'error': 'Authentication failed'}), 401
        
        email = resp.json()["email"]
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        portfolio = user.portfolio
        
        if symbol not in stock_data:
            return jsonify({'error': 'Invalid stock symbol'}), 400
        
        current_price = stock_data[symbol]['price']
        
        try:
            if action == 'buy':
                total_cost = current_price * quantity
                if total_cost > portfolio.balance:
                    return jsonify({'error': 'Insufficient funds'}), 400
                
                holding = Holding.query.filter_by(portfolio=portfolio, symbol=symbol).first()
                if not holding:
                    holding = Holding(
                        portfolio=portfolio,
                        symbol=symbol,
                        quantity=quantity,
                        avg_price=current_price
                    )
                    db.session.add(holding)
                else:
                    old_qty = holding.quantity
                    old_avg = holding.avg_price
                    new_qty = old_qty + quantity
                    new_avg = ((old_qty * old_avg) + (quantity * current_price)) / new_qty
                    holding.quantity = new_qty
                    holding.avg_price = new_avg
                
                portfolio.balance -= total_cost
                
            elif action == 'sell':
                holding = Holding.query.filter_by(portfolio=portfolio, symbol=symbol).first()
                if not holding:
                    return jsonify({'error': 'Stock not in portfolio'}), 400
                
                if quantity > holding.quantity:
                    return jsonify({'error': 'Insufficient stocks to sell'}), 400
                
                holding.quantity -= quantity
                if holding.quantity == 0:
                    db.session.delete(holding)
                
                portfolio.balance += (current_price * quantity)
            
            # Record transaction
            transaction = Transaction(
                portfolio=portfolio,
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=current_price
            )
            db.session.add(transaction)
            db.session.commit()
            
            # Emit updated portfolio to all clients
            socketio.emit('portfolio_update', {
                'email': email,
                'portfolio': {
                    'balance': portfolio.balance,
                    'holdings': [
                        {
                            'symbol': h.symbol,
                            'quantity': h.quantity,
                            'avg_price': h.avg_price
                        } for h in portfolio.holdings
                    ],
                    'transactions': [
                        {
                            'action': t.action,
                            'symbol': t.symbol,
                            'quantity': t.quantity,
                            'price': t.price,
                            'timestamp': t.timestamp.isoformat()
                        } for t in portfolio.transactions
                    ]
                }
            })
            
            return jsonify({
                'success': True,
                'portfolio': {
                    'balance': portfolio.balance,
                    'holdings': [
                        {
                            'symbol': h.symbol,
                            'quantity': h.quantity,
                            'avg_price': h.avg_price
                        } for h in portfolio.holdings
                    ]
                }
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error processing trade: {e}")
            return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        print(f"Error processing trade: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/google_login')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('main.index'))


google_blueprint = make_google_blueprint(client_id='GOOGLE_CLIENT_ID', client_secret='GOOGLE_CLIENT_SECRET', redirect_to='google_login')  # Define the google_blueprint

@main.route('/logout')
def logout():
    token = google_blueprint.token
    if token:
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token["access_token"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        del google_blueprint.token
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index')) 