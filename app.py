from flask import Flask
from tasks import botprogram

class MyServer(Flask):

    def __init__(self, *args, **kwargs):
            super(MyServer, self).__init__(*args, **kwargs)

            self.start = 0

app = MyServer(__name__)

botprogram.delay()
@app.route('/')
def index():

    return 'Start'

if __name__ == "__main__":
    app.run()
