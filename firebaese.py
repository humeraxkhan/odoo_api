from flask import Flask, request, jsonify
import xmlrpc.client
import os

app = Flask(__name__)

ODOO_URL = os.getenv("ODOO_URL", "https://dolphin-devices4.odoo.com")
ODOO_DB = os.getenv("ODOO_DB", "dolphin-devices4")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "khumera503@gmail.com")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "humera11")

@app.route("/create-delivery-order", methods=["POST"])
def create_delivery_order():
    try:
        data = request.json
        date = data["Date"]
        company = data["Company Name"].strip().lower()
        product_name = data["Product Name"]
        quantity = int(data["Quantity"])

        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

        # Get required Odoo IDs
        picking_type_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.picking.type', 'search_read', [[('code', '=', 'outgoing')]], {'fields': ['id']})[0]['id']
        location_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.location', 'search_read', [[('usage', '=', 'internal')]], {'fields': ['id']})[0]['id']
        location_dest_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.location', 'search_read', [[('usage', '=', 'customer')]], {'fields': ['id']})[0]['id']

        # Get or create customer
        customer = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search_read', [[('name', '=', company)]], {'fields': ['id']})
        customer_id = customer[0]['id'] if customer else models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'create', [{'name': company, 'company_type': 'company'}])

        # Get or create product
        product = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search_read', [[('name', '=', product_name)]], {'fields': ['id']})
        product_id = product[0]['id'] if product else models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'create', [{'name': product_name, 'type': 'product', 'uom_id': 1}])

        # Check stock
        stock = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.quant', 'search_read',
                                  [[('product_id', '=', product_id), ('location_id', '=', location_id)]],
                                  {'fields': ['quantity'], 'limit': 1})
        available_stock = stock[0]['quantity'] if stock else 0
        status = "Available" if quantity <= available_stock else "Out of Stock"

        order_id = ""
        if status == "Available":
            order_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'stock.picking', 'create', [{
                'partner_id': customer_id,
                'picking_type_id': picking_type_id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'move_ids_without_package': [(0, 0, {
                    'name': product_name,
                    'product_id': product_id,
                    'product_uom_qty': quantity,
                    'product_uom': 1,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id
                })],
            }])

        return jsonify({
            "order_id": order_id,
            "stock": available_stock,
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
