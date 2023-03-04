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

ignore_empty = plugins.toolkit.get_validator('ignore_empty')


def convert(): 
    
    resource_id = request.form.get('resource_id')    
    rsc = toolkit.get_action('resource_show')({}, {'id': resource_id})
    upload = uploader.get_resource_uploader(rsc)
    filepath = upload.get_path(rsc['id'])

    outImg = stretchImg(filepath )
    return outImg



#百分比拉伸
def stretchImg(imgPath):
    outImg= None
    with rasterio.open(imgPath) as dataset:
        img=dataset.read()[0]
        img[img == dataset.nodata] = np.nan  # Convert NoData to NaN
        vmin, vmax = np.nanpercentile(img, (5,95))  # 5-95% stretch
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
    