from flask_restplus import Model, fields

# Used as a base model to create member
PartialMember = Model('PartialMember', {
    # Should be changed to name? We dont work with nicknames
    'realName': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String(required=True),
    'classof': fields.String(required=True),
    'graduated': fields.Boolean(required=True),
    'phone': fields.String
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
