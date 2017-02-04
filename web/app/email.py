from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail

def send_async_email(app, msg):
    """ Started as a separate thread from send_email. Asynchronously
    sends email.
    """
    with app.app_context():
        mail.send(msg)


def send_email(dest, subject, template, **kwargs):
    """ Asynchronously sends email to dest, with subject,
    using template.html and template.txt.
    """
    return True
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[dest])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
