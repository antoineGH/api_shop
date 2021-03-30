from logging import INFO, WARNING
from operator import add
from flask import Flask, jsonify, abort, make_response, request, render_template, url_for, redirect
from flask_cors.core import serialize_option
from flask_mail import Message, Mail
import os
import json
import datetime
import random
import string
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_bcrypt import Bcrypt
from flask_jwt_extended import ( JWTManager, jwt_required, create_access_token, jwt_refresh_token_required, create_refresh_token, get_jwt_identity, get_jwt_claims)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from flask_cors import CORS
import stripe


# # --- INFO: LOAD CONFIG VARIABLES ---
# with open('config.json') as config_file:
#     config = json.load(config_file)

# --- INFO: APP CONFIGURATION ---

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] =  os.environ.get('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=7)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=7)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS')
db = SQLAlchemy(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
stripe.api_key = os.environ.get('SRIPE_API_KEY')

# --- INFO: DATABASE MODEL ---

class User(db.Model):
    user_id = Column(Integer, primary_key=True)
    email = Column(String(40), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    role = Column(Integer, nullable=False, default=0)
    first_name = Column(String(40), nullable=False)
    last_name = Column(String(40), nullable=False)
    profile_picture = Column(String(250), nullable=True, default='default.jpg')

    def __repr__(self):
        return "ID: {}, email: {}, role: {}, first_name: {}, last_name: {}, profile_picture".format(self.user_id, self.email, self.role, self.first_name, self.last_name, self.profile_picture)

    def get_reset_token(self, expires_seconds=1800):
            s = Serializer(app.config['SECRET_KEY'], expires_seconds)
            return s.dumps({'user_id': self.user_id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try: 
            user_id = s.loads(token)['user_id']
        except: 
            return None
        return User.query.get(user_id)

    @property
    def serialize(self):
        return {
            'user_id': self.user_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'profile_picture': self.profile_picture,
            
        }

class UserDetails(db.Model):
    user_details_id= Column(Integer, primary_key=True)
    address = Column(String(100), nullable=True)
    city = Column(String(40), nullable=True)
    state = Column(String(50), nullable=True)
    postcode = Column(String(40), nullable=True)
    country = Column(String(40), nullable=True)
    phone = Column(String(40), nullable=True)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False)

    def __repr__(self):
        return "user_details_id: {}, address: {}, city: {} state: {}, postcode: {}, country: {}, phone: {}, user_id: {}".format(self.user_details_id, self.address, self.city, self.state, self.postcode, self.country, self.phone, self.user_id)

    @property
    def serialize(self):
        return {
            'user_details_id': self.user_details_id,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postcode': self.postcode,
            'country': self.country,
            'phone': self.phone,
            'user_id': self.user_id
        }

class Order(db.Model):
    order_id = Column(Integer, primary_key=True)
    order_number = Column(String(40), nullable=True)
    order_details = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False)

    def __repr__(self):
        return "order_id: {}, order_number: {}, order_details: {}, user_id: {}".format(self.order_id, self.order_number, self.order_details, self.user_id)

    @property
    def serialize(self):
        return {
            'order_id': self.order_id,
            'order_number': self.order_number,
            'order_details': self.order_details,
            'user_id': self.user_id,
        }

class Delivery(db.Model):
    delivery_id = Column(Integer, primary_key=True)
    status = Column(String(40), nullable=True)
    company = Column(String(40), nullable=True)
    phone = Column(String(40), nullable=True)
    order_id = Column(Integer, ForeignKey(Order.order_id), nullable=False)

    def __repr__(self):
        return "delivery_id: {}, status: {}, company: {}, phone: {}, order_id: {}".format(self.delivery_id, self.status, self.company, self.phone, self.order_id)

    @property
    def serialize(self):
        return {
            'delivery_id': self.delivery_id,
            'status': self.status,
            'company': self.company,
            'phone': self.phone,
            'order_id': self.order_id,
        }

class Payment(db.Model):
    payment_id = Column(Integer, primary_key=True)
    payment_stripe_number = Column(String(40), nullable=True)
    payment_method = Column(String(40), nullable=True)
    payment_method_number = Column(String(40), nullable=True)
    payment_date = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    amount = Column(Float, nullable=True)
    currency = Column(String(40), nullable=True)
    status = Column(String(40), nullable=True)
    order_id = Column(Integer, ForeignKey(Order.order_id), nullable=False)

    def __repr__(self):
        return "payment_id: {}, payment_method: {}, payment_date: {}, order_id: {}".format(self.payment_id, self.payment_method, self.payment_date, self.order_id)

    @property
    def serialize(self):
        return {
            'payment_id': self.payment_id,
            'payment_method': self.payment_method,
            'payment_method_number': self.payment_method_number,
            'payment_date': self.payment_date,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'order_id': self.order_id,
        }

class Category(db.Model):
    category_id = Column(Integer, primary_key=True)
    name = Column(String(40), nullable=True)
    gender = Column(String(40), nullable=True)
    description = Column(String(100), nullable=True)

    def __repr__(self):
            return "category_id: {}, name: {}, description: {}, gender: {}".format(self.category_id, self.name, self.description, self.gender)

    @property
    def serialize(self):
        return {
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
            'gender': self.gender,
        }

class Product(db.Model):
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(40), nullable=True)
    product_description = Column(String(100), nullable=True)
    price = Column(Float, nullable=True)
    stock = Column(Integer, nullable=True)
    images_url = Column(String(1000), nullable=True)
    category_id = Column(Integer, ForeignKey(Category.category_id), nullable=False)

    def __repr__(self):
            return "product_id: {}, product_name: {}, product_description: {}, price: {}, stock: {}, image_url: {}, category_id: {}".format(self.product_id, self.product_name, self.product_description, self.price, self.stock, self.images_url, self.category_id)

    @property
    def serialize(self):
        category = Category.query.get(self.category_id)
        category_name = category.name
        category_description = category.description
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_description': self.product_description,
            'price': self.price,
            'stock': self.stock,
            'images_url': self.images_url,
            'category_id': self.category_id,
            'category_name': category_name,
            'category_description': category_description,
        }

class OrderDetails(db.Model):
        order_details_id = Column(Integer, primary_key=True)
        quantity = Column(Integer, nullable=True)
        total = Column(Float, nullable=True)
        product_id = Column(Integer, ForeignKey(Product.product_id), nullable=False)
        order_id = Column(Integer, ForeignKey(Order.order_id), nullable=False)

        def __repr__(self):
            return "order_details_id: {}, quantity: {}, total: {}, product_id: {}, order_id: {}".format(self.order_details_id, self.quantity, self.total, self.product_id, self.order_id)

        @property
        def serialize(self):
            return {
                'order_details_id': self.order_details_id,
                'quantity': self.quantity,
                'total': self.total,
                'product_id': self.product_id,
                'order_id': self.order_id,
            }

class CartDetails(db.Model):
    cart_id = Column(Integer, primary_key=True)
    quantity = Column(Integer, nullable=True)
    total = Column(Integer, nullable=True)
    product_id = Column(Integer, ForeignKey(Product.product_id), nullable=False)
    user_id = Column(Integer, ForeignKey(User.user_id), nullable=False)

    def __repr__(self):
        return "cart_id: {}, quantity: {}, total: {}, product_id: {}, user_id: {}".format(self.cart_id, self.quantity, self.total, self.product_id, self.user_id)

    @property
    def serialize(self):
        return {
            'cart_id': self.cart_id,
            'quantity': self.quantity,
            'total': self.total,
            'product_id': self.product_id,
            'user_id': self.user_id
        }

# --- INFO: ADMIN FUNCTIONS ---

# UTILS FUNCTIONS
def isAdmin():
    current_user = get_jwt_identity()
    if not current_user == 'antoine.ratat@gmail.com':
        return jsonify({'message': "Unauthorized Admin only"}), 403

# CRUD FUNCTIONS CATEGORY
def getAdminCategories():
    categories = Category.query.all()
    return jsonify(categories=[category.serialize for category in categories])

def postAdminCategory(name, description):
    category_existing = Category.query.filter_by(name=name).first()
    if category_existing:
        return jsonify({'message': 'Category already existing'}), 400
    
    category = Category(name=name, description=description)
    db.session.add(category)
    db.session.commit()
    return jsonify(category=category.serialize)

def getAdminCategory(id):
    category = Category.query.get(id)
    if not category:
        return jsonify({'message': 'Category doesn\'t exist'}), 404
    return jsonify(category=category.serialize)

def updateAdminCategory(id, name, description):
    category = Category.query.get(id)
    if not category:
        return jsonify({'message': 'Category doesn\'t exist'}), 404
    if name:
        category_existing = Category.query.filter_by(name=name).first()
        if category_existing:
            if int(category_existing.category_id) != int(id):
                return jsonify({'message': 'Category already existing'}), 400
        category.name = name
    if description:
        category.description = description
    db.session.add(category)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated category with ID: {}'.format(id)}), 200)

def deleteAdminCategory(id):
    category = Category.query.get(id)
    if not category:
        return jsonify({'message': 'Category doesn\'t exist'}), 404
    db.session.delete(category)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed category with ID {}'.format(id)}), 200)

# CRUD FUNCTIONS PRODUCT
def getAdminProducts():
    products = Product.query.all()
    return jsonify(products=[product.serialize for product in products])

def postAdminProduct(product_name, product_description, price, stock, images_url, category_id):
    product_existing = Product.query.filter_by(product_name=product_name).first()
    if product_existing: 
        return jsonify({'message': 'Product already existing'}), 400

    category = Category.query.filter_by(category_id=category_id).first()
    if not category:
        return jsonify({'message': 'Category doesn\'t exist'}), 400

    product = Product(product_name=product_name, product_description=product_description, price=price, stock=stock, images_url=images_url, category_id=category_id)
    db.session.add(product)
    db.session.commit()
    return jsonify(product=product.serialize)

def getAdminProduct(id):
    product = Product.query.get(id)
    if not product: 
        return jsonify({'message': 'Product doesn\'t exist'}), 404
    return jsonify(product=product.serialize)

def updateAdminProduct(id, product_name, product_description, price, stock, images_url, category_id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'message': 'Product doesn\'t exist'}), 404
    if product_name:
        product_existing = Product.query.filter_by(product_name=product_name).first()
        if product_existing: 
            if int(product_existing.product_id) != int(id):
                return jsonify({'message': 'Product already existing'}), 400
        product.product_name = product_name
    if product_description:
        product.product_description = product_description
    if price:
        product.price = price
    if stock:
        product.stock = stock
    if images_url:
        product.images_url = images_url
    if category_id:
        category = Category.query.filter_by(category_id=category_id).first()
        if not category:
            return jsonify({'message': 'Category doesn\'t exist}'}), 400
        product.category_id = category_id
    
    db.session.add(product)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated product with ID: {}'.format(id)}), 200)

def deleteAdminProduct(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'message': 'Product doesn\'t exist'}), 404
    db.session.delete(product)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed product with ID {}'.format(id)}), 200)

# CRUD FUNCTIONS DELIVERY
def getAdminDeliverys():
    deliveries = Delivery.query.all()
    return jsonify(deliveries=[shipper.serialize for shipper in deliveries])

def postAdminDelivery(status, company, phone, order_id):
    order_id_existing = Order.query.get(order_id)
    if not order_id_existing:
        return jsonify({'message': 'Order ID doesn\'t exist'}), 404
    order_id_delivery_existing = Delivery.query.get(order_id)
    if order_id_delivery_existing:
        return jsonify({'message': 'Delivery Order ID already exists'}), 400
    delivery = Delivery(status=status, company=company, phone=phone, order_id=order_id)
    db.session.add(delivery)
    db.session.commit()
    return jsonify(delivery=delivery.serialize)

def getAdminDelivery(id):
    delivery = Delivery.query.get(id)
    if not delivery:
        return jsonify({'message': 'Delivery doesn\'t exist'}), 404
    return jsonify(delivery=delivery.serialize)

def updateAdminDelivery(id, status, company, phone, order_id):
    delivery = Delivery.query.get(id)
    if not delivery:
        return jsonify({'message': 'Delivery doesn\'t exist'}), 404
    if status:
        delivery.status = status
    if company:
        delivery.company = company
    if phone: 
        delivery.phone = phone
    if order_id:
        order_id_existing = Order.query.get(order_id)
        if not order_id_existing:
            return jsonify({'message': 'Order ID doesn\'t exist'}), 404
        order_id_delivery_existing = Delivery.query.filter_by(order_id=order_id).first()
        if order_id_delivery_existing:
                return jsonify({'message': 'Delivery Order ID already exists'}), 400
        delivery.order_id = order_id
    db.session.add(delivery)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated delivery with ID: {}'.format(id)}), 200)

def deleteAdminDelivery(id):
    shipper = Delivery.query.get(id)
    if not shipper:
        return jsonify({'message': 'Delivery doesn\'t exist'}), 404
    db.session.delete(shipper)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed shipper with ID {}'.format(id)}), 200)

# CRUD FUNCTIONS USER
def getAdminUsers():
    users = User.query.all()
    return jsonify(users=[user.serialize for user in users])

def postAdminUser(email, password, first_name, last_name, role, profile_picture, address, city, state, postcode, country, phone):
    user_existing = User.query.filter_by(email=email).first()
    if user_existing: 
        return jsonify({'message': 'User already existing'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password=hashed_password, first_name=first_name, last_name=last_name, role=role, profile_picture=profile_picture)
    db.session.add(user)
    db.session.commit()

    userdetails = UserDetails(address=address, city=city, state=state, postcode=postcode, country=country, phone=phone, user_id=user.user_id)
    db.session.add(userdetails)
    db.session.commit()
    return jsonify(user=user.serialize)

def getAdminUser(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User doesn\'t exist'}), 404
    return jsonify(user=user.serialize)

def updateAdminUser(id, email, password, first_name, last_name, role, profile_picture, address, city, state, postcode, country, phone):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User doesn\'t exist'}), 404
    userdetails = UserDetails.query.filter_by(user_id=user.user_id).first()
    if not userdetails:
        return jsonify({'message': 'User Details doesn\'t exist'}), 404
    if email:
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            if int(existing_email.user_id) != int(id):
                return jsonify({'message': 'Email already existing'}), 400
        user.email = email
    if password:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password = hashed_password
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    if role:
        user.role = role
    if profile_picture:
        user.profile_picture = profile_picture
    if address:
        userdetails.address = address
    if city:
        userdetails.city = city
    if state:
        userdetails.state = state
    if postcode:
        userdetails.postcode = postcode
    if country:
        userdetails.country = country
    if phone:
        userdetails.phone = phone
    
    db.session.add(user)
    db.session.add(userdetails)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated user with ID: {}'.format(id)}), 200)

def deleteAdminUser(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'message': 'User doesn\'t exist'}), 404
    userdetails = UserDetails.query.filter_by(user_id=id)
    if userdetails:
        for userdetail in userdetails:
            db.session.delete(userdetail)
    db.session.delete(user)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed user with ID: {}'.format(id)}), 200)

# CRUD FUNCTIONS USERDETAILS
def getAdminUserDetails():
    userdetails = UserDetails.query.all()
    return jsonify(userdetails=[userdetail.serialize for userdetail in userdetails])

def getAdminUserDetail(id):
    userdetail = UserDetails.query.get(id)
    if not userdetail:
        return jsonify({'message': 'UserDetails doesn\'t exist'}), 404
    return jsonify(userdetail=userdetail.serialize)

# CRUD FUNCTIONS ORDERS
def getAdminOrders():
    orders = Order.query.all()
    return jsonify(orders=[order.serialize for order in orders])

def postAdminOrder(order_number, order_details, user_id):
    order_existing = Order.query.filter_by(order_number=order_number).first()
    if order_existing: 
        return jsonify({'message': 'Order already existing'}), 400
    user_id_existing = User.query.get(user_id)
    if not user_id_existing:
        return jsonify({'message': 'User ID doesn\'t exist'}), 400
    order = Order(order_number=order_number, order_details=order_details, user_id=user_id)
    db.session.add(order)
    db.session.commit()
    return jsonify(order=order.serialize)

def getAdminOrder(id):
    order = Order.query.get(id)
    if not order:
        return jsonify({'message': 'Order doesn\'t exist'}), 404
    return jsonify(order=order.serialize)

def updateAdminOrder(id, order_number, order_details, user_id):
    order = Order.query.get(id)
    if not order:
        return jsonify({'message': 'Order doesn\'t exist'}), 400
    if order_number:
        order_existing = Order.query.filter_by(order_number=order_number).first()
        if order_existing: 
                return jsonify({'message': 'Order already existing'}), 400
        order.order_number = order_number
    if order_details:
        order.order_details = order_details
    if user_id:
        user_id_existing = User.query.get(user_id)
        if not user_id_existing:
            return jsonify({'message': 'User ID doesn\'t exist'}), 400
        order.user_id = user_id
    db.session.add(order)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated Order with ID: {}'.format(id)}), 200)

def deleteAdminOrder(id):
    order = Order.query.get(id)
    if not order:
        return jsonify({'message': 'Order doesn\'t exist'}), 404
    orderdetails = OrderDetails.query.filter_by(order_id=order.order_id)
    if orderdetails:
        for orderdetail in orderdetails:
            db.session.delete(orderdetail)
    db.session.delete(order)
    # db.session.delete(orderdetails)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed order with ID {}'.format(id)}), 200)

# CRUD FUNCTIONS ORDERDETAILS
def getAdminOrderDetails():
    orderdetails = OrderDetails.query.all()
    return jsonify(orderdetails=[orderdetail.serialize for orderdetail in orderdetails])

def postAdminOrderDetails(quantity, product_id, order_id):
    product_id_existing = Product.query.get(product_id)
    if not product_id_existing: 
        return jsonify({'message': 'Product ID does\'t exist'}), 400
    order_id_existing = Order.query.get(order_id)
    if not order_id_existing: 
        return jsonify({'message': 'Order ID does\'t exist'}), 400
    product = Product.query.get(product_id)
    product.stock = int(product.stock) - int(quantity) 
    if product.stock < 0:
        return jsonify({'message': 'Not in stock'}), 400
    db.session.add(product)
    total = product.price * int(quantity)
    orderdetails = OrderDetails(quantity=quantity, total=total, product_id=product_id, order_id=order_id)
    db.session.add(orderdetails)
    db.session.commit()
    return jsonify(orderdetails=orderdetails.serialize)

def getAdminOrderDetail(id):
    orderdetail = OrderDetails.query.get(id)
    if not orderdetail:
        return jsonify({'message': 'Order Detail doesn\'t exist'}), 404
    return jsonify(orderdetail=orderdetail.serialize)

def updateAdminOrderDetails(id, quantity, product_id, order_id):
    orderdetail = OrderDetails.query.get(id)
    if not orderdetail:
        return jsonify({'message': 'OrderDetails doesn\'t exist'}), 400
    if quantity:
        if not quantity.isdigit():
            return jsonify({"message": "Quantity should be an integer"}), 400
        previous_quantity = orderdetail.quantity
        delta = int(previous_quantity) - int(quantity)
        if delta > 0:
            product = Product.query.get(orderdetail.product_id)
            product.stock = int(product.stock) - int(delta)
            db.session.add(product)
        elif delta < 0:
            product = Product.query.get(orderdetail.product_id)
            product.stock = int(product.stock) + int(delta)
            db.session.add(product)
            
        orderdetail.quantity = quantity
        product = Product.query.get(orderdetail.product_id)
        orderdetail.total = product.price * int(quantity)
    if product_id:
        product_id_existing = Product.query.get(product_id)
        if not product_id_existing:
            return jsonify({'message': 'Product ID does\'t exist'}), 400
        orderdetail.product_id = product_id
    if order_id:
        order_id_existing = Order.query.get(order_id)
        if not order_id_existing:
            return jsonify({'message': 'Order ID does\'t exist'}), 400
        orderdetail.order_id = order_id
    db.session.add(orderdetail)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated Order Details with ID: {}'.format(id)}), 200)

def deleteAdminOrderDetails(id):
    orderdetail = OrderDetails.query.get(id)
    if not orderdetail:
        return jsonify({'message': 'OrderDetails doesn\'t exist'}), 404
    db.session.delete(orderdetail)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed Order Detail with ID {}'.format(id)}), 200)

# CRUD FUNCTION PAYMENTS
def getAdminPayments():
    payments = Payment.query.all()
    return jsonify(payments=[payment.serialize for payment in payments])

def postAdminPayment(payment_method, order_id):
    payment_id_existing = Payment.query.get(order_id)
    if payment_id_existing:
        return jsonify({'message': "Order ID already exist in Payment"}), 400
    order_id_existing = Order.query.get(order_id)
    if not order_id_existing: 
        return jsonify({'message': "Order ID doesn\'t exist in Order"}), 400
    payment = Payment(payment_method=payment_method, order_id=order_id)
    db.session.add(payment)
    db.session.commit()
    return jsonify(payment=payment.serialize)

def getAdminPayment(id):
    payment = Payment.query.get(id)
    if not payment:
        return jsonify({'message': 'Payment doesn\'t exist'}), 404
    return jsonify(payment=payment.serialize)

def updateAdminPayment(id, payment_method, order_id):
    payment = Payment.query.get(id)
    if not payment:
        return jsonify({'message': 'Payment doesn\'t exist'}), 400
    if payment_method:
        payment.payment_method = payment_method
    if order_id:
        order_id_existing = Order.query.get(order_id)
        if order_id_existing:
            return jsonify({'message': 'Order ID already exist'}), 400
        payment.order_id = order_id
    db.session.add(payment)
    db.session.commit()
    return make_response(jsonify({'message': 'Updated Payment with ID: {}'.format(id)}), 200)

def deleteAdminPayment(id):
    payment = Payment.query.get(id)
    if not payment:
        return jsonify({'message': 'Payment doesn\'t exist'}), 404
    db.session.delete(payment)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed Payment with ID {}'.format(id)}), 200)

# CRUD FUNCTION CARTDETAILS
def getAdminCartDetails():
    cartdetails = CartDetails.query.all()
    return jsonify(cartdetails=[cartdetail.serialize for cartdetail in cartdetails])

def postAdminCartDetails(quantity, product_id, user_id):
    product_id_existing = Product.query.get(product_id)
    if not product_id_existing:
        return jsonify({'message': 'Product ID does\'t exist'}), 400
    user_id_existing = User.query.get(user_id)
    if not user_id_existing:
        return jsonify({'message': 'User ID does\'t exist'}), 400
    cartdetails_existing = CartDetails.query.filter_by(product_id=product_id, user_id=user_id).first()
    if cartdetails_existing:
        cartdetails_existing.quantity = int(cartdetails_existing.quantity) + int(quantity)
        total = cartdetails_existing.quantity * product_id_existing.price
        cartdetails_existing.total = total
        db.session.add(cartdetails_existing)
        db.session.commit()
        return jsonify(cartdetails_existing=cartdetails_existing.serialize)
    total = int(quantity) * product_id_existing.price
    cartdetails = CartDetails(quantity=quantity, total=total, product_id=product_id, user_id=user_id)
    db.session.add(cartdetails)
    db.session.commit()
    return jsonify(cartdetails=cartdetails.serialize)

def getAdminCartDetail(id):
    cartdetail = CartDetails.query.get(id)
    if not cartdetail:
        return jsonify({'message': 'Cart Detail doesn\'t exist'}), 404
    return jsonify(cartdetail=cartdetail.serialize)

def updateAdminCartDetail(id, quantity, product_id, user_id):
    cartdetail = CartDetails.query.get(id)
    if not cartdetail:
        return jsonify({'message': 'Cart Detail doesn\'t exist'}), 400
    if quantity:
        delta = int(cartdetail.quantity) - int(quantity)
        if delta > 0:
            product = Product.query.get(cartdetail.product_id)
            product.stock = int(product.stock) - int(delta)
            db.session.add(product)
            total = int(quantity) * product.price
            cartdetail.total = total
        elif delta <0:
            product = Product.query.get(cartdetail.product_id)
            product.stock = int(product.stock) + int(delta)
            db.session.add(product)
            total = int(quantity) * product.price
            cartdetail.total = total
        cartdetail.quantity = quantity
        
    if product_id:
        cartdetail.product_id = product_id
    if user_id: 
        cartdetail.user_id = user_id
    
    db.session.add(cartdetail)
    db.session.commit()

def deleteAdminCartDetail(id):
    cartdetail = CartDetails.query.get(id)
    if not cartdetail:
        return jsonify({'message': 'Cart Details doesn\'texist'}), 404
    db.session.delete(cartdetail)
    db.session.commit()
    return make_response(jsonify({'message': 'Removed Cart Details with ID {}'.format(id)}), 200)

# --- INFO: REACT FUNCTIONS --- 

@jwt.user_claims_loader
def add_claims_to_access_token(identity):
    user = User.query.filter_by(email=identity).first()
    userdetails = UserDetails.query.filter_by(user_id=user.user_id).first()
    return {
        'email': user.email,
        'first_name' : user.first_name,
        'last_name' : user.last_name,
        'profile_picture' : user.profile_picture,
        'address' : userdetails.address,
        'city' : userdetails.city,
        'state' : userdetails.state,
        'postcode' : userdetails.postcode,
        'country' : userdetails.country,
        'phone' : userdetails.phone,
    }

def login(email, password):
    if not email: 
        return jsonify({"message": "Missing Email"}), 400
    if not password: 
        return jsonify({"message": "Missing Password"}), 400
    user = User.query.filter_by(email=email).first()
    if not user: 
        return jsonify({"message": "User not found"}), 404
    if user.password == '':
        return jsonify({"message": "Account not active, Check your Emails"}), 401
    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Bad email or password"}), 401
    ret = {
        'access_token': create_access_token(identity=email),
    }
    return jsonify(ret), 201

def register(email, first_name, last_name):
    user = User.query.filter_by(email=email).first()
    if user:
        if user.password == '':
            db.session.delete(user)
            db.session.commit()
        else:
            return jsonify({"message": "Email already existing"}), 400

    user = User(email=email, password='', first_name=first_name, last_name=last_name)
    db.session.add(user)
    db.session.commit()

    userdetail = UserDetails(user_id=user.user_id)
    db.session.add(userdetail)
    db.session.commit()

    send_set_email(user)
    return jsonify({"message": "Check " + email + " to set your password"})

def send_set_email(user):
    token = user.get_reset_token()
    msg = Message('Account Activation', sender='templars69@mail.com', recipients=[user.email])
    msg.body = f'''Hello and welcome to our shop,

To activate your account, please visit the following link:

{'https://react-shop-application.herokuapp.com/auth/set/' + token}

Luxury Shop
'''
    try:
        mail.send(msg)
    except: 
        return jsonify({"message": "Mailbox unavailable invalid SMTP"}), 401

def send_reset_email(user):
    token = user.get_reset_token()

    msg = Message('Password Reset Request', sender='templars69@mail.com', recipients=[user.email])
    msg.body = f'''To reset your password, please visit the following link:

{ 'https://react-shop-application.herokuapp.com/auth/set/' + token}

If you did not make this request, simply ignore this email and no changes would be made.

Luxury Shop
'''
    try:
        mail.send(msg)
    except: 
        return jsonify({"message": "Mailbox unavailable invalid SMTP"}), 401

def user_info(email): 
    user = User.query.filter_by(email=email).first()
    if not user: 
        return jsonify({"message": "User not found"}), 404

    return jsonify(user.serialize)

def update(email, content):
    user = User.query.filter_by(email=email).first()
    password = content.get("password", None)
    first_name = content.get("first_name", None)
    last_name = content.get("last_name", None)
    profile_picture = content.get("profile_picture", None)

    if password:
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    if profile_picture:
        user.profile_picture = profile_picture
    
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "{} updated".format(email)}), 200 

def delete(email):
    user = User.query.filter_by(email=email).first()
    if not user: 
        return jsonify({"message": "User not found"}), 401
    userdetails = UserDetails.query.filter_by(user_id=user.user_id).all()
    for userdetail in userdetails:
        db.session.delete(userdetail)
    db.session.delete(user)
    db.session.commit()
    return make_response(jsonify({'Deleted': 'Removed user {}'.format(email)}), 200)

# --- INFO: ROUTES ---

@app.route('/')
def home():
    return render_template('documentation.html', title='Documentation')

# --- INFO: ADMIN ROUTES ---

# CRUD ROUTES CATEGORY
@app.route('/api/admin/categories', methods=['GET', 'POST'])
@jwt_required
def adminCategories():
    isAdmin()
    if request.method == 'GET':
        return getAdminCategories()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400

        content = request.get_json(force=True)
        name = content.get("name", None)
        description = content.get("description", None)
        if not name:
            return jsonify({'message': 'Missing Name'})
        if not description:
            return jsonify({'message': 'Missing Description'})
        return postAdminCategory(name, description)

@app.route('/api/admin/category/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminCategory(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminCategory(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        name = content['name'] if 'name' in content.keys() else ''
        description = content['description'] if 'description' in content.keys() else ''
        return updateAdminCategory(id, name, description)

    if request.method == 'DELETE':
        return deleteAdminCategory(id)

# CRUD ROUTES PRODUCT
@app.route('/api/admin/products', methods=['GET', 'POST'])
@jwt_required
def adminProducts():
    isAdmin()
    if request.method == 'GET':
        return getAdminProducts()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        product_name = content.get("product_name", None)
        product_description = content.get("product_description", None)
        price = content.get("price", None)
        stock = content.get("stock", None)
        images_url = content.get("images_url", None)
        category_id = content.get("category_id", None)
        if not product_name:
            return jsonify({'message': 'Missing Product name'})
        if not product_description:
            return jsonify({'message': 'Missing Product description'})
        if not price:
            return jsonify({'message': 'Missing Price'})
        if not stock:
            return jsonify({'message': 'Missing Stock'})
        if not category_id:
            return jsonify({'message': 'Missing Category ID'})
        return postAdminProduct(product_name, product_description, price, stock, images_url, category_id)

@app.route('/api/admin/product/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminProduct(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminProduct(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        product_name = content['product_name'] if 'product_name' in content.keys() else ''
        product_description = content['product_description'] if 'product_description' in content.keys() else ''
        price = content['price'] if 'price' in content.keys() else ''
        stock = content['stock'] if 'stock' in content.keys() else ''
        images_url = content['images_url'] if 'images_url' in content.keys() else ''
        category_id = content['category_id'] if 'category_id' in content.keys() else ''
        return updateAdminProduct(id, product_name, product_description, price, stock, images_url, category_id)

    if request.method == 'DELETE':
        return deleteAdminProduct(id)

# CRUD ROUTES SHIPPER
@app.route('/api/admin/deliveries', methods=['GET', 'POST'])
@jwt_required
def adminDeliverys():
    isAdmin()
    if request.method == 'GET':
        return getAdminDeliverys()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        status = content.get("status", None)
        company = content.get("company", None)
        phone = content.get("phone", None)
        order_id = content.get("order_id", None)
        if not status:
            return jsonify({'message': 'Missing Status'})
        if not company:
            return jsonify({'message': 'Missing Company'})
        if not phone:
            return jsonify({'message': 'Missing Phone'})
        if not order_id:
            return jsonify({'message': 'Missing Order ID'})
        return postAdminDelivery(status, company, phone, order_id)

@app.route('/api/admin/delivery/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminDelivery(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404 

    if request.method == 'GET':
        return getAdminDelivery(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        status = content['status'] if 'status' in content.keys() else ''
        company = content['company'] if 'company' in content.keys() else ''
        phone = content['phone'] if 'phone' in content.keys() else ''
        order_id = content['order_id'] if 'order_id' in content.keys() else ''
        return updateAdminDelivery(id, status, company, phone, order_id)

    if request.method == 'DELETE':
        return deleteAdminDelivery(id)

# CRUD ROUTES USER
@app.route('/api/admin/users', methods=['GET', 'POST'])
@jwt_required
def adminUsers():
    isAdmin()
    if request.method == 'GET':
        return getAdminUsers()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        email = content.get("email", None)
        password = content.get("password", None)
        first_name = content.get("first_name", None)
        last_name = content.get("last_name", None)
        role = content['role'] if 'role' in content.keys() else ''
        profile_picture = content['profile_picture'] if 'profile_picture' in content.keys() else ''
        address = content['address'] if 'address' in content.keys() else ''
        city = content['city'] if 'city' in content.keys() else ''
        state = content['state'] if 'state' in content.keys() else ''
        postcode = content['postcode'] if 'postcode' in content.keys() else ''
        country = content['country'] if 'country' in content.keys() else ''
        phone = content['phone'] if 'phone' in content.keys() else ''
        if not email:
            return jsonify({'message': 'Missing Company'})
        if not password:
            return jsonify({'message': 'Missing Password'})
        if not first_name:
            return jsonify({'message': 'Missing First Name'})
        if not last_name:
            return jsonify({'message': 'Missing Last Name'})
        return postAdminUser(email, password, first_name, last_name, role, profile_picture, address, city, state, postcode, country, phone)

@app.route('/api/admin/user/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminUser(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminUser(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        email = content['email'] if 'email' in content.keys() else ''
        password = content['password'] if 'password' in content.keys() else ''
        first_name = content['first_name'] if 'first_name' in content.keys() else ''
        last_name = content['last_name'] if 'last_name' in content.keys() else ''
        role = content['role'] if 'role' in content.keys() else ''
        profile_picture = content['profile_picture'] if 'profile_picture' in content.keys() else ''
        address = content['address'] if 'address' in content.keys() else ''
        city = content['city'] if 'city' in content.keys() else ''
        state = content['state'] if 'state' in content.keys() else ''
        postcode = content['postcode'] if 'postcode' in content.keys() else ''
        country = content['country'] if 'country' in content.keys() else ''
        phone = content['phone'] if 'phone' in content.keys() else ''
        return updateAdminUser(id, email, password, first_name, last_name, role, profile_picture, address, city, state, postcode, country, phone)

    if request.method == 'DELETE':
        return deleteAdminUser(id)

# CRUD ROUTES USERDETAILS
@app.route('/api/admin/userdetails', methods=['GET'])
@jwt_required
def adminUserDetails():
    isAdmin()
    return getAdminUserDetails()

@app.route('/api/admin/userdetail/<id>', methods=['GET'])
@jwt_required
def adminUserDetail(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404
    return getAdminUserDetail(id)

# CRUD ROUTES ORDER
@app.route('/api/admin/orders', methods=['GET', 'POST'])
@jwt_required
def adminOrders():
    isAdmin()
    if request.method == 'GET':
        return getAdminOrders()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        order_number = content.get("order_number", None)
        order_details = content.get("order_details", None)
        user_id = content.get("user_id", None)
        if not order_number:
            return jsonify({'message': 'Missing Order Number'})
        if not order_details:
            return jsonify({'message': 'Missing Order Details'})
        if not user_id:
            return jsonify({'message': 'Missing User ID'})
        return postAdminOrder(order_number, order_details, user_id)

@app.route('/api/admin/order/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminOrder(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminOrder(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        order_number = content['order_number'] if 'order_number' in content.keys() else ''
        order_details = content['order_details'] if 'order_details' in content.keys() else ''
        user_id = content['user_id'] if 'user_id' in content.keys() else ''
        return updateAdminOrder(id, order_number, order_details, user_id)

    if request.method == 'DELETE':
        return deleteAdminOrder(id)

# CRUD ROUTES ORDERDETAILS
@app.route('/api/admin/orderdetails', methods=['GET', 'POST'])
@jwt_required
def adminOrderDetails():
    isAdmin()
    if request.method == 'GET':
        return getAdminOrderDetails()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        quantity = content['quantity'] if 'quantity' in content.keys() else ''
        product_id = content['product_id'] if 'product_id' in content.keys() else ''
        order_id = content['order_id'] if 'order_id' in content.keys() else ''
        if not quantity:
            return jsonify({'message': 'Missing Quantity'})
        if not quantity.isdigit():
            return jsonify({"message": "Quantity should be an integer"}), 400
        if not product_id:
            return jsonify({'message': 'Missing Prodcut ID'})
        if not order_id:
            return jsonify({'message': 'Missing Order ID'})
        return postAdminOrderDetails(quantity, product_id, order_id)

@app.route('/api/admin/orderdetail/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminOrderDetail(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminOrderDetail(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        quantity = content['quantity'] if 'quantity' in content.keys() else ''
        product_id = content['product_id'] if 'product_id' in content.keys() else ''
        order_id = content['order_id'] if 'order_id' in content.keys() else ''
        return updateAdminOrderDetails(id, quantity, product_id, order_id)

    if request.method == 'DELETE':
        return deleteAdminOrderDetails(id)

# CRUD ROUTES PAYMENT
@app.route('/api/admin/payments', methods=['GET', 'POST'])
@jwt_required
def adminPayments():
    isAdmin()
    
    if request.method == 'GET':
        return getAdminPayments()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        payment_method = content['payment_method'] if 'payment_method' in content.keys() else ''
        order_id = content['order_id'] if 'order_id' in content.keys() else ''
        if not payment_method:
            return jsonify({'message': 'Missing Payment Method'})
        if not order_id:
            return jsonify({'message': 'Missing Payment Order ID'})
        return postAdminPayment(payment_method, order_id)

@app.route('/api/admin/payment/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminPayment(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminPayment(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        payment_method = content['payment_method'] if 'payment_method' in content.keys() else ''
        order_id = content['order_id'] if 'order_id' in content.keys() else ''
        return updateAdminPayment(id, payment_method, order_id)

    if request.method == 'DELETE':
        return deleteAdminPayment(id)

# CRUD ROUTES CARTDETAILS
@app.route('/api/admin/cartdetails', methods=['GET', 'POST'])
@jwt_required
def adminCartDetails():
    isAdmin()
    if request.method == 'GET':
        return getAdminCartDetails()

    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        quantity = content['quantity'] if 'quantity' in content.keys() else ''
        product_id = content['product_id'] if 'product_id' in content.keys() else ''
        user_id = content['user_id'] if 'user_id' in content.keys() else ''
        if not quantity:
            return jsonify({'message': 'Missing Quantity'})
        if not product_id:
            return jsonify({'message': 'Missing Product ID'})
        if not user_id:
            return jsonify({'message': 'Missing User ID'})
        return postAdminCartDetails(quantity, product_id, user_id)

@app.route('/api/admin/cartdetail/<id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def adminCartDetail(id):
    isAdmin()
    if not id: 
        return jsonify({"message": "Missing ID Parameter"}), 404

    if request.method == 'GET':
        return getAdminCartDetail(id)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        quantity = content['quantity'] if 'quantity' in content.keys() else ''
        product_id = content['product_id'] if 'product_id' in content.keys() else ''
        user_id = content['user_id'] if 'user_id' in content.keys() else ''
        return updateAdminCartDetail(id, quantity, product_id, user_id)

    if request.method == 'DELETE':
        return deleteAdminCartDetail(id)

# --- INFO: REACT JWT ROUTES ---

@app.route('/api/login', methods=['POST'])
def user_login():
    if not request.is_json: 
        return jsonify({"message": "Missing JSON in request"}), 400
    content = request.get_json(force=True)
    email = content.get("email", None)
    password = content.get("password", None)
    return login(email, password)

@app.route('/api/register', methods=['POST'])
def user_register():
    if not request.is_json: 
        return jsonify({"message": "Missing JSON in request"}), 400

    content = request.get_json(force=True)
    email = content.get("email", None)
    first_name = content.get("first_name", None)
    last_name = content.get("last_name", None)

    if not email:
        return jsonify({"message": "Missing Email"}), 400
    if not first_name:
        return jsonify({"message": "Missing First name"}), 400
    if not last_name:
        return jsonify({"message": "Missing Last name"}), 400

    return register(email, first_name, last_name)

@app.route('/api/forgot', methods=['POST'])
def forgot_password():
    if not request.is_json: 
        return jsonify({"message": "Missing JSON in request"}), 400

    email = request.get_json(force=True)
    user = User.query.filter_by(email=email).first()
    if not user: 
        return jsonify({"message": "Email doesn\'t exist"}), 401

    send_reset_email(user)
    return jsonify({"message": "Email Sucessfully sent to "+ email})

@app.route('/api/set_password', methods=['POST'])
def set_password():
    if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400

    content = request.get_json(force=True)
    password = content.get("password", None)
    token = content.get("token", None)
    
    if not password:
        return jsonify({"message": "Missing Password"}), 400
    if not token:
        return jsonify({"message": "Missing Token"}), 400

    user = User.verify_reset_token(token)
    if not user:
        return jsonify({"message": "Invalid Token. Token is either invalid or expired"}), 400
    
    user.password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Password Updated"}), 200 

@app.route('/api/user', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def user_update():
    email = get_jwt_identity()
    if not email: 
        return jsonify({"message": "Missing Email in Token"}), 400

    if request.method == 'GET':
        return user_info(email)

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        return update(email, content)

    if request.method == "DELETE":
        return delete(email)

@app.route('/api/userdetails', methods=['GET', 'POST'])
@jwt_required
def userdetails():
    email = get_jwt_identity()
    if not email: 
        return jsonify({"message": "Missing Email in Token"}), 400
    user = User.query.filter_by(email=email).first()
    if not user: 
        return jsonify({"message": "User doesn\'t exist"}), 404

    if request.method == "GET":
        userdetails = UserDetails.query.filter_by(user_id=user.user_id).all()
        return jsonify([userdetail.serialize for userdetail in userdetails])
    
    if request.method == "POST":
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        address = content.get("address", None)
        city = content.get("city", None)
        state = content.get("state", None)
        postcode = content.get("postcode", None)
        country = content.get("country", None)
        phone = content.get("phone", None)

        if not address:
            return jsonify({"message": "Missing address"}), 400
        if not city:
            return jsonify({"message": "Missing city"}), 400
        if not state:
            return jsonify({"message": "Missing state"}), 400
        if not postcode:
            return jsonify({"message": "Missing postcode"}), 400
        if not country:
            return jsonify({"message": "Missing country"}), 400
        if not phone:
            return jsonify({"message": "Missing phone"}), 400

        userdetail = UserDetails(address=address, city=city, state=state, postcode=postcode, country=country, phone=phone, user_id=user.user_id)
        db.session.add(userdetail)
        db.session.commit()
        return jsonify(userdetail.serialize)

@app.route('/api/userdetail/<user_details_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required
def userdetail_id(user_details_id):
    email = get_jwt_identity()
    if not email: 
        return jsonify({"message": "Missing Email in Token"}), 400
    user = User.query.filter_by(email=email).first()
    if not user: 
        return jsonify({"message": "User doesn\'t exist"}), 404
    userdetail = UserDetails.query.get(user_details_id)
    if not userdetail:
            return jsonify({"message": 'UserDetails doesn\'t exist'}), 404
    if userdetail.user_id != user.user_id:
        return jsonify({"message": 'Not Authorized'}), 400

    if request.method == "GET":
        return jsonify(userdetail.serialize)

    if request.method == "PUT":
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        address = content.get("address", None)
        city = content.get("city", None)
        state = content.get("state", None)
        postcode = content.get("postcode", None)
        country = content.get("country", None)
        phone = content.get("phone", None)
        if address:
            userdetail.address = address
        if city:
            userdetail.city = city
        if state:
            userdetail.state = state
        if postcode:
            userdetail.postcode = postcode
        if country:
            userdetail.country = country
        if phone:
            userdetail.phone = phone
        db.session.add(userdetail)
        db.session.commit()
        return jsonify({"message": "userdetail {} updated".format(user_details_id)}), 200 

    if request.method == "DELETE":
        db.session.delete(userdetail)
        db.session.commit()
        return make_response(jsonify({'message': 'Removed userdetail ID {}'.format(user_details_id)}), 200)
    
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify(categories=[category.serialize for category in categories])

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([product.serialize for product in products])

@app.route('/api/products/<filter>', methods=['GET'])
def get_products_filter(filter):
    products = []
    categories = Category.query.filter_by(gender=filter).all()
    for category in categories:
        products += Product.query.filter_by(category_id=category.category_id).all()
    return jsonify([product.serialize for product in products])

@app.route('/api/product/<product_id>', methods=['GET'])
def get_product(product_id):
    if not product_id:
        return jsonify({'message': 'Product ID missing'}), 404
    product = Product.query.get(product_id)
    if not product: 
        return jsonify({'message': 'Product doesn\'t exist'}), 404
    return jsonify(product.serialize)

@app.route('/api/orders', methods=['GET'])
@jwt_required
def get_order():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Email not found from Token'}), 404
    orders = Order.query.filter_by(user_id=user.user_id).all()
    if not orders:
        return jsonify({'message': 'No orders for {}'.format(email)})

    order_info = []
    count_order = 1
    for order in orders:
        total_order = 0
        order_info.append({'order_number': order.order_number, 'order_details': order.order_details, 'products': []})

        delivery = Delivery.query.filter_by(order_id=order.order_id).first()
        if delivery:
            dict_delivery = {'delivery_company': delivery.company, 'delivery_phone': delivery.phone, 'delivery_status': delivery.status}
            order_info[count_order-1].update(dict_delivery)

        payment = Payment.query.filter_by(order_id=order.order_id).first()
        if payment:
            dict_payment = {'payment_method': payment.payment_method, 'payment_date': payment.payment_date}
            order_info[count_order-1].update(dict_payment)

        count_details = 0
        orderdetails = OrderDetails.query.filter_by(order_id=order.order_id).all()
        if orderdetails:
            for orderdetail in orderdetails:
                dict_orderdetails = {'quantity': orderdetail.quantity, 'total_product': orderdetail.total}
                order_info[count_order-1]['products'].append(dict_orderdetails)

                product = Product.query.get(orderdetail.product_id)
                if product:
                    dict_product= {'product_name': product.product_name, 'product_description': product.product_description, 'unit_price': product.price, 'stock': product.stock, 'image_url': product.images_url}
                    order_info[count_order-1]['products'][count_details].update(dict_product)
                
                category = Category.query.get(product.category_id)
                if category:
                    dict_category = {'category_name': category.name, 'category_description': category.description}
                    order_info[count_order-1]['products'][count_details].update(dict_category)
                
                total_order += orderdetail.total
                count_details += 1
            order_info[count_order-1].update(total_order= total_order)
            count_order += 1
    return jsonify(order_info)

@app.route('/api/cart', methods=['GET', 'POST'])
@jwt_required
def get_cart():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    if not user:
         return jsonify({'message': 'Email not found from Token'}), 404

    if request.method == 'GET':
        cartdetails = CartDetails.query.filter_by(user_id=user.user_id).all()
        if not cartdetails:
            return jsonify({'message': 'Cart is empty'})
        
        cart_info = []
        count = 0
        total_cart = 0
        for cartdetail in cartdetails:
            cart_info.append({'cart_id': cartdetail.cart_id,  'quantity': cartdetail.quantity, 'total_product': cartdetail.total})
            total_cart += cartdetail.total
            
            product = Product.query.get(cartdetail.product_id)
            if product:
                    dict_product={'product_id': product.product_id, 'product_name': product.product_name, 'product_description': product.product_description, 'unit_price': product.price, 'stock': product.stock, 'images_url': product.images_url}
                    cart_info[count].update(dict_product)

            category = Category.query.get(product.category_id)
            if category:
                    dict_category={'category_name': category.name, 'category_description': category.description}
                    cart_info[count].update(dict_category)

            count += 1
        cart_info.append({'total_cart': total_cart})
        return jsonify(cart_info)
          
    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        quantity = content['quantity'] if 'quantity' in content.keys() else ''
        product_id = content['product_id'] if 'product_id' in content.keys() else ''
        if not quantity:
            return jsonify({'message': 'Missing Quantity'})
        if not product_id:
            return jsonify({'message': 'Missing Product ID'})

        return postAdminCartDetails(quantity, product_id, user.user_id)

@app.route('/api/cart/<cart_id>', methods=['PUT', 'DELETE'])
@jwt_required
def cart_id(cart_id):
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    if not user:
         return jsonify({'message': 'Email not found from Token'}), 404
    cartdetail = CartDetails.query.get(cart_id)
    if not cartdetail:
         return jsonify({'message': 'Cart is empty'})
    if user.user_id != cartdetail.user_id:
            return jsonify({'message': 'Unauthorized user'}), 401

    if request.method == 'PUT':
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400
        content = request.get_json(force=True)
        quantity = content.get("quantity", None)
        if not quantity:
            return jsonify({"message": "Missing Quantity in request"}), 400
        
        product = Product.query.get(cartdetail.product_id)
        total = int(quantity) * product.price
        cartdetail.total = total
        cartdetail.quantity = quantity
        db.session.add(cartdetail)
        db.session.commit()
        return make_response(jsonify({'message': 'Cart updated'}), 200)

    if request.method == 'DELETE':
       
        db.session.delete(cartdetail)
        db.session.commit()
        return make_response(jsonify({'message': 'Product removed'}), 200)
        
@app.route('/api/pay', methods=['GET', 'POST'])
@jwt_required
def pay():
    email = get_jwt_identity()

    if not request.is_json:
                return jsonify({"message": "Missing JSON in request"}), 400

    content = request.get_json(force=True)

    delivery = content['delivery'] if 'delivery' in content.keys() else ''
    cart = content['cart'] if 'cart' in content.keys() else ''
    total = content['total'] if 'total' in content.keys() else ''

    if not delivery:
        return jsonify({'message': 'Missing Delivery'})
    if not cart:
        return jsonify({'message': 'Missing Cart'})
    if not total:
        return jsonify({'message': 'Missing Total'})

    total_back = 0
    for elem in cart: 
        quantity = int(elem['quantity'])
        unit_price = int(elem['unit_price'])
        total_back += unit_price * quantity

    if (total == total_back):
        intent = stripe.PaymentIntent.create(
        amount=total*100,
        currency="usd",
        receipt_email= email,
        payment_method_types=["card"],
        )
        return jsonify(client_secret=intent.client_secret), 200
    return jsonify({"message": "Amount Issue, Transaction Cancelled."}), 200

@app.route('/api/order', methods=['POST'])
@jwt_required
def order():
    email = get_jwt_identity()

    if not request.is_json:
                return jsonify({"message": "Missing JSON in request"}), 400

    content = request.get_json(force=True)
    cart = content['cart'] if 'cart' in content.keys() else ''
    payment = content['payment'] if 'payment' in content.keys() else ''
    total = content['total'] if 'total' in content.keys() else ''

    if not payment:
        return jsonify({'message': 'Missing Payment'}), 400
    if not cart:
        return jsonify({'message': 'Missing Cart'}), 400
    if not total:
        return jsonify({'message': 'Missing Total'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'User does\'t exist'}), 404
    
    order_number = ''.join(random.choices(string.digits, k=8))
    order_details = 'Order number {} for {}'.format(order_number, user.email)

    order = Order(order_number=order_number, order_details=order_details, user_id=user.user_id)
    db.session.add(order)

    for cart_id in cart:
        orderdetail = CartDetails.query.get(cart_id['cart_id'])
        orderdetails = OrderDetails(quantity=orderdetail.quantity, total=orderdetail.total, product_id=orderdetail.product_id, order_id=order.order_id)
        db.session.add(orderdetails)

    delivery = Delivery(status='pending', company='UPS', phone='0601942777', order_id=order.order_id)
    db.session.add(delivery)
    
    pay = Payment(payment_stripe_number=payment['id'], payment_method=payment['payment_method_types'][0], payment_method_number=payment['payment_method'], amount=payment['amount'], currency=payment['currency'], status=payment['status'], order_id=order.order_id)
    db.session.add(pay)

    # Delete Existing Cart for User
    cartdetails = CartDetails.query.filter_by(user_id=user.user_id).all()
    for cartdetail in cartdetails:
        db.session.delete(cartdetail)

    db.session.commit()

    return jsonify({'order_number': order_number, 'payment_stripe_number': pay.payment_stripe_number, 'payment_method': pay.payment_method, 'payment_status': pay.status, 'delivery_company': delivery.company, 'delivery_status': delivery.status, 'delivery_contact': delivery.phone})

if __name__ == '__main__':
    app.run(debug=True)