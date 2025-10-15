import bpy, mathutils, os, pickle

class _Settings:
    def __init__(self):
        self.dir = None
        self.name = None
        self.b_export = False

class VActIOTransform:
    def do_execute(self, context, settings):
        _blend_filepath = bpy.data.filepath;
        _dir_name = settings.dir if settings.dir else os.path.dirname(_blend_filepath)
        _file_name = settings.name if settings.name else os.path.splitext(os.path.basename(_blend_filepath))[0] + '.bpy'
        _filepath = os.path.join(_dir_name, _file_name)
        
        
        if settings.b_export:   
            with open(_filepath, "wb") as file:
                _transforms = {}
                for item in context:
                    _transforms[item.name] = [list(x) for x in item.matrix_world] 
                pickle.dump(_transforms, file)
        else:
            with open(_filepath, "rb") as file:
                _transforms = pickle.load(file)
                for k, v in _transforms.items():
                    _item = bpy.data.objects[k]
                    if _item: _item.matrix_world = mathutils.Matrix(v)

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActIOTransform()
operator.do_execute(selection, settings)