from flask import request, session
from flask_socketio import emit
from flask_dance.contrib.google import google
from app import socketio
from app.stock_data import stock_data
from app.models import db, User

@socketio.on('connect')
def handle_connect():
    """Handle new socket connections"""
    try:
        if google.authorized:
            resp = google.get("/oauth2/v2/userinfo")
            if resp.ok:
                email = resp.json()["email"]
                user = User.query.filter_by(email=email).first()
                if user:
                    # Send initial data to the new client
                    emit('updates', {'stocks': stock_data})
                    emit('portfolio_update', {
                        'email': email,
                        'portfolio': {
                            'balance': user.portfolio.balance,
                            'holdings': [
                                {
                                    'symbol': h.symbol,
                                    'quantity': h.quantity,
                                    'avg_price': h.avg_price
                                } for h in user.portfolio.holdings
                            ],
                            'transactions': [
                                {
                                    'action': t.action,
                                    'symbol': t.symbol,
                                    'quantity': t.quantity,
                                    'price': t.price,
                                    'timestamp': t.timestamp.isoformat()
                                } for t in user.portfolio.transactions
                            ]
                        }
                    })
    except Exception as e:
        print(f"Error in connect handler: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle socket disconnections"""
    pass 