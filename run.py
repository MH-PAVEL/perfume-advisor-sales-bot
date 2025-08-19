from app import create_app

app = create_app()


@app.route('/flask/')
def home():
    return "Flask is running!"


if __name__ == "__main__":
    app.run(debug=True, port=5500)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5500)
