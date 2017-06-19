import boto3
from chalice import Chalice
import configparser
import json
import os
import uuid

config = configparser.ConfigParser()
config.read ("{0}\app.ini".format(os.path.dirname(__file__)))

BUCKET = 'zippy1981'
PNG_MIME_TYPE = 'image/png'
PNG_TEMPLATE_PATH = "{0}\..\png_template.html".format(os.path.dirname(__file__))
S3 = boto3.client('s3', region_name='us-east-1')

app = Chalice(app_name='src')
app.debug = True

@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/status', methods=['GET'])
def status():
    """
    >>> status()
    'OK'

    :return: OK
    """
    return 'OK'


@app.route('/piper')
def processFeed():
    raise NotImplementedError('I need to finish writing this')

@app.route('/png', methods=['POST'], content_types=['image/png'])
def pushPng():
    request = app.current_request
    key = uuid.uuid4()
    png_file = "{0}.png".format(key)
    html_file = "{0}.html".format(key)
    S3.put_object(
        Bucket=BUCKET,
        Key=png_file,
        Body=request.raw_body,
        ACL='public-read',
        ContentDisposition='inline',
        ContentType='image/png'
    )
    with open(PNG_TEMPLATE_PATH, 'r') as template:
        html = template.read().format(BUCKET, png_file)
        S3.put_object(
            Bucket=BUCKET,
            Key=html_file,
            Body=html,
            ACL='public-read',
            ContentDisposition='inline',
            ContentType='text/html'
        )
    return {
        'png_url': "https://s3.amazonaws.com/{0}/{1}".format(BUCKET, png_file),
        'html_url': "https://s3.amazonaws.com/{0}/{1}".format(BUCKET, html_file)
    }

