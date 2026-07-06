"""
Inventory management service.

Uses weighted-average costing:
- On purchase: new_unit_cost = (old_qty*old_cost + bought_qty*bought_cost) / (old_qty+bought_qty)
- On sale: COGS = qty_sold * current weighted-average unit_cost

Every purchase/sale also creates a ledger Transaction, so the books and the
stock room always agree, and the P&L/Balance Sheet services can read straight
from the ledger + current stock valuation.
"""
from datetime import datetime
from decimal import Decimal
from app.extensions import db
from app.models import InventoryItem, StockMovement, Transaction, Category


class InventoryError(Exception):
    pass


class InventoryService:

    def _get_or_create_category(self, user_id, name, cat_type, icon='📦'):
        category = Category.query.filter_by(user_id=user_id, name=name).first()
        if not category:
            category = Category(user_id=user_id, name=name, type=cat_type, icon=icon,
                                 is_system=False)
            db.session.add(category)
            db.session.flush()
        return category

    def create_item(self, user_id, name, sku=None, unit='pcs', unit_cost=0,
                     selling_price=0, opening_quantity=0, reorder_level=0):
        item = InventoryItem(
            user_id=user_id,
            name=name,
            sku=sku or None,
            unit=unit,
            unit_cost=Decimal(str(unit_cost or 0)),
            selling_price=Decimal(str(selling_price or 0)),
            quantity_on_hand=Decimal(str(opening_quantity or 0)),
            reorder_level=Decimal(str(reorder_level or 0)),
        )
        db.session.add(item)
        db.session.flush()

        if opening_quantity and float(opening_quantity) > 0:
            movement = StockMovement(
                user_id=user_id,
                item_id=item.id,
                movement_type='adjustment',
                quantity=Decimal(str(opening_quantity)),
                unit_cost=Decimal(str(unit_cost or 0)),
                notes='Opening stock',
            )
            db.session.add(movement)

        db.session.commit()
        return item

    def record_purchase(self, user_id, item_id, quantity, unit_cost, description=None,
                         payment_method='cash', post_to_ledger=True):
        """Buying more stock. Updates weighted-average cost and books an expense."""
        item = InventoryItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            raise InventoryError('Inventory item not found')

        quantity = Decimal(str(quantity))
        unit_cost = Decimal(str(unit_cost))
        if quantity <= 0:
            raise InventoryError('Quantity must be greater than zero')

        old_qty = item.quantity_on_hand or Decimal('0')
        old_cost = item.unit_cost or Decimal('0')
        new_qty = old_qty + quantity

        if new_qty > 0:
            item.unit_cost = ((old_qty * old_cost) + (quantity * unit_cost)) / new_qty
        else:
            item.unit_cost = unit_cost
        item.quantity_on_hand = new_qty
        item.updated_at = datetime.utcnow()

        tx = None
        if post_to_ledger:
            category = self._get_or_create_category(user_id, 'Stock Purchase', 'expense')
            tx = Transaction(
                user_id=user_id,
                category_id=category.id,
                type='expense',
                amount=quantity * unit_cost,
                payment_method=payment_method,
                description=description or f'Stock purchase: {item.name}',
                inventory_item_id=item.id,
                is_cogs=False,
                is_inventory_purchase=True,
            )
            db.session.add(tx)
            db.session.flush()

        movement = StockMovement(
            user_id=user_id,
            item_id=item.id,
            movement_type='purchase',
            quantity=quantity,
            unit_cost=unit_cost,
            transaction_id=tx.id if tx else None,
            notes=description,
        )
        db.session.add(movement)
        db.session.commit()
        return item

    def record_sale(self, user_id, item_id, quantity, unit_price=None, description=None,
                     payment_method='cash', post_to_ledger=True):
        """Selling stock. Books revenue at unit_price and COGS at the item's
        current weighted-average cost."""
        item = InventoryItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            raise InventoryError('Inventory item not found')

        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise InventoryError('Quantity must be greater than zero')
        if quantity > (item.quantity_on_hand or Decimal('0')):
            raise InventoryError(
                f'Not enough stock: only {item.quantity_on_hand} {item.unit} available'
            )

        unit_price = Decimal(str(unit_price)) if unit_price is not None else (item.selling_price or Decimal('0'))
        cogs_unit_cost = item.unit_cost or Decimal('0')

        item.quantity_on_hand = item.quantity_on_hand - quantity
        item.updated_at = datetime.utcnow()

        revenue_tx = None
        cogs_tx = None
        if post_to_ledger:
            sales_category = self._get_or_create_category(user_id, 'Sales', 'income', icon='💰')
            revenue_tx = Transaction(
                user_id=user_id,
                category_id=sales_category.id,
                type='income',
                amount=quantity * unit_price,
                payment_method=payment_method,
                description=description or f'Sale: {item.name}',
                inventory_item_id=item.id,
            )
            db.session.add(revenue_tx)

            if cogs_unit_cost > 0:
                cogs_category = self._get_or_create_category(
                    user_id, 'Cost of Goods Sold', 'expense', icon='📦'
                )
                cogs_tx = Transaction(
                    user_id=user_id,
                    category_id=cogs_category.id,
                    type='expense',
                    amount=quantity * cogs_unit_cost,
                    payment_method=payment_method,
                    description=f'COGS: {item.name}',
                    inventory_item_id=item.id,
                    is_cogs=True,
                )
                db.session.add(cogs_tx)

            db.session.flush()

        movement = StockMovement(
            user_id=user_id,
            item_id=item.id,
            movement_type='sale',
            quantity=quantity,
            unit_cost=cogs_unit_cost,
            transaction_id=revenue_tx.id if revenue_tx else None,
            notes=description,
        )
        db.session.add(movement)
        db.session.commit()
        return item

    def adjust_stock(self, user_id, item_id, new_quantity, notes=None):
        """Manual correction (breakage, stocktake, etc.) - no ledger entry."""
        item = InventoryItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            raise InventoryError('Inventory item not found')

        new_quantity = Decimal(str(new_quantity))
        delta = new_quantity - (item.quantity_on_hand or Decimal('0'))
        item.quantity_on_hand = new_quantity
        item.updated_at = datetime.utcnow()

        movement = StockMovement(
            user_id=user_id,
            item_id=item.id,
            movement_type='adjustment',
            quantity=abs(delta),
            unit_cost=item.unit_cost or Decimal('0'),
            notes=notes or ('Stock increase' if delta >= 0 else 'Stock decrease'),
        )
        db.session.add(movement)
        db.session.commit()
        return item

    def list_items(self, user_id, active_only=True):
        query = InventoryItem.query.filter_by(user_id=user_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(InventoryItem.name).all()

    def low_stock_items(self, user_id):
        return [i for i in self.list_items(user_id) if i.is_low_stock]

    def total_inventory_value(self, user_id):
        return sum(i.stock_value for i in self.list_items(user_id))


inventory_service = InventoryService()
