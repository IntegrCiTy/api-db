import datetime

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from marshmallow import Schema, fields, ValidationError, pre_load, validate

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/quotes.db"
db = SQLAlchemy(app)

##### MODELS #####

units = ["kW", "Nm3/s", "degC", "m3/s"]


class Model(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	name = db.Column(db.String(80))
	tool = db.Column(db.String(80))
	wrap = db.Column(db.String(80))


class Node(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	name = db.Column(db.String(80))

	model_id = db.Column(db.Integer, db.ForeignKey("model.id"))
	model = db.relationship("Model", backref=db.backref("nodes", lazy="dynamic"))


class Attribute(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	unit = db.Column(db.Enum(*units))
	vector = db.Column(db.String(80))
	port = db.Column(db.Enum("in", "out"))

	node_id = db.Column(db.Integer, db.ForeignKey("node.id"))
	node = db.relationship("Node", backref=db.backref("attributes", lazy="dynamic")) 


class Link(db.Model):
	id = db.Column(db.Integer, primary_key=True)

	attr_get_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
	attr_get = db.relationship("Attribute",
		foreign_keys=[attr_get_id],
		backref=db.backref("link_in", lazy="dynamic"))

	attr_set_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
	attr_set = db.relationship("Attribute",
		foreign_keys=[attr_set_id],
		backref=db.backref("link_out", lazy="dynamic"))


##### SCHEMA #####


class ModelSchema(Schema):
	id = fields.Int(dump_only=True)

	name = fields.Str()
	tool = fields.Str()
	wrap = fields.Str()


class NodeSchema(Schema):
	id = fields.Int(dump_only=True)

	name = fields.Str(required=True)
	model_name = fields.Str(required=True)


class AttributeSchema(Schema):
	id = fields.Int(dump_only=True)

	unit = fields.Str(required=True, validate=validate.OneOf(units))
	vector = fields.Str(required=True)
	port = fields.Str(required=True, validate=validate.OneOf(["in", "out"]))

	node = fields.Nested(NodeSchema, required=True)


class LinkSchema(Schema):
	id = fields.Int(dump_only=True)

	attr_get = fields.Nested(AttributeSchema, required=True)	
	attr_set = fields.Nested(AttributeSchema, required=True)	


model_schema = ModelSchema()
models_schema = ModelSchema(many=True)
node_schema = NodeSchema()
nodes_schema = NodeSchema(many=True)
attribute_schema = AttributeSchema()
attributes_schema = AttributeSchema(many=True)
link_schema = LinkSchema()
links_schema = LinkSchema(many=True)


##### API #####


@app.route("/models")
def get_models():
	models = Model.query.all()
	results = models_schema.dump(models)
	return jsonify({"models": results.data})

@app.route("/models/<string:m_name>")
def get_model(m_name):
	try:
		model = Model.query.filter_by(name="m_name").first()
	except IntegrityError:
		return jsonify({"message": "Model could not be found."}), 400
	result_model = model_schema.dump(model)
	result_nodes = nodes_schema.dump(model.nodes.all())
	return jsonify({"model": result_model.data, "nodes": result_nodes.data})

@app.route("/nodes")
def get_nodes():
	nodes = Node.query.all()
	results = nodes_schema.dump(nodes)
	return jsonify({"nodes": results.data})

@app.route("/nodes/<string:m_name>")
def get_node(n_name):
	try:
		node = Node.query.filter_by(name="n_name").first()
	except IntegrityError:
		return jsonify({"message": "Node could not be found."}), 400
	result_node = node_schema.dump(node)
	result_attrs = attributes_schema.dump(node.attributes.all())
	return jsonify({"node": result_node.data, "nodes": result_attrs.data})

@app.route("/links")
def get_links():
	links = Links.query.all()
	results = links_schema.dump(links)
	return jsonify({"links": results.data})

@app.route("/models/", methods=["POST"])
def new_model():
	json_data = request.get_json()
	if not json_data:
		return jsonify({"message": "No input data provided"}), 400
	data, errors = model_schema.load(json_data)
	if errors:
		return jsonify(errors), 422
	model = Model(
		name = data["name"],
		tool = data["tool"],
		wrap = data["wrap"]
	)
	db.session.add(model)
	db.session.commit()
	result = model_schema.dump(Model.query.get(model.id))
	return jsonify({"message": "Created new model.", "model": result.data})

@app.route("/nodes/", methods=["POST"])
def new_node():
	json_data = request.get_json()
	if not json_data:
		return jsonify({"message": "No input data provided"}), 400
	data, errors = node_schema.load(json_data)
	if errors:
		return jsonify(errors), 422
	model = Model.query.filter_by(name=data["model_name"]).first()

	node = Node(
		name = data["name"],
		model = model
	)
	db.session.add(node)
	db.session.commit()
	result = node_schema.dump(Node.query.get(node.id))
	return jsonify({"message": "Created new node.", "node": result.data, "model_name": model.name})


if __name__ == '__main__':
	db.create_all()
	app.run(debug=True, host='0.0.0.0', port=5000)
