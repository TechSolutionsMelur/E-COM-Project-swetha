const CSRF = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

// ── Add item to cart ──
function addItem(itemId, isCartPage = false) {
    fetch(`/orders/cart/add/${itemId}/`, {
        method:  'POST',
        headers: {
            'X-CSRFToken': CSRF,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'confirm_clear=no',
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            updateQtyDisplay(itemId, data.item_qty);
            updateCartCount(data.cart_count);
            updateSubtotals(data.cart_subtotal, itemId, data.item_total);
            showToast(data.message, 'success');
        } else if (data.status === 'conflict') {
            showConflictModal(data.message, data.item_id);
        }
    })
    .catch(() => showToast('Something went wrong.', 'error'));
}

// ── Remove (decrement) item ──
function removeItem(itemId, isCartPage = false) {
    fetch(`/orders/cart/remove/${itemId}/`, {
        method:  'POST',
        headers: { 'X-CSRFToken': CSRF },
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            if (data.item_qty === 0) {
                removeItemFromDOM(itemId, isCartPage);
            } else {
                updateQtyDisplay(itemId, data.item_qty);
                updateSubtotals(data.cart_subtotal, itemId, data.item_total);
            }
            updateCartCount(data.cart_count);
            if (data.cart_count === 0) handleEmptyCart(isCartPage);
        }
    })
    .catch(() => showToast('Something went wrong.', 'error'));
}

// ── Delete entire item row ──
function deleteItem(itemId, isCartPage = false) {
    fetch(`/orders/cart/delete/${itemId}/`, {
        method:  'POST',
        headers: { 'X-CSRFToken': CSRF },
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            removeItemFromDOM(itemId, isCartPage);
            updateCartCount(data.cart_count);
            updateSubtotals(data.cart_subtotal, itemId, '0');
            if (data.cart_count === 0) handleEmptyCart(isCartPage);
        }
    })
    .catch(() => showToast('Something went wrong.', 'error'));
}

// ── DOM helpers ──
function updateQtyDisplay(itemId, qty) {
    // Update all qty displays with this item id
    document.querySelectorAll(`#qty${itemId}`).forEach(el => {
        el.textContent = qty;
    });

    // Swap Add button ↔ qty controls on menu page
    const controls = document.getElementById(`controls${itemId}`);
    if (controls) {
        if (qty > 0) {
            controls.innerHTML = `
                <div class="qty-controls active">
                    <button class="qty-btn minus"
                            onclick="removeItem(${itemId})">
                        <i class="bi bi-dash"></i>
                    </button>
                    <span class="qty-value" id="qty${itemId}">${qty}</span>
                    <button class="qty-btn plus"
                            onclick="addItem(${itemId})">
                        <i class="bi bi-plus"></i>
                    </button>
                </div>`;
        } else {
            controls.innerHTML = `
                <button class="btn-add-item"
                        onclick="addItem(${itemId})">
                    <i class="bi bi-plus"></i> Add
                </button>`;
        }
    }
}

function updateCartCount(count) {
    const badge = document.getElementById('navCartCount');
    if (badge) {
        badge.textContent = count;
        badge.classList.toggle('d-none', count === 0);
    }
}

function updateSubtotals(subtotal, itemId, itemTotal) {
    // Cart sidebar subtotal
    const sidebarSub = document.getElementById('cartSubtotal');
    if (sidebarSub) sidebarSub.textContent = `₹${subtotal}`;

    // Full cart page summary subtotal
    const summarySub = document.getElementById('summarySubtotal');
    if (summarySub) summarySub.textContent = `₹${subtotal}`;

    // Per-item total
    const itemTotalEl = document.getElementById(`itemTotal${itemId}`);
    if (itemTotalEl) itemTotalEl.textContent = `₹${itemTotal}`;
}

function removeItemFromDOM(itemId, isCartPage) {
    if (isCartPage) {
        const row = document.getElementById(`fullCartRow${itemId}`);
        if (row) row.remove();
    }
    const sidebarRow = document.getElementById(`cartRow${itemId}`);
    if (sidebarRow) sidebarRow.remove();

    // Revert menu card to Add button
    updateQtyDisplay(itemId, 0);
}

function handleEmptyCart(isCartPage) {
    // Show empty state in sidebar
    const body = document.getElementById('cartBody');
    if (body) {
        body.innerHTML = `
            <div class="cart-empty-state">
                <i class="bi bi-bag"></i>
                <p>Your cart is empty</p>
                <small style="color:var(--text-muted);">
                    Add items from the menu to get started
                </small>
            </div>`;
    }
    // Reload full cart page to show empty state
    if (isCartPage) {
        setTimeout(() => window.location.reload(), 600);
    }
}

// ── Conflict modal ──
let conflictItemId = null;

function showConflictModal(message, itemId) {
    conflictItemId = itemId;
    document.getElementById('conflictMsg').innerHTML = message;
    document.getElementById('conflictOverlay').style.display = 'flex';
}

function closeConflict() {
    document.getElementById('conflictOverlay').style.display = 'none';
    conflictItemId = null;
}

const confirmClearBtn = document.getElementById('confirmClearBtn');
if (confirmClearBtn) {
    confirmClearBtn.addEventListener('click', () => {
        if (!conflictItemId) return;
        closeConflict();
        // Re-send with confirm_clear=yes
        fetch(`/orders/cart/add/${conflictItemId}/`, {
            method:  'POST',
            headers: {
                'X-CSRFToken': CSRF,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'confirm_clear=yes',
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                updateQtyDisplay(conflictItemId, data.item_qty);
                updateCartCount(data.cart_count);
                showToast(data.message, 'success');
            }
        });
    });
}

// ── Toast notification ──
function showToast(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.style.cssText = `
        background: rgba(20,20,40,0.95);
        backdrop-filter: blur(20px);
        border: 1px solid ${type === 'success'
            ? 'rgba(16,185,129,0.4)'
            : 'rgba(220,53,69,0.4)'};
        border-radius: 12px;
        padding: 12px 18px;
        color: ${type === 'success' ? '#10b981' : '#ff6b7a'};
        font-size: 0.85rem;
        font-weight: 500;
        min-width: 220px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 8px;
        animation: slideInToast 0.3s ease;
    `;
    toast.innerHTML = `
        <i class="bi bi-${type === 'success'
            ? 'check-circle-fill'
            : 'exclamation-circle-fill'}"></i>
        ${message}
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// Add toast animation to page
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInToast {
        from { opacity:0; transform: translateX(20px); }
        to   { opacity:1; transform: translateX(0); }
    }
`;
document.head.appendChild(style);

/* ── Coupon / Promo Code ── */
function applyCoupon() {
    const code = document.getElementById('couponCode')?.value?.trim();
    if (!code) return;

    fetch('/orders/cart/coupon/apply/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': CSRF,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `code=${encodeURIComponent(code)}`,
    })
    .then(r => r.json())
    .then(data => {
        const msg = document.getElementById('couponMsg');
        if (data.status === 'ok') {
            // Show applied state
            document.getElementById('offerCodeText').textContent = code;
            document.getElementById('offerSavingText').textContent =
                data.discount;
            document.getElementById('summaryDiscount').textContent =
                data.discount;
            document.getElementById('offerApplied').style.display = 'flex';
            document.getElementById('couponInputRow').style.display = 'none';
            document.getElementById('discountRow').style.display = 'flex';
            showToast(data.message, 'success');
            // Recalculate total display
            recalcTotal();
        } else {
            msg.style.display = 'block';
            msg.style.color   = '#f87171';
            msg.textContent   = data.message;
        }
    })
    .catch(() => showToast('Something went wrong.', 'error'));
}

function removeCoupon() {
    fetch('/orders/cart/coupon/remove/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF },
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            document.getElementById('offerApplied').style.display = 'none';
            document.getElementById('couponInputRow').style.display = '';
            document.getElementById('discountRow').style.display = 'none';
            document.getElementById('couponCode').value = '';
            document.getElementById('summaryDiscount').textContent = '0';
            showToast('Offer removed.', 'success');
            recalcTotal();
        }
    });
}

function recalcTotal() {
    // Re-read all values and update total display
    const subtotalEl  = document.getElementById('summarySubtotal');
    const discountEl  = document.getElementById('summaryDiscount');
    const totalEl     = document.getElementById('cartFinalTotal');

    if (!subtotalEl || !totalEl) return;

    const subtotal  = parseFloat(subtotalEl.textContent.replace('₹','')) || 0;
    const discount  = parseFloat(discountEl?.textContent || '0') || 0;
    const delivery  = 40;
    const taxes     = Math.round(subtotal * 0.05 * 100) / 100;
    const total     = Math.max(subtotal - discount, 0) + delivery + taxes;

    totalEl.textContent = '₹' + total.toFixed(2);
}

// Allow pressing Enter on coupon input
document.addEventListener('DOMContentLoaded', () => {
    const couponInput = document.getElementById('couponCode');
    if (couponInput) {
        couponInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                applyCoupon();
            }
        });
    }
});