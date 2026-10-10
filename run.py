from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

@app.route('/')

def index():
    return "Hello World"

if __name__ ==  "__main__":
    app.run(debug=True);
