from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True лише для локальної розробки
    app.run(debug=True)
