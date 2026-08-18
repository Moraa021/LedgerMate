from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import InventoryItem, InventoryMovement
from app.extensions import db, csrf
from decimal import Decimal
import uuid

bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@bp.route('/')
@login_required
def inventory():
    return render_template('inventory/inventory.html')


@bp.route('/api/list')
@login_required
def list_items():
    items = InventoryItem.query.filter_by(
        user_id=current_user.id, is_deleted=False
    ).order_by(InventoryItem.name.asc()).all()

    data = [i.to_dict() for i in items]
    total_value = sum(i['stock_value'] for i in data)
    low_stock_count = sum(1 for i in data if i['is_low_stock'])

    return jsonify({
        'success': True,
        'items': data,
        'total_stock_value': total_value,
        'low_stock_count': low_stock_count
    })


@bp.route('/api/add', methods=['POST'])
@csrf.exempt
@login_required
def add_item():
    try:
        payload = request.get_json() or request.form
        item = InventoryItem(
            public_id=str(uuid.uuid4()),
            user_id=current_user.id,
            name=payload.get('name'),
            sku=payload.get('sku'),
            category=payload.get('category'),
            quantity_on_hand=Decimal(str(payload.get('quantity_on_hand') or 0)),
            unit_cost=Decimal(str(payload.get('unit_cost') or 0)),
            unit_price=Decimal(str(payload.get('unit_price') or 0)),
            reorder_level=Decimal(str(payload.get('reorder_level') or 5)),
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'item': item.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/<public_id>/movement', methods=['POST'])
@csrf.exempt
@login_required
def add_movement(public_id):
    """Record a restock, sale, or manual adjustment against an item."""
    try:
        item = InventoryItem.query.filter_by(public_id=public_id, user_id=current_user.id).first()
        if not item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        payload = request.get_json() or request.form
        movement_type = payload.get('movement_type')  # 'restock', 'sale', 'adjustment'
        quantity = Decimal(str(payload.get('quantity') or 0))

        if movement_type == 'restock':
            item.quantity_on_hand += quantity
            unit_cost = payload.get('unit_cost')
            if unit_cost:
                item.unit_cost = Decimal(str(unit_cost))
        elif movement_type == 'sale':
            if quantity > item.quantity_on_hand:
                return jsonify({'success': False, 'error': 'Not enough stock on hand'}), 400
            item.quantity_on_hand -= quantity
        elif movement_type == 'adjustment':
            item.quantity_on_hand = quantity
        else:
            return jsonify({'success': False, 'error': 'Invalid movement_type'}), 400

        movement = InventoryMovement(
            item_id=item.id,
            user_id=current_user.id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=item.unit_cost,
            unit_price=item.unit_price,
            notes=payload.get('notes')
        )
        db.session.add(movement)
        db.session.commit()
        return jsonify({'success': True, 'item': item.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/<public_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
def delete_item(public_id):
    item = InventoryItem.query.filter_by(public_id=public_id, user_id=current_user.id).first()
    if item:
        item.is_deleted = True
        db.session.commit()
    return jsonify({'success': True})
