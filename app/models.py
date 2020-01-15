from flask_restplus import Model, fields

# Used as a base model to create member
PartialMember = Model('PartialMember', {
    # Should be changed to name
    'realName': fields.String(required=True),
    'email': fields.String(required=True),
    'phone': fields.String,  # Should be changed to INTEGER or empty
    'classof': fields.String(required=True),
    'graduated': fields.Boolean(required=True)
})

# Used to respond with a detailed model
Member = PartialMember.clone('Member', {
    'id': fields.Integer,
    '_id': fields.String,
    'roles': fields.List(fields.String),
    'status': fields.String,
})

loginModel = Model('loginModel', {
    'email': fields.String(required=True),
    'password': fields.String(required=True)})

tokenModel = Model('tokenModel', {
    'token': fields.String,
    'refreshToken': fields.String
})
