from os import read
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from six import text_type
from flask import Blueprint, request
import ckan.lib.helpers as h
from PIL import Image
import io
import ckan.lib.uploader as uploader
import base64
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform
from matplotlib import pyplot
from logging import getLogger
from matplotlib import cm
import os

log = getLogger(__name__)

ignore_empty = plugins.toolkit.get_validator('ignore_empty')


def convert(): 
    
    resource_id = request.form.get('resource_id')    
    rsc = toolkit.get_action('resource_show')({}, {'id': resource_id})
    log.info("rsc is {}".format(rsc))
    upload = uploader.get_resource_uploader(rsc)
    log.info("upload is {}".format(upload))
    tmp_name = "/tmp/resources_"+rsc['id']+"_"+rsc['url'].split('/')[-1]
    if os.path.exists(tmp_name):
        log.info("has tmp image")
        outImg = stretchImg1(tmp_name)
        return outImg
    else:
        upload.get_object_to_file("resources/"+rsc['id']+"/"+rsc['url'].split('/')[-1],tmp_name)
        outImg = stretchImg1(tmp_name)
        return outImg



#百分比拉伸
def stretchImg(imgPath):
    outImg= None
    with rasterio.open(imgPath) as dataset:
        img=dataset.read()[0]
        img[img == dataset.nodata] = np.nan  # Convert NoData to NaN
        vmin, vmax = np.nanpercentile(img, (5,95))  # 5-95% stretch
        log.info('vmin is {}, vmax is {}'.format(vmin,vmax))
        pyplot.imshow(img, cmap='viridis', vmin=vmin, vmax=vmax)
        with io.BytesIO() as buffer:
            pyplot.savefig(buffer, format='jpg')
            buffer.seek(0)
            # 读取图像数据并将其编码为Base64字符串
            img_data = buffer.getvalue()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
        outImg = img_base64
    return outImg
    # outImg.save(resultPath)

#百分比拉伸
def stretchImg1(imgPath, lower_percent=20, higher_percent=80):
    outImg= None
    log.info('imgPath is {}'.format(imgPath))

    with rasterio.open(imgPath) as dataset:
        img=dataset.read()[0]
        img[img == dataset.nodata] = np.nan 
        out = np.zeros_like(img, dtype=np.uint8)
        a = 0 
        b = 255
        log.info('lower_percent is {}'.format(lower_percent))
        c = np.nanpercentile(img, lower_percent)
        log.info('c is {}'.format(str(c)))
        d = np.nanpercentile(img, higher_percent)
        t = a + (img - c) * (b - a) / (d - c)
        t[t < a] = a
        t[t > b] = b
        out= np.nan_to_num(t)
        outImg=Image.fromarray(np.uint8(out))
        buffer = io.BytesIO()
        outImg.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        # log.info('img_base64 is {}'.format(img_base64))

    outImg = img_base64    
    return outImg

   

class TifImageviewPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceView, inherit=True)
    plugins.implements(plugins.IBlueprint)



    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'theme/templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'tif_imageview')
        self.formats = config_.get(
            'ckan.preview.image_formats',
            'tiff tif TIFF').split()
        
        
    def info(self):
        return {'name': 'tif_imageview',
            'title': plugins.toolkit._('TIF Viewer'),
            'schema': {'tif_url': [ignore_empty, text_type]},
            'iframed': False,
            'icon': 'link',
            'always_available': True,
            'default_title': plugins.toolkit._('TIF Viewer'),
        }
    
    def can_view(self, data_dict):
        resource = data_dict['resource']
        return (resource.get('format', '').lower() in ['tif', 'tiff' ] or
                resource['url'].split('.')[-1] in ['tif'])

    def view_template(self, context, data_dict):
        return 'tif_view.html'

    def form_template(self, context, data_dict):
        return 'tif_form.html'

    def get_blueprint(self):

        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        blueprint.add_url_rule(
            u'/tif_view/convert',
            u'convert',
            convert,
            methods=['POST']
            )
        
        return blueprint
    
if __name__=='__main__':
    filepath='/mnt/temp/soil_moister/SMY2003DECA01.tif'
    # filepath='/var/lib/ckan/resources/b8a/668/f8-8b19-4cfc-88c8-ce7834cbbedc'
    