from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import InventoryItem
from app.services.inventory_service import inventory_service, InventoryError

bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@bp.route('/')
@login_required
def inventory_page():
    return render_template('inventory/inventory.html')


@bp.route('/api/list')
@login_required
def list_items():
    items = inventory_service.list_items(current_user.id)
    return jsonify({
        'success': True,
        'items': [i.to_dict() for i in items],
        'total_value': inventory_service.total_inventory_value(current_user.id),
        'low_stock_count': len(inventory_service.low_stock_items(current_user.id)),
    })


@bp.route('/api/add', methods=['POST'])
@login_required
def add_item():
    data = request.get_json() or {}
    try:
        item = inventory_service.create_item(
            user_id=current_user.id,
            name=data.get('name'),
            sku=data.get('sku'),
            unit=data.get('unit', 'pcs'),
            unit_cost=data.get('unit_cost', 0),
            selling_price=data.get('selling_price', 0),
            opening_quantity=data.get('opening_quantity', 0),
            reorder_level=data.get('reorder_level', 0),
        )
        return jsonify({'success': True, 'item': item.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/<string:public_id>/purchase', methods=['POST'])
@login_required
def purchase(public_id):
    item = InventoryItem.query.filter_by(public_id=public_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    try:
        item = inventory_service.record_purchase(
            user_id=current_user.id,
            item_id=item.id,
            quantity=data.get('quantity'),
            unit_cost=data.get('unit_cost'),
            description=data.get('description'),
            payment_method=data.get('payment_method', 'cash'),
        )
        return jsonify({'success': True, 'item': item.to_dict()})
    except InventoryError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/<string:public_id>/sale', methods=['POST'])
@login_required
def sale(public_id):
    item = InventoryItem.query.filter_by(public_id=public_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    try:
        item = inventory_service.record_sale(
            user_id=current_user.id,
            item_id=item.id,
            quantity=data.get('quantity'),
            unit_price=data.get('unit_price'),
            description=data.get('description'),
            payment_method=data.get('payment_method', 'cash'),
        )
        return jsonify({'success': True, 'item': item.to_dict()})
    except InventoryError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/<string:public_id>/adjust', methods=['POST'])
@login_required
def adjust(public_id):
    item = InventoryItem.query.filter_by(public_id=public_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    try:
        item = inventory_service.adjust_stock(
            user_id=current_user.id,
            item_id=item.id,
            new_quantity=data.get('new_quantity'),
            notes=data.get('notes'),
        )
        return jsonify({'success': True, 'item': item.to_dict()})
    except InventoryError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/<string:public_id>', methods=['DELETE'])
@login_required
def deactivate_item(public_id):
    item = InventoryItem.query.filter_by(public_id=public_id, user_id=current_user.id).first_or_404()
    item.is_active = False
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/low-stock')
@login_required
def low_stock():
    items = inventory_service.low_stock_items(current_user.id)
    return jsonify({'success': True, 'items': [i.to_dict() for i in items]})
