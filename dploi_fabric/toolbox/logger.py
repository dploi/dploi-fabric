# -*- coding: utf-8 -*-
class Logger():
    """
    Capture print statements and write them to a variable
    but still allow them to be printed on the screen.
    You can also redirect multiple streams into one Logger.
    """

    def __init__(self, stream):
        self.stream = stream
        self.log = ""

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def write(self, text):
        self.stream.write(text)
        self.log += str(text)

    def get_log(self):
        return self.log

    def clear(self):
        self.log = ""
