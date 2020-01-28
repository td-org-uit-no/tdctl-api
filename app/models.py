from flask_restplus import Model, fields

# Used as a base model to create member
PartialMember = Model('PartialMember', {
    'realName': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String(required=True),
    'classof': fields.String(required=True),
    'graduated': fields.Boolean(required=True),
    'phone': fields.String
})

# Used to represent the member
Member = Model('Member', {
    '_id': fields.String(required=True),
    'realName': fields.String(required=True),
    'email': fields.String(required=True),
    'classof': fields.String(required=True),
    'graduated': fields.Boolean(required=True),
    'phone': fields.String,
    'roles': fields.List(fields.String),
    'status': fields.String,
})

Login = Model('Login', {
    'email': fields.String(required=True),
    'password': fields.String(required=True)})


RefreshToken = Model('RefreshToken', {'refreshToken': fields.String})

Tokens = RefreshToken.clone('Tokens', {'token': fields.String})
