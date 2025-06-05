import jwt

token = jwt.encode({"sub": "usuario1234", "exp": 9999999999}, "tu_clave_super_secreta", algorithm="HS256")
print(token)
