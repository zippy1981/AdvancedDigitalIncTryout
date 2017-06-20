import boto3
from chalice import Chalice, BadRequestError
import imghdr
from ipaddress import ip_address
from png import png
import os
from time import localtime, time
import urllib.request
import uuid

BUCKET = 'zippy1981'
PNG_MIME_TYPE = 'image/png'
PNG_TEMPLATE_PATH = "{0}\..\png_template.html".format(os.path.dirname(__file__))
S3 = boto3.client('s3', region_name='us-east-1')

app = Chalice(app_name='src')
app.debug = True

def get_html_url(html_file):
    return "https://s3.amazonaws.com/{0}/{1}".format(BUCKET, html_file)

def get_latitude_from_ip(ip_addr):
    """
    Using a simple cross multplying algorithm to convert your ipv4 address into a latitude 0.0.0.0 becomes
    :param ip_addr: Ip address in any form castable by ipaddress.ip_address
    :return: a longitude between -90 and 90
    """
    ip_int = float(int(ip_address(ip_addr)))
    return 90.0-((180.0*ip_int) / (float(2 ** 32)))


def get_get_longitude_from_time(time_stamp = None):
    """
    Converts the hours and minues in a timestamp to a latitude.
    :param time_stamp: Unix timestamp
    :return: A latitude between -180 and 180
    """
    if time_stamp is None:
        time_stamp = time()
    time_s = localtime(time_stamp)
    longitude = (float)(time_s.tm_hour * 15.0)
    longitude += (float)(time_s.tm_min)/60.0
    longitude -= 180
    return longitude

def get_png_dimensions(file_name):
    # Some kind of splatting could probably avoid the need to set this explicitly
    reader = png.Reader(bytes=file_name)
    img = reader.read()
    return {
        'length': img[0],
        'width': img[1]
    }

def get_png_url(file_name):
    return "https://s3.amazonaws.com/{0}/{1}".format(BUCKET, file_name)

def get_osm_static_map_url(client_ip, zoom = 7):
    return "http://staticmap.openstreetmap.de/staticmap.php?center={0},{1}&zoom={2}&size=400x200&maptype=mapnik" \
        .format(get_latitude_from_ip(client_ip), get_get_longitude_from_time(), zoom)
def generate_template(png_file, dimensions):
    with open(PNG_TEMPLATE_PATH, 'r') as template:
        return template.read().format(BUCKET, png_file, dimensions['length'], dimensions['width'])

def scale_dimensions(dimensions, max_dimension):
    if (dimensions['length'] <= max_dimension and dimensions['width'] <= max_dimension):
        return dimensions
    elif (dimensions['length'] == dimensions['width']):
        return {
            'length' : max_dimension,
            'width' : max_dimension,
        }
    elif (dimensions['length'] > dimensions['width']):
        return {
            'length' : max_dimension,
            'width' : (dimensions['width'] * max_dimension)/dimensions['length'],
        }
    else:
        return {
            'width': max_dimension,
            'length': (dimensions['length'] * max_dimension) / dimensions['width'],
        }


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


@app.route('/map')
def process_feed():
    client_ip = app.current_request.context['identity']['sourceIp']
    service_url = get_osm_static_map_url(client_ip)

    file_name = "{0}.png".format(uuid.uuid4())



    S3.put_object(
        Bucket=BUCKET,
        Key=file_name,
        Body=urllib.request.urlopen(service_url).read(),
        ACL='public-read',
        ContentDisposition='inline',
        ContentType='image/png'
    )

    return {
        'service_url': service_url,
        's3_url': get_png_url(file_name)
    }

@app.route('/png', methods=['POST'], content_types=['image/png'])
@app.route('/png/{max_scale_dimension}', methods=['POST'], content_types=['image/png'])
def push_png(max_scale_dimension=100):
    request = app.current_request
    actual_image_type = imghdr.what(None, h=request.raw_body)
    if actual_image_type != 'png':
        raise BadRequestError("Type of uploaded image is not png. [ actual = {0}]".format(actual_image_type))

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

    dimensions = get_png_dimensions(request.raw_body)
    scaled_dimensions = scale_dimensions(dimensions, int(max_scale_dimension))
    html = generate_template(png_file, scaled_dimensions)
    S3.put_object(
        Bucket=BUCKET,
        Key=html_file,
        Body=html,
        ACL='public-read',
        ContentDisposition='inline',
        ContentType='text/html'
    )
    return {
        'png_url': get_png_url(png_file),
        'html_url': get_html_url(html_file)
    }

if __name__ == "__main__":
    response = urllib.request.urlopen('https://www.gstatic.com/webp/gallery3/3.png')
    print(response)
    dimensions = get_png_dimensions(response.read())
    print(scale_dimensions(dimensions, 50))
    print(scale_dimensions(dimensions, 500))
    print(scale_dimensions(dimensions, 600))
    print(scale_dimensions(dimensions, 800))
    print(scale_dimensions(dimensions, 1000))
    print(get_latitude_from_ip('0.0.0.0'))
    print(get_latitude_from_ip('127.0.0.1'))
    print(get_latitude_from_ip('255.255.255.255'))
    print("Longitude: {0}".format(get_get_longitude_from_time()))