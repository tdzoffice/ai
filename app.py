from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from werkzeug.middleware.proxy_fix import ProxyFix

from sqlalchemy import URL, create_engine

# Replace with your actual PostgreSQL connection details
connection_string = URL.create(
    'postgresql',
    username='thawdezin.office',
    password='jJyMXPvdsm63',
    host='ep-rough-rice-a1zsohm3.ap-southeast-1.aws.neon.tech',
    database='israfil',
    query={'sslmode': 'require'}  # Pass SSL mode as part of the query string
)

engine = create_engine(connection_string)

app = Flask(__name__)
CORS(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["14000 per day", "600 per hour"],
    storage_uri="memory://",
)
app.wsgi_app = ProxyFix(app.wsgi_app)

# Set SQLAlchemy database URI
app.config['SQLALCHEMY_DATABASE_URI'] = connection_string

# Set of banned IP addresses
BANNED_IPS = set()

# Secret key for authentication
SECRET_KEY_A = 'THAW_DE_ZIN'
EXPECTED_USER_AGENT = 'Hsu Myat Wai'

# Middleware function to validate the secret key
def authenticate():
    secret = request.headers.get('secret')
    user_agent = request.headers.get('User-Agent')

    # Get the client's IP address, considering it may be behind a proxy
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

    if secret == SECRET_KEY_A and user_agent == EXPECTED_USER_AGENT:
        # Proceed to the next middleware or route handler
        return True
    else:
        # Unauthorized access
        # Ban the IP if not authorized
        BANNED_IPS.add(client_ip)
        return False

# Apply the authentication middleware to the route
@app.before_request
def before_request():

    # Get the client's IP address, considering it may be behind a proxy
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

    if client_ip in BANNED_IPS:
        # IP is banned, return a 403 Forbidden response
        return jsonify({'message': f'Forbidden: {client_ip}'}), 403

    if not authenticate():
        return jsonify({'message': 'Unauthorized'}), 401

# Load environment variables from .env file (optional)
# load_dotenv()

# Initialize extensions
db = SQLAlchemy(app)

class Shop(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(255))
    address = db.Column(db.String(355))
    phone = db.Column(db.String(20))
    is_halal_certified = db.Column(db.Boolean)
    social_media_link = db.Column(db.String(255))
    latitude = db.Column(db.String(20))
    longitude = db.Column(db.String(20))
    expire_on = db.Column(db.Date)
    description = db.Column(db.Text)
    cluster = db.Column(db.String(50))
    food_category = db.Column(db.String(50))
    shop_type = db.Column(db.String(100))
    remark = db.Column(db.Text)
    img1 = db.Column(db.Text)
    img2 = db.Column(db.Text)
    img3 = db.Column(db.Text)
    preserved1 = db.Column(db.Text)
    preserved2 = db.Column(db.String(255))

# Create tables if they don't exist
with app.app_context():
    db.create_all()

@app.route('/addNewShop', methods=['POST'])
def add_new_shop():
    data = request.json

    # Convert 'expire_on' string to datetime.date object
    data['expire_on'] = datetime.strptime(data['expireOn'], '%Y-%m-%d').date()

    new_shop = Shop(
        id=data['id'],
        name=data['name'],
        address=data['address'],
        phone=data['phone'],
        is_halal_certified=data['isHalalCertified'],
        social_media_link=data['socialMediaLink'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        expire_on=data['expire_on'],
        description=data['description'],
        cluster=data['cluster'],
        food_category=data['foodCategory'],
        shop_type=data['shopType'],  
        remark=data['remark'],
        img1=data['img1'],
        img2=data['img2'],
        img3=data['img3'],
        preserved1=data['preserved1'],
        preserved2=data['preserved2']
    )

    try:
        db.session.add(new_shop)
        db.session.commit()
        return jsonify({'message': 'Shop added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# New route to retrieve all shops
@app.route('/retrieveAllShop', methods=['GET'])
@limiter.limit("100/day;10/hour;1/minute")
def retrieve_all_shop():
    try:
        # Get pagination parameters from the request or use default values
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))

        # Calculate offset based on pagination parameters
        offset = (page - 1) * page_size

        # Query a subset of shops from the database based on pagination parameters
        shops = Shop.query.offset(offset).limit(page_size).all()

        # Convert each shop object to a dictionary
        shop_list = []
        for shop in shops:
            shop_data = {
                'id': shop.id,
                'name': shop.name,
                'address': shop.address,
                'phone': shop.phone,
                'isHalalCertified': shop.is_halal_certified,
                'socialMediaLink': shop.social_media_link,
                'latitude': shop.latitude,
                'longitude': shop.longitude,
                'expireOn': shop.expire_on.strftime('%Y-%m-%d'),
                'description': shop.description,
                'cluster': shop.cluster,
                'foodCategory': shop.food_category,
                'shopType': shop.shop_type,  
                'remark': shop.remark,
                'img1': shop.img1,
                'img2': shop.img2,
                'img3': shop.img3,
                'preserved1': shop.preserved1,
                'preserved2': shop.preserved2
            }
            shop_list.append(shop_data)

        return jsonify({'shops': shop_list, 'page': page, 'pageSize': page_size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Function to calculate distance between two coordinates using Haversine formula
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in kilometers

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

# New route to search for nearest shops
@app.route('/nearOrNot', methods=['GET'])
def near_or_not():
    try:
        # Get parameters from the request
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        distance_unit = request.args.get('unit', 'km')  # Default unit is kilometers
        range_value = float(request.args.get('range', 5))  # Default range is 5 units

        # Get pagination parameters from the request or use default values
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))

        # Calculate offset based on pagination parameters
        offset = (page - 1) * page_size

        # Query all shops from the database
        all_shops = Shop.query.all()

        # Filter shops based on the specified range
        nearby_shops = [
            shop for shop in all_shops if calculate_distance(lat, lng, float(shop.latitude), float(shop.longitude)) <= range_value
        ]

        # Sort nearby shops based on distance
        nearby_shops.sort(key=lambda shop: calculate_distance(lat, lng, float(shop.latitude), float(shop.longitude)))

        # Apply pagination to the filtered shops
        paginated_shops = nearby_shops[offset:offset + page_size]

        # Convert each shop object to a dictionary
        shop_list = []
        for shop in paginated_shops:
            shop_data = {
                'id': shop.id,
                'name': shop.name,
                'address': shop.address,
                'distance': calculate_distance(lat, lng, float(shop.latitude), float(shop.longitude)),
                'unit': distance_unit,
                'expireOn': shop.expire_on.strftime('%Y-%m-%d'),
                # Add other relevant fields as needed
            }
            shop_list.append(shop_data)

        return jsonify({'nearbyShops': shop_list, 'page': page, 'pageSize': page_size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# New route to search for nearest shops
@app.route('/searchNearShop', methods=['GET'])
def search_near_shop():
    try:
        # Get parameters from the request
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        distance_unit = request.args.get('unit', 'km')  # Default unit is kilometers

        # Use 'radius' instead of 'range'
        radius = float(request.args.get('radius', 5))  # Default radius is 5 units

        # Get pagination parameters from the request or use default values
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))

        # Calculate offset based on pagination parameters
        offset = (page - 1) * page_size

        # Query all shops from the database
        all_shops = Shop.query.all()

        # Filter shops based on the specified radius
        nearby_shops = [
            shop for shop in all_shops if calculate_distance(lat, lng, float(shop.latitude), float(shop.longitude)) <= radius
        ]

        # Sort nearby shops based on distance
        nearby_shops.sort(key=lambda shop: calculate_distance(lat, lng, float(shop.latitude), float(shop.longitude)))

        # Apply pagination to the filtered shops
        paginated_shops = nearby_shops[offset:offset + page_size]

        # Convert each shop object to a dictionary
        shop_list = []
        for shop in paginated_shops:
            shop_data = {
                # 'id': shop.id,
                # 'name': shop.name,
                # 'address': shop.address,
                # 'distance': calculate_distance(lat, lng, float(shop.latitude), float(shop.longitude)),
                # 'unit': distance_unit,
                # 'expireOn': shop.expire_on.strftime('%Y-%m-%d'),
                'id': shop.id,
                'name': shop.name,
                'address': shop.address,
                'phone': shop.phone,
                'isHalalCertified': shop.is_halal_certified,
                'socialMediaLink': shop.social_media_link,
                'latitude': shop.latitude,
                'longitude': shop.longitude,
                'expireOn': shop.expire_on.strftime('%Y-%m-%d'),
                'description': shop.description,
                'cluster': shop.cluster,
                'foodCategory': shop.food_category,
                'shopType': shop.shop_type,  
                'remark': shop.remark,
                'img1': shop.img1,
                'img2': shop.img2,
                'img3': shop.img3,
                'preserved1': shop.preserved1,
                'preserved2': shop.preserved2
                # Add other relevant fields as needed
            }
            shop_list.append(shop_data)

        return jsonify({'nearbyShops': shop_list, 'page': page, 'pageSize': page_size}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



# New route to modify an existing shop
@app.route('/modifyShop', methods=['POST'])
def modify_shop():
    data = request.json

    # Check if the 'id' is provided in the request
    if 'id' not in data:
        return jsonify({'error': 'Missing shop ID'}), 400

    # Query the shop to be modified
    existing_shop = Shop.query.get(data['id'])

    # Check if the shop with the given ID exists
    if existing_shop is None:
        return jsonify({'error': 'Shop not found'}), 404

    # Update the existing shop data
    existing_shop.name = data.get('name', existing_shop.name)
    existing_shop.address = data.get('address', existing_shop.address)
    existing_shop.phone = data.get('phone', existing_shop.phone)
    existing_shop.is_halal_certified = data.get('isHalalCertified', existing_shop.is_halal_certified)
    existing_shop.social_media_link = data.get('socialMediaLink', existing_shop.social_media_link)
    existing_shop.latitude = data.get('latitude', existing_shop.latitude)
    existing_shop.longitude = data.get('longitude', existing_shop.longitude)
    existing_shop.expire_on = datetime.strptime(data.get('expireOn', existing_shop.expire_on), '%Y-%m-%d').date()
    existing_shop.description = data.get('description', existing_shop.description)
    existing_shop.cluster = data.get('cluster', existing_shop.cluster)
    existing_shop.food_category = data.get('foodCategory', existing_shop.food_category)
    existing_shop.shop_type = data.get('shopType', existing_shop.shop_type)  
    existing_shop.remark = data.get('remark', existing_shop.remark)
    existing_shop.img1 = data.get('img1', existing_shop.img1)
    existing_shop.img2 = data.get('img2', existing_shop.img2)
    existing_shop.img3 = data.get('img3', existing_shop.img3)
    existing_shop.preserved1 = data.get('preserved1', existing_shop.preserved1)
    existing_shop.preserved2 = data.get('preserved2', existing_shop.preserved2)

    try:
        db.session.commit()
        return jsonify({'message': 'Shop modified successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# New route to find a shop by ID
@app.route('/findShopByID', methods=['GET'])
def find_shop_by_id():
    try:
        # Get the shop ID from the request
        shop_id = request.args.get('id')

        # Query the shop from the database by ID
        shop = Shop.query.get(shop_id)

        if shop:
            # Convert the shop object to a dictionary
            shop_data = {
                'id': shop.id,
                'name': shop.name,
                'address': shop.address,
                'phone': shop.phone,
                'isHalalCertified': shop.is_halal_certified,
                'socialMediaLink': shop.social_media_link,
                'latitude': shop.latitude,
                'longitude': shop.longitude,
                'expireOn': shop.expire_on.strftime('%Y-%m-%d'),
                'description': shop.description,
                'cluster': shop.cluster,
                'foodCategory': shop.food_category,
                'shopType': shop.shop_type,  
                'remark': shop.remark,
                'img1': shop.img1,
                'img2': shop.img2,
                'img3': shop.img3,
                'preserved1': shop.preserved1,
                'preserved2': shop.preserved2
                # Add other relevant fields as needed
            }
            return jsonify(shop_data), 200
        else:
            return jsonify({'error': 'Shop not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# New route to delete a shop by ID
@app.route('/deleteShop', methods=['POST'])
def delete_shop():
    try:
        # Get the shop ID from the request
        data = request.json
        shop_id = data.get('id')

        # Query the shop from the database by ID
        shop = Shop.query.get(shop_id)

        if shop:
            db.session.delete(shop)
            db.session.commit()
            return jsonify({'message': 'Shop deleted successfully'}), 200
        else:
            return jsonify({'error': 'Shop not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
