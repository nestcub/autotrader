const socket = io();
let stockData = {};

// Socket.io event handlers
socket.on('updates', function(data) {
    stockData = data.stocks;
    updateStockDisplay();
});

socket.on('portfolio_update', function(data) {
    if (data.email === userEmail) {  // userEmail will be set in the template
        updatePortfolioDisplay(data.portfolio);
    }
});

function updateStockDisplay() {
    for (const [symbol, data] of Object.entries(stockData)) {
        const row = document.getElementById(symbol);
        if (row) {
            const priceCell = row.querySelector('.price');
            const changeCell = row.querySelector('.change');
            const tradeSignalCell = row.querySelector('.trade-signal');
            const stopLossCell = row.querySelector('.stop-loss');

            priceCell.textContent = `₹${data.price.toFixed(2)}`;
            changeCell.textContent = `${data.change.toFixed(2)}%`;
            changeCell.className = data.change >= 0 ? 'change text-success' : 'change text-danger';

            if (tradeSignalCell) tradeSignalCell.textContent = data.trade_signal || "-";
            if (stopLossCell) stopLossCell.textContent = data.stop_loss ? `₹${data.stop_loss.toFixed(2)}` : "-";
            
            // Update modal if open and showing this stock
            if (document.getElementById('stockSymbol').value === symbol) {
                document.getElementById('currentPrice').textContent = `₹${data.price.toFixed(2)}`;
                document.getElementById('tradeSignal').textContent = data.trade_signal || "-";
                document.getElementById('stopLoss').textContent = data.stop_loss ? `₹${data.stop_loss.toFixed(2)}` : "-";
                updateTotalCost();
            }
            
        }
    }
}

function updatePortfolioDisplay(portfolio) {
    // Update balance
    const balanceElement = document.querySelector('.card-text');
    if (balanceElement) {
        balanceElement.textContent = `Balance: ₹${portfolio.balance.toFixed(2)}`;
    }

    // Update holdings
    const holdingsContainer = document.getElementById('holdings');
    if (portfolio.holdings.length === 0) {
        holdingsContainer.innerHTML = '<p>No holdings yet. Start trading!</p>';
    } else {
        holdingsContainer.innerHTML = portfolio.holdings
            .map(holding => `
                <div class="holding-item mb-2">
                    <strong>${holding.symbol}</strong>
                    <br>
                    Quantity: ${holding.quantity}
                    <br>
                    Avg Price: ₹${holding.avg_price.toFixed(2)}
                </div>
            `)
            .join('');
    }
}

// Trade modal handling
document.addEventListener('DOMContentLoaded', function() {
    const tradeModal = document.getElementById('tradeModal');
    const quantityInput = document.getElementById('quantity');

    // Update modal when opened
    tradeModal.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        const symbol = button.getAttribute('data-symbol');
        const name = button.getAttribute('data-name');
        
        document.getElementById('selectedStock').textContent = `${name} (${symbol})`;
        document.getElementById('stockSymbol').value = symbol;
        document.getElementById('currentPrice').textContent = stockData[symbol] ? `₹${stockData[symbol].price.toFixed(2)}` : '-';
        document.getElementById('tradeSignal').textContent = stockData[symbol] ? stockData[symbol].trade_signal || "-" : "-";
        document.getElementById('stopLoss').textContent = stockData[symbol] && stockData[symbol].stop_loss ? `₹${stockData[symbol].stop_loss.toFixed(2)}` : "-";
            
        
        // Reset form
        document.getElementById('tradeForm').reset();
        document.getElementById('tradeError').classList.add('d-none');
        document.getElementById('totalCost').textContent = '-';
    });

    // Calculate total cost when quantity changes
    quantityInput.addEventListener('input', updateTotalCost);
});

function updateTotalCost() {
    const symbol = document.getElementById('stockSymbol').value;
    const quantity = parseInt(document.getElementById('quantity').value) || 0;
    
    if (stockData[symbol] && quantity > 0) {
        const total = stockData[symbol].price * quantity;
        document.getElementById('totalCost').textContent = `₹${total.toFixed(2)}`;
    } else {
        document.getElementById('totalCost').textContent = '-';
    }
}

function trade(action) {
    const symbol = document.getElementById('stockSymbol').value;
    const quantity = parseInt(document.getElementById('quantity').value);
    const errorElement = document.getElementById('tradeError');

    if (!symbol || !quantity) {
        errorElement.textContent = 'Please enter a valid quantity';
        errorElement.classList.remove('d-none');
        return;
    }

    fetch('/trade', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: action,
            symbol: symbol,
            quantity: quantity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            errorElement.textContent = data.error;
            errorElement.classList.remove('d-none');
        } else {
            // Close modal on success
            const modal = bootstrap.Modal.getInstance(document.getElementById('tradeModal'));
            modal.hide();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        errorElement.textContent = 'An error occurred while processing your trade';
        errorElement.classList.remove('d-none');
    });
} 