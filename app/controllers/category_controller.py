from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app.models import Category, Transaction
from app.extensions import db
from datetime import datetime

bp = Blueprint('categories', __name__, url_prefix='/categories')

@bp.route('/')
@login_required
def categories():
    """Categories management page"""
    return render_template('categories/categories.html')

@bp.route('/api/list')
@login_required
def list_categories():
    """API endpoint to list categories"""
    try:
        # Get user's custom categories and system categories
        categories = Category.query.filter(
            (Category.user_id == current_user.id) | (Category.is_system == True)
        ).all()
        
        category_list = []
        for cat in categories:
            # Count transactions using this category
            transaction_count = Transaction.query.filter_by(
                category_id=cat.id,
                user_id=current_user.id,
                is_deleted=False
            ).count()
            
            category_list.append({
                'id': cat.id,
                'name': cat.name,
                'name_sw': cat.name_sw,
                'type': cat.type,
                'icon': cat.icon,
                'color': cat.color,
                'is_system': cat.is_system,
                'transaction_count': transaction_count
            })
        
        return jsonify({
            'success': True,
            'categories': category_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/add', methods=['POST'])
@login_required
def add_category():
    """Add new category"""
    try:
        data = request.get_json()
        
        name = data.get('name')
        name_sw = data.get('name_sw', '')
        category_type = data.get('type')
        icon = data.get('icon', '📁')
        color = data.get('color', '#3498db')
        
        # Validation
        if not name or not category_type:
            return jsonify({
                'success': False,
                'error': 'Name and type are required'
            }), 400
        
        # Check if category already exists for this user
        existing = Category.query.filter_by(
            name=name,
            user_id=current_user.id
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Category with this name already exists'
            }), 400
        
        # Create category
        category = Category(
            name=name,
            name_sw=name_sw,
            type=category_type,
            icon=icon,
            color=color,
            user_id=current_user.id,
            is_system=False
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category added successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'name_sw': category.name_sw,
                'type': category.type,
                'icon': category.icon,
                'color': category.color
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """Update category"""
    try:
        category = Category.query.filter_by(
            id=category_id,
            user_id=current_user.id
        ).first_or_404()
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            # Check if new name conflicts
            existing = Category.query.filter_by(
                name=data['name'],
                user_id=current_user.id
            ).first()
            if existing and existing.id != category_id:
                return jsonify({
                    'success': False,
                    'error': 'Category with this name already exists'
                }), 400
            category.name = data['name']
        
        if 'name_sw' in data:
            category.name_sw = data['name_sw']
        
        if 'type' in data:
            category.type = data['type']
        
        if 'icon' in data:
            category.icon = data['icon']
        
        if 'color' in data:
            category.color = data['color']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """Delete category"""
    try:
        category = Category.query.filter_by(
            id=category_id,
            user_id=current_user.id
        ).first_or_404()
        
        # Check if category has transactions
        transaction_count = Transaction.query.filter_by(
            category_id=category_id,
            user_id=current_user.id
        ).count()
        
        if transaction_count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete category with {transaction_count} transactions. Please reassign transactions first.'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/defaults')
@login_required
def get_default_categories():
    """Get default system categories"""
    try:
        default_categories = Category.query.filter_by(is_system=True).all()
        
        categories_list = []
        for cat in default_categories:
            categories_list.append({
                'id': cat.id,
                'name': cat.name,
                'name_sw': cat.name_sw,
                'type': cat.type,
                'icon': cat.icon,
                'color': cat.color
            })
        
        return jsonify({
            'success': True,
            'categories': categories_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/stats')
@login_required
def category_stats():
    """Get statistics for categories"""
    try:
        # Get all categories for user
        categories = Category.query.filter(
            (Category.user_id == current_user.id) | (Category.is_system == True)
        ).all()
        
        stats = {
            'total_categories': len(categories),
            'income_categories': 0,
            'expense_categories': 0,
            'most_used': None,
            'least_used': None
        }
        
        category_usage = []
        
        for cat in categories:
            if cat.type == 'income':
                stats['income_categories'] += 1
            else:
                stats['expense_categories'] += 1
            
            # Count transactions
            count = Transaction.query.filter_by(
                category_id=cat.id,
                user_id=current_user.id,
                is_deleted=False
            ).count()
            
            category_usage.append({
                'name': cat.name,
                'count': count
            })
        
        # Find most and least used
        if category_usage:
            stats['most_used'] = max(category_usage, key=lambda x: x['count'])
            stats['least_used'] = min(category_usage, key=lambda x: x['count'])
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500