from flask import Flask
from flasgger import Swagger
from routes.authentication import auth_blueprint
from routes.kong import kong_blueprint
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.register_blueprint(auth_blueprint)
app.register_blueprint(kong_blueprint)

swagger = Swagger(app)
if __name__ == "__main__":
    app.run(port=5005, debug=True)
