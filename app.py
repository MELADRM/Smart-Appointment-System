"""SmartBook Pro entry point."""

from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    return 'Smart Appointment Booking System'


if __name__ == '__main__':
    app.run(debug=True, port=5000)
